"""Version currency check for the gds-idea-app-kit CLI.

Provides functions to fetch the latest published version from the internal
PyPI index and prompt the user to upgrade if a newer version is available.
"""

import re
import sys
import urllib.error
import urllib.request

import click

from gds_idea_app_kit import __version__

_GDS_IDEA_INDEX_URL = "https://co-cddo.github.io/gds-idea-pypi/simple/"


def _parse_version(version: str) -> tuple[int, ...]:
    """Parse a dotted version string into a tuple of integers for comparison.

    Args:
        version: A dotted version string (e.g. "0.1.0").

    Returns:
        Tuple of integers (e.g. (0, 1, 0)).
    """
    return tuple(int(x) for x in version.split("."))


def _fetch_latest_version(timeout: int = 3) -> str | None:
    """Fetch the latest published version of gds-idea-app-kit from the internal PyPI index.

    Returns None silently if the network is unavailable or the response cannot be parsed.

    Args:
        timeout: Request timeout in seconds.

    Returns:
        Latest version string (e.g. "0.3.2"), or None on any error.
    """
    url = f"{_GDS_IDEA_INDEX_URL}gds-idea-app-kit/"
    try:
        with urllib.request.urlopen(url, timeout=timeout) as response:  # noqa: S310
            html = response.read().decode("utf-8", errors="replace")
    except (urllib.error.URLError, OSError):
        return None

    # PEP 503 simple index: links look like gds_idea_app_kit-0.3.1-py3-none-any.whl
    versions = re.findall(r"gds[_-]idea[_-]app[_-]kit-(\d+\.\d+(?:\.\d+)?)", html)
    if not versions:
        return None

    try:
        return max(versions, key=_parse_version)
    except (ValueError, TypeError):
        return None


def check_tool_is_current() -> None:
    """Check whether the installed tool is the latest available version.

    Fetches the latest version from the internal PyPI index and compares it
    against the currently installed version. If a newer version is available,
    prints a warning to stderr with upgrade instructions and prompts the user
    to confirm whether to continue. Defaults to No (exit) to encourage upgrading.

    Does nothing if the network is unavailable or the version cannot be fetched.
    """
    latest = _fetch_latest_version()
    if latest is None:
        return

    try:
        if _parse_version(latest) <= _parse_version(__version__):
            return
    except (ValueError, TypeError):
        return

    click.echo(
        f"Warning: gds-idea-app-kit {latest} is available (you have {__version__}).",
        err=True,
    )
    click.echo("", err=True)
    click.echo("To upgrade:", err=True)
    click.echo("  idea-tools upgrade gds-idea-app-kit", err=True)
    click.echo("    (if you have idea-tools set up)", err=True)
    click.echo("", err=True)
    click.echo("    OR", err=True)
    click.echo("", err=True)
    click.echo(
        f'  uv tool upgrade gds-idea-app-kit --index "gds-idea={_GDS_IDEA_INDEX_URL}"',
        err=True,
    )
    click.echo("", err=True)

    if not click.confirm("Continue with the current version?", default=False, err=True):
        sys.exit(0)

    click.echo("", err=True)
