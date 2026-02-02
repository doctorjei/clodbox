"""Tests for clodbox.commands.remove."""

from __future__ import annotations

import argparse
from pathlib import Path
from unittest.mock import patch

import pytest

from clodbox.config import write_global_config


class TestRemove:
    def test_removes_config(self, tmp_home):
        from clodbox.commands.remove import run

        config_file = tmp_home / "config" / "clodbox" / "clodbox.toml"
        write_global_config(config_file)
        assert config_file.exists()

        with (
            patch("clodbox.commands.remove._remove_cron"),
            patch("clodbox.commands.remove.confirm_prompt"),
        ):
            args = argparse.Namespace()
            rc = run(args)

        assert rc == 0
        assert not config_file.exists()
