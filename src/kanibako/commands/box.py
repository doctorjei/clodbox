"""kanibako box: project lifecycle management (list, migrate, duplicate, archive, purge, restore)."""

from __future__ import annotations

import argparse
import shutil
import sys
from pathlib import Path

from kanibako.config import load_config
from kanibako.errors import ProjectError
from kanibako.paths import (
    ProjectMode,
    _find_workset_for_path,
    _xdg,
    detect_project_mode,
    iter_projects,
    iter_workset_projects,
    load_std_paths,
    resolve_any_project,
    resolve_decentralized_project,
    resolve_project,
    resolve_workset_project,
)
from kanibako.utils import confirm_prompt, project_hash, short_hash

_MODE_CHOICES = ["account-centric", "decentralized", "workset"]


def add_parser(subparsers: argparse._SubParsersAction) -> None:
    p = subparsers.add_parser(
        "box",
        help="Project lifecycle commands (list, migrate, duplicate, archive, purge, restore)",
        description="Manage per-project session data: list, migrate, duplicate, archive, purge, restore.",
    )
    box_sub = p.add_subparsers(dest="box_command", metavar="COMMAND")

    # kanibako box list (default behavior)
    list_p = box_sub.add_parser(
        "list",
        help="List known projects and their status (default)",
        description="List all known kanibako projects with their hash, status, and path.",
    )
    list_p.set_defaults(func=run_list)

    # kanibako box migrate
    migrate_p = box_sub.add_parser(
        "migrate",
        help="Remap project data from old path to new path, or convert between modes",
        description=(
            "Move project session data from one path hash to another.\n"
            "Use this after moving or renaming a project directory.\n"
            "With --to, convert a project between modes (e.g. account-centric to decentralized)."
        ),
    )
    migrate_p.add_argument(
        "old_path", nargs="?", default=None,
        help="Original project directory path (for path remap), or project path (for --to)",
    )
    migrate_p.add_argument(
        "new_path", nargs="?", default=None,
        help="New project directory path (default: current working directory)",
    )
    migrate_p.add_argument(
        "--to", dest="to_mode", choices=_MODE_CHOICES, default=None,
        help="Convert project to a different mode",
    )
    migrate_p.add_argument(
        "--force", action="store_true", help="Skip confirmation prompt",
    )
    migrate_p.add_argument(
        "--workset", default=None,
        help="Target workset name (required when --to workset)",
    )
    migrate_p.add_argument(
        "--name", dest="project_name", default=None,
        help="Project name in workset (default: directory basename)",
    )
    migrate_p.add_argument(
        "--in-place", action="store_true", dest="in_place",
        help="Keep workspace at current location (don't move into workset)",
    )
    migrate_p.set_defaults(func=run_migrate)

    # kanibako box duplicate
    duplicate_p = box_sub.add_parser(
        "duplicate",
        help="Duplicate a project (workspace + metadata) under a new path",
        description=(
            "Copy a project's workspace directory and kanibako metadata to a new path.\n"
            "The metadata is re-keyed under the new path's hash.\n"
            "With --to, duplicate into a different mode layout."
        ),
    )
    duplicate_p.add_argument("source_path", help="Existing project directory to duplicate")
    duplicate_p.add_argument("new_path", help="Destination path for the duplicate")
    duplicate_p.add_argument(
        "--bare", action="store_true",
        help="Copy only kanibako metadata, don't touch the workspace directory",
    )
    duplicate_p.add_argument(
        "--to", dest="to_mode", choices=_MODE_CHOICES, default=None,
        help="Duplicate into a different mode layout",
    )
    duplicate_p.add_argument(
        "--force", action="store_true",
        help="Skip confirmation, overwrite existing data/metadata at destination",
    )
    duplicate_p.add_argument(
        "--workset", default=None,
        help="Target workset name (required when --to workset)",
    )
    duplicate_p.add_argument(
        "--name", dest="project_name", default=None,
        help="Project name in workset (default: directory basename)",
    )
    duplicate_p.set_defaults(func=run_duplicate)

    # kanibako box info
    info_p = box_sub.add_parser(
        "info",
        help="Show project details",
        description="Show project mode, paths, and status for a kanibako project.",
    )
    info_p.add_argument("path", nargs="?", default=None, help="Project directory (default: cwd)")
    info_p.set_defaults(func=run_info)

    # Reuse existing subcommand modules under box.
    from kanibako.commands.archive import add_parser as add_archive_parser
    from kanibako.commands.clean import add_parser as add_purge_parser
    from kanibako.commands.restore import add_parser as add_restore_parser

    add_archive_parser(box_sub)
    add_purge_parser(box_sub)
    add_restore_parser(box_sub)

    # Default to list if no subcommand given.
    p.set_defaults(func=run_list)


