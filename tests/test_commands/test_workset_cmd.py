"""Tests for kanibako.commands.workset_cmd."""

from __future__ import annotations

import argparse


from kanibako.config import load_config
from kanibako.paths import load_std_paths
from kanibako.workset import (
    add_project,
    create_workset,
)


class TestWorksetCreate:
    def test_create_success(self, config_file, tmp_home, capsys):
        from kanibako.commands.workset_cmd import run_create

        ws_root = tmp_home / "myworkset"
        args = argparse.Namespace(name="dev", path=str(ws_root))
        rc = run_create(args)
        assert rc == 0
        out = capsys.readouterr().out
        assert "Created working set 'dev'" in out
        assert ws_root.resolve().is_dir()

    def test_create_duplicate_name_error(self, config_file, tmp_home, capsys):
        from kanibako.commands.workset_cmd import run_create

        ws_root1 = tmp_home / "ws1"
        args1 = argparse.Namespace(name="dup", path=str(ws_root1))
        run_create(args1)

        ws_root2 = tmp_home / "ws2"
        args2 = argparse.Namespace(name="dup", path=str(ws_root2))
        rc = run_create(args2)
        assert rc == 1
        err = capsys.readouterr().err
        assert "already registered" in err

    def test_create_existing_root_error(self, config_file, tmp_home, capsys):
        from kanibako.commands.workset_cmd import run_create

        ws_root = tmp_home / "existing"
        ws_root.mkdir()
        args = argparse.Namespace(name="ex", path=str(ws_root))
        rc = run_create(args)
        assert rc == 1
        err = capsys.readouterr().err
        assert "already exists" in err

    def test_create_empty_name_error(self, config_file, tmp_home, capsys):
        from kanibako.commands.workset_cmd import run_create

        ws_root = tmp_home / "empty_name_ws"
        args = argparse.Namespace(name="", path=str(ws_root))
        rc = run_create(args)
        assert rc == 1
        err = capsys.readouterr().err
        assert "must not be empty" in err


class TestWorksetList:
    def test_list_empty(self, config_file, tmp_home, capsys):
        from kanibako.commands.workset_cmd import run_list

        args = argparse.Namespace()
        rc = run_list(args)
        assert rc == 0
        out = capsys.readouterr().out
        assert "No working sets" in out

    def test_list_shows_worksets(self, config_file, tmp_home, capsys):
        from kanibako.commands.workset_cmd import run_list

        config = load_config(config_file)
        std = load_std_paths(config)
        create_workset("alpha", tmp_home / "ws_alpha", std)

        args = argparse.Namespace()
        rc = run_list(args)
        assert rc == 0
        out = capsys.readouterr().out
        assert "alpha" in out
        assert "NAME" in out

    def test_list_shows_project_count(self, config_file, tmp_home, capsys):
        from kanibako.commands.workset_cmd import run_list

        config = load_config(config_file)
        std = load_std_paths(config)
        ws = create_workset("beta", tmp_home / "ws_beta", std)

        src = tmp_home / "proj_src"
        src.mkdir()
        add_project(ws, "myproj", src)

        args = argparse.Namespace()
        rc = run_list(args)
        assert rc == 0
        out = capsys.readouterr().out
        assert "beta" in out
        assert "1" in out


class TestWorksetDelete:
    def test_delete_success(self, config_file, tmp_home, capsys):
        from kanibako.commands.workset_cmd import run_delete

        config = load_config(config_file)
        std = load_std_paths(config)
        create_workset("todel", tmp_home / "ws_todel", std)

        args = argparse.Namespace(name="todel", remove_files=False, force=True)
        rc = run_delete(args)
        assert rc == 0
        out = capsys.readouterr().out
        assert "Deleted working set 'todel'" in out

    def test_delete_with_remove_files(self, config_file, tmp_home, capsys):
        from kanibako.commands.workset_cmd import run_delete

        config = load_config(config_file)
        std = load_std_paths(config)
        ws = create_workset("rmfiles", tmp_home / "ws_rmfiles", std)
        root = ws.root

        assert root.is_dir()
        args = argparse.Namespace(name="rmfiles", remove_files=True, force=True)
        rc = run_delete(args)
        assert rc == 0
        assert not root.is_dir()

    def test_delete_unknown_error(self, config_file, tmp_home, capsys):
        from kanibako.commands.workset_cmd import run_delete

        args = argparse.Namespace(name="nonexistent", remove_files=False, force=True)
        rc = run_delete(args)
        assert rc == 1
        err = capsys.readouterr().err
        assert "not registered" in err


