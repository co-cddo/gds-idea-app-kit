"""Integration tests that run real commands (cdk, uv, git).

These tests require:
- cdk installed (npm install -g aws-cdk)
- uv installed
- git installed
- Network access to GitHub (for private deps)

Run with: uv run pytest -m integration
Skip with: uv run pytest -m "not integration"
"""

import os
import subprocess
import tomllib

import pytest

from gds_idea_app_kit.init import run_init
from gds_idea_app_kit.manifest import read_manifest


@pytest.mark.integration
def test_init_streamlit_end_to_end(tmp_path):
    """Full init creates a working streamlit project with all deps resolved."""
    os.chdir(tmp_path)
    run_init(framework="streamlit", app_name="integ-test", python_version="3.13")

    project = tmp_path / "gds-idea-app-integ-test"

    # ---- Project structure ----

    assert project.is_dir(), "Project directory should be created"

    # CDK files
    assert (project / "app.py").exists(), "CDK entry point should exist"
    assert (project / "cdk.json").exists(), "cdk.json should exist"

    # App source
    assert (project / "app_src" / "Dockerfile").exists()
    assert (project / "app_src" / "streamlit_app.py").exists()
    assert (project / "app_src" / "pyproject.toml").exists()

    # Dev container
    assert (project / ".devcontainer" / "devcontainer.json").exists()
    assert (project / ".devcontainer" / "docker-compose.yml").exists()

    # Dev mocks
    assert (project / "dev_mocks" / "dev_mock_authoriser.json").exists()
    assert (project / "dev_mocks" / "dev_mock_user.json").exists()

    # ---- Template variables substituted ----

    dockerfile = (project / "app_src" / "Dockerfile").read_text()
    assert "python:3.13" in dockerfile, "Python version should be substituted in Dockerfile"
    assert "{{python_version}}" not in dockerfile, "Template placeholder should not remain"

    app_pyproject = (project / "app_src" / "pyproject.toml").read_text()
    assert "integ-test" in app_pyproject, "App name should be substituted in pyproject.toml"
    assert "{{app_name}}" not in app_pyproject, "Template placeholder should not remain"

    # ---- Root pyproject.toml config ----

    with open(project / "pyproject.toml", "rb") as f:
        root_config = tomllib.load(f)

    webapp = root_config.get("tool", {}).get("webapp", {})
    assert webapp.get("framework") == "streamlit"
    assert webapp.get("app_name") == "integ-test"

    # ---- Manifest ----

    manifest = read_manifest(project)
    assert manifest, "Manifest should be written"
    assert manifest["framework"] == "streamlit"
    assert manifest["app_name"] == "integ-test"
    assert "files" in manifest, "Manifest should contain file hashes"
    assert len(manifest["files"]) > 0, "Manifest should track at least one file"

    # ---- Dependencies resolved ----

    assert (project / "uv.lock").exists(), "uv.lock should be created by uv sync"
    assert (project / ".venv").is_dir(), ".venv should be created by uv sync"

    # ---- Git history ----

    result = subprocess.run(
        ["git", "log", "--oneline"],
        cwd=project,
        capture_output=True,
        text=True,
        check=True,
    )
    assert "Initial scaffold" in result.stdout, "Initial commit should exist"
    assert "streamlit" in result.stdout, "Commit message should mention the framework"

    # ---- .gitignore ----

    gitignore = (project / ".gitignore").read_text()
    assert ".aws-dev" in gitignore, ".aws-dev should be in gitignore"
    assert "*.new" in gitignore, "*.new files should be in gitignore"
