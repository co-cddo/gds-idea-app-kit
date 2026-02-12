"""Shared test fixtures."""

import pytest

from gds_idea_app_kit.manifest import MANIFEST_KEY


@pytest.fixture()
def project_dir(tmp_path):
    """Create a minimal project directory with a pyproject.toml."""
    pyproject = tmp_path / "pyproject.toml"
    pyproject.write_text('[project]\nname = "test-app"\nversion = "0.1.0"\n\n[tool]\n')
    return tmp_path


@pytest.fixture()
def project_with_manifest(project_dir):
    """Create a project directory with an existing manifest in pyproject.toml."""
    pyproject = project_dir / "pyproject.toml"
    pyproject.write_text(
        f'[project]\nname = "test-app"\nversion = "0.1.0"\n\n'
        f"[tool.{MANIFEST_KEY}]\n"
        f'framework = "streamlit"\n'
        f'app_name = "test-app"\n'
        f'tool_version = "0.1.0"\n\n'
        f"[tool.{MANIFEST_KEY}.files]\n"
        f'"app_src/Dockerfile" = "sha256:abc123"\n'
        f'".devcontainer/devcontainer.json" = "sha256:def456"\n'
    )
    return project_dir