def run_list(args: argparse.Namespace) -> int:
    config_file = _xdg("XDG_CONFIG_HOME", ".config") / "kanibako" / "kanibako.toml"
    config = load_config(config_file)
    std = load_std_paths(config)

    projects = iter_projects(std, config)
    ws_data = iter_workset_projects(std, config)

    if not projects and not ws_data:
        print("No known projects.")
        return 0

    if projects:
        print(f"{'HASH':<10} {'STATUS':<10} {'PATH'}")
        for settings_path, project_path in projects:
            h8 = short_hash(settings_path.name)
            if project_path is None:
                status = "unknown"
                label = "(no breadcrumb)"
            elif project_path.is_dir():
                status = "ok"
                label = str(project_path)
            else:
                status = "missing"
                label = str(project_path)
            print(f"{h8:<10} {status:<10} {label}")

    for ws_name, ws, project_list in ws_data:
        print()
        print(f"Working set: {ws_name} ({ws.root})")
        if project_list:
            print(f"  {'NAME':<18} {'STATUS':<10} {'SOURCE'}")
            for proj_name, status in project_list:
                # Look up source_path from workset projects.
                source = ""
                for p in ws.projects:
                    if p.name == proj_name:
                        source = str(p.source_path)
                        break
                print(f"  {proj_name:<18} {status:<10} {source}")
        else:
            print("  (no projects)")

    return 0


def run_migrate(args: argparse.Namespace) -> int:
    import os

    config_file = _xdg("XDG_CONFIG_HOME", ".config") / "kanibako" / "kanibako.toml"
    config = load_config(config_file)
    std = load_std_paths(config)

    # Cross-mode conversion.
    if getattr(args, "to_mode", None) is not None:
        return _run_convert(args, std, config)

    # Same-mode path remap: old_path is required.
    if args.old_path is None:
        print("Error: old_path is required for path remap (use --to for mode conversion).", file=sys.stderr)
        return 1

    # Resolve paths — old path may no longer exist, so use str directly.
    old_path = Path(args.old_path).resolve()
    new_path = Path(args.new_path).resolve() if args.new_path else Path(os.getcwd()).resolve()

    # Validate: paths must differ.
    if old_path == new_path:
        print("Error: old and new paths are the same.", file=sys.stderr)
        return 1

    # Validate: new path must exist as a directory.
    if not new_path.is_dir():
        print(f"Error: new path does not exist as a directory: {new_path}", file=sys.stderr)
        return 1

    # Compute hashes.
    old_hash = project_hash(str(old_path))
    new_hash = project_hash(str(new_path))

    projects_base = std.data_path / "settings"
    old_project_dir = projects_base / old_hash
    new_project_dir = projects_base / new_hash

    # Validate: old project data must exist.
    if not old_project_dir.is_dir():
        print(
            f"Error: no project data found for old path: {old_path}",
            file=sys.stderr,
        )
        print(f"  (expected: {old_project_dir})", file=sys.stderr)
        return 1

    # Validate: new project data must NOT already exist.
    if new_project_dir.is_dir():
        print(
            f"Error: project data already exists for new path: {new_path}",
            file=sys.stderr,
        )
        print("  Use 'kanibako box purge' to remove it first.", file=sys.stderr)
        return 1

    # Warn if lock file exists.
    lock_file = old_project_dir / ".kanibako.lock"
    if lock_file.exists():
        print(
            "Warning: lock file found — a container may be running for this project.",
            file=sys.stderr,
        )
        if not args.force:
            try:
                confirm_prompt("Continue anyway? Type 'yes' to confirm: ")
            except Exception:
                print("Aborted.")
                return 2

    # Confirm with user.
    if not args.force:
        print(f"Migrate project data:")
        print(f"  from: {old_path}")
        print(f"    to: {new_path}")
        print()
        try:
            confirm_prompt("Type 'yes' to confirm: ")
        except Exception:
            print("Aborted.")
            return 2

    # Rename project directory (includes home/ inside it).
    old_project_dir.rename(new_project_dir)

    # Update the breadcrumb.
    breadcrumb = new_project_dir / "project-path.txt"
    breadcrumb.write_text(str(new_path) + "\n")

    print(f"Migrated project data:")
    print(f"  from: {old_path} ({short_hash(old_hash)})")
    print(f"    to: {new_path} ({short_hash(new_hash)})")
    return 0


