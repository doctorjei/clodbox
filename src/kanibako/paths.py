"""XDG resolution, project hash computation, directory creation, and initialization."""

from __future__ import annotations

import os
import shutil
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import TYPE_CHECKING

from kanibako.config import KanibakoConfig, load_config
from kanibako.errors import ConfigError, ProjectError, WorksetError
from kanibako.utils import project_hash

if TYPE_CHECKING:
    from kanibako.workset import Workset


class ProjectMode(Enum):
    """How a project's persistent state is organized on disk."""

    account_centric = "account_centric"
    workset = "workset"
    decentralized = "decentralized"


@dataclass
class StandardPaths:
    """Resolved XDG and kanibako standard directory paths."""

    config_home: Path
    data_home: Path
    state_home: Path
    cache_home: Path
    config_file: Path
    data_path: Path
    state_path: Path
    cache_path: Path
    credentials_path: Path


@dataclass
class ProjectPaths:
    """Resolved paths for a specific project."""

    project_path: Path
    project_hash: str
    metadata_path: Path      # host-only: project.toml, breadcrumb, lock
    home_path: Path          # mounted as /home/agent
    vault_ro_path: Path      # {project}/vault/share-ro (→ /home/agent/share-ro)
    vault_rw_path: Path      # {project}/vault/share-rw (→ /home/agent/share-rw)
    is_new: bool = field(default=False)
    mode: ProjectMode = field(default=ProjectMode.account_centric)


def _xdg(env_var: str, default_suffix: str) -> Path:
    """Resolve an XDG directory from environment or default under $HOME."""
    val = os.environ.get(env_var, "")
    if val:
        return Path(val).resolve()
    return Path.home() / default_suffix


def load_std_paths(config: KanibakoConfig | None = None) -> StandardPaths:
    """Compute all standard kanibako directories.

    If *config* is None, it is loaded from the config file (which must exist).
    Directories are created as needed.
    """
    config_home = _xdg("XDG_CONFIG_HOME", ".config")
    data_home = _xdg("XDG_DATA_HOME", ".local/share")
    state_home = _xdg("XDG_STATE_HOME", ".local/state")
    cache_home = _xdg("XDG_CACHE_HOME", ".cache")

    config_file = config_home / "kanibako" / "kanibako.toml"

    if config is None:
        if not config_file.exists():
            # Check for legacy .rc file
            legacy = config_file.with_name("kanibako.rc")
            if legacy.exists():
                raise ConfigError(
                    f"Legacy config {legacy} found but no kanibako.toml. "
                    "Run 'kanibako setup' to migrate."
                )
            raise ConfigError(
                f"{config_file} is missing. Run 'kanibako setup' to set up."
            )
        config = load_config(config_file)

    rel = config.paths_relative_std_path
    data_path = data_home / rel
    state_path = state_home / rel
    cache_path = cache_home / rel
    credentials_path = data_path / config.paths_init_credentials_path

    # Ensure directories exist.
    config_file.parent.mkdir(parents=True, exist_ok=True)
    data_path.mkdir(parents=True, exist_ok=True)
    state_path.mkdir(parents=True, exist_ok=True)
    cache_path.mkdir(parents=True, exist_ok=True)

    return StandardPaths(
        config_home=config_home,
        data_home=data_home,
        state_home=state_home,
        cache_home=cache_home,
        config_file=config_file,
        data_path=data_path,
        state_path=state_path,
        cache_path=cache_path,
        credentials_path=credentials_path,
    )


