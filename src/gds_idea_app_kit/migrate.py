"""Implementation of the migrate command.

Converts an existing project created from the old dumper template to work with
idea-app. Creates the [tool.gds-idea-app-kit] manifest from the current state
of tracked files, removes old template/ directory and entry points, and
optionally updates files to the latest templates.

Usage:
    idea-app migrate    # interactive, run from project root
"""

import re
import shutil
import sys
import tomllib
from pathlib import Path

import click
import tomlkit

from gds_idea_app_kit import __version__
from gds_idea_app_kit.manifest import build_manifest, read_manifest, write_manifest
from gds_idea_app_kit.update import run_update


def _detect_python_version(project_dir: Path) -> str:
    """Detect the Python version from project files.

    Checks the Dockerfile for a FROM python:X.Y line first, then falls back
    to requires-python in app_src/pyproject.toml.

    Args:
        project_dir: The project root directory.

    Returns:
        The Python version string (e.g. "3.13").
    """
    # Try Dockerfile first: FROM python:X.Y-slim
    dockerfile = project_dir / "app_src" / "Dockerfile"
    if dockerfile.exists():
        match = re.search(r"FROM python:(\d+\.\d+)", dockerfile.read_text())
        if match:
            return match.group(1)

    # Try app_src/pyproject.toml: requires-python = ">=X.Y"
    app_pyproject = project_dir / "app_src" / "pyproject.toml"
    if app_pyproject.exists():
        with open(app_pyproject, "rb") as f:
            config = tomllib.load(f)
        requires = config.get("project", {}).get("requires-python", "")
        match = re.search(r"(\d+\.\d+)", requires)
        if match:
            return match.group(1)

    return "3.13"


def _read_webapp_config(project_dir: Path) -> dict[str, str]:
    """Read framework and app_name from [tool.webapp] in pyproject.toml.

    Args:
        project_dir: The project root directory.

    Returns:
        Dict with "framework" and "app_name".
    """
    pyproject_path = project_dir / "pyproject.toml"

    if not pyproject_path.exists():
        click.echo("Error: No pyproject.toml found. Are you in a project root?", err=True)
        sys.exit(1)

    with open(pyproject_path, "rb") as f:
        config = tomllib.load(f)

    webapp = config.get("tool", {}).get("webapp", {})
    framework = webapp.get("framework", "")
    app_name = webapp.get("app_name", "")

    if not framework or not app_name:
        click.echo("Error: No [tool.webapp] section with framework and app_name found.", err=True)
        click.echo("  This doesn't look like a project created from the template.", err=True)
        sys.exit(1)

    return {"framework": framework, "app_name": app_name}


def _remove_old_config(project_dir: Path) -> None:
    """Remove old template entry points and build config from pyproject.toml.

    Removes:
    - [project.scripts] entries (configure, smoke_test, provide_role)
    - [build-system] section
    - [tool.uv.build-backend] section
    - Sets package = false in [tool.uv]

    Preserves all other content.

    Args:
        project_dir: The project root directory.
    """
    pyproject_path = project_dir / "pyproject.toml"
    with open(pyproject_path) as f:
        config = tomlkit.load(f)

    # Remove [build-system]
    if "build-system" in config:
        del config["build-system"]

    # Remove [project.scripts]
    if "project" in config and "scripts" in config["project"]:
        del config["project"]["scripts"]

    # Remove [tool.uv.build-backend] and set package = false
    if "tool" in config and "uv" in config["tool"]:
        uv_config = config["tool"]["uv"]
        if "build-backend" in uv_config:
            del uv_config["build-backend"]
        uv_config["package"] = False

    with open(pyproject_path, "w") as f:
        tomlkit.dump(config, f)


def _remove_template_dir(project_dir: Path) -> None:
    """Remove the old template/ directory if it exists.

    Args:
        project_dir: The project root directory.
    """
    template_dir = project_dir / "template"
    if template_dir.is_dir():
        shutil.rmtree(template_dir)


def run_migrate() -> None:
    """Migrate an existing project to use idea-app.

    Interactive command that:
    1. Reads existing [tool.webapp] config
    2. Builds a manifest from current tracked files
    3. Removes old template/ directory and entry points
    4. Optionally runs update to get latest template files
    """
    project_dir = Path.cwd()
    pyproject_path = project_dir / "pyproject.toml"

    # -- Pre-flight checks --
    if not pyproject_path.exists():
        click.echo("Error: No pyproject.toml found. Are you in a project root?", err=True)
        sys.exit(1)

    manifest = read_manifest(project_dir)
    if manifest:
        click.echo("This project has already been migrated.", err=True)
        click.echo("  Use 'idea-app update' instead.", err=True)
        sys.exit(1)

    webapp_config = _read_webapp_config(project_dir)
    framework = webapp_config["framework"]
    app_name = webapp_config["app_name"]
    python_version = _detect_python_version(project_dir)

    # -- Summary --
    click.echo(f"Migrating project: {app_name} ({framework})")
    click.echo(f"  Python version: {python_version}")
    click.echo()
    click.echo("This will:")
    click.echo("  - Add [tool.gds-idea-app-kit] manifest to pyproject.toml")
    click.echo("  - Remove old template/ directory and entry points")
    click.echo("  - Set package = false in [tool.uv]")
    click.echo("  - Remove [build-system]")
    click.echo()
    click.echo("Recommendation: run this on a clean branch.")
    click.echo("  git checkout -b migrate-to-idea-app")
    click.echo()

    if not click.confirm("Continue?", default=False):
        click.echo("Aborted.")
        return

    # -- Execute migration --
    click.echo()
    click.echo("Building manifest from current files...")
    new_manifest = build_manifest(
        framework=framework,
        app_name=app_name,
        tool_version=__version__,
        project_dir=project_dir,
    )
    new_manifest["python_version"] = python_version
    write_manifest(project_dir, new_manifest)

    click.echo("Removing old template configuration...")
    _remove_old_config(project_dir)

    template_dir = project_dir / "template"
    if template_dir.is_dir():
        click.echo("Removing template/ directory...")
        _remove_template_dir(project_dir)

    click.echo("Migration complete.")
    click.echo()

    # -- Offer update --
    if not click.confirm("Would you like to update to the latest template files?", default=True):
        click.echo("Run 'idea-app update' when ready.")
        return

    click.echo()
    run_update(dry_run=True)

    click.echo()
    if not click.confirm("Apply these changes?", default=True):
        click.echo("Run 'idea-app update' when ready.")
        return

    click.echo()
    run_update(dry_run=False)

    # -- Next steps --
    click.echo()
    click.echo("Next steps:")
    click.echo("  1. Review changes: git diff")
    click.echo('  2. Commit: git add -A && git commit -m "Migrate to idea-app"')