# -- Cross-mode conversion helpers --

def _run_convert(args: argparse.Namespace, std, config) -> int:
    """Dispatch cross-mode conversion based on --to flag."""
    import os

    to_mode_str = args.to_mode

    # Convert TO workset: separate code path.
    if to_mode_str == "workset":
        return _convert_to_workset(args, std, config)

    # Resolve project path (positional arg or cwd).
    raw_path = args.old_path or os.getcwd()
    project_path = Path(raw_path).resolve()

    if not project_path.is_dir():
        print(f"Error: project path does not exist: {project_path}", file=sys.stderr)
        return 1

    # Detect current mode.
    current_mode = detect_project_mode(project_path, std, config)

    # Convert FROM workset: separate code path.
    if current_mode == ProjectMode.workset:
        return _convert_from_workset(args, project_path, std, config)

    # Parse target mode.
    target_mode = ProjectMode.decentralized if to_mode_str == "decentralized" else ProjectMode.account_centric

    if current_mode == target_mode:
        print(f"Error: project is already in {current_mode.value} mode.", file=sys.stderr)
        return 1

    # Resolve current project paths.
    if current_mode == ProjectMode.account_centric:
        proj = resolve_project(std, config, project_dir=str(project_path), initialize=False)
    else:
        proj = resolve_decentralized_project(std, config, project_dir=str(project_path), initialize=False)

    # Check that project data exists.
    if not proj.metadata_path.is_dir():
        print(f"Error: no project data found for {project_path}", file=sys.stderr)
        return 1

    # Lock file warning.
    lock_file = proj.metadata_path / ".kanibako.lock"
    if lock_file.exists():
        print(
            "Warning: lock file found — a container may be running for this project.",
            file=sys.stderr,
        )
        if not args.force:
            print("Aborted.")
            return 2

    # Confirm with user.
    if not args.force:
        print(f"Convert project to {target_mode.value} mode:")
        print(f"  project: {project_path}")
        print(f"  from:    {current_mode.value}")
        print(f"    to:    {target_mode.value}")
        print()
        try:
            confirm_prompt("Type 'yes' to confirm: ")
        except Exception:
            print("Aborted.")
            return 2

    # Dispatch.
    if target_mode == ProjectMode.decentralized:
        _convert_ac_to_decentral(project_path, std, config, proj)
    else:
        _convert_decentral_to_ac(project_path, std, config, proj)

    print(f"Converted project to {target_mode.value} mode:")
    print(f"  project: {project_path}")
    return 0


def _convert_ac_to_decentral(project_path, std, config, proj):
    """Convert an account-centric project to decentralized layout."""
    from kanibako.commands.init import _write_project_gitignore

    dst_metadata = project_path / ".kanibako"
    dst_shell = dst_metadata / "shell"

    # Copy metadata (excluding lock file and shell/ directory).
    shutil.copytree(
        proj.metadata_path, dst_metadata,
        ignore=shutil.ignore_patterns(".kanibako.lock", "shell"),
    )

    # Remove breadcrumb (decentralized doesn't use it).
    breadcrumb = dst_metadata / "project-path.txt"
    if breadcrumb.exists():
        breadcrumb.unlink()

    # Copy shell.
    if proj.shell_path.is_dir():
        shutil.copytree(proj.shell_path, dst_shell)

    # Write .gitignore entries for .kanibako/.
    _write_project_gitignore(project_path)

    # Write vault .gitignore if vault exists but gitignore doesn't.
    vault_dir = project_path / "vault"
    if vault_dir.is_dir():
        vault_gitignore = vault_dir / ".gitignore"
        if not vault_gitignore.exists():
            vault_gitignore.write_text("share-rw/\n")

    # Clean up old AC data.
    shutil.rmtree(proj.metadata_path)


def _convert_decentral_to_ac(project_path, std, config, proj):
    """Convert a decentralized project to account-centric layout."""
    phash = project_hash(str(project_path))
    settings_base = std.data_path / "settings"
    dst_project = settings_base / phash

    # Copy metadata (excluding lock file and shell/).
    shutil.copytree(
        proj.metadata_path, dst_project,
        ignore=shutil.ignore_patterns(".kanibako.lock", "shell"),
    )

    # Write breadcrumb.
    (dst_project / "project-path.txt").write_text(str(project_path) + "\n")

    # Copy shell into the settings dir.
    if proj.shell_path.is_dir():
        dst_shell = dst_project / "shell"
        shutil.copytree(proj.shell_path, dst_shell)

    # Clean up old decentralized data.
    shutil.rmtree(proj.metadata_path)


