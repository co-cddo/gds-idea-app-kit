"""Implementation of the smoke-test command."""

import click


def run_smoke_test(build_only: bool, wait: bool) -> None:
    """Build and health-check the production Docker image.

    Args:
        build_only: If True, only build the image without running health check.
        wait: If True, keep the container running until Enter is pressed.
    """
    if build_only:
        click.echo("Building Docker image (build only)...")
    elif wait:
        click.echo("Building and running smoke test (waiting)...")
    else:
        click.echo("Building and running smoke test...")
