"""Tests for kanibako.snapshots: vault share-rw snapshot engine."""

from __future__ import annotations

import tarfile
from pathlib import Path

import pytest

from kanibako.snapshots import (
    auto_snapshot,
    create_snapshot,
    list_snapshots,
    prune_snapshots,
    restore_snapshot,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _populate_rw(vault_rw: Path) -> None:
    """Put some files into share-rw for snapshot tests."""
    vault_rw.mkdir(parents=True, exist_ok=True)
    (vault_rw / "file1.txt").write_text("hello")
    sub = vault_rw / "subdir"
    sub.mkdir()
    (sub / "file2.txt").write_text("world")


# ---------------------------------------------------------------------------
# create_snapshot
# ---------------------------------------------------------------------------


class TestCreateSnapshot:
    def test_creates_archive(self, tmp_path):
        vault_rw = tmp_path / "vault" / "share-rw"
        _populate_rw(vault_rw)

        result = create_snapshot(vault_rw)

        assert result is not None
        assert result.exists()
        assert result.name.endswith(".tar.xz")
        assert result.parent.name == ".versions"

    def test_returns_none_when_empty(self, tmp_path):
        vault_rw = tmp_path / "vault" / "share-rw"
        vault_rw.mkdir(parents=True)

        assert create_snapshot(vault_rw) is None

    def test_returns_none_when_missing(self, tmp_path):
        vault_rw = tmp_path / "vault" / "share-rw"

        assert create_snapshot(vault_rw) is None

    def test_archive_contains_files(self, tmp_path):
        vault_rw = tmp_path / "vault" / "share-rw"
        _populate_rw(vault_rw)

        result = create_snapshot(vault_rw)
        with tarfile.open(result, "r:xz") as tar:
            names = tar.getnames()
            assert "file1.txt" in names
            assert "subdir/file2.txt" in names


# ---------------------------------------------------------------------------
# list_snapshots
# ---------------------------------------------------------------------------


class TestListSnapshots:
    def test_lists_snapshots(self, tmp_path):
        vault_rw = tmp_path / "vault" / "share-rw"
        _populate_rw(vault_rw)

        create_snapshot(vault_rw)
        snaps = list_snapshots(vault_rw)

        assert len(snaps) == 1
        name, ts, size = snaps[0]
        assert name.endswith(".tar.xz")
        assert "UTC" in ts
        assert size > 0

    def test_empty_when_no_versions(self, tmp_path):
        vault_rw = tmp_path / "vault" / "share-rw"
        vault_rw.mkdir(parents=True)

        assert list_snapshots(vault_rw) == []

    def test_sorted_by_time(self, tmp_path):
        vault_rw = tmp_path / "vault" / "share-rw"
        versions = tmp_path / "vault" / ".versions"
        versions.mkdir(parents=True)
        _populate_rw(vault_rw)

        # Manually create two snapshots with different timestamps.
        import tarfile
        for name in ("20260101T000000Z.tar.xz", "20260201T000000Z.tar.xz"):
            with tarfile.open(versions / name, "w:xz") as tar:
                tar.add(str(vault_rw / "file1.txt"), arcname="file1.txt")

        snaps = list_snapshots(vault_rw)
        assert len(snaps) == 2
        assert snaps[0][0] == "20260101T000000Z.tar.xz"
        assert snaps[1][0] == "20260201T000000Z.tar.xz"


# ---------------------------------------------------------------------------
# restore_snapshot
# ---------------------------------------------------------------------------


class TestRestoreSnapshot:
    def test_restores_contents(self, tmp_path):
        vault_rw = tmp_path / "vault" / "share-rw"
        _populate_rw(vault_rw)

        snap = create_snapshot(vault_rw)

        # Modify share-rw.
        (vault_rw / "file1.txt").write_text("modified")
        (vault_rw / "new_file.txt").write_text("should disappear")

        restore_snapshot(vault_rw, snap.name)

        assert (vault_rw / "file1.txt").read_text() == "hello"
        assert (vault_rw / "subdir" / "file2.txt").read_text() == "world"
        assert not (vault_rw / "new_file.txt").exists()

    def test_raises_on_missing_snapshot(self, tmp_path):
        vault_rw = tmp_path / "vault" / "share-rw"
        vault_rw.mkdir(parents=True)

        with pytest.raises(FileNotFoundError, match="Snapshot not found"):
            restore_snapshot(vault_rw, "nonexistent.tar.xz")


# ---------------------------------------------------------------------------
# prune_snapshots
# ---------------------------------------------------------------------------


class TestPruneSnapshots:
    def test_prunes_old_snapshots(self, tmp_path):
        vault_rw = tmp_path / "vault" / "share-rw"
        versions = tmp_path / "vault" / ".versions"
        versions.mkdir(parents=True)
        _populate_rw(vault_rw)

        # Create 7 snapshots manually.
        for i in range(7):
            name = f"2026010{i + 1}T000000Z.tar.xz"
            with tarfile.open(versions / name, "w:xz") as tar:
                tar.add(str(vault_rw / "file1.txt"), arcname="file1.txt")

        removed = prune_snapshots(vault_rw, max_keep=3)

        assert removed == 4
        remaining = list(versions.iterdir())
        assert len(remaining) == 3

    def test_no_prune_when_under_limit(self, tmp_path):
        vault_rw = tmp_path / "vault" / "share-rw"
        _populate_rw(vault_rw)
        create_snapshot(vault_rw)

        removed = prune_snapshots(vault_rw, max_keep=5)
        assert removed == 0

    def test_no_prune_when_no_versions(self, tmp_path):
        vault_rw = tmp_path / "vault" / "share-rw"
        vault_rw.mkdir(parents=True)

        removed = prune_snapshots(vault_rw, max_keep=5)
        assert removed == 0


# ---------------------------------------------------------------------------
# auto_snapshot
# ---------------------------------------------------------------------------


class TestAutoSnapshot:
    def test_creates_and_prunes(self, tmp_path):
        vault_rw = tmp_path / "vault" / "share-rw"
        _populate_rw(vault_rw)

        result = auto_snapshot(vault_rw, max_keep=2)
        assert result is not None
        assert result.exists()

    def test_returns_none_when_empty(self, tmp_path):
        vault_rw = tmp_path / "vault" / "share-rw"
        vault_rw.mkdir(parents=True)

        assert auto_snapshot(vault_rw) is None