# -- Workset conversion helpers --

def _convert_to_workset(args, std, config) -> int:
    """Convert an AC or decentralized project into a workset."""
    import os

    from kanibako.workset import add_project, list_worksets, load_workset

    ws_name = getattr(args, "workset", None)
    if not ws_name:
        print("Error: --workset is required when converting to workset mode.", file=sys.stderr)
        return 1

    # Load target workset.
    registry = list_worksets(std)
    if ws_name not in registry:
        print(f"Error: workset '{ws_name}' not found.", file=sys.stderr)
        return 1
    ws = load_workset(registry[ws_name])

    # Resolve source project.
    raw_path = args.old_path or os.getcwd()
    project_path = Path(raw_path).resolve()

    if not project_path.is_dir():
        print(f"Error: project path does not exist: {project_path}", file=sys.stderr)
        return 1

    current_mode = detect_project_mode(project_path, std, config)
    if current_mode == ProjectMode.workset:
        print("Error: project is already in workset mode.", file=sys.stderr)
        return 1

    # Determine project name.
    proj_name = getattr(args, "project_name", None) or project_path.name

    # Validate name not taken.
    for p in ws.projects:
        if p.name == proj_name:
            print(f"Error: project '{proj_name}' already exists in workset '{ws_name}'.", file=sys.stderr)
            return 1

    # Resolve source paths.
    if current_mode == ProjectMode.account_centric:
        src_proj = resolve_project(std, config, project_dir=str(project_path), initialize=False)
    else:
        src_proj = resolve_decentralized_project(std, config, project_dir=str(project_path), initialize=False)

    if not src_proj.metadata_path.is_dir():
        print(f"Error: no project data found for {project_path}", file=sys.stderr)
        return 1

    # Lock file warning.
    lock_file = src_proj.metadata_path / ".kanibako.lock"
    if lock_file.exists():
        print(
            "Warning: lock file found — a container may be running for this project.",
            file=sys.stderr,
        )
        if not args.force:
            print("Aborted.")
            return 2

    in_place = getattr(args, "in_place", False)

    # Confirm.
    if not args.force:
        action = "in-place (workspace stays)" if in_place else "move workspace into workset"
        print(f"Convert project to workset mode ({action}):")
        print(f"  project:  {project_path}")
        print(f"  workset:  {ws_name}")
        print(f"  name:     {proj_name}")
        print()
        try:
            confirm_prompt("Type 'yes' to confirm: ")
        except Exception:
            print("Aborted.")
            return 2

    # Register project in workset (creates skeleton dirs).
    add_project(ws, proj_name, project_path)

    # Copy metadata (excluding lock, breadcrumb, and home/).
    dst_project = ws.projects_dir / proj_name
    shutil.copytree(
        src_proj.metadata_path, dst_project,
        ignore=shutil.ignore_patterns(".kanibako.lock", "project-path.txt", "shell"),
        dirs_exist_ok=True,
    )

    # Copy home.
    if src_proj.shell_path.is_dir():
        dst_home = dst_project / "shell"
        shutil.copytree(src_proj.shell_path, dst_home, dirs_exist_ok=True)

    # Move workspace unless --in-place.
    if not in_place:
        dst_workspace = ws.workspaces_dir / proj_name
        # Copy workspace content (exclude decentralized metadata).
        ignore = None
        if current_mode == ProjectMode.decentralized:
            ignore = shutil.ignore_patterns(".kanibako")
        shutil.copytree(project_path, dst_workspace, ignore=ignore, dirs_exist_ok=True)

    # Clean up old metadata.
    shutil.rmtree(src_proj.metadata_path)
    if src_proj.shell_path.is_dir():
        shutil.rmtree(src_proj.shell_path)

    print(f"Converted project to workset mode:")
    print(f"  workset: {ws_name}/{proj_name}")
    return 0


