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
    """update --help shows --dry-run and --force options."""
    result = cli_runner.invoke(cli, ["update", "--help"])
    assert result.exit_code == 0
    assert "--dry-run" in result.output
    assert "--force" in result.output


def test_update_runs(cli_runner):
    """update passes dry_run=False and force=False to run_update."""
    with patch("gds_idea_app_kit.update.run_update") as mock:
        result = cli_runner.invoke(cli, ["update"])
    assert result.exit_code == 0
    mock.assert_called_once_with(dry_run=False, force=False)


def test_update_dry_run(cli_runner):
    """update --dry-run passes dry_run=True to run_update."""
    with patch("gds_idea_app_kit.update.run_update") as mock:
        result = cli_runner.invoke(cli, ["update", "--dry-run"])
    assert result.exit_code == 0
    mock.assert_called_once_with(dry_run=True, force=False)


def test_update_force(cli_runner):
    """update --force passes force=True to run_update."""
    with patch("gds_idea_app_kit.update.run_update") as mock:
        result = cli_runner.invoke(cli, ["update", "--force"])
    assert result.exit_code == 0
    mock.assert_called_once_with(dry_run=False, force=True)


# ---- smoke-test command ----


def test_smoke_test_help_shows_options(cli_runner):
    result = cli_runner.invoke(cli, ["smoke-test", "--help"])
    assert result.exit_code == 0
    assert "--build-only" in result.output
    assert "--wait" in result.output


def test_smoke_test_runs(cli_runner):
    """smoke-test passes build_only=False and wait=False to run_smoke_test."""
    with patch("gds_idea_app_kit.smoke_test.run_smoke_test") as mock:
        result = cli_runner.invoke(cli, ["smoke-test"])
    assert result.exit_code == 0
    mock.assert_called_once_with(build_only=False, wait=False)


def test_smoke_test_build_only(cli_runner):
    """smoke-test --build-only passes build_only=True."""
    with patch("gds_idea_app_kit.smoke_test.run_smoke_test") as mock:
        result = cli_runner.invoke(cli, ["smoke-test", "--build-only"])
    assert result.exit_code == 0
    mock.assert_called_once_with(build_only=True, wait=False)


def test_smoke_test_wait(cli_runner):
    """smoke-test --wait passes wait=True."""
    with patch("gds_idea_app_kit.smoke_test.run_smoke_test") as mock:
        result = cli_runner.invoke(cli, ["smoke-test", "--wait"])
    assert result.exit_code == 0
    mock.assert_called_once_with(build_only=False, wait=True)


# ---- provide-role command ----


def test_provide_role_help_shows_options(cli_runner):
    result = cli_runner.invoke(cli, ["provide-role", "--help"])
    assert result.exit_code == 0
    assert "--use-profile" in result.output
    assert "--duration" in result.output
    assert "3600" in result.output  # default value shown


def test_provide_role_runs(cli_runner):
    """provide-role passes use_profile=False and default duration to run_provide_role."""
    with patch("gds_idea_app_kit.provide_role.run_provide_role") as mock:
        result = cli_runner.invoke(cli, ["provide-role"])
    assert result.exit_code == 0
    mock.assert_called_once_with(use_profile=False, duration=3600)


def test_provide_role_default_duration(cli_runner):
    """provide-role uses 3600 as default duration."""
    with patch("gds_idea_app_kit.provide_role.run_provide_role") as mock:
        result = cli_runner.invoke(cli, ["provide-role"])
    assert result.exit_code == 0
    assert mock.call_args == ((), {"use_profile": False, "duration": 3600})


def test_provide_role_custom_duration(cli_runner):
    """provide-role --duration 7200 passes custom duration."""
    with patch("gds_idea_app_kit.provide_role.run_provide_role") as mock:
        result = cli_runner.invoke(cli, ["provide-role", "--duration", "7200"])
    assert result.exit_code == 0
    mock.assert_called_once_with(use_profile=False, duration=7200)


def test_provide_role_use_profile(cli_runner):
    """provide-role --use-profile passes use_profile=True."""
    with patch("gds_idea_app_kit.provide_role.run_provide_role") as mock:
        result = cli_runner.invoke(cli, ["provide-role", "--use-profile"])
    assert result.exit_code == 0
    mock.assert_called_once_with(use_profile=True, duration=3600)


# ---- migrate command ----


def test_migrate_help_shows_description(cli_runner):
    """migrate --help shows the command description."""
    result = cli_runner.invoke(cli, ["migrate", "--help"])
    assert result.exit_code == 0
    assert "Migrate" in result.output


def test_migrate_runs(cli_runner):
    """migrate calls run_migrate."""
    with patch("gds_idea_app_kit.migrate.run_migrate") as mock:
        result = cli_runner.invoke(cli, ["migrate"])
    assert result.exit_code == 0
    mock.assert_called_once_with()


# ---- unknown command ----


def test_unknown_command(cli_runner):
    result = cli_runner.invoke(cli, ["nonexistent"])
    assert result.exit_code != 0
