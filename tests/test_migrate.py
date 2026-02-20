"""Tests for the migrate command."""

import os
import subprocess
from unittest.mock import patch

import pytest
import tomlkit

from gds_idea_app_kit.manifest import read_manifest
from gds_idea_app_kit.migrate import (
    _detect_python_version,
    _read_webapp_config,
    _remove_old_config,
    _remove_template_dir,
    run_migrate,
)

# ---- fixtures ----


OLD_PYPROJECT = """\
[build-system]
requires = ["uv_build>=0.9.2,<0.10.0"]
build-backend = "uv_build"

[project]
name = "gds-idea-templates"
version = "0.1.2"
description = "Test project"
requires-python = ">=3.11"
dependencies = [
    "aws-cdk-lib>=2.180.0",
    "constructs>=10.0.0,<11.0.0",
]

[project.scripts]
configure = "template.configure:main"
smoke_test = "template.smoke_test:main"
provide_role = "template.provide_role:main"

[tool.uv]
package = true
dev-dependencies = [
    "pytest>=6.2.5",
]

[tool.uv.build-backend]
module-name = "template"
module-root = ""

[tool.webapp]
app_name = "test-app"
framework = "streamlit"

[tool.webapp.dev]
# aws_role_arn = "arn:aws:iam::123456:role/my-role"
# aws_region = "eu-west-2"
"""


@pytest.fixture()
def old_project(tmp_path):
    """Create a mock old-style project with template/ directory and old pyproject.toml.

    Returns the project directory path.
    """
    # Write old-style pyproject.toml
    (tmp_path / "pyproject.toml").write_text(OLD_PYPROJECT)

    # Create template/ directory with scripts
    template_dir = tmp_path / "template"
    template_dir.mkdir()
    (template_dir / "__init__.py").write_text("")
    (template_dir / "configure.py").write_text("def main(): pass")
    (template_dir / "smoke_test.py").write_text("def main(): pass")
    (template_dir / "provide_role.py").write_text("def main(): pass")

    # Create app_src/ with Dockerfile
    app_src = tmp_path / "app_src"
    app_src.mkdir()
    (app_src / "Dockerfile").write_text("FROM python:3.13-slim AS base\nWORKDIR /app\n")
    (app_src / "pyproject.toml").write_text(
        '[project]\nname = "test-app"\nrequires-python = ">=3.13"\n'
    )
    (app_src / "streamlit_app.py").write_text("import streamlit as st\n")

    # Create .devcontainer/
    devcontainer = tmp_path / ".devcontainer"
    devcontainer.mkdir()
    (devcontainer / "devcontainer.json").write_text('{"name": "test"}')
    (devcontainer / "docker-compose.yml").write_text("services:\n  app:\n")

    # Create dev_mocks/
    dev_mocks = tmp_path / "dev_mocks"
    dev_mocks.mkdir()
    (dev_mocks / "dev_mock_authoriser.json").write_text("{}")
    (dev_mocks / "dev_mock_user.json").write_text("{}")

    return tmp_path


# ---- _detect_python_version ----


def test_detect_python_version_from_dockerfile(tmp_path):
    """Parses Python version from Dockerfile FROM line."""
    app_src = tmp_path / "app_src"
    app_src.mkdir()
    (app_src / "Dockerfile").write_text("FROM python:3.13-slim AS base\n")

    assert _detect_python_version(tmp_path) == "3.13"


def test_detect_python_version_312_from_dockerfile(tmp_path):
    """Parses a different Python version from Dockerfile."""
    app_src = tmp_path / "app_src"
    app_src.mkdir()
    (app_src / "Dockerfile").write_text("FROM python:3.12-slim AS base\n")

    assert _detect_python_version(tmp_path) == "3.12"


def test_detect_python_version_falls_back_to_pyproject(tmp_path):
    """Falls back to app_src/pyproject.toml when Dockerfile has no version."""
    app_src = tmp_path / "app_src"
    app_src.mkdir()
    (app_src / "Dockerfile").write_text("FROM ubuntu:latest\n")
    (app_src / "pyproject.toml").write_text('[project]\nrequires-python = ">=3.12"\n')

    assert _detect_python_version(tmp_path) == "3.12"


def test_detect_python_version_defaults_when_no_files(tmp_path):
    """Defaults to 3.13 when no files can be parsed."""
    assert _detect_python_version(tmp_path) == "3.13"


# ---- _read_webapp_config ----


def test_read_webapp_config_reads_framework_and_name(old_project):
    """Reads framework and app_name from [tool.webapp]."""
    config = _read_webapp_config(old_project)
    assert config["framework"] == "streamlit"
    assert config["app_name"] == "test-app"


def test_read_webapp_config_exits_when_no_pyproject(tmp_path):
    """Exits with error when pyproject.toml doesn't exist."""
    with pytest.raises(SystemExit):
        _read_webapp_config(tmp_path)


def test_read_webapp_config_exits_when_no_webapp(tmp_path):
    """Exits with error when [tool.webapp] section is missing."""
    (tmp_path / "pyproject.toml").write_text('[project]\nname = "test"\n')
    with pytest.raises(SystemExit):
        _read_webapp_config(tmp_path)


# ---- _remove_old_config ----


