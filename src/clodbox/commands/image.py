"""clodbox image: list built-in/local/remote container images."""

from __future__ import annotations

import argparse
import json
import sys
import urllib.request
import urllib.error
from pathlib import Path

from clodbox.config import load_config, load_merged_config
from clodbox.container import ContainerRuntime
from clodbox.errors import ContainerError
from clodbox.paths import _xdg, load_std_paths, resolve_project


# Descriptions for known Containerfile variants.
_VARIANT_DESCRIPTIONS = {
    "base": "Python, nano, git, jq, ssh, gh, archives",
    "systems": "C/C++, Rust, assemblers, QEMU, debuggers",
    "jvm": "Java, Kotlin, Maven",
    "android": "JVM + Gradle, Android SDK",
    "ndk": "Android + systems toolchain",
    "dotnet": ".NET SDK 8.0",
    "behemoth": "All toolchains combined",
}


def add_parser(subparsers: argparse._SubParsersAction) -> None:
    p = subparsers.add_parser(
        "image",
        help="List available container images",
        description="List available container images (built-in variants, local, and remote).",
    )
    p.add_argument(
        "-p", "--project", default=None, help="Show current image for a specific project"
    )
    p.set_defaults(func=run)


def run(args: argparse.Namespace) -> int:
    config_file = _xdg("XDG_CONFIG_HOME", ".config") / "clodbox" / "clodbox.toml"
    config = load_config(config_file)
    std = load_std_paths(config)
    proj = resolve_project(std, config, project_dir=args.project, initialize=False)

    # Merged config for current image display
    project_toml = proj.settings_path / "project.toml"
    merged = load_merged_config(config_file, project_toml)

    # ---- Built-in Variants ----
    containers_dir = std.data_path / "containers"
    found_variants = False
    if containers_dir.is_dir():
        for cf in sorted(containers_dir.glob("Containerfile.*")):
            variant = cf.suffix.lstrip(".")
            if not found_variants:
                print("Built-in image variants:")
                found_variants = True
            desc = _VARIANT_DESCRIPTIONS.get(variant, "(no description)")
            print(f"  {variant:<12} {desc}")

    if not found_variants:
        print("Built-in image variants: (none installed -- run clodbox install first)")

    print()

    # ---- Local Images ----
    try:
        runtime = ContainerRuntime()
        print("Local images:")
        images = runtime.list_local_images()
        if images:
            for repo, size in images:
                print(f"  {repo:<50} {size}")
        else:
            print("  (none)")
    except ContainerError:
        print("Local images: (no container runtime found)")

    print()

    # ---- Remote Registry Images ----
    image = merged.container_image
    owner = _extract_ghcr_owner(image)

    print("Remote registry images:")
    if owner:
        _list_remote_packages(owner)
    elif not owner and image:
        print(f"  (registry owner not detected from image: {image})")
    else:
        print("  (image not configured)")

    print()

    # ---- Current Image ----
    print(f"Current image: {merged.container_image}")
    return 0


def _extract_ghcr_owner(image: str) -> str | None:
    """Extract GitHub owner from ghcr.io/<owner>/... image path."""
    if not image.startswith("ghcr.io/"):
        return None
    remainder = image[len("ghcr.io/"):]
    return remainder.split("/")[0] if "/" in remainder else None


def _list_remote_packages(owner: str) -> None:
    """Query GitHub API for the owner's clodbox container packages."""
    url = f"https://api.github.com/users/{owner}/packages?package_type=container"
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "clodbox"})
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read())
    except (urllib.error.URLError, OSError, json.JSONDecodeError):
        print("  (could not reach GitHub API)")
        return

    packages = [pkg["name"] for pkg in data if "clodbox" in pkg.get("name", "").lower()]
    if packages:
        for pkg in packages:
            print(f"  ghcr.io/{owner}/{pkg}")
    else:
        print(f"  (no clodbox packages found for {owner})")
