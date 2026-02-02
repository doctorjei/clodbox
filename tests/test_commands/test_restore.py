"""Tests for clodbox.commands.restore."""

from __future__ import annotations

import argparse
import tarfile
from pathlib import Path

import pytest

from clodbox.config import load_config
from clodbox.paths import load_std_paths, resolve_project


class TestRestore:
    def test_round_trip(self, config_file, tmp_home, credentials_dir):
        """Archive then restore; verify data preserved."""
        from clodbox.commands.archive import run as archive_run
        from clodbox.commands.restore import run as restore_run

        config = load_config(config_file)
        std = load_std_paths(config)
        project_dir = str(tmp_home / "project")
        proj = resolve_project(std, config, project_dir=project_dir, initialize=True)

        # Add test data
        (proj.settings_path / "mydata.txt").write_text("important")

        archive_path = str(tmp_home / "roundtrip.txz")
        args = argparse.Namespace(
            path=project_dir,
            file=archive_path,
            all_projects=False,
            allow_uncommitted=True,
            allow_unpushed=True,
            force=True,
        )
        assert archive_run(args) == 0

        # Clean
        import shutil
        shutil.rmtree(proj.settings_path)
        assert not proj.settings_path.exists()

        # Restore
        args = argparse.Namespace(
            path=project_dir,
            file=archive_path,
            all_archives=False,
            force=True,
        )
        assert restore_run(args) == 0
        assert proj.settings_path.is_dir()
        assert (proj.settings_path / "mydata.txt").read_text() == "important"
        # Info file should be cleaned up
        assert not (proj.settings_path / "clodbox-archive-info.txt").exists()

    def test_missing_archive(self, config_file, tmp_home, credentials_dir):
        from clodbox.commands.restore import run

        args = argparse.Namespace(
            path=str(tmp_home / "project"),
            file="/nonexistent/archive.txz",
            all_archives=False,
            force=True,
        )
        assert run(args) == 1