class TestWorksetAdd:
    def test_add_success(self, config_file, tmp_home, capsys):
        from kanibako.commands.workset_cmd import run_add

        config = load_config(config_file)
        std = load_std_paths(config)
        create_workset("addws", tmp_home / "ws_add", std)

        src = tmp_home / "add_src"
        src.mkdir()

        args = argparse.Namespace(
            workset="addws", source=str(src), project_name=None,
        )
        rc = run_add(args)
        assert rc == 0
        out = capsys.readouterr().out
        assert "Added project" in out
        assert "add_src" in out

    def test_add_defaults_to_cwd(self, config_file, tmp_home, capsys, monkeypatch):
        from kanibako.commands.workset_cmd import run_add

        config = load_config(config_file)
        std = load_std_paths(config)
        create_workset("cwdws", tmp_home / "ws_cwd", std)

        cwd_dir = tmp_home / "cwd_proj"
        cwd_dir.mkdir()
        monkeypatch.chdir(cwd_dir)

        args = argparse.Namespace(
            workset="cwdws", source=None, project_name=None,
        )
        rc = run_add(args)
        assert rc == 0
        out = capsys.readouterr().out
        assert "cwd_proj" in out

    def test_add_custom_name(self, config_file, tmp_home, capsys):
        from kanibako.commands.workset_cmd import run_add

        config = load_config(config_file)
        std = load_std_paths(config)
        create_workset("namews", tmp_home / "ws_name", std)

        src = tmp_home / "name_src"
        src.mkdir()

        args = argparse.Namespace(
            workset="namews", source=str(src), project_name="custom-name",
        )
        rc = run_add(args)
        assert rc == 0
        out = capsys.readouterr().out
        assert "custom-name" in out

    def test_add_duplicate_error(self, config_file, tmp_home, capsys):
        from kanibako.commands.workset_cmd import run_add

        config = load_config(config_file)
        std = load_std_paths(config)
        ws = create_workset("dupws", tmp_home / "ws_dup", std)

        src = tmp_home / "dup_src"
        src.mkdir()
        add_project(ws, "proj1", src)

        args = argparse.Namespace(
            workset="dupws", source=str(src), project_name="proj1",
        )
        rc = run_add(args)
        assert rc == 1
        err = capsys.readouterr().err
        assert "already exists" in err


class TestWorksetRemove:
    def test_remove_success(self, config_file, tmp_home, capsys):
        from kanibako.commands.workset_cmd import run_remove

        config = load_config(config_file)
        std = load_std_paths(config)
        ws = create_workset("rmws", tmp_home / "ws_rm", std)

        src = tmp_home / "rm_src"
        src.mkdir()
        add_project(ws, "rmproj", src)

        args = argparse.Namespace(
            workset="rmws", project="rmproj",
            remove_files=False, force=True,
        )
        rc = run_remove(args)
        assert rc == 0
        out = capsys.readouterr().out
        assert "Removed project 'rmproj'" in out

    def test_remove_with_files(self, config_file, tmp_home, capsys):
        from kanibako.commands.workset_cmd import run_remove

        config = load_config(config_file)
        std = load_std_paths(config)
        ws = create_workset("rmfws", tmp_home / "ws_rmf", std)

        src = tmp_home / "rmf_src"
        src.mkdir()
        add_project(ws, "rmfproj", src)

        # Verify per-project dirs were created.
        assert (ws.projects_dir / "rmfproj").is_dir()

        args = argparse.Namespace(
            workset="rmfws", project="rmfproj",
            remove_files=True, force=True,
        )
        rc = run_remove(args)
        assert rc == 0
        assert not (ws.projects_dir / "rmfproj").is_dir()

    def test_remove_unknown_error(self, config_file, tmp_home, capsys):
        from kanibako.commands.workset_cmd import run_remove

        config = load_config(config_file)
        std = load_std_paths(config)
        create_workset("rmunkws", tmp_home / "ws_rmunk", std)

        args = argparse.Namespace(
            workset="rmunkws", project="nope",
            remove_files=False, force=True,
        )
        rc = run_remove(args)
        assert rc == 1
        err = capsys.readouterr().err
        assert "not found" in err


class TestWorksetInfo:
    def test_info_success(self, config_file, tmp_home, capsys):
        from kanibako.commands.workset_cmd import run_info

        config = load_config(config_file)
        std = load_std_paths(config)
        ws = create_workset("infows", tmp_home / "ws_info", std)

        src = tmp_home / "info_src"
        src.mkdir()
        add_project(ws, "infoproj", src)

        args = argparse.Namespace(name="infows")
        rc = run_info(args)
        assert rc == 0
        out = capsys.readouterr().out
        assert "infows" in out
        assert "infoproj" in out
        assert "Root:" in out
        assert "Created:" in out

    def test_info_unknown_error(self, config_file, tmp_home, capsys):
        from kanibako.commands.workset_cmd import run_info

        args = argparse.Namespace(name="nosuchws")
        rc = run_info(args)
        assert rc == 1
        err = capsys.readouterr().err
        assert "not registered" in err
