"""ClaudeTarget: Claude Code agent target implementation."""

from __future__ import annotations

import shutil
from pathlib import Path

from kanibako.targets.base import AgentInstall, Mount, Target


class ClaudeTarget(Target):
    """Target for Claude Code."""

    @property
    def name(self) -> str:
        return "claude"

    @property
    def display_name(self) -> str:
        return "Claude Code"

    def detect(self) -> AgentInstall | None:
        """Detect Claude Code installation on the host.

        Resolves the ``claude`` symlink to find the real binary, then walks up
        the directory tree to locate the ``claude/`` installation root.
        """
        claude_path = shutil.which("claude")
        if not claude_path:
            return None

        binary = Path(claude_path)

        try:
            resolved = binary.resolve()
        except OSError:
            return None

        # Walk up from the resolved binary to find the 'claude' directory.
        install_dir = resolved.parent
        while install_dir.name != "claude" and install_dir != install_dir.parent:
            install_dir = install_dir.parent

        # Sanity check: if we hit the filesystem root without finding 'claude',
        # fall back to the immediate parent of the binary.
        if install_dir.name != "claude":
            install_dir = resolved.parent

        return AgentInstall(name="claude", binary=binary, install_dir=install_dir)

    def binary_mounts(self, install: AgentInstall) -> list[Mount]:
        """Return mounts for Claude install dir and binary."""
        return [
            Mount(
                source=install.install_dir,
                destination="/home/agent/.local/share/claude",
                options="ro",
            ),
            Mount(
                source=install.binary,
                destination="/home/agent/.local/bin/claude",
                options="ro",
            ),
        ]

    def init_home(self, home: Path) -> None:
        """Initialize Claude-specific files in the project home.

        Creates ``.claude/`` directory and copies filtered ``.claude.json``
        and ``.credentials.json`` from the host.
        """
        claude_dir = home / ".claude"
        claude_dir.mkdir(parents=True, exist_ok=True)

        # Copy credentials from host ~/.claude/.credentials.json
        host_creds = Path.home() / ".claude" / ".credentials.json"
        if host_creds.is_file():
            shutil.copy2(str(host_creds), str(claude_dir / ".credentials.json"))

        # Copy filtered .claude.json from host
        host_settings = Path.home() / ".claude.json"
        if host_settings.is_file():
            from kanibako.credentials import filter_settings
            filter_settings(host_settings, home / ".claude.json")
        else:
            (home / ".claude.json").touch()

    def refresh_credentials(self, home: Path) -> None:
        """Refresh Claude credentials from host into project home.

        Syncs host ``~/.claude/.credentials.json`` into ``home/.claude/.credentials.json``
        using mtime-based freshness.
        """
        from kanibako.credentials import refresh_central_to_project, refresh_host_to_central

        # Central store path (kept for cron compatibility).
        central_creds = self._central_creds_path()
        project_creds = home / ".claude" / ".credentials.json"

        refresh_host_to_central(central_creds)
        refresh_central_to_project(central_creds, project_creds)

    def writeback_credentials(self, home: Path) -> None:
        """Write back refreshed credentials from project home to host."""
        from kanibako.credentials import writeback_project_to_central_and_host

        central_creds = self._central_creds_path()
        project_creds = home / ".claude" / ".credentials.json"

        writeback_project_to_central_and_host(project_creds, central_creds)

    def build_cli_args(
        self,
        *,
        safe_mode: bool,
        resume_mode: bool,
        new_session: bool,
        is_new_project: bool,
        extra_args: list[str],
    ) -> list[str]:
        """Build CLI arguments for Claude Code."""
        cli_args: list[str] = []

        if not safe_mode:
            cli_args.append("--dangerously-skip-permissions")

        if resume_mode:
            cli_args.append("--resume")
        else:
            skip_continue = new_session or is_new_project
            if any(a in ("--resume", "-r") for a in extra_args):
                skip_continue = True
            if not skip_continue:
                cli_args.append("--continue")

        cli_args.extend(extra_args)
        return cli_args

    @staticmethod
    def _central_creds_path() -> Path:
        """Return the central credential store path for Claude."""
        from kanibako.config import KanibakoConfig
        from kanibako.paths import _xdg

        data_home = _xdg("XDG_DATA_HOME", ".local/share")
        config = KanibakoConfig()
        data_path = data_home / config.paths_relative_std_path
        return data_path / config.paths_init_credentials_path / config.paths_dot_path / ".credentials.json"