def _convert_from_workset(args, project_path, std, config) -> int:
    """Convert a workset project to AC or decentralized mode."""
    to_mode_str = args.to_mode

    ws, proj_name = _find_workset_for_path(project_path, std)
    src_proj = resolve_workset_project(ws, proj_name, std, config, initialize=False)

    target_mode = ProjectMode.decentralized if to_mode_str == "decentralized" else ProjectMode.account_centric

    if not src_proj.metadata_path.is_dir():
        print(f"Error: no project data found for {project_path}", file=sys.stderr)
        return 1

    # Lock file warning.
    lock_file = src_proj.metadata_path / ".kanibako.lock"
    if lock_file.exists():
        print(
            "Warning: lock file found — a container may be running for this project.",
            file=sys.stderr,
        )
        if not args.force:
            print("Aborted.")
            return 2

    # Determine destination path: use source_path from workset project.
    found_proj = None
    for p in ws.projects:
        if p.name == proj_name:
            found_proj = p
            break
    dest_path = found_proj.source_path if found_proj else project_path

    # Confirm.
    if not args.force:
        print(f"Convert workset project to {target_mode.value} mode:")
        print(f"  workset:  {ws.name}/{proj_name}")
        print(f"  target:   {dest_path}")
        print()
        try:
            confirm_prompt("Type 'yes' to confirm: ")
        except Exception:
            print("Aborted.")
            return 2

    if target_mode == ProjectMode.account_centric:
        _convert_ws_to_ac(src_proj, dest_path, std, config)
    else:
        _convert_ws_to_decentral(src_proj, dest_path)

    # Move workspace from workset to destination if it exists and differs.
    ws_workspace = ws.workspaces_dir / proj_name
    in_place = getattr(args, "in_place", False)
    if not in_place and ws_workspace.is_dir() and ws_workspace != dest_path:
        dest_path.mkdir(parents=True, exist_ok=True)
        shutil.copytree(ws_workspace, dest_path, dirs_exist_ok=True)

    # Remove workset registration + workset dirs.
    from kanibako.workset import remove_project

    remove_project(ws, proj_name, remove_files=True)

    print(f"Converted project to {target_mode.value} mode:")
    print(f"  project: {dest_path}")
    return 0


def _convert_ws_to_ac(src_proj, dest_path, std, config):
    """Copy workset project metadata into account-centric layout."""
    phash = project_hash(str(dest_path))
    projects_base = std.data_path / "settings"
    dst_project = projects_base / phash

    # Copy metadata (excluding lock and home/).
    shutil.copytree(
        src_proj.metadata_path, dst_project,
        ignore=shutil.ignore_patterns(".kanibako.lock", "shell"),
    )

    # Write breadcrumb.
    (dst_project / "project-path.txt").write_text(str(dest_path) + "\n")

    # Copy home.
    if src_proj.shell_path.is_dir():
        dst_home = dst_project / "shell"
        shutil.copytree(src_proj.shell_path, dst_home)


def _convert_ws_to_decentral(src_proj, dest_path):
    """Copy workset project metadata into decentralized layout."""
    from kanibako.commands.init import _write_project_gitignore

    dest_path.mkdir(parents=True, exist_ok=True)
    dst_metadata = dest_path / ".kanibako"
    dst_shell = dst_metadata / "shell"

    # Copy metadata (excluding lock and shell/).
    shutil.copytree(
        src_proj.metadata_path, dst_metadata,
        ignore=shutil.ignore_patterns(".kanibako.lock", "shell"),
    )

    # Copy shell.
    if src_proj.shell_path.is_dir():
        shutil.copytree(src_proj.shell_path, dst_shell)

    _write_project_gitignore(dest_path)

    # Write vault .gitignore if vault exists.
    vault_dir = dest_path / "vault"
    if vault_dir.is_dir():
        vault_gitignore = vault_dir / ".gitignore"
        if not vault_gitignore.exists():
            vault_gitignore.write_text("share-rw/\n")


# -- Cross-mode duplicate helpers --

