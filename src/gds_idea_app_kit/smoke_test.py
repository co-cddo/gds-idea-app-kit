"""Implementation of the smoke-test command.

Builds the production Docker image using docker compose and optionally runs
a health check to verify the container starts and responds correctly. This
validates that a cdk deploy will succeed before pushing.

Usage:
    idea-app smoke-test              # build, health check, teardown
    idea-app smoke-test --build-only # build image only
    idea-app smoke-test --wait       # build, health check, keep running
"""

import os
import subprocess
import sys
import time
import tomllib
import urllib.error
import urllib.request
from pathlib import Path

import click

COMPOSE_FILE = ".devcontainer/docker-compose.yml"
SERVICE_NAME = "app"
CONTAINER_PORT = 8080
MAX_WAIT_SECONDS = 120
POLL_INTERVAL_SECONDS = 2

HEALTH_PATHS: dict[str, str] = {
    "streamlit": "/_stcore/health",
    "dash": "/health",
    "fastapi": "/health",
}


def _get_framework(project_dir: Path) -> str:
    """Read the framework from [tool.webapp] in pyproject.toml.

    Args:
        project_dir: The project root directory.

    Returns:
        The framework name (e.g. "streamlit").
    """
    pyproject_path = project_dir / "pyproject.toml"

    if not pyproject_path.exists():
        click.echo("Error: No pyproject.toml found. Are you in a project root?", err=True)
        sys.exit(1)

    with open(pyproject_path, "rb") as f:
        config = tomllib.load(f)

    framework = config.get("tool", {}).get("webapp", {}).get("framework", "")

    if not framework:
        click.echo("Error: No framework configured in [tool.webapp].", err=True)
        click.echo("  This doesn't look like a project created by idea-app.", err=True)
        sys.exit(1)

    return framework


def _get_health_path(framework: str) -> str:
    """Get the health check URL path for a framework.

    Args:
        framework: The framework name (e.g. "streamlit").

    Returns:
        The health check path (e.g. "/_stcore/health").
    """
    return HEALTH_PATHS.get(framework, "/health")


def _compose(
    *args: str,
    stream: bool = False,
    check: bool = True,
) -> subprocess.CompletedProcess:
    """Run a docker compose command targeting the production image.

    Args:
        *args: Arguments to pass to docker compose (e.g. "build", "up", "-d").
        stream: If True, inherit stdout/stderr so output streams to terminal.
        check: If True, raise CalledProcessError on non-zero exit.

    Returns:
        The CompletedProcess result.
    """
    cmd = ["docker", "compose", "-f", COMPOSE_FILE, *args]

    env = os.environ.copy()
    env["DOCKER_TARGET"] = "production"

    if stream:
        return subprocess.run(cmd, check=check, env=env)
    else:
        return subprocess.run(cmd, check=check, capture_output=True, text=True, env=env)


def _get_host_port() -> str:
    """Get the host port mapped to the container's port 8080.

    Returns:
        The host port as a string (e.g. "8080").
    """
    result = _compose("port", SERVICE_NAME, str(CONTAINER_PORT))
    # Output format: "0.0.0.0:8080" or ":::8080"
    return result.stdout.strip().split(":")[-1]


def _check_health(url: str) -> bool:
    """Check if a health endpoint responds with HTTP 200.

    Args:
        url: The full URL to check (e.g. "http://localhost:8080/health").

    Returns:
        True if the endpoint responds with 200, False otherwise.
    """
    try:
        with urllib.request.urlopen(url, timeout=2) as response:
            return response.status == 200
    except (urllib.error.URLError, urllib.error.HTTPError, TimeoutError, OSError):
        return False


def _poll_health(url: str, timeout: int = MAX_WAIT_SECONDS) -> bool:
    """Poll a health endpoint until it responds or the timeout expires.

    Prints dots while waiting.

    Args:
        url: The health check URL.
        timeout: Maximum seconds to wait.

    Returns:
        True if the health check passed, False if it timed out.
    """
    seconds_waited = 0
    while seconds_waited < timeout:
        if _check_health(url):
            click.echo()
            return True
        click.echo(".", nl=False)
        time.sleep(POLL_INTERVAL_SECONDS)
        seconds_waited += POLL_INTERVAL_SECONDS

    click.echo()
    return False


def _show_failure_logs() -> None:
    """Print container logs to help debug a health check failure."""
    click.echo()
    click.echo("Container logs:")
    _compose("logs", stream=True, check=False)


def _cleanup() -> None:
    """Stop and remove containers."""
    click.echo()
    click.echo("Cleaning up...")
    _compose("down", check=False)


def run_smoke_test(build_only: bool, wait: bool = False) -> None:
    """Build and health-check the production Docker image.

    Args:
        build_only: If True, only build the image without running a container.
        wait: If True, keep the container running after health check until Enter.
    """
    project_dir = Path.cwd()

    # -- Validate configuration --
    click.echo("Loading configuration...")
    framework = _get_framework(project_dir)
    health_path = _get_health_path(framework)
    click.echo(f"  Framework: {framework}")
    click.echo(f"  Health check: {health_path}")
    click.echo()

    # -- Check compose file exists --
    compose_path = project_dir / COMPOSE_FILE
    if not compose_path.exists():
        click.echo(f"Error: {COMPOSE_FILE} not found.", err=True)
        click.echo("  Run 'idea-app update' to restore missing files.", err=True)
        sys.exit(1)

    # -- Build --
    click.echo("Building production image...")
    try:
        _compose("build", stream=True)
    except subprocess.CalledProcessError:
        click.echo("Error: Docker build failed.", err=True)
        sys.exit(1)
    except FileNotFoundError:
        click.echo("Error: docker not found. Is Docker installed and running?", err=True)
        sys.exit(1)
    click.echo("Build complete.")

    if build_only:
        return

    # -- Start, health check, teardown --
    container_started = False
    try:
        click.echo()
        click.echo("Starting container...")
        _compose("up", "-d")
        container_started = True

        host_port = _get_host_port()
        health_url = f"http://localhost:{host_port}{health_path}"
        click.echo(f"  Health check URL: {health_url}")
        click.echo()
        click.echo("Tip: To see container logs, run in another terminal:")
        click.echo(f"  docker compose -f {COMPOSE_FILE} logs -f")
        click.echo()

        click.echo(f"Waiting for health check (up to {MAX_WAIT_SECONDS}s)...")
        passed = _poll_health(health_url)

        if not passed:
            click.echo("Health check failed. The container did not respond in time.", err=True)
            _show_failure_logs()
            sys.exit(1)

        click.echo("Health check passed.")

        if wait:
            click.echo()
            click.echo(f"Container running at http://localhost:{host_port}")
            click.echo("Press Enter to stop and clean up...")
            input()

    finally:
        if container_started:
            _cleanup()