def resolve_project(
    std: StandardPaths,
    config: KanibakoConfig,
    project_dir: str | None = None,
    *,
    initialize: bool = False,
) -> ProjectPaths:
    """Resolve (and optionally initialize) per-project paths.

    When *initialize* is True (used by ``start``), missing project directories
    are created and credential templates are copied in.  When False (used by
    subcommands like ``archive``/``purge``), the paths are merely computed.
    """
    raw = project_dir or os.getcwd()
    project_path = Path(raw).resolve()

    if not project_path.is_dir():
        raise ProjectError(f"Project path '{project_path}' does not exist.")

    phash = project_hash(str(project_path))
    project_dir_path = std.data_path / "projects" / phash
    metadata_path = project_dir_path
    home_path = project_dir_path / "home"
    vault_ro_path = project_path / "vault" / "share-ro"
    vault_rw_path = project_path / "vault" / "share-rw"

    is_new = False
    if initialize and not project_dir_path.is_dir():
        _init_project(
            std, metadata_path, home_path,
            vault_ro_path, vault_rw_path, project_path,
        )
        is_new = True

    if initialize:
        # Recovery: ensure home exists even if metadata_path was present.
        if not home_path.is_dir():
            home_path.mkdir(parents=True, exist_ok=True)
            _bootstrap_shell(home_path)
        # Backfill project-path.txt for pre-existing projects.
        breadcrumb = metadata_path / "project-path.txt"
        if metadata_path.is_dir() and not breadcrumb.exists():
            breadcrumb.write_text(str(project_path) + "\n")

    return ProjectPaths(
        project_path=project_path,
        project_hash=phash,
        metadata_path=metadata_path,
        home_path=home_path,
        vault_ro_path=vault_ro_path,
        vault_rw_path=vault_rw_path,
        is_new=is_new,
        mode=ProjectMode.account_centric,
    )


def _bootstrap_shell(home_path: Path) -> None:
    """Write minimal shell skeleton files into a new home directory."""
    bashrc = home_path / ".bashrc"
    if not bashrc.exists():
        bashrc.write_text(
            "# kanibako shell environment\n"
            "[ -f /etc/bashrc ] && . /etc/bashrc\n"
            'export PS1="(kanibako) \\u@\\h:\\w\\$ "\n'
        )
    profile = home_path / ".profile"
    if not profile.exists():
        profile.write_text(
            "# kanibako login profile\n"
            "[ -f ~/.bashrc ] && . ~/.bashrc\n"
        )


def _init_project(
    std: StandardPaths,
    metadata_path: Path,
    home_path: Path,
    vault_ro_path: Path,
    vault_rw_path: Path,
    project_path: Path,
) -> None:
    """First-time project setup: create directories, copy credential template."""
    import sys

    print(
        f"[One Time Setup] Initializing kanibako in {project_path}... ",
        end="",
        flush=True,
        file=sys.stderr,
    )
    metadata_path.mkdir(parents=True, exist_ok=True)

    # Record the original project path for reverse lookup.
    (metadata_path / "project-path.txt").write_text(str(project_path) + "\n")

    # Create persistent agent home.
    home_path.mkdir(parents=True, exist_ok=True)
    _bootstrap_shell(home_path)

    # Copy credential template into home.
    creds = std.credentials_path
    if creds.is_dir():
        # Copy credentials into home/.claude/ directory structure.
        _copy_credentials_to_home(creds, home_path)
    else:
        # No credential template; create minimal structure.
        (home_path / ".claude").mkdir(parents=True, exist_ok=True)
        (home_path / ".claude.json").touch()

    # Vault directories.
    vault_ro_path.mkdir(parents=True, exist_ok=True)
    vault_rw_path.mkdir(parents=True, exist_ok=True)
    # .gitignore in vault/ to exclude share-rw from version control.
    vault_dir = vault_ro_path.parent
    gitignore = vault_dir / ".gitignore"
    if not gitignore.exists():
        gitignore.write_text("share-rw/\n")

    print("done.", file=sys.stderr)


