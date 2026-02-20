"""Pre-requisite checks for external tools.

Verifies that tools like cdk, uv, git, docker, and the docker compose
plugin are installed and available before starting work.  Used by both
``init`` (checks everything) and ``smoke-test`` (checks docker only).
"""

import subprocess
import sys

import click

# Each entry is (display_name, check_command, install_hint, optional_url).
PREREQUISITES: list[tuple[str, list[str], str, str | None]] = [
    ("cdk", ["cdk", "--version"], "brew install aws-cdk", None),
    ("uv", ["uv", "--version"], "brew install uv", None),
    ("git", ["git", "--version"], "brew install git", None),
    ("docker", ["docker", "--version"], "brew install docker", None),
    (
        "docker compose",
        ["docker", "compose", "version"],
        "brew install docker-compose",
        "https://github.com/co-cddo/gds-idea-app-kit#docker-compose-not-found--unknown-shorthand-flag--f",
    ),
]


def check_prerequisites(only: list[str] | None = None) -> None:
    """Verify that required external tools are installed.

    Checks every tool and reports all missing ones at once, so the user
    can fix everything in a single pass rather than hitting errors one
    at a time.

    Args:
        only: If provided, only check tools whose display name is in
              this list.  If None, check all prerequisites.
    """
    to_check = PREREQUISITES
    if only is not None:
        to_check = [p for p in PREREQUISITES if p[0] in only]

    missing: list[tuple[str, str, str | None]] = []

    for name, check_cmd, install_hint, url in to_check:
        try:
            subprocess.run(check_cmd, capture_output=True, check=True)
        except (FileNotFoundError, subprocess.CalledProcessError):
            missing.append((name, install_hint, url))

    if not missing:
        return

    click.echo("Error: missing required tools:", err=True)
    click.echo("", err=True)
    for name, hint, url in missing:
        click.echo(f"  {name:20s} {hint}", err=True)
        if url:
            click.echo(f"  {'':20s} {url}", err=True)
    click.echo("", err=True)
    click.echo("Install the missing tools and try again.", err=True)
    sys.exit(1)
