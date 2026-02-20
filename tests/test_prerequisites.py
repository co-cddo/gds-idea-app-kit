"""Tests for the prerequisites module."""

import subprocess
from unittest.mock import patch

import pytest

from gds_idea_app_kit.prerequisites import PREREQUISITES, check_prerequisites


def _make_side_effect(missing_names: set[str]):
    """Return a subprocess.run side_effect that fails for the given tool names.

    Args:
        missing_names: Set of display names (e.g. {"docker compose"}) whose
            check commands should raise FileNotFoundError.
    """
    # Build a lookup from the first element of each check_cmd to the name.
    cmd_to_name: dict[tuple[str, ...], str] = {}
    for name, check_cmd, _, _ in PREREQUISITES:
        cmd_to_name[tuple(check_cmd)] = name

    def side_effect(cmd, **kwargs):
        key = tuple(cmd)
        if key in cmd_to_name and cmd_to_name[key] in missing_names:
            raise FileNotFoundError(f"{cmd[0]} not found")
        return subprocess.CompletedProcess(cmd, 0, stdout="", stderr="")

    return side_effect


# ---- All tools present ----


def test_all_present_does_not_exit():
    """When all tools are found, check_prerequisites returns without error."""
    with patch("gds_idea_app_kit.prerequisites.subprocess.run") as mock_run:
        mock_run.return_value = subprocess.CompletedProcess([], 0)
        check_prerequisites()  # should not raise


# ---- Single tool missing ----


def test_single_missing_tool_exits(capsys):
    """When one tool is missing, exits with an error naming that tool."""
    with (
        patch(
            "gds_idea_app_kit.prerequisites.subprocess.run",
            side_effect=_make_side_effect({"git"}),
        ),
        pytest.raises(SystemExit),
    ):
        check_prerequisites()

    captured = capsys.readouterr()
    assert "git" in captured.err
    assert "brew install git" in captured.err


# ---- Multiple tools missing ----


def test_multiple_missing_tools_lists_all(capsys):
    """When several tools are missing, all are listed in the error output."""
    with (
        patch(
            "gds_idea_app_kit.prerequisites.subprocess.run",
            side_effect=_make_side_effect({"cdk", "uv"}),
        ),
        pytest.raises(SystemExit),
    ):
        check_prerequisites()

    captured = capsys.readouterr()
    assert "cdk" in captured.err
    assert "uv" in captured.err
    assert "brew install aws-cdk" in captured.err
    assert "brew install uv" in captured.err


# ---- docker compose missing shows URL ----


def test_docker_compose_missing_shows_url(capsys):
    """When docker compose is missing, the error includes the troubleshooting URL."""
    with (
        patch(
            "gds_idea_app_kit.prerequisites.subprocess.run",
            side_effect=_make_side_effect({"docker compose"}),
        ),
        pytest.raises(SystemExit),
    ):
        check_prerequisites()

    captured = capsys.readouterr()
    assert "docker compose" in captured.err
    assert "brew install docker-compose" in captured.err
    assert "github.com/co-cddo/gds-idea-app-kit" in captured.err


# ---- CalledProcessError treated as missing ----


def test_called_process_error_treated_as_missing(capsys):
    """A tool that exists but returns non-zero is treated as missing."""

    def side_effect(cmd, **kwargs):
        if cmd == ["docker", "compose", "version"]:
            raise subprocess.CalledProcessError(1, cmd)
        return subprocess.CompletedProcess(cmd, 0)

    with (
        patch("gds_idea_app_kit.prerequisites.subprocess.run", side_effect=side_effect),
        pytest.raises(SystemExit),
    ):
        check_prerequisites()

    captured = capsys.readouterr()
    assert "docker compose" in captured.err


# ---- only parameter ----


def test_only_filters_to_specified_tools():
    """When only is given, tools not in the list are not checked."""
    calls = []

    def side_effect(cmd, **kwargs):
        calls.append(tuple(cmd))
        return subprocess.CompletedProcess(cmd, 0)

    with patch("gds_idea_app_kit.prerequisites.subprocess.run", side_effect=side_effect):
        check_prerequisites(only=["docker", "docker compose"])

    # Only docker and docker compose should have been checked
    assert ("docker", "--version") in calls
    assert ("docker", "compose", "version") in calls
    # cdk, uv, git should NOT have been checked
    assert ("cdk", "--version") not in calls
    assert ("uv", "--version") not in calls
    assert ("git", "--version") not in calls


def test_only_missing_tool_still_exits(capsys):
    """A filtered check still exits when the specified tool is missing."""
    with (
        patch(
            "gds_idea_app_kit.prerequisites.subprocess.run",
            side_effect=_make_side_effect({"docker compose"}),
        ),
        pytest.raises(SystemExit),
    ):
        check_prerequisites(only=["docker", "docker compose"])

    captured = capsys.readouterr()
    assert "docker compose" in captured.err


def test_only_all_present_does_not_exit():
    """A filtered check returns without error when all specified tools exist."""
    with patch("gds_idea_app_kit.prerequisites.subprocess.run") as mock_run:
        mock_run.return_value = subprocess.CompletedProcess([], 0)
        check_prerequisites(only=["docker", "docker compose"])  # should not raise