def _copy_credentials_to_home(creds_source: Path, home_path: Path) -> None:
    """Copy credential template tree from central store into home directory.

    The central store has the old layout (dotclaude/.credentials.json, claude.json).
    This copies into the new natural-path layout (home/.claude/.credentials.json,
    home/.claude.json).
    """
    # Find the dotclaude directory (or whatever paths_dot_path is configured as).
    for child in creds_source.iterdir():
        if child.is_dir():
            # This is the dot_path equivalent (e.g. "dotclaude/")
            dst_claude = home_path / ".claude"
            dst_claude.mkdir(parents=True, exist_ok=True)
            # Copy contents (e.g. .credentials.json)
            for item in child.iterdir():
                if item.is_file():
                    shutil.copy2(str(item), str(dst_claude / item.name))
        elif child.is_file() and child.name != "project-path.txt":
            # This is likely claude.json → .claude.json
            shutil.copy2(str(child), str(home_path / f".{child.name}" if not child.name.startswith(".") else child.name))


def detect_project_mode(
    project_dir: Path,
    std: StandardPaths,
    config: KanibakoConfig,
) -> ProjectMode:
    """Infer which project mode applies to *project_dir*.

    Detection order:
    1. Workset — *project_dir* lives inside a registered workset root's
       ``workspaces/`` directory.
    2. Account-centric — ``projects/{hash}/`` already exists under
       *std.data_path*.
    3. Decentralized — a ``kanibako`` **directory** exists inside
       *project_dir*.
    4. Default — ``account_centric`` (new project).
    """
    # 1. Workset check: is project_dir inside a registered workset's
    #    workspaces/ directory?
    worksets_toml = std.data_path / "worksets.toml"
    if worksets_toml.is_file():
        import tomllib as _tomllib
        with open(worksets_toml, "rb") as _f:
            _data = _tomllib.load(_f)
        for _root_str in _data.get("worksets", {}).values():
            _ws_workspaces = Path(_root_str) / "workspaces"
            try:
                project_dir.relative_to(_ws_workspaces)
                return ProjectMode.workset
            except ValueError:
                continue

    # 2. Account-centric: projects/{hash}/ already exists
    phash = project_hash(str(project_dir))
    projects_path = std.data_path / "projects" / phash
    if projects_path.is_dir():
        return ProjectMode.account_centric

    # 3. Decentralized: kanibako directory inside project (no dot prefix)
    if (project_dir / "kanibako").is_dir():
        return ProjectMode.decentralized

    # 4. Default for new projects
    return ProjectMode.account_centric


def resolve_workset_project(
    ws: Workset,
    project_name: str,
    std: StandardPaths,
    config: KanibakoConfig,
    *,
    initialize: bool = False,
) -> ProjectPaths:
    """Resolve per-project paths for a project inside a workset.

    Raises ``WorksetError`` if *project_name* is not registered in *ws*.
    """
    # Look up project in workset.
    found = None
    for p in ws.projects:
        if p.name == project_name:
            found = p
            break
    if found is None:
        raise WorksetError(
            f"Project '{project_name}' not found in workset '{ws.name}'."
        )

    # Name-based paths (not hash-based).
    project_path = ws.workspaces_dir / project_name
    project_dir = ws.projects_dir / project_name
    metadata_path = project_dir
    home_path = project_dir / "home"
    vault_ro_path = ws.vault_dir / project_name / "share-ro"
    vault_rw_path = ws.vault_dir / project_name / "share-rw"

    # Hash the resolved workspace path for container naming.
    phash = project_hash(str(project_path.resolve()))

    is_new = False
    if initialize and not home_path.is_dir():
        _init_workset_project(std, metadata_path, home_path)
        is_new = True

    if initialize:
        # Recovery: ensure home exists.
        if not home_path.is_dir():
            home_path.mkdir(parents=True, exist_ok=True)
            _bootstrap_shell(home_path)

    return ProjectPaths(
        project_path=project_path,
        project_hash=phash,
        metadata_path=metadata_path,
        home_path=home_path,
        vault_ro_path=vault_ro_path,
        vault_rw_path=vault_rw_path,
        is_new=is_new,
        mode=ProjectMode.workset,
    )


