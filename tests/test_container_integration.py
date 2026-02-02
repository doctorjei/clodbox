"""Integration tests for container operations.

Every test is a stub that skips immediately.  Run with::

    pytest -m integration tests/test_container_integration.py -v
"""

from __future__ import annotations

import pytest


@pytest.mark.integration
class TestRuntimeDetection:
    """Verify real runtime detection on the host."""

    def test_detect_finds_podman_or_docker(self):
        """Real ``shutil.which`` finds a container runtime."""
        pytest.skip("STUB: not yet implemented")

    def test_env_override_takes_precedence(self):
        """``CLODBOX_DOCKER_CMD`` overrides automatic detection."""
        pytest.skip("STUB: not yet implemented")


@pytest.mark.integration
class TestImageOperations:
    """Image inspect / pull against a real registry."""

    def test_image_exists_returns_true_for_pulled_image(self, pulled_image):
        """``image inspect`` succeeds for a locally-pulled image."""
        pytest.skip("STUB: not yet implemented")

    def test_image_exists_returns_false_for_missing(self, container_runtime_cmd):
        """``image inspect`` fails for a bogus image tag."""
        pytest.skip("STUB: not yet implemented")

    def test_pull_succeeds_for_real_image(self, container_runtime_cmd):
        """Real registry pull of a lightweight image returns True."""
        pytest.skip("STUB: not yet implemented")

    def test_pull_fails_for_nonexistent_image(self, container_runtime_cmd):
        """Pull of a bogus image returns False."""
        pytest.skip("STUB: not yet implemented")

    def test_ensure_image_skips_pull_when_exists(self, pulled_image):
        """No-op when image is already present locally."""
        pytest.skip("STUB: not yet implemented")


@pytest.mark.integration
class TestRunContainer:
    """Run real containers via podman/docker."""

    def test_run_returns_zero_on_success(self, pulled_image, container_runtime_cmd):
        """``/bin/true`` inside the container exits 0."""
        pytest.skip("STUB: not yet implemented")

    def test_run_returns_nonzero_on_failure(self, pulled_image, container_runtime_cmd):
        """``/bin/false`` inside the container exits != 0."""
        pytest.skip("STUB: not yet implemented")

    def test_run_volume_mounts_are_accessible(self, pulled_image, container_runtime_cmd):
        """A host file is readable inside the container via volume mount."""
        pytest.skip("STUB: not yet implemented")


@pytest.mark.integration
class TestListLocalImages:
    """Verify real ``images`` output parsing."""

    def test_list_includes_pulled_image(self, pulled_image, container_runtime_cmd):
        """Parsed output contains the pulled image as a valid tuple."""
        pytest.skip("STUB: not yet implemented")
