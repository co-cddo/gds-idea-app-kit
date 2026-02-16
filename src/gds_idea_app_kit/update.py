"""Implementation of the update command.

Compares gds-idea-app-kit managed files against the manifest hashes to detect
local modifications, then overwrites unchanged files with the latest templates.
Locally modified files get a .new file written alongside for manual review,
unless --force is used to overwrite everything.

The update is structured as plan -> apply -> report:

1. _plan_updates() classifies each tracked file into an Action (CREATE, UPDATE,
   SKIP, or FORCE) without touching the filesystem.
2. _apply_updates() writes files to disk based on the plan.
3. _report_updates() prints results to the user.
"""

import sys
from dataclasses import dataclass
from enum import Enum
from pathlib import Path

import click

from gds_idea_app_kit import __version__
from gds_idea_app_kit.init import _apply_template_vars, _get_templates_dir
from gds_idea_app_kit.manifest import (
    build_manifest,
    get_tracked_files,
    hash_file,
    read_manifest,
    write_manifest,
)


class Action(Enum):
    """What to do with a tracked file during update."""

    CREATE = "create"  # file missing from project
    UPDATE = "update"  # file unchanged from manifest, overwrite with latest
    SKIP = "skip"  # locally modified, write .new alongside
    FORCE = "force"  # locally modified, overwrite anyway (--force)


@dataclass
class FileUpdate:
    """A planned update action for a single tracked file.

    Attributes:
        dest_path: Relative path in the project (e.g. "app_src/Dockerfile").
        dest_full: Absolute path to the file.
        new_content: Rendered template content to write.
        action: What to do with this file.
    """

    dest_path: str
    dest_full: Path
    new_content: str
    action: Action


def _parse_version(version: str) -> tuple[int, ...]:
    """Parse a dotted version string into a tuple of integers for comparison.

    Args:
        version: A dotted version string (e.g. "0.1.0").

    Returns:
        Tuple of integers (e.g. (0, 1, 0)).
    """
    return tuple(int(x) for x in version.split("."))


def _check_version(manifest: dict) -> None:
    """Warn if the installed tool is older than the version that created the project.

    Args:
        manifest: The manifest dict from pyproject.toml.
    """
    manifest_version = manifest.get("tool_version", "0.0.0")
    try:
        if _parse_version(__version__) < _parse_version(manifest_version):
            click.echo(
                f"Warning: This project was created with gds-idea-app-kit {manifest_version}, "
                f"but you have {__version__} installed.",
                err=True,
            )
            click.echo(
                "  Consider upgrading: uv tool upgrade gds-idea-app-kit",
                err=True,
            )
            click.echo()
    except (ValueError, TypeError):
        # Don't crash on malformed version strings
        pass


def _render_template(template_path: Path, template_vars: dict[str, str]) -> str:
    """Read a template file and apply variable substitution.

    Args:
        template_path: Path to the template file.
        template_vars: Mapping of placeholder names to values.

    Returns:
        The rendered template content.
    """
    content = template_path.read_text()
    return _apply_template_vars(content, template_vars)


def _classify_file(
    dest_full: Path,
    manifest_hashes: dict[str, str],
    dest_path: str,
    force: bool,
) -> Action:
    """Determine the action for a single tracked file.

    Args:
        dest_full: Absolute path to the file in the project.
        manifest_hashes: Mapping of relative paths to their manifest hashes.
        dest_path: Relative path of the file (used as key into manifest_hashes).
        force: Whether --force was specified.

    Returns:
        The Action to take for this file.
    """
    if not dest_full.exists():
        return Action.CREATE

    current_hash = hash_file(dest_full)
    manifest_hash = manifest_hashes.get(dest_path)
    is_modified = manifest_hash is not None and current_hash != manifest_hash

    if not is_modified:
        return Action.UPDATE

    return Action.FORCE if force else Action.SKIP


def _plan_updates(
    project_dir: Path,
    tracked: dict[str, str],
    templates_dir: Path,
    template_vars: dict[str, str],
    manifest_hashes: dict[str, str],
    force: bool,
) -> list[FileUpdate]:
    """Build the update plan by classifying each tracked file.

    This is a pure planning step -- no filesystem writes, no output.

    Args:
        project_dir: The project root directory.
        tracked: Mapping of template source paths to destination paths.
        templates_dir: Root directory containing template files.
        template_vars: Template variable substitutions.
        manifest_hashes: Current manifest file hashes.
        force: Whether --force was specified.

    Returns:
        List of FileUpdate objects describing what to do with each file.
    """
    plan = []
    for template_src, dest_path in sorted(tracked.items()):
        template_full = templates_dir / template_src

        if not template_full.exists():
            continue

        new_content = _render_template(template_full, template_vars)
        dest_full = project_dir / dest_path
        action = _classify_file(dest_full, manifest_hashes, dest_path, force)

        plan.append(FileUpdate(dest_path, dest_full, new_content, action))

    return plan