def test_remove_old_config_removes_scripts_and_build(old_project):
    """Removes [project.scripts], [build-system], [tool.uv.build-backend]."""
    _remove_old_config(old_project)

    with open(old_project / "pyproject.toml") as f:
        config = tomlkit.load(f)

    assert "build-system" not in config
    assert "scripts" not in config.get("project", {})
    assert "build-backend" not in config.get("tool", {}).get("uv", {})


def test_remove_old_config_sets_package_false(old_project):
    """Sets package = false in [tool.uv]."""
    _remove_old_config(old_project)

    with open(old_project / "pyproject.toml") as f:
        config = tomlkit.load(f)

    assert config["tool"]["uv"]["package"] is False


def test_remove_old_config_preserves_other_content(old_project):
    """Preserves [project], [tool.webapp], [tool.webapp.dev], [tool.uv] dev-dependencies."""
    _remove_old_config(old_project)

    with open(old_project / "pyproject.toml") as f:
        config = tomlkit.load(f)

    # Project metadata preserved
    assert config["project"]["name"] == "gds-idea-templates"
    assert config["project"]["version"] == "0.1.2"

    # Webapp config preserved
    assert config["tool"]["webapp"]["app_name"] == "test-app"
    assert config["tool"]["webapp"]["framework"] == "streamlit"

    # UV dev-dependencies preserved
    assert "pytest>=6.2.5" in config["tool"]["uv"]["dev-dependencies"]


def test_remove_old_config_handles_missing_sections(tmp_path):
    """Does not error when sections to remove don't exist."""
    (tmp_path / "pyproject.toml").write_text(
        '[project]\nname = "test"\n\n[tool.uv]\ndev-dependencies = []\n'
    )
    # Should not raise
    _remove_old_config(tmp_path)

    with open(tmp_path / "pyproject.toml") as f:
        config = tomlkit.load(f)

    assert config["project"]["name"] == "test"


# ---- _remove_template_dir ----


def test_remove_template_dir_deletes_directory(old_project):
    """Removes the template/ directory and all its contents."""
    assert (old_project / "template").is_dir()
    _remove_template_dir(old_project)
    assert not (old_project / "template").exists()


def test_remove_template_dir_no_error_when_missing(tmp_path):
    """Does not error when template/ directory doesn't exist."""
    _remove_template_dir(tmp_path)  # Should not raise


# ---- run_migrate integration ----


def test_migrate_full_flow(old_project):
    """Full migration creates manifest, removes old config, removes template/."""
    os.chdir(old_project)

    # Simulate user confirming migration but declining update
    with (
        patch("gds_idea_app_kit.migrate.click") as mock_click,
        patch("gds_idea_app_kit.migrate.subprocess.run") as mock_run,
    ):
        mock_click.confirm = lambda msg, **kwargs: msg.startswith("Continue")
        mock_click.echo = click_echo_noop
        mock_run.return_value = subprocess.CompletedProcess([], 0)

        run_migrate()

    # Manifest should be written
    manifest = read_manifest(old_project)
    assert manifest is not None
    assert manifest["framework"] == "streamlit"
    assert manifest["app_name"] == "test-app"
    assert manifest["python_version"] == "3.13"

    # template/ should be gone
    assert not (old_project / "template").exists()

    # Old config should be cleaned up
    with open(old_project / "pyproject.toml") as f:
        config = tomlkit.load(f)

    assert "build-system" not in config
    assert "scripts" not in config.get("project", {})
    assert config["tool"]["uv"]["package"] is False


def test_migrate_exits_when_already_migrated(old_project, capsys):
    """Exits with message when manifest already exists."""
    os.chdir(old_project)

    # Write a manifest to simulate already-migrated project
    from gds_idea_app_kit.manifest import build_manifest, write_manifest

    manifest = build_manifest(
        framework="streamlit",
        app_name="test-app",
        tool_version="0.1.0",
        project_dir=old_project,
    )
    write_manifest(old_project, manifest)

    with pytest.raises(SystemExit):
        run_migrate()

    captured = capsys.readouterr()
    assert "already been migrated" in captured.err


def test_migrate_aborts_on_decline(old_project):
    """No changes are made when user declines the confirmation."""
    os.chdir(old_project)

    # Read pyproject.toml before
    original_content = (old_project / "pyproject.toml").read_text()

    with patch("gds_idea_app_kit.migrate.click") as mock_click:
        mock_click.confirm = lambda msg, **kwargs: False
        mock_click.echo = click_echo_noop

        run_migrate()

    # pyproject.toml should be unchanged
    assert (old_project / "pyproject.toml").read_text() == original_content

    # template/ should still exist
    assert (old_project / "template").is_dir()

    # No manifest should exist
    assert read_manifest(old_project) == {}


# ---- uv sync ----


def test_migrate_runs_uv_sync(old_project):
    """Migration runs 'uv sync' to remove old entry points from the environment."""
    os.chdir(old_project)

    with (
        patch("gds_idea_app_kit.migrate.click") as mock_click,
        patch("gds_idea_app_kit.migrate.subprocess.run") as mock_run,
    ):
        mock_click.confirm = lambda msg, **kwargs: msg.startswith("Continue")
        mock_click.echo = click_echo_noop
        mock_run.return_value = subprocess.CompletedProcess([], 0)

        run_migrate()

    mock_run.assert_called_once_with(
        ["uv", "sync"], cwd=old_project, check=True, capture_output=True, text=True
    )


# ---- helper ----


def click_echo_noop(*args, **kwargs):
    """No-op replacement for click.echo in tests."""
