"""clodbox refresh-credentials: cron job to sync host creds to central store."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from clodbox.config import load_config
from clodbox.credentials import refresh_host_to_central
from clodbox.errors import ConfigError
from clodbox.paths import _xdg


def add_parser(subparsers: argparse._SubParsersAction) -> None:
    p = subparsers.add_parser(
        "refresh-creds",
        help="Sync host credentials to central store",
        description="Refresh the clodbox central credential store from host credentials. "
        "Intended to be run via cron.",
    )
    p.set_defaults(func=run)


def run(args: argparse.Namespace) -> int:
    config_file = _xdg("XDG_CONFIG_HOME", ".config") / "clodbox" / "clodbox.toml"
    if not config_file.exists():
        print(
            f"Error: [{config_file}] is missing. Reinstall to fix.",
            file=sys.stderr,
        )
        return 1

    config = load_config(config_file)
    data_home = _xdg("XDG_DATA_HOME", ".local/share")
    data_path = data_home / config.paths_relative_std_path
    credentials_path = data_path / config.paths_init_credentials_path
    dot_template = credentials_path / config.paths_dot_path / ".credentials.json"

    refresh_host_to_central(dot_template)
    return 0
