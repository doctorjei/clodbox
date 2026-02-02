"""Tests for clodbox.container."""

from __future__ import annotations

from unittest.mock import patch

import pytest

from clodbox.container import ContainerRuntime
from clodbox.errors import ContainerError


class TestContainerRuntime:
    def test_detect_raises_when_nothing_found(self, monkeypatch):
        monkeypatch.delenv("CLODBOX_DOCKER_CMD", raising=False)
        with patch("shutil.which", return_value=None):
            with pytest.raises(ContainerError, match="No container runtime"):
                ContainerRuntime()

    def test_uses_env_override(self, monkeypatch):
        monkeypatch.setenv("CLODBOX_DOCKER_CMD", "/usr/bin/fake-docker")
        rt = ContainerRuntime()
        assert rt.cmd == "/usr/bin/fake-docker"

    def test_explicit_command(self):
        rt = ContainerRuntime(command="/usr/bin/podman")
        assert rt.cmd == "/usr/bin/podman"

    def test_guess_containerfile(self):
        assert ContainerRuntime._guess_containerfile("ghcr.io/x/clodbox-base:latest") == "base"
        assert ContainerRuntime._guess_containerfile("ghcr.io/x/clodbox-systems:v1") == "systems"
        assert ContainerRuntime._guess_containerfile("ghcr.io/x/clodbox-jvm:latest") == "jvm"
        assert ContainerRuntime._guess_containerfile("totally-unrelated:latest") is None
