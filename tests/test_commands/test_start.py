"""Tests for clodbox.commands.start."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest


class TestStartArgs:
    """Verify CLI args are correctly passed through to container."""

    def test_claude_mode_adds_skip_permissions(self):
        """Default (no entrypoint) should inject --dangerously-skip-permissions."""
        from clodbox.commands.start import _run_container

        # We can't run a real container, but we can test the arg assembly
        # by mocking the runtime and checking what gets passed.
        with (
            patch("clodbox.commands.start.load_config"),
            patch("clodbox.commands.start.load_std_paths"),
            patch("clodbox.commands.start.resolve_project") as mock_proj,
            patch("clodbox.commands.start.load_merged_config") as mock_merged,
            patch("clodbox.commands.start.ContainerRuntime") as MockRT,
            patch("clodbox.commands.start.refresh_host_to_central"),
            patch("clodbox.commands.start.refresh_central_to_project"),
            patch("clodbox.commands.start.writeback_project_to_central_and_host"),
            patch("clodbox.commands.start.fcntl"),
            patch("builtins.open", MagicMock()),
        ):
            proj = MagicMock()
            proj.is_new = False
            proj.settings_path = MagicMock()
            proj.settings_path.__truediv__ = MagicMock(return_value=MagicMock())
            proj.dot_path.__truediv__ = MagicMock(return_value=MagicMock())
            mock_proj.return_value = proj

            merged = MagicMock()
            merged.container_image = "test:latest"
            mock_merged.return_value = merged

            runtime = MagicMock()
            runtime.run.return_value = 0
            MockRT.return_value = runtime

            _run_container(
                project_dir=None,
                entrypoint=None,
                image_override=None,
                new_session=False,
                safe_mode=False,
                resume_mode=False,
                extra_args=[],
            )

            call_kwargs = runtime.run.call_args
            cli_args = call_kwargs.kwargs.get("cli_args", [])
            assert "--dangerously-skip-permissions" in cli_args
            assert "--continue" in cli_args

    def test_safe_mode_skips_permissions(self):
        from clodbox.commands.start import _run_container

        with (
            patch("clodbox.commands.start.load_config"),
            patch("clodbox.commands.start.load_std_paths"),
            patch("clodbox.commands.start.resolve_project") as mock_proj,
            patch("clodbox.commands.start.load_merged_config") as mock_merged,
            patch("clodbox.commands.start.ContainerRuntime") as MockRT,
            patch("clodbox.commands.start.refresh_host_to_central"),
            patch("clodbox.commands.start.refresh_central_to_project"),
            patch("clodbox.commands.start.writeback_project_to_central_and_host"),
            patch("clodbox.commands.start.fcntl"),
            patch("builtins.open", MagicMock()),
        ):
            proj = MagicMock()
            proj.is_new = True
            proj.settings_path = MagicMock()
            proj.settings_path.__truediv__ = MagicMock(return_value=MagicMock())
            proj.dot_path.__truediv__ = MagicMock(return_value=MagicMock())
            mock_proj.return_value = proj

            merged = MagicMock()
            merged.container_image = "test:latest"
            mock_merged.return_value = merged

            runtime = MagicMock()
            runtime.run.return_value = 0
            MockRT.return_value = runtime

            _run_container(
                project_dir=None,
                entrypoint=None,
                image_override=None,
                new_session=False,
                safe_mode=True,
                resume_mode=False,
                extra_args=[],
            )

            call_kwargs = runtime.run.call_args
            cli_args = call_kwargs.kwargs.get("cli_args") or []
            assert "--dangerously-skip-permissions" not in cli_args
