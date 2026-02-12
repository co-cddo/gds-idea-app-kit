"""Implementation of the update command."""

import click


def run_update(dry_run: bool) -> None:
    """Update tool-owned files in an existing project.

    Args:
        dry_run: If True, show what would change without applying.
    """
    if dry_run:
        click.echo("Dry run: showing what would change...")
    else:
        click.echo("Updating tool-owned files...")