def _apply_updates(plan: list[FileUpdate]) -> None:
    """Write files to disk based on the update plan.

    CREATE, UPDATE, and FORCE actions write to the destination path.
    SKIP actions write a .new file alongside for manual review.

    Args:
        plan: List of FileUpdate objects from _plan_updates().
    """
    for item in plan:
        if item.action == Action.SKIP:
            new_path = Path(f"{item.dest_full}.new")
            new_path.write_text(item.new_content)
        else:
            item.dest_full.parent.mkdir(parents=True, exist_ok=True)
            item.dest_full.write_text(item.new_content)


def _report_updates(plan: list[FileUpdate], dry_run: bool) -> None:
    """Print the results of the update to the user.

    Args:
        plan: List of FileUpdate objects from _plan_updates().
        dry_run: Whether this was a dry run.
    """
    created = [item for item in plan if item.action == Action.CREATE]
    updated = [item for item in plan if item.action in (Action.UPDATE, Action.FORCE)]
    skipped = [item for item in plan if item.action == Action.SKIP]

    for item in created:
        click.echo(f"  Created: {item.dest_path}")

    for item in updated:
        click.echo(f"  Updated: {item.dest_path}")

    if skipped:
        click.echo()
        for item in skipped:
            click.echo(f"  Skipped: {item.dest_path} (locally modified)")
            click.echo(f"    New version written to: {item.dest_path}.new")
            click.echo(f"    Review changes: diff {item.dest_path} {item.dest_path}.new")

    if not created and not updated and not skipped:
        click.echo("  Nothing to update.")

    if skipped and not dry_run:
        click.echo()
        count = len(skipped)
        click.echo(
            f"{count} file(s) were locally modified and skipped. Review the .new files above,"
        )
        click.echo("then rename or delete them when done.")

    if dry_run:
        click.echo()
        click.echo("No changes made (dry run).")


def _update_manifest(
    project_dir: Path,
    framework: str,
    app_name: str,
    python_version: str,
) -> None:
    """Rebuild and write the manifest after applying updates.

    Args:
        project_dir: The project root directory.
        framework: The framework name (e.g. "streamlit").
        app_name: The application name.
        python_version: The Python version string.
    """
    click.echo()
    click.echo("Updating manifest...")
    new_manifest = build_manifest(
        framework=framework,
        app_name=app_name,
        tool_version=__version__,
        project_dir=project_dir,
    )
    new_manifest["python_version"] = python_version
    write_manifest(project_dir, new_manifest)


def run_update(dry_run: bool, force: bool = False) -> None:
    """Update gds-idea-app-kit managed files in an existing project.

    Reads the manifest from pyproject.toml, plans updates by classifying each
    tracked file, then applies the plan (unless --dry-run).

    Args:
        dry_run: If True, show what would change without applying.
        force: If True, overwrite locally modified files without creating .new files.
    """
    project_dir = Path.cwd()
    pyproject_path = project_dir / "pyproject.toml"

    if not pyproject_path.exists():
        click.echo("Error: No pyproject.toml found. Are you in a project root?", err=True)
        sys.exit(1)

    # -- Read manifest --
    manifest = read_manifest(project_dir)
    if not manifest:
        click.echo(
            "Error: No [tool.gds-idea-app-kit] section found in pyproject.toml.",
            err=True,
        )
        click.echo("  This doesn't look like a project created by idea-app.", err=True)
        sys.exit(1)

    framework = manifest.get("framework")
    app_name = manifest.get("app_name")
    if not framework or not app_name:
        click.echo("Error: Manifest is missing framework or app_name.", err=True)
        sys.exit(1)

    # -- Check version --
    _check_version(manifest)

    if dry_run:
        click.echo("Dry run: showing what would change...")
    elif force:
        click.echo("Updating gds-idea-app-kit managed files (force)...")
    else:
        click.echo("Updating gds-idea-app-kit managed files...")
    click.echo()

    # -- Prepare template variables --
    python_version = manifest.get("python_version", "3.13")
    python_version_nodot = python_version.replace(".", "")
    template_vars = {
        "app_name": app_name,
        "python_version": python_version,
        "python_version_nodot": python_version_nodot,
    }

    templates_dir = _get_templates_dir()
    tracked = get_tracked_files(framework)
    manifest_hashes = manifest.get("files", {})

    # -- Plan -> Apply -> Report --
    plan = _plan_updates(project_dir, tracked, templates_dir, template_vars, manifest_hashes, force)

    if not dry_run:
        _apply_updates(plan)

    _report_updates(plan, dry_run)

    has_writes = any(item.action in (Action.CREATE, Action.UPDATE, Action.FORCE) for item in plan)
    if not dry_run and has_writes:
        _update_manifest(project_dir, framework, app_name, python_version)