def _run_duplicate_cross_mode(args: argparse.Namespace, std, config) -> int:
    """Duplicate a project into a different mode layout."""
    import os

    to_mode_str = args.to_mode

    # Duplicate TO workset: separate code path.
    if to_mode_str == "workset":
        return _duplicate_to_workset(args, std, config)

    source_path = Path(args.source_path).resolve()
    new_path = Path(args.new_path).resolve()

    if source_path == new_path:
        print("Error: source and destination paths are the same.", file=sys.stderr)
        return 1

    if not source_path.is_dir():
        print(f"Error: source path does not exist as a directory: {source_path}", file=sys.stderr)
        return 1

    # Detect source mode and resolve.
    source_mode = detect_project_mode(source_path, std, config)

    # Duplicate FROM workset: separate code path.
    if source_mode == ProjectMode.workset:
        return _duplicate_from_workset(args, source_path, new_path, std, config)

    if source_mode == ProjectMode.account_centric:
        src_proj = resolve_project(std, config, project_dir=str(source_path), initialize=False)
    else:
        src_proj = resolve_decentralized_project(std, config, project_dir=str(source_path), initialize=False)

    if not src_proj.metadata_path.is_dir():
        print(f"Error: no project data found for source path: {source_path}", file=sys.stderr)
        return 1

    # Lock file warning.
    lock_file = src_proj.metadata_path / ".kanibako.lock"
    if lock_file.exists():
        print(
            "Warning: lock file found — a container may be running for this project.",
            file=sys.stderr,
        )
        if not args.force:
            print("Aborted.")
            return 2

    # Confirm with user.
    target_mode = ProjectMode.decentralized if to_mode_str == "decentralized" else ProjectMode.account_centric
    if not args.force:
        mode = "metadata only (bare)" if args.bare else "workspace + metadata"
        print(f"Duplicate project ({mode}) to {target_mode.value} mode:")
        print(f"  from: {source_path}")
        print(f"    to: {new_path}")
        print()
        try:
            confirm_prompt("Type 'yes' to confirm: ")
        except Exception:
            print("Aborted.")
            return 2

    # Copy workspace (unless --bare).
    if not args.bare:
        shutil.copytree(source_path, new_path, dirs_exist_ok=args.force)

    # Copy metadata into target mode layout.
    if target_mode == ProjectMode.decentralized:
        _duplicate_to_decentral(src_proj, new_path, args.force)
    else:
        _duplicate_to_ac(src_proj, new_path, std, config, args.force)

    print(f"Duplicated project to {target_mode.value} mode:")
    print(f"  from: {source_path}")
    print(f"    to: {new_path}")
    return 0


def _duplicate_to_decentral(src_proj, new_path, force):
    """Copy metadata into decentralized layout at new_path."""
    from kanibako.commands.init import _write_project_gitignore

    dst_metadata = new_path / ".kanibako"
    dst_shell = dst_metadata / "shell"

    # Ensure new_path exists for bare duplicates.
    new_path.mkdir(parents=True, exist_ok=True)

    if force and dst_metadata.is_dir():
        shutil.rmtree(dst_metadata)
    shutil.copytree(
        src_proj.metadata_path, dst_metadata,
        ignore=shutil.ignore_patterns(".kanibako.lock", "shell"),
    )

    # Remove breadcrumb if present (decentralized doesn't use it).
    breadcrumb = dst_metadata / "project-path.txt"
    if breadcrumb.exists():
        breadcrumb.unlink()

    if src_proj.shell_path.is_dir():
        if force and dst_shell.is_dir():
            shutil.rmtree(dst_shell)
        shutil.copytree(src_proj.shell_path, dst_shell)

    _write_project_gitignore(new_path)

    # Write vault .gitignore if vault exists.
    vault_dir = new_path / "vault"
    if vault_dir.is_dir():
        vault_gitignore = vault_dir / ".gitignore"
        if not vault_gitignore.exists():
            vault_gitignore.write_text("share-rw/\n")


def _duplicate_to_ac(src_proj, new_path, std, config, force):
    """Copy metadata into account-centric layout for new_path."""
    phash = project_hash(str(new_path))
    projects_base = std.data_path / "settings"
    dst_project = projects_base / phash

    if force and dst_project.is_dir():
        shutil.rmtree(dst_project)
    shutil.copytree(
        src_proj.metadata_path, dst_project,
        ignore=shutil.ignore_patterns(".kanibako.lock"),
    )

    # Write breadcrumb.
    (dst_project / "project-path.txt").write_text(str(new_path) + "\n")

    # Ensure home is inside the project dir.
    if src_proj.shell_path.is_dir():
        dst_home = dst_project / "shell"
        if not dst_home.is_dir():
            shutil.copytree(src_proj.shell_path, dst_home)


