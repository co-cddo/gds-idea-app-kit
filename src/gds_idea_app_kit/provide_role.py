"""Implementation of the provide-role command."""

import click


def run_provide_role(use_profile: bool, duration: int) -> None:
    """Provide AWS credentials to the dev container.

    Args:
        use_profile: If True, use the current AWS profile directly.
        duration: Session duration in seconds for role assumption.
    """
    if use_profile:
        click.echo(f"Using current AWS profile (duration={duration}s)...")
    else:
        click.echo(f"Assuming role (duration={duration}s)...")
