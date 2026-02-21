"""Extended tests for kanibako.commands.clean: decentralized mode + workset support."""

from __future__ import annotations

import argparse

import pytest

from kanibako.config import load_config
from kanibako.paths import load_std_paths, resolve_project, resolve_workset_project
from kanibako.workset import add_project, create_workset


class TestCleanExtended:
    def test_purge_decentralized_project(self, config_file, tmp_home):
        """Purge removes .kanibako/ for decentralized projects."""
        from kanibako.commands.clean import run

        project_dir = tmp_home / "project"
        kanibako_dir = project_dir / ".kanibako"
        kanibako_dir.mkdir()
        (kanibako_dir / "data.txt").write_text("session-data")

        args = argparse.Namespace(
            path=str(project_dir), all_projects=False, force=True,
        )
        rc = run(args)
        assert rc == 0
        assert not kanibako_dir.exists()

    def test_purge_all_skips_decentralized(self, config_file, tmp_home, credentials_dir, capsys):
        """--all only covers account-centric projects, not decentralized."""
        from kanibako.commands.clean import run

        config = load_config(config_file)
        std = load_std_paths(config)

        # Create an account-centric project
        ac_dir = tmp_home / "ac_project"
        ac_dir.mkdir()
        proj = resolve_project(std, config, project_dir=str(ac_dir), initialize=True)

        # Create a decentralized project
        dec_dir = tmp_home / "dec_project"
        dec_dir.mkdir()
        (dec_dir / ".kanibako").mkdir()
        (dec_dir / ".kanibako" / "data.txt").write_text("dec-data")

        args = argparse.Namespace(all_projects=True, force=True)
        rc = run(args)
        assert rc == 0

        # Account-centric settings should be gone
        assert not proj.metadata_path.exists()
        # Decentralized .kanibako/ should still exist (not covered by --all)
        assert (dec_dir / ".kanibako" / "data.txt").exists()


class TestCleanWorkset:
    def test_purge_all_includes_workset_projects(self, config_file, tmp_home, credentials_dir, capsys):
        from kanibako.commands.clean import run

        config = load_config(config_file)
        std = load_std_paths(config)

        # Create an AC project
        ac_dir = tmp_home / "ac_purge"
        ac_dir.mkdir()
        ac_proj = resolve_project(std, config, project_dir=str(ac_dir), initialize=True)

        # Create a workset with an initialized project
        ws_root = tmp_home / "worksets" / "purge-ws"
        ws = create_workset("purge-ws", ws_root, std)
        source = tmp_home / "purge_src"
        source.mkdir()
        add_project(ws, "purge-proj", source)
        ws_proj = resolve_workset_project(ws, "purge-proj", std, config, initialize=True)
        (ws_proj.metadata_path / "data.txt").write_text("ws-data")

        args = argparse.Namespace(all_projects=True, force=True)
        rc = run(args)
        assert rc == 0

        # AC settings should be gone
        assert not ac_proj.metadata_path.exists()
        # Workset settings should be gone
        assert not (ws.projects_dir / "purge-proj" / "data.txt").exists()

    def test_purge_workset_project_single(self, config_file, tmp_home, credentials_dir):
        from kanibako.commands.clean import run

        config = load_config(config_file)
        std = load_std_paths(config)

        ws_root = tmp_home / "worksets" / "single-purge-ws"
        ws = create_workset("single-purge-ws", ws_root, std)
        source = tmp_home / "single_purge_src"
        source.mkdir()
        add_project(ws, "single-purge-proj", source)
        ws_proj = resolve_workset_project(ws, "single-purge-proj", std, config, initialize=True)
        (ws_proj.metadata_path / "data.txt").write_text("purge-data")

        # Use workspace path as path arg
        args = argparse.Namespace(
            path=str(ws.workspaces_dir / "single-purge-proj"),
            all_projects=False, force=True,
        )
        rc = run(args)
        assert rc == 0
        assert not ws_proj.metadata_path.exists()
