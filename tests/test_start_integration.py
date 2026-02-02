"""Integration tests for the start command pipeline.

Every test is a stub that skips immediately.  Run with::

    pytest -m integration tests/test_start_integration.py -v
"""

from __future__ import annotations

import pytest


@pytest.mark.integration
class TestRealFcntlLocking:
    """fcntl-based lock acquisition with real file descriptors."""

    def test_lock_acquired_and_released(self, integration_home, integration_config):
        """Lock file is unlocked after the pipeline returns."""
        pytest.skip("STUB: not yet implemented")

    def test_concurrent_lock_contention(self, integration_home, integration_config):
        """A second caller gets exit 1 when the lock is already held."""
        pytest.skip("STUB: not yet implemented")

    def test_lock_released_after_container_error(
        self, integration_home, integration_config
    ):
        """Lock is released in the finally block even after a container error."""
        pytest.skip("STUB: not yet implemented")


@pytest.mark.integration
class TestCredentialFlow:
    """End-to-end credential refresh pipeline with real files."""

    def test_host_to_central_to_project_flow(
        self, integration_home, integration_config, integration_credentials
    ):
        """Full credential pipeline: host → central → project, real files."""
        pytest.skip("STUB: not yet implemented")

    def test_mtime_based_freshness(
        self, integration_home, integration_config, integration_credentials
    ):
        """A newer project credential is not overwritten by an older central one."""
        pytest.skip("STUB: not yet implemented")


@pytest.mark.integration
class TestExitCodePropagation:
    """Exit code propagation through the full start pipeline."""

    def test_zero_exit_code(
        self, integration_home, integration_config, integration_credentials
    ):
        """Real pipeline exits 0 on success."""
        pytest.skip("STUB: not yet implemented")

    def test_nonzero_exit_code(
        self, integration_home, integration_config, integration_credentials
    ):
        """Real pipeline propagates exit code 42."""
        pytest.skip("STUB: not yet implemented")
