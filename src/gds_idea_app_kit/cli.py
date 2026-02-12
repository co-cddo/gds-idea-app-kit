"""CLI entry point for idea-app."""

import click

from gds_idea_app_kit import DEFAULT_PYTHON_VERSION, __version__


@click.group()
@click.version_option(version=__version__, prog_name="idea-app")
def cli():
    """GDS IDEA App Kit - scaffold and maintain web apps on AWS."""


@cli.command()
@click.argument("framework", type=click.Choice(["streamlit", "dash", "fastapi"]))
@click.argument("app_name")
@click.option(
    "--python",
    "python_version",
    default=DEFAULT_PYTHON_VERSION,
    show_default=True,
    help="Python version for the project.",
)
def init(framework: str, app_name: str, python_version: str):
    """Scaffold a new project: idea-app init <framework> <app-name>."""
    from gds_idea_app_kit.init import run_init

    run_init(framework=framework, app_name=app_name, python_version=python_version)


@cli.command()
@click.option("--dry-run", is_flag=True, help="Show what would change without applying.")
def update(dry_run: bool):
    """Update tool-owned files in an existing project."""
    from gds_idea_app_kit.update import run_update

    run_update(dry_run=dry_run)


@cli.command("smoke-test")
@click.option("--build-only", is_flag=True, help="Only build the Docker image, skip health check.")
@click.option("--wait", is_flag=True, help="Keep container running until Enter is pressed.")
def smoke_test(build_only: bool, wait: bool):
    """Build and health-check the production Docker image."""
    from gds_idea_app_kit.smoke_test import run_smoke_test

    run_smoke_test(build_only=build_only, wait=wait)


@cli.command("provide-role")
@click.option("--use-profile", is_flag=True, help="Use current AWS profile directly.")
@click.option(
    "--duration",
    type=int,
    default=3600,
    show_default=True,
    help="Session duration in seconds for role assumption.",
)
def provide_role(use_profile: bool, duration: int):
    """Provide AWS credentials to the dev container."""
    from gds_idea_app_kit.provide_role import run_provide_role

    run_provide_role(use_profile=use_profile, duration=duration)
