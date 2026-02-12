"""Implementation of the update command.

Compares gds-idea-app-kit managed files against the manifest hashes to detect
local modifications, then overwrites unchanged files with the latest templates.
Locally modified files get a .new file written alongside for manual review,
unless --force is used to overwrite everything.
"""

import sys
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


def run_update(dry_run: bool, force: bool = False) -> None:
    """Update gds-idea-app-kit managed files in an existing project.

    Reads the manifest from pyproject.toml, compares file hashes to detect
    local modifications, and overwrites unchanged files with the latest
    templates from the installed version of gds-idea-app-kit.

    Locally modified files are not overwritten unless --force is used. Instead,
    the new version is written alongside as a .new file for manual review.

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

    updated = []
    skipped = []
    created = []

    for template_src, dest_path in sorted(tracked.items()):
        dest_full = project_dir / dest_path
        template_full = templates_dir / template_src

        if not template_full.exists():
            # Template file missing from installed package -- skip silently
            continue

        new_content = _render_template(template_full, template_vars)

        if not dest_full.exists():
            # File is missing from project -- create it
            if not dry_run:
                dest_full.parent.mkdir(parents=True, exist_ok=True)
                dest_full.write_text(new_content)
            created.append(dest_path)
            continue

        # File exists -- check if user has modified it
        current_hash = hash_file(dest_full)
        manifest_hash = manifest_hashes.get(dest_path)

        if manifest_hash and current_hash != manifest_hash:
            if force:
                # Force mode -- overwrite the file
                if not dry_run:
                    dest_full.write_text(new_content)
                updated.append(dest_path)
            else:
                # Normal mode -- write .new alongside for review
                new_path = Path(f"{dest_full}.new")
                if not dry_run:
                    new_path.write_text(new_content)
                skipped.append(dest_path)
            continue

        # File is unchanged (or wasn't in the old manifest) -- overwrite
        if not dry_run:
            dest_full.write_text(new_content)
        updated.append(dest_path)

    # -- Report results --
    if created:
        for path in created:
            click.echo(f"  Created: {path}")

    if updated:
        for path in updated:
            click.echo(f"  Updated: {path}")

    if skipped:
        click.echo()
        for path in skipped:
            click.echo(f"  Skipped: {path} (locally modified)")
            click.echo(f"    New version written to: {path}.new")
            click.echo(f"    Review changes: diff {path} {path}.new")

    if not created and not updated and not skipped:
        click.echo("  Nothing to update.")

    # -- Update manifest --
    if not dry_run and (created or updated):
        click.echo()
        click.echo("Updating manifest...")
        new_manifest = build_manifest(
            framework=framework,
            app_name=app_name,
            tool_version=__version__,
            project_dir=project_dir,
        )
        # Preserve python_version in manifest
        new_manifest["python_version"] = python_version
        write_manifest(project_dir, new_manifest)

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