def _init_workset_project(
    std: StandardPaths,
    metadata_path: Path,
    home_path: Path,
) -> None:
    """First-time workset project setup: copy credentials and bootstrap shell.

    Unlike ``_init_project``, this does not write a ``project-path.txt``
    breadcrumb (workset.toml already records source_path) and does not create
    vault ``.gitignore`` files (vault lives under the workset root, not inside
    a user git repo).
    """
    import sys

    print(
        f"[One Time Setup] Initializing workset project in {metadata_path}... ",
        end="",
        flush=True,
        file=sys.stderr,
    )
    metadata_path.mkdir(parents=True, exist_ok=True)

    # Create persistent agent home.
    home_path.mkdir(parents=True, exist_ok=True)
    _bootstrap_shell(home_path)

    # Copy credential template into home.
    creds = std.credentials_path
    if creds.is_dir():
        _copy_credentials_to_home(creds, home_path)
    else:
        (home_path / ".claude").mkdir(parents=True, exist_ok=True)
        (home_path / ".claude.json").touch()

    print("done.", file=sys.stderr)


def iter_projects(std: StandardPaths, config: KanibakoConfig) -> list[tuple[Path, Path | None]]:
    """Return ``(metadata_path, project_path | None)`` for every known project.

    *project_path* is read from the ``project-path.txt`` breadcrumb when
    available; otherwise it is ``None``.
    """
    projects_dir = std.data_path / "projects"
    if not projects_dir.is_dir():
        return []
    results: list[tuple[Path, Path | None]] = []
    for entry in sorted(projects_dir.iterdir()):
        if not entry.is_dir():
            continue
        breadcrumb = entry / "project-path.txt"
        project_path = None
        if breadcrumb.is_file():
            text = breadcrumb.read_text().strip()
            if text:
                project_path = Path(text)
        results.append((entry, project_path))
    return results


def iter_workset_projects(
    std: StandardPaths,
    config: KanibakoConfig,
) -> list[tuple[str, "Workset", list[tuple[str, str]]]]:
    """Return workset project info for all registered worksets.

    Each entry is ``(workset_name, workset, [(project_name, status), ...])``.
    Status is ``"ok"``, ``"missing"`` (no workspace), or ``"no-data"``
    (no project dir).
    """
    import sys

    from kanibako.workset import list_worksets, load_workset

    registry = list_worksets(std)
    results: list[tuple[str, Workset, list[tuple[str, str]]]] = []

    for ws_name in sorted(registry):
        root = registry[ws_name]
        if not root.is_dir():
            print(
                f"Warning: workset '{ws_name}' root missing: {root}",
                file=sys.stderr,
            )
            continue
        try:
            ws = load_workset(root)
        except Exception as exc:
            print(
                f"Warning: failed to load workset '{ws_name}': {exc}",
                file=sys.stderr,
            )
            continue

        project_list: list[tuple[str, str]] = []
        for proj in ws.projects:
            has_project_dir = (ws.projects_dir / proj.name).is_dir()
            has_workspace = (ws.workspaces_dir / proj.name).is_dir()
            if has_project_dir and has_workspace:
                status = "ok"
            elif has_project_dir and not has_workspace:
                status = "missing"
            else:
                status = "no-data"
            project_list.append((proj.name, status))

        results.append((ws_name, ws, project_list))

    return results


def _find_workset_for_path(project_dir: Path, std: StandardPaths) -> tuple[Workset, str]:
    """Return ``(Workset, project_name)`` for a path inside a workset workspace.

    *project_dir* may be the workspace root or a subdirectory within it.
    Raises ``WorksetError`` if *project_dir* does not belong to any
    registered workset.
    """
    from kanibako.workset import list_worksets, load_workset

    registry = list_worksets(std)
    for _name, root in registry.items():
        ws_workspaces = root / "workspaces"
        try:
            rel = project_dir.relative_to(ws_workspaces)
        except ValueError:
            continue
        project_name = rel.parts[0]
        ws = load_workset(root)
        return ws, project_name
    raise WorksetError(f"No workset found for path: {project_dir}")


