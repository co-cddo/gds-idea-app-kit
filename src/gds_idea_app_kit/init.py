"""Implementation of the init command."""

import re
import subprocess
import sys
from importlib.resources import files
from pathlib import Path

import click

from gds_idea_app_kit import REPO_PREFIX


def _sanitize_app_name(name: str) -> str:
    """Sanitize and validate an app name for use as a DNS subdomain label.

    The name will become part of a domain: {name}.gds-idea.click

    Args:
        name: The raw app name from the user.

    Returns:
        The cleaned app name.

    Raises:
        click.BadParameter: If the name is invalid.
    """
    # Strip the repo prefix if the user accidentally included it
    prefix = f"{REPO_PREFIX}-"
    if name.startswith(prefix):
        name = name[len(prefix) :]

    # Lowercase
    name = name.lower()

    # Validate DNS label rules
    if not name:
        raise click.BadParameter("App name cannot be empty.")

    if len(name) > 63:
        raise click.BadParameter("App name must be 63 characters or fewer (DNS label limit).")

    if not re.match(r"^[a-z0-9]([a-z0-9-]*[a-z0-9])?$", name):
        raise click.BadParameter(
            "App name must contain only lowercase letters, numbers, and hyphens, "
            "and must start and end with a letter or number."
        )

    if "--" in name:
        raise click.BadParameter("App name must not contain consecutive hyphens (--).")

    if name.isdigit():
        raise click.BadParameter("App name must not be purely numeric.")

    return name


def _get_templates_dir() -> Path:
    """Get the path to the bundled templates directory."""
    return Path(str(files("gds_idea_app_kit") / "templates"))


def _apply_template_vars(content: str, variables: dict[str, str]) -> str:
    """Apply template variable substitution to content.

    Replaces {{key}} with value for each entry in variables.

    Args:
        content: The template content with {{placeholders}}.
        variables: Mapping of placeholder names to values.

    Returns:
        Content with all placeholders replaced.
    """
    for key, value in variables.items():
        content = content.replace(f"{{{{{key}}}}}", value)
    return content


def _copy_template(src: Path, dest: Path, variables: dict[str, str] | None = None) -> None:
    """Copy a template file to a destination, optionally applying variable substitution.

    Args:
        src: Path to the source template file.
        dest: Path to the destination file.
        variables: Optional mapping of placeholder names to values.
    """
    dest.parent.mkdir(parents=True, exist_ok=True)
    content = src.read_text()
    if variables:
        content = _apply_template_vars(content, variables)
    dest.write_text(content)


def _run_command(
    cmd: list[str],
    cwd: Path,
    project_dir: Path | None = None,
) -> subprocess.CompletedProcess:
    """Run a subprocess command with error handling.

    Args:
        cmd: The command and arguments to run.
        cwd: Working directory for the command.
        project_dir: The project directory (for cleanup message on failure).
            If not provided, uses cwd.

    Returns:
        The completed process result.
    """
    cleanup_dir = project_dir or cwd
    try:
        return subprocess.run(cmd, cwd=cwd, check=True, capture_output=True, text=True)
    except FileNotFoundError:
        if cmd[0] == "cdk":
            click.echo("Error: 'cdk' is not installed.", err=True)
            click.echo("", err=True)
            click.echo("Install it with one of:", err=True)
            click.echo("  npm install -g aws-cdk", err=True)
            click.echo("  brew install aws-cdk", err=True)
        else:
            click.echo(f"Error: '{cmd[0]}' is not installed.", err=True)
        sys.exit(1)
    except subprocess.CalledProcessError as e:
        click.echo(f"Error running: {' '.join(cmd)}", err=True)
        if e.stderr:
            click.echo(e.stderr, err=True)
        click.echo("", err=True)
        click.echo("To clean up the failed project:", err=True)
        click.echo(f"  rm -rf {cleanup_dir}", err=True)
        sys.exit(1)


def run_init(framework: str, app_name: str, python_version: str) -> None:
    """Scaffold a new project.

    Args:
        framework: The web framework (streamlit, dash, fastapi).
        app_name: Name for the application.
        python_version: Python version for the project.
    """
    click.echo(f"Initializing {framework} app: {app_name} (Python {python_version})")
