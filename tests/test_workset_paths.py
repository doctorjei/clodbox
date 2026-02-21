"""Tests for resolve_workset_project() in kanibako.paths."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from kanibako.config import load_config
from kanibako.errors import WorksetError
from kanibako.paths import (
    ProjectMode,
    load_std_paths,
    resolve_workset_project,
)
from kanibako.utils import project_hash
from kanibako.workset import add_project, create_workset


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def std(config_file, tmp_home):
    config = load_config(config_file)
    return load_std_paths(config)


@pytest.fixture
def config(config_file):
    return load_config(config_file)


@pytest.fixture
def workset_env(std, config, tmp_home):
    """Create a workset with one project and return (ws, project_name)."""
    ws_root = tmp_home / "worksets" / "my-set"
    ws = create_workset("my-set", ws_root, std)
    source = tmp_home / "original-project"
    source.mkdir()
    add_project(ws, "cool-app", source)
    return ws, "cool-app"


# ---------------------------------------------------------------------------
# TestResolveWorksetProject
# ---------------------------------------------------------------------------

class TestResolveWorksetProject:
    def test_returns_project_paths_with_workset_mode(self, workset_env, std, config):
        ws, name = workset_env
        proj = resolve_workset_project(ws, name, std, config)
        assert proj.mode is ProjectMode.workset

    def test_paths_use_project_name_not_hash(self, workset_env, std, config):
        ws, name = workset_env
        proj = resolve_workset_project(ws, name, std, config)

        assert proj.project_path == ws.workspaces_dir / name
        assert proj.settings_path == ws.settings_dir / name
        assert proj.dot_path == ws.settings_dir / name / config.paths_dot_path
        assert proj.cfg_file == ws.settings_dir / name / config.paths_cfg_file
        assert proj.shell_path == ws.shell_dir / name
        assert proj.vault_ro_path == ws.vault_dir / name / "share-ro"
        assert proj.vault_rw_path == ws.vault_dir / name / "share-rw"

    def test_project_hash_is_sha256_of_workspace_path(self, workset_env, std, config):
        ws, name = workset_env
        proj = resolve_workset_project(ws, name, std, config)

        expected = project_hash(str((ws.workspaces_dir / name).resolve()))
        assert proj.project_hash == expected

    def test_project_not_found_raises(self, workset_env, std, config):
        ws, _ = workset_env
        with pytest.raises(WorksetError, match="not found"):
            resolve_workset_project(ws, "nonexistent", std, config)

    def test_initialize_creates_dot_path_and_cfg_file(
        self, workset_env, std, config, credentials_dir
    ):
        ws, name = workset_env
        proj = resolve_workset_project(ws, name, std, config, initialize=True)

        assert proj.dot_path.is_dir()
        assert proj.cfg_file.exists()

    def test_initialize_copies_credentials(
        self, workset_env, std, config, credentials_dir
    ):
        ws, name = workset_env
        proj = resolve_workset_project(ws, name, std, config, initialize=True)

        creds_file = proj.dot_path / ".credentials.json"
        assert creds_file.is_file()
        data = json.loads(creds_file.read_text())
        assert "claudeAiOauth" in data

    def test_initialize_bootstraps_shell(
        self, workset_env, std, config, credentials_dir
    ):
        ws, name = workset_env
        proj = resolve_workset_project(ws, name, std, config, initialize=True)

        assert (proj.shell_path / ".bashrc").is_file()
        assert (proj.shell_path / ".profile").is_file()

    def test_no_initialize_skips_creation(self, workset_env, std, config):
        ws, name = workset_env
        proj = resolve_workset_project(ws, name, std, config, initialize=False)

        assert not proj.dot_path.is_dir()
        assert not proj.is_new

    def test_is_new_true_on_first_init(
        self, workset_env, std, config, credentials_dir
    ):
        ws, name = workset_env
        proj = resolve_workset_project(ws, name, std, config, initialize=True)
        assert proj.is_new is True

    def test_is_new_false_on_reinit(
        self, workset_env, std, config, credentials_dir
    ):
        ws, name = workset_env
        resolve_workset_project(ws, name, std, config, initialize=True)
        proj2 = resolve_workset_project(ws, name, std, config, initialize=True)
        assert proj2.is_new is False

    def test_recovery_missing_dot_path(
        self, workset_env, std, config, credentials_dir
    ):
        ws, name = workset_env
        # First init to create everything.
        proj = resolve_workset_project(ws, name, std, config, initialize=True)
        # Delete dot_path to simulate corruption.
        import shutil
        shutil.rmtree(proj.dot_path)
        assert not proj.dot_path.exists()

        # Re-resolve with initialize; recovery should recreate dot_path.
        proj2 = resolve_workset_project(ws, name, std, config, initialize=True)
        assert proj2.dot_path.is_dir()
        # Not "new" because dot_path already existed at the is_new check point
        # (it was removed after first init, but settings_path was present).

    def test_recovery_missing_cfg_file(
        self, workset_env, std, config, credentials_dir
    ):
        ws, name = workset_env
        proj = resolve_workset_project(ws, name, std, config, initialize=True)
        proj.cfg_file.unlink()
        assert not proj.cfg_file.exists()

        proj2 = resolve_workset_project(ws, name, std, config, initialize=True)
        assert proj2.cfg_file.exists()

    def test_recovery_missing_shell(
        self, workset_env, std, config, credentials_dir
    ):
        ws, name = workset_env
        proj = resolve_workset_project(ws, name, std, config, initialize=True)
        import shutil
        shutil.rmtree(proj.shell_path)
        assert not proj.shell_path.exists()

        proj2 = resolve_workset_project(ws, name, std, config, initialize=True)
        assert proj2.shell_path.is_dir()
        assert (proj2.shell_path / ".bashrc").is_file()

    def test_no_project_path_breadcrumb(
        self, workset_env, std, config, credentials_dir
    ):
        """Workset projects should NOT create project-path.txt."""
        ws, name = workset_env
        proj = resolve_workset_project(ws, name, std, config, initialize=True)
        assert not (proj.settings_path / "project-path.txt").exists()

    def test_no_vault_gitignore(
        self, workset_env, std, config, credentials_dir
    ):
        """Workset projects should NOT create .gitignore in vault dirs."""
        ws, name = workset_env
        resolve_workset_project(ws, name, std, config, initialize=True)
        vault_proj = ws.vault_dir / name
        assert not (vault_proj / ".gitignore").exists()


# ---------------------------------------------------------------------------
# TestWorksetProjectCredentialFlow
# ---------------------------------------------------------------------------

class TestWorksetProjectCredentialFlow:
    def test_credential_paths_resolve_into_workset_settings(
        self, workset_env, std, config, credentials_dir
    ):
        ws, name = workset_env
        proj = resolve_workset_project(ws, name, std, config, initialize=True)

        creds_file = proj.dot_path / ".credentials.json"
        assert creds_file.is_file()
        # Path should be under the workset's settings dir.
        assert str(ws.settings_dir) in str(creds_file)

    def test_refresh_central_to_project_works_with_workset_dot_path(
        self, workset_env, std, config, credentials_dir
    ):
        ws, name = workset_env
        proj = resolve_workset_project(ws, name, std, config, initialize=True)

        from kanibako.credentials import refresh_central_to_project

        central = std.credentials_path / config.paths_dot_path / ".credentials.json"
        project_creds = proj.dot_path / ".credentials.json"

        # Central is newer (copy from credential template), so merge should work.
        # Touch central to ensure it's newer.
        import time
        time.sleep(0.05)
        central.write_text(json.dumps(
            {"claudeAiOauth": {"token": "refreshed-token"}}
        ))

        result = refresh_central_to_project(central, project_creds)
        assert result is True

        updated = json.loads(project_creds.read_text())
        assert updated["claudeAiOauth"]["token"] == "refreshed-token"


# ---------------------------------------------------------------------------
# TestIterWorksetProjects
# ---------------------------------------------------------------------------

class TestIterWorksetProjects:
    def test_iter_workset_projects_normal(self, std, config, tmp_home):
        from kanibako.paths import iter_workset_projects

        ws_root = tmp_home / "worksets" / "iter-set"
        ws = create_workset("iter-set", ws_root, std)
        source = tmp_home / "iter-src"
        source.mkdir()
        add_project(ws, "proj-a", source)

        results = iter_workset_projects(std, config)
        assert len(results) == 1
        ws_name, ws_obj, project_list = results[0]
        assert ws_name == "iter-set"
        assert len(project_list) == 1
        assert project_list[0] == ("proj-a", "ok")

    def test_iter_workset_projects_missing_workspace(self, std, config, tmp_home):
        import shutil
        from kanibako.paths import iter_workset_projects

        ws_root = tmp_home / "worksets" / "miss-set"
        ws = create_workset("miss-set", ws_root, std)
        source = tmp_home / "miss-src"
        source.mkdir()
        add_project(ws, "miss-proj", source)
        # Remove workspace dir
        shutil.rmtree(ws.workspaces_dir / "miss-proj")

        results = iter_workset_projects(std, config)
        assert len(results) == 1
        _, _, project_list = results[0]
        assert project_list[0] == ("miss-proj", "missing")

    def test_iter_workset_projects_missing_root(self, std, config, tmp_home, capsys):
        import shutil
        from kanibako.paths import iter_workset_projects

        ws_root = tmp_home / "worksets" / "gone-set"
        create_workset("gone-set", ws_root, std)
        shutil.rmtree(ws_root)

        results = iter_workset_projects(std, config)
        # Gone workset produces warning, no entries
        assert len(results) == 0
        err = capsys.readouterr().err
        assert "Warning" in err
