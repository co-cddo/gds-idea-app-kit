"""Tests for the CLI interface."""

from unittest.mock import patch

import pytest

from gds_idea_app_kit import DEFAULT_PYTHON_VERSION, __version__
from gds_idea_app_kit.cli import cli

# ---- version and help ----


def test_version(cli_runner):
    """--version prints the package version."""
    result = cli_runner.invoke(cli, ["--version"])
    assert result.exit_code == 0
    assert __version__ in result.output


def test_help_lists_all_commands(cli_runner):
    """--help lists all four commands."""
    result = cli_runner.invoke(cli, ["--help"])
    assert result.exit_code == 0
    assert "init" in result.output
    assert "update" in result.output
    assert "smoke-test" in result.output
    assert "provide-role" in result.output


# ---- init command ----


def test_init_help_shows_options(cli_runner):
    """init --help shows framework choices and --python option."""
    result = cli_runner.invoke(cli, ["init", "--help"])
    assert result.exit_code == 0
    assert "streamlit" in result.output
    assert "dash" in result.output
    assert "fastapi" in result.output
    assert "--python" in result.output
    assert DEFAULT_PYTHON_VERSION in result.output


@pytest.mark.parametrize("framework", ["streamlit", "dash", "fastapi"])
def test_init_valid_framework(cli_runner, framework):
    """init accepts valid framework and passes correct args to run_init."""
    with patch("gds_idea_app_kit.init.run_init") as mock:
        result = cli_runner.invoke(cli, ["init", framework, "my-app"])
    assert result.exit_code == 0
    mock.assert_called_once_with(
        framework=framework, app_name="my-app", python_version=DEFAULT_PYTHON_VERSION
    )


def test_init_custom_python_version(cli_runner):
    """init --python passes the custom version to run_init."""
    with patch("gds_idea_app_kit.init.run_init") as mock:
        result = cli_runner.invoke(cli, ["init", "streamlit", "my-app", "--python", "3.12"])
    assert result.exit_code == 0
    mock.assert_called_once_with(framework="streamlit", app_name="my-app", python_version="3.12")


def test_init_default_python_version(cli_runner):
    """init uses DEFAULT_PYTHON_VERSION when --python is not given."""
    with patch("gds_idea_app_kit.init.run_init") as mock:
        result = cli_runner.invoke(cli, ["init", "streamlit", "my-app"])
    assert result.exit_code == 0
    mock.assert_called_once_with(
        framework="streamlit", app_name="my-app", python_version=DEFAULT_PYTHON_VERSION
    )


def test_init_invalid_framework(cli_runner):
    result = cli_runner.invoke(cli, ["init", "flask", "my-app"])
    assert result.exit_code != 0
    assert "Invalid value" in result.output


def test_init_missing_app_name(cli_runner):
    result = cli_runner.invoke(cli, ["init", "streamlit"])
    assert result.exit_code != 0


def test_init_missing_all_args(cli_runner):
    result = cli_runner.invoke(cli, ["init"])
    assert result.exit_code != 0


# ---- update command ----


def test_update_help_shows_options(cli_runner):
    result = cli_runner.invoke(cli, ["update", "--help"])
    assert result.exit_code == 0
    assert "--dry-run" in result.output


def test_update_runs(cli_runner):
    result = cli_runner.invoke(cli, ["update"])
    assert result.exit_code == 0
    assert "Updating" in result.output


def test_update_dry_run(cli_runner):
    result = cli_runner.invoke(cli, ["update", "--dry-run"])
    assert result.exit_code == 0
    assert "Dry run" in result.output


# ---- smoke-test command ----


def test_smoke_test_help_shows_options(cli_runner):
    result = cli_runner.invoke(cli, ["smoke-test", "--help"])
    assert result.exit_code == 0
    assert "--build-only" in result.output
    assert "--wait" in result.output


def test_smoke_test_runs(cli_runner):
    result = cli_runner.invoke(cli, ["smoke-test"])
    assert result.exit_code == 0
    assert "smoke test" in result.output


def test_smoke_test_build_only(cli_runner):
    result = cli_runner.invoke(cli, ["smoke-test", "--build-only"])
    assert result.exit_code == 0
    assert "build only" in result.output


def test_smoke_test_wait(cli_runner):
    result = cli_runner.invoke(cli, ["smoke-test", "--wait"])
    assert result.exit_code == 0
    assert "waiting" in result.output


# ---- provide-role command ----


def test_provide_role_help_shows_options(cli_runner):
    result = cli_runner.invoke(cli, ["provide-role", "--help"])
    assert result.exit_code == 0
    assert "--use-profile" in result.output
    assert "--duration" in result.output
    assert "3600" in result.output  # default value shown


def test_provide_role_runs(cli_runner):
    result = cli_runner.invoke(cli, ["provide-role"])
    assert result.exit_code == 0
    assert "Assuming role" in result.output


def test_provide_role_default_duration(cli_runner):
    result = cli_runner.invoke(cli, ["provide-role"])
    assert result.exit_code == 0
    assert "duration=3600s" in result.output


def test_provide_role_custom_duration(cli_runner):
    result = cli_runner.invoke(cli, ["provide-role", "--duration", "7200"])
    assert result.exit_code == 0
    assert "duration=7200s" in result.output


def test_provide_role_use_profile(cli_runner):
    result = cli_runner.invoke(cli, ["provide-role", "--use-profile"])
    assert result.exit_code == 0
    assert "Using current AWS profile" in result.output


# ---- unknown command ----


def test_unknown_command(cli_runner):
    result = cli_runner.invoke(cli, ["nonexistent"])
    assert result.exit_code != 0