def resolve_any_project(
    std: StandardPaths,
    config: KanibakoConfig,
    project_dir: str | None = None,
    *,
    initialize: bool = False,
) -> ProjectPaths:
    """Auto-detect project mode and resolve paths accordingly."""
    raw = project_dir or os.getcwd()
    raw_dir = Path(raw).resolve()
    mode = detect_project_mode(raw_dir, std, config)
    if mode == ProjectMode.workset:
        ws, proj_name = _find_workset_for_path(raw_dir, std)
        return resolve_workset_project(ws, proj_name, std, config, initialize=initialize)
    if mode == ProjectMode.decentralized:
        return resolve_decentralized_project(std, config, project_dir, initialize=initialize)
    return resolve_project(std, config, project_dir=project_dir, initialize=initialize)


def resolve_decentralized_project(
    std: StandardPaths,
    config: KanibakoConfig,
    project_dir: str | None = None,
    *,
    initialize: bool = False,
) -> ProjectPaths:
    """Resolve (and optionally initialize) per-project paths for decentralized mode.

    All project state lives inside *project_dir* itself (``kanibako/``,
    ``home/``, ``vault/``).  No data is written to ``$XDG_DATA_HOME``.
    """
    raw = project_dir or os.getcwd()
    project_path = Path(raw).resolve()

    if not project_path.is_dir():
        raise ProjectError(f"Project path '{project_path}' does not exist.")

    phash = project_hash(str(project_path))
    metadata_path = project_path / "kanibako"
    home_path = project_path / "home"
    vault_ro_path = project_path / "vault" / "share-ro"
    vault_rw_path = project_path / "vault" / "share-rw"

    is_new = False
    if initialize and not metadata_path.is_dir():
        _init_decentralized_project(
            std, metadata_path, home_path,
            vault_ro_path, vault_rw_path, project_path,
        )
        is_new = True

    if initialize:
        # Recovery: ensure home exists.
        if not home_path.is_dir():
            home_path.mkdir(parents=True, exist_ok=True)
            _bootstrap_shell(home_path)

    return ProjectPaths(
        project_path=project_path,
        project_hash=phash,
        metadata_path=metadata_path,
        home_path=home_path,
        vault_ro_path=vault_ro_path,
        vault_rw_path=vault_rw_path,
        is_new=is_new,
        mode=ProjectMode.decentralized,
    )


def _init_decentralized_project(
    std: StandardPaths,
    metadata_path: Path,
    home_path: Path,
    vault_ro_path: Path,
    vault_rw_path: Path,
    project_path: Path,
) -> None:
    """First-time decentralized project setup: all state inside project dir.

    Unlike ``_init_project``, this does not write a ``project-path.txt``
    breadcrumb (the project is self-contained).  Unlike workset init, this
    *does* create vault directories and a ``.gitignore`` (vault lives inside
    the user's project, likely a git repo).
    """
    import sys

    print(
        f"[One Time Setup] Initializing kanibako in {project_path}... ",
        end="",
        flush=True,
        file=sys.stderr,
    )
    metadata_path.mkdir(parents=True, exist_ok=True)

    # Create persistent agent home.
    home_path.mkdir(parents=True, exist_ok=True)
    _bootstrap_shell(home_path)

    # Copy credential template into home.
    creds = std.credentials_path
    if creds.is_dir():
        _copy_credentials_to_home(creds, home_path)
    else:
        (home_path / ".claude").mkdir(parents=True, exist_ok=True)
        (home_path / ".claude.json").touch()

    # Vault directories.
    vault_ro_path.mkdir(parents=True, exist_ok=True)
    vault_rw_path.mkdir(parents=True, exist_ok=True)
    # .gitignore in vault/ to exclude share-rw from version control.
    vault_dir = vault_ro_path.parent
    gitignore = vault_dir / ".gitignore"
    if not gitignore.exists():
        gitignore.write_text("share-rw/\n")

    print("done.", file=sys.stderr)