def _duplicate_to_workset(args, std, config) -> int:
    """Duplicate a project into a workset (source untouched)."""
    from kanibako.workset import add_project, list_worksets, load_workset

    ws_name = getattr(args, "workset", None)
    if not ws_name:
        print("Error: --workset is required when duplicating to workset mode.", file=sys.stderr)
        return 1

    registry = list_worksets(std)
    if ws_name not in registry:
        print(f"Error: workset '{ws_name}' not found.", file=sys.stderr)
        return 1
    ws = load_workset(registry[ws_name])

    source_path = Path(args.source_path).resolve()
    if not source_path.is_dir():
        print(f"Error: source path does not exist as a directory: {source_path}", file=sys.stderr)
        return 1

    source_mode = detect_project_mode(source_path, std, config)
    if source_mode == ProjectMode.workset:
        print("Error: source is already a workset project.", file=sys.stderr)
        return 1

    proj_name = getattr(args, "project_name", None) or source_path.name

    # Validate name not taken.
    for p in ws.projects:
        if p.name == proj_name:
            print(f"Error: project '{proj_name}' already exists in workset '{ws_name}'.", file=sys.stderr)
            return 1

    if source_mode == ProjectMode.account_centric:
        src_proj = resolve_project(std, config, project_dir=str(source_path), initialize=False)
    else:
        src_proj = resolve_decentralized_project(std, config, project_dir=str(source_path), initialize=False)

    if not src_proj.metadata_path.is_dir():
        print(f"Error: no project data found for source path: {source_path}", file=sys.stderr)
        return 1

    # Lock file warning.
    lock_file = src_proj.metadata_path / ".kanibako.lock"
    if lock_file.exists():
        print(
            "Warning: lock file found — a container may be running for this project.",
            file=sys.stderr,
        )
        if not args.force:
            print("Aborted.")
            return 2

    if not args.force:
        mode = "metadata only (bare)" if args.bare else "workspace + metadata"
        print(f"Duplicate project ({mode}) to workset:")
        print(f"  from:    {source_path}")
        print(f"  workset: {ws_name}/{proj_name}")
        print()
        try:
            confirm_prompt("Type 'yes' to confirm: ")
        except Exception:
            print("Aborted.")
            return 2

    # Register in workset (creates skeleton dirs).
    add_project(ws, proj_name, source_path)

    # Copy metadata (excluding lock, breadcrumb, and home/).
    dst_project = ws.projects_dir / proj_name
    shutil.copytree(
        src_proj.metadata_path, dst_project,
        ignore=shutil.ignore_patterns(".kanibako.lock", "project-path.txt", "shell"),
        dirs_exist_ok=True,
    )

    # Copy home.
    if src_proj.shell_path.is_dir():
        dst_home = dst_project / "shell"
        shutil.copytree(src_proj.shell_path, dst_home, dirs_exist_ok=True)

    # Copy workspace (unless --bare).
    if not args.bare:
        dst_workspace = ws.workspaces_dir / proj_name
        ignore = None
        if source_mode == ProjectMode.decentralized:
            ignore = shutil.ignore_patterns(".kanibako")
        shutil.copytree(source_path, dst_workspace, ignore=ignore, dirs_exist_ok=True)

    print(f"Duplicated project to workset:")
    print(f"  from:    {source_path}")
    print(f"  workset: {ws_name}/{proj_name}")
    return 0


def _duplicate_from_workset(args, source_path, new_path, std, config) -> int:
    """Duplicate a workset project to AC or decentralized layout (source untouched)."""
    to_mode_str = args.to_mode

    ws, proj_name = _find_workset_for_path(source_path, std)
    src_proj = resolve_workset_project(ws, proj_name, std, config, initialize=False)

    if not src_proj.metadata_path.is_dir():
        print(f"Error: no project data found for source path: {source_path}", file=sys.stderr)
        return 1

    target_mode = ProjectMode.decentralized if to_mode_str == "decentralized" else ProjectMode.account_centric

    # Lock file warning.
    lock_file = src_proj.metadata_path / ".kanibako.lock"
    if lock_file.exists():
        print(
            "Warning: lock file found — a container may be running for this project.",
            file=sys.stderr,
        )
        if not args.force:
            print("Aborted.")
            return 2

    if not args.force:
        mode = "metadata only (bare)" if args.bare else "workspace + metadata"
        print(f"Duplicate workset project ({mode}) to {target_mode.value} mode:")
        print(f"  from: {ws.name}/{proj_name}")
        print(f"    to: {new_path}")
        print()
        try:
            confirm_prompt("Type 'yes' to confirm: ")
        except Exception:
            print("Aborted.")
            return 2

    # Copy workspace (unless --bare).
    if not args.bare:
        ws_workspace = ws.workspaces_dir / proj_name
        if ws_workspace.is_dir():
            shutil.copytree(ws_workspace, new_path, dirs_exist_ok=args.force)

    # Copy metadata into target layout.
    if target_mode == ProjectMode.decentralized:
        _duplicate_to_decentral(src_proj, new_path, args.force)
    else:
        _duplicate_to_ac(src_proj, new_path, std, config, args.force)

    print(f"Duplicated project to {target_mode.value} mode:")
    print(f"  from: {ws.name}/{proj_name}")
    print(f"    to: {new_path}")
    return 0


