"""Integration tests for archive / restore workflows.

Every test is a stub that skips immediately.  Run with::

    pytest -m integration tests/test_archive_restore_integration.py -v
"""

from __future__ import annotations

import pytest


@pytest.mark.integration
class TestArchiveGitIntegration:
    """Archive creation against real git repos."""

    def test_archive_clean_git_repo(self, real_git_repo, integration_config):
        """Archive from a clean git repo succeeds."""
        pytest.skip("STUB: not yet implemented")

    def test_archive_detects_uncommitted_changes(self, real_git_repo, integration_config):
        """Real ``git diff-index`` detects uncommitted changes."""
        pytest.skip("STUB: not yet implemented")

    def test_archive_detects_unpushed_commits(self, real_git_repo, integration_config):
        """Real ``git rev-list`` detects unpushed commits."""
        pytest.skip("STUB: not yet implemented")

    def test_archive_contains_git_metadata(self, real_git_repo, integration_config):
        """Archive info contains branch, commit, and remote fields."""
        pytest.skip("STUB: not yet implemented")

    def test_archive_non_git_project_includes_warning(
        self, integration_home, integration_config
    ):
        """Archiving a non-git project includes a warning in metadata."""
        pytest.skip("STUB: not yet implemented")


@pytest.mark.integration
class TestRestoreGitIntegration:
    """Restore validation against real git state."""

    def test_restore_validates_git_commit_match(self, real_git_repo, integration_config):
        """Same-commit restore proceeds without prompt."""
        pytest.skip("STUB: not yet implemented")

    def test_restore_detects_git_commit_mismatch(self, real_git_repo, integration_config):
        """Different HEAD triggers a warning / confirmation prompt."""
        pytest.skip("STUB: not yet implemented")

    def test_restore_to_non_git_workspace_from_git_archive(
        self, integration_home, integration_config
    ):
        """Restoring a git-based archive into a non-git workspace warns."""
        pytest.skip("STUB: not yet implemented")


@pytest.mark.integration
class TestArchiveRestoreRoundTrip:
    """End-to-end archive → restore preservation."""

    def test_full_round_trip_preserves_session_data(
        self, real_git_repo, integration_config, integration_credentials
    ):
        """Byte-for-byte preservation of session data through round trip."""
        pytest.skip("STUB: not yet implemented")

    def test_round_trip_with_binary_data(
        self, real_git_repo, integration_config, integration_credentials
    ):
        """Binary data survives the archive / restore cycle."""
        pytest.skip("STUB: not yet implemented")

    def test_round_trip_to_different_project_path(
        self, real_git_repo, integration_config, integration_credentials
    ):
        """Cross-project restore works when project paths differ."""
        pytest.skip("STUB: not yet implemented")
