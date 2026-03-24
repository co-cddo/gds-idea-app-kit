"""Implementation of the adopt command.

Adds CI/CD workflows, common configuration files, and the
gds-idea-cdk-constructs dependency to an existing CDK project that was
not originally scaffolded by idea-app.
"""

import sys
from datetime import datetime
from pathlib import Path

import click
import tomlkit

from gds_idea_app_kit import (
    GITHUB_ORG,
    REPO_PREFIX,
    __version__,
)
from gds_idea_app_kit.init import (
    _apply_template_vars,
    _copy_template,
    _get_templates_dir,
    _run_command,
)
from gds_idea_app_kit.manifest import (
    MANIFEST_KEY,
    build_manifest,
    read_manifest,
    write_manifest,
)
from gds_idea_app_kit.prerequisites import check_prerequisites
from gds_idea_app_kit.version import check_tool_is_current


def _read_project_name(project_dir: Path) -> str | None:
    """Read the project name from pyproject.toml [project].name.

    Args:
        project_dir: Root directory of the project.

    Returns:
        The project name, or None if not found.
    """
    pyproject_path = project_dir / "pyproject.toml"
    with open(pyproject_path) as f:
        config = tomlkit.load(f)
    return config.get("project", {}).get("name")


def run_adopt() -> None:
    """Add CI/CD and config files to an existing CDK project.

    Must be run from inside the project directory.  Requires an existing
    pyproject.toml and cdk.json.  Will not overwrite an existing manifest
    (use ``update`` for projects already managed by idea-app).
    """
    project_dir = Path.cwd()
    pyproject_path = project_dir / "pyproject.toml"
    cdk_json_path = project_dir / "cdk.json"

    # -- Validate project --
    if not pyproject_path.exists():
        click.echo("Error: No pyproject.toml found. Are you in a project root?", err=True)
        sys.exit(1)

    if not cdk_json_path.exists():
        click.echo("Error: No cdk.json found. This doesn't look like a CDK project.", err=True)
        sys.exit(1)

    existing_manifest = read_manifest(project_dir)
    if existing_manifest:
        click.echo(
            "Error: This project already has a [tool.gds-idea-app-kit] manifest.",
            err=True,
        )
        click.echo("  Use 'idea-app update' to update managed files.", err=True)
        sys.exit(1)

    # -- Check tool is current --
    check_tool_is_current()

    # -- Check prerequisites (no Docker needed for infra) --
    check_prerequisites(only=["cdk", "uv", "git"])

    # -- Determine app name --
    project_name = _read_project_name(project_dir)
    if not project_name:
        click.echo(
            "Error: Could not read project name from [project].name in pyproject.toml.",
            err=True,
        )
        sys.exit(1)

    # Strip the repo prefix if present to get the app name.
    prefix = f"{REPO_PREFIX}-"
    if project_name.startswith(prefix):
        app_name = project_name[len(prefix) :]
    else:
        app_name = project_name

    click.echo(f"Adopting project: {app_name}")
    click.echo(f"  Directory: {project_dir.name}/")
    click.echo()

    # -- Prepare template variables --
    template_vars = {
        "app_name": app_name,
        "year": str(datetime.now().year),
    }
    templates = _get_templates_dir()

    # -- Copy common files --
    click.echo("Copying common files...")

    # CI/CD workflows
    _copy_template(
        templates / "common" / "ci_cd_cdk_app.yml",
        project_dir / ".github" / "workflows" / "ci_cd_cdk_app.yml",
    )
    _copy_template(
        templates / "common" / "ci_pr_cdk_app.yml",
        project_dir / ".github" / "workflows" / "ci_pr_cdk_app.yml",
    )

    # CODEOWNERS
    _copy_template(
        templates / "common" / "CODEOWNERS.template",
        project_dir / ".github" / "CODEOWNERS",
    )

    # Dependabot
    _copy_template(
        templates / "common" / "dependabot.yml",
        project_dir / ".github" / "dependabot.yml",
    )

    # LICENCE
    _copy_template(
        templates / "common" / "LICENCE",
        project_dir / "LICENCE",
        variables=template_vars,
    )

    # README -- only if one doesn't already exist
    readme_path = project_dir / "README.md"
    if not readme_path.exists():
        _copy_template(
            templates / "common" / "README.md.template",
            readme_path,
            variables=template_vars,
        )
    else:
        click.echo("  Skipping README.md (already exists)")

    # Append to .gitignore if it exists
    gitignore = project_dir / ".gitignore"
    if gitignore.exists():
        extra = (templates / "common" / "gitignore-extra").read_text()
        with open(gitignore, "a") as f:
            f.write("\n")
            f.write(extra)
    else:
        _copy_template(templates / "common" / "gitignore-extra", gitignore)

    # -- Install gds-idea-cdk-constructs --
    click.echo("Installing gds-idea-cdk-constructs...")
    _run_command(
        [
            "uv",
            "add",
            "gds-idea-cdk-constructs>=0.3.0",
            "--index",
            "gds-idea=https://co-cddo.github.io/gds-idea-pypi/simple/",
        ],
        cwd=project_dir,
    )

    # -- Write [tool.webapp] config --
    click.echo("Writing project configuration...")
    pyproject_path = project_dir / "pyproject.toml"
    with open(pyproject_path) as f:
        config = tomlkit.load(f)

    if "tool" not in config:
        config["tool"] = {}

    webapp = tomlkit.table()
    webapp.add("app_name", app_name)
    webapp.add("framework", "infra")
    config["tool"]["webapp"] = webapp

    with open(pyproject_path, "w") as f:
        tomlkit.dump(config, f)

    # -- Build and write manifest --
    click.echo("Writing manifest...")
    manifest = build_manifest(
        framework="infra",
        app_name=app_name,
        tool_version=__version__,
        project_dir=project_dir,
    )
    write_manifest(project_dir, manifest)

    # -- Sync dependencies --
    click.echo("Syncing dependencies...")
    _run_command(["uv", "sync"], cwd=project_dir)

    # -- Done (don't auto-commit -- let the user review) --
    click.echo()
    click.echo("Done! Files have been added to your project.")
    click.echo()
    click.echo("Review the changes and commit when ready:")
    click.echo("  git add .")
    click.echo('  git commit -m "Adopt project into gds-idea-app-kit"')
    click.echo()
    click.echo("You can now use 'idea-app update' to keep managed files up to date.")