def run_duplicate(args: argparse.Namespace) -> int:
    config_file = _xdg("XDG_CONFIG_HOME", ".config") / "kanibako" / "kanibako.toml"
    config = load_config(config_file)
    std = load_std_paths(config)

    # Cross-mode duplication.
    if getattr(args, "to_mode", None) is not None:
        return _run_duplicate_cross_mode(args, std, config)

    source_path = Path(args.source_path).resolve()
    new_path = Path(args.new_path).resolve()

    # 1. Paths must differ.
    if source_path == new_path:
        print("Error: source and destination paths are the same.", file=sys.stderr)
        return 1

    # 2. Source must be an existing directory.
    if not source_path.is_dir():
        print(f"Error: source path does not exist as a directory: {source_path}", file=sys.stderr)
        return 1

    # 3. Source must have kanibako metadata.
    source_hash = project_hash(str(source_path))
    projects_base = std.data_path / "settings"
    source_project_dir = projects_base / source_hash

    if not source_project_dir.is_dir():
        print(
            f"Error: no project data found for source path: {source_path}",
            file=sys.stderr,
        )
        return 1

    # 4. Non-bare: destination workspace must not already exist (unless --force).
    if not args.bare and new_path.exists() and not args.force:
        print(
            f"Error: destination already exists: {new_path}",
            file=sys.stderr,
        )
        print("  Use --force to overwrite.", file=sys.stderr)
        return 1

    # 5. Destination metadata must not already exist (unless --force).
    new_hash = project_hash(str(new_path))
    new_project_dir = projects_base / new_hash

    if new_project_dir.is_dir() and not args.force:
        print(
            f"Error: project data already exists for destination: {new_path}",
            file=sys.stderr,
        )
        print("  Use --force to overwrite.", file=sys.stderr)
        return 1

    # 6. Lock file warning.
    lock_file = source_project_dir / ".kanibako.lock"
    if lock_file.exists():
        print(
            "Warning: lock file found — a container may be running for this project.",
            file=sys.stderr,
        )
        if not args.force:
            print("Aborted.")
            return 2

    # 7. User confirmation.
    if not args.force:
        mode = "metadata only (bare)" if args.bare else "workspace + metadata"
        print(f"Duplicate project ({mode}):")
        print(f"  from: {source_path}")
        print(f"    to: {new_path}")
        print()
        try:
            confirm_prompt("Type 'yes' to confirm: ")
        except Exception:
            print("Aborted.")
            return 2

    # Copy workspace (unless --bare).
    if not args.bare:
        shutil.copytree(source_path, new_path, dirs_exist_ok=args.force)

    # Copy metadata (entire project dir including home/).
    if args.force and new_project_dir.is_dir():
        shutil.rmtree(new_project_dir)
    shutil.copytree(
        source_project_dir, new_project_dir,
        ignore=shutil.ignore_patterns(".kanibako.lock"),
    )

    # Update breadcrumb.
    breadcrumb = new_project_dir / "project-path.txt"
    breadcrumb.write_text(str(new_path) + "\n")

    print(f"Duplicated project:")
    print(f"  from: {source_path} ({short_hash(source_hash)})")
    print(f"    to: {new_path} ({short_hash(new_hash)})")
    return 0


def run_info(args: argparse.Namespace) -> int:
    config_file = _xdg("XDG_CONFIG_HOME", ".config") / "kanibako" / "kanibako.toml"
    config = load_config(config_file)
    std = load_std_paths(config)

    try:
        proj = resolve_any_project(std, config, project_dir=args.path, initialize=False)
    except ProjectError as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1

    if not proj.metadata_path.is_dir():
        print(f"Error: No project data found for {proj.project_path}", file=sys.stderr)
        return 1

    print(f"Mode:      {proj.mode.value}")
    print(f"Project:   {proj.project_path}")
    print(f"Hash:      {short_hash(proj.project_hash)}")
    print(f"Metadata:  {proj.metadata_path}")
    print(f"Shell:     {proj.shell_path}")
    print(f"Vault RO:  {proj.vault_ro_path}")
    print(f"Vault RW:  {proj.vault_rw_path}")

    lock_file = proj.metadata_path / ".kanibako.lock"
    if lock_file.exists():
        print(f"Lock:      ACTIVE ({lock_file})")
    else:
        print(f"Lock:      none")

    return 0
