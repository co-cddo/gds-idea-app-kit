"""Implementation of the init command."""

import click


def run_init(framework: str, app_name: str, python_version: str) -> None:
    """Scaffold a new project.

    Args:
        framework: The web framework (streamlit, dash, fastapi).
        app_name: Name for the application.
        python_version: Python version for the project.
    """
    click.echo(f"Initializing {framework} app: {app_name} (Python {python_version})")
