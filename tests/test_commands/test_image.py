"""Tests for clodbox.commands.image."""

from __future__ import annotations

import argparse

import pytest

from clodbox.config import load_config
from clodbox.paths import load_std_paths, resolve_project


class TestImage:
    def test_runs_without_error(self, config_file, tmp_home, credentials_dir, capsys):
        """Smoke test: image list runs without crashing."""
        from clodbox.commands.image import run

        config = load_config(config_file)
        std = load_std_paths(config)
        project_dir = str(tmp_home / "project")
        resolve_project(std, config, project_dir=project_dir, initialize=True)

        args = argparse.Namespace(project=project_dir)
        rc = run(args)
        assert rc == 0

        captured = capsys.readouterr()
        assert "Current image:" in captured.out


class TestExtractGhcrOwner:
    def test_valid_ghcr_url(self):
        from clodbox.commands.image import _extract_ghcr_owner

        assert _extract_ghcr_owner("ghcr.io/doctorjei/clodbox-base:latest") == "doctorjei"

    def test_non_ghcr_url(self):
        from clodbox.commands.image import _extract_ghcr_owner

        assert _extract_ghcr_owner("docker.io/library/ubuntu:latest") is None
