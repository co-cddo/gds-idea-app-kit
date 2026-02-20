"""Tests for the smoke-test command."""

import os
from unittest.mock import MagicMock, patch

import pytest

from gds_idea_app_kit.smoke_test import _get_framework, _get_health_path, run_smoke_test

# ---- _get_health_path ----


def test_health_path_streamlit():
    """Streamlit uses the _stcore health endpoint."""
    assert _get_health_path("streamlit") == "/_stcore/health"


def test_health_path_dash():
    """Dash uses /health."""
    assert _get_health_path("dash") == "/health"


def test_health_path_fastapi():
    """FastAPI uses /health."""
    assert _get_health_path("fastapi") == "/health"


def test_health_path_unknown_falls_back():
    """Unknown frameworks fall back to /health."""
    assert _get_health_path("unknown-framework") == "/health"


# ---- _get_framework ----


def test_get_framework_reads_from_pyproject(tmp_path):
    """Reads the framework from [tool.webapp] in pyproject.toml."""
    pyproject = tmp_path / "pyproject.toml"
    pyproject.write_text('[project]\nname = "test"\n\n[tool.webapp]\nframework = "streamlit"\n')

    result = _get_framework(tmp_path)
    assert result == "streamlit"


def test_get_framework_exits_when_no_pyproject(tmp_path):
    """Exits with error when pyproject.toml doesn't exist."""
    with pytest.raises(SystemExit):
        _get_framework(tmp_path)


def test_get_framework_exits_when_no_webapp_section(tmp_path):
    """Exits with error when [tool.webapp] section is missing."""
    pyproject = tmp_path / "pyproject.toml"
    pyproject.write_text('[project]\nname = "test"\n')

    with pytest.raises(SystemExit):
        _get_framework(tmp_path)


def test_get_framework_exits_when_framework_empty(tmp_path):
    """Exits with error when framework key exists but is empty."""
    pyproject = tmp_path / "pyproject.toml"
    pyproject.write_text('[project]\nname = "test"\n\n[tool.webapp]\nframework = ""\n')

    with pytest.raises(SystemExit):
        _get_framework(tmp_path)


# ---- run_smoke_test build_only ----


def test_build_only_does_not_start_container(tmp_path):
    """Build-only mode calls build but never starts a container or runs cleanup."""
    pyproject = tmp_path / "pyproject.toml"
    pyproject.write_text('[project]\nname = "test"\n\n[tool.webapp]\nframework = "streamlit"\n')
    compose_file = tmp_path / ".devcontainer" / "docker-compose.yml"
    compose_file.parent.mkdir(parents=True)
    compose_file.write_text("services:\n  app:\n")

    os.chdir(tmp_path)

    with patch("gds_idea_app_kit.smoke_test._compose") as mock_compose:
        run_smoke_test(build_only=True)

        # Build should have been called (via stream=True)
        calls = [str(c) for c in mock_compose.call_args_list]
        build_called = any("build" in c for c in calls)
        assert build_called

        # up and down should NOT have been called
        up_called = any("up" in c for c in calls)
        down_called = any("down" in c for c in calls)
        assert not up_called
        assert not down_called


# ---- run_smoke_test cleanup on failure ----


def test_cleanup_runs_on_failure(tmp_path):
    """Cleanup runs even when an error occurs after the container starts."""
    pyproject = tmp_path / "pyproject.toml"
    pyproject.write_text('[project]\nname = "test"\n\n[tool.webapp]\nframework = "streamlit"\n')
    compose_file = tmp_path / ".devcontainer" / "docker-compose.yml"
    compose_file.parent.mkdir(parents=True)
    compose_file.write_text("services:\n  app:\n")

    os.chdir(tmp_path)

    compose_calls = []

    def fake_compose(*args, stream=False, check=True):
        compose_calls.append(args)
        if args and args[0] == "up":
            # Simulate successful up, then _get_host_port will fail
            return MagicMock(stdout="0.0.0.0:8080\n")
        if args and args[0] == "port":
            # After up succeeds, port query raises to simulate failure
            raise RuntimeError("simulated failure")
        return MagicMock(stdout="")

    with (
        patch("gds_idea_app_kit.smoke_test._compose", side_effect=fake_compose),
        pytest.raises(RuntimeError, match="simulated failure"),
    ):
        run_smoke_test(build_only=False)

    # Cleanup (down) should have been called despite the error
    down_calls = [c for c in compose_calls if c and c[0] == "down"]
    assert len(down_calls) == 1


# ---- prerequisite check ----


def test_smoke_test_checks_docker_prerequisites(tmp_path):
    """run_smoke_test calls check_prerequisites for docker and docker compose."""
    pyproject = tmp_path / "pyproject.toml"
    pyproject.write_text('[project]\nname = "test"\n\n[tool.webapp]\nframework = "streamlit"\n')
    compose_file = tmp_path / ".devcontainer" / "docker-compose.yml"
    compose_file.parent.mkdir(parents=True)
    compose_file.write_text("services:\n  app:\n")

    os.chdir(tmp_path)

    with (
        patch("gds_idea_app_kit.smoke_test.check_prerequisites") as mock_prereqs,
        patch("gds_idea_app_kit.smoke_test._compose"),
    ):
        run_smoke_test(build_only=True)

    mock_prereqs.assert_called_once_with(only=["docker", "docker compose"])
