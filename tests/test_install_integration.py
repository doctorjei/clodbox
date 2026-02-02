"""Integration tests for the install command.

Every test is a stub that skips immediately.  Run with::

    pytest -m integration tests/test_install_integration.py -v
"""

from __future__ import annotations

import shutil

import pytest


@pytest.mark.integration
class TestInstallFilesystem:
    """Verify real filesystem operations during install."""

    def test_full_install_creates_directory_tree(
        self, integration_home, integration_config
    ):
        """Install creates config, data, and credentials directories."""
        pytest.skip("STUB: not yet implemented")

    def test_install_preserves_existing_config(
        self, integration_home, integration_config
    ):
        """Running install twice is idempotent — existing config untouched."""
        pytest.skip("STUB: not yet implemented")

    def test_install_copies_host_credentials(
        self, integration_home, integration_config
    ):
        """Host credentials are copied to the central store."""
        pytest.skip("STUB: not yet implemented")

    def test_install_filters_settings_json(
        self, integration_home, integration_config
    ):
        """Only safe keys survive the settings filter."""
        pytest.skip("STUB: not yet implemented")


@pytest.mark.integration
class TestContainerfileDiscovery:
    """Containerfile discovery and copy logic."""

    def test_discovers_containers_in_cwd(self, integration_home):
        """Finds Containerfile / Dockerfile variants in the working directory."""
        pytest.skip("STUB: not yet implemented")

    def test_returns_none_when_no_containerfiles(self, integration_home):
        """Returns None when no Containerfiles are present."""
        pytest.skip("STUB: not yet implemented")

    def test_containerfiles_copied_to_data_dir(
        self, integration_home, integration_config
    ):
        """Discovered Containerfiles are copied to the data directory."""
        pytest.skip("STUB: not yet implemented")


@pytest.mark.integration
class TestCronInstallation:
    """Cron job installation for credential refresh."""

    @pytest.mark.skipif(
        shutil.which("crontab") is None, reason="crontab not available"
    )
    def test_cron_entry_installed(self, integration_home, integration_config):
        """A cron entry for credential refresh is present in crontab."""
        pytest.skip("STUB: not yet implemented")

    @pytest.mark.skipif(
        shutil.which("crontab") is None, reason="crontab not available"
    )
    def test_cron_deduplication(self, integration_home, integration_config):
        """Running install twice does not create duplicate cron entries."""
        pytest.skip("STUB: not yet implemented")


@pytest.mark.integration
class TestLegacyMigration:
    """Legacy .rc → .toml migration."""

    def test_legacy_rc_migrated_to_toml(self, integration_home):
        """A legacy ``.rc`` file is migrated to ``.toml`` with a ``.rc.bak`` backup."""
        pytest.skip("STUB: not yet implemented")
