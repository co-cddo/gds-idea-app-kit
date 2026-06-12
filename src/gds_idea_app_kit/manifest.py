"""Manifest management for tracking tool-owned files in [tool.gds-idea-app-kit].

The manifest lives in pyproject.toml under the [tool.gds-idea-app-kit] section and tracks:
- Project metadata (framework, app_name, tool_version)
- SHA256 hashes of tool-owned files (for change detection during updates)
"""

import hashlib
from pathlib import Path

import tomlkit

from gds_idea_app_kit import WEB_FRAMEWORKS

# Key used in pyproject.toml [tool.*] section
MANIFEST_KEY = "gds-idea-app-kit"

# Files that `update` manages for ALL project types.
# The dict maps template source path -> destination path in the project.
TOOL_OWNED_FILES = {
    "common/ci_cd_cdk_app.yml": ".github/workflows/ci_cd_cdk_app.yml",
    "common/ci_pr_cdk_app.yml": ".github/workflows/ci_pr_cdk_app.yml",
    "common/CODEOWNERS.template": ".github/CODEOWNERS",
    "common/dependabot.yml": ".github/dependabot.yml",
    "common/LICENCE": "LICENCE",
}

# Files that `update` manages only for web framework projects.
WEB_OWNED_FILES = {
    "web_common/devcontainer.json": ".devcontainer/devcontainer.json",
    "web_common/docker-compose.yml": ".devcontainer/docker-compose.yml",
    "dev_mocks/dev_mock_authoriser.json": "dev_mocks/dev_mock_authoriser.json",
    "dev_mocks/dev_mock_user.json": "dev_mocks/dev_mock_user.json",
}

# Framework-specific files that `update` manages (web frameworks only).
# The framework name is substituted at runtime.
FRAMEWORK_OWNED_FILES = {
    "Dockerfile": "app_src/Dockerfile",
}

# Files that `update` manages for Python package projects.
PYTHON_OWNED_FILES = {
    "python/ci.yml": ".github/workflows/ci.yml",
    "python/release.yml": ".github/workflows/release.yml",
    "python/CODEOWNERS.template": ".github/CODEOWNERS",
    "python/dependabot.yml": ".github/dependabot.yml",
    "python/pre-commit-config.yaml": ".pre-commit-config.yaml",
    "common/LICENCE": "LICENCE",
}


def hash_file(path: Path) -> str:
    """Compute SHA256 hash of a file.

    Args:
        path: Path to the file to hash.

    Returns:
        Hash string in the format "sha256:<hex_digest>".
    """
    content = path.read_bytes()
    digest = hashlib.sha256(content).hexdigest()
    return f"sha256:{digest}"


def get_tracked_files(framework: str) -> dict[str, str]:
    """Get the full mapping of template source -> project destination for a framework.

    Args:
        framework: The project type (streamlit, dash, fastapi, infra, or python).

    Returns:
        Dict mapping template source paths to project destination paths.
    """
    if framework == "python":
        return dict(PYTHON_OWNED_FILES)

    files = dict(TOOL_OWNED_FILES)
    if framework in WEB_FRAMEWORKS:
        files.update(WEB_OWNED_FILES)
        for template_name, dest_path in FRAMEWORK_OWNED_FILES.items():
            files[f"{framework}/{template_name}"] = dest_path
    return files


def read_manifest(project_dir: Path) -> dict:
    """Read [tool.gds-idea-app-kit] from pyproject.toml.

    Args:
        project_dir: Root directory of the project.

    Returns:
        The manifest dict, or empty dict if the section doesn't exist.
    """
    pyproject_path = project_dir / "pyproject.toml"
    if not pyproject_path.exists():
        return {}

    with open(pyproject_path) as f:
        config = tomlkit.load(f)

    return dict(config.get("tool", {}).get(MANIFEST_KEY, {}))


def write_manifest(project_dir: Path, manifest: dict) -> None:
    """Write/update [tool.gds-idea-app-kit] in pyproject.toml, preserving other content.

    Args:
        project_dir: Root directory of the project.
        manifest: The manifest dict to write.
    """
    pyproject_path = project_dir / "pyproject.toml"

    with open(pyproject_path) as f:
        config = tomlkit.load(f)

    # Ensure [tool] section exists
    if "tool" not in config:
        config["tool"] = {}

    # Write the manifest section
    config["tool"][MANIFEST_KEY] = manifest

    with open(pyproject_path, "w") as f:
        tomlkit.dump(config, f)


def build_manifest(
    framework: str,
    app_name: str,
    tool_version: str,
    project_dir: Path,
) -> dict:
    """Build a manifest dict by hashing the tracked files in project_dir.

    Args:
        framework: The project type (streamlit, dash, fastapi, or infra).
        app_name: The application name.
        tool_version: The version of gds-idea-app-kit that generated the project.
        project_dir: Root directory of the project.

    Returns:
        Complete manifest dict ready to write to pyproject.toml.
    """
    tracked = get_tracked_files(framework)

    file_hashes = {}
    for _template_src, dest_path in sorted(tracked.items()):
        full_path = project_dir / dest_path
        if full_path.exists():
            file_hashes[dest_path] = hash_file(full_path)

    manifest = {
        "framework": framework,
        "app_name": app_name,
        "tool_version": tool_version,
        "files": file_hashes,
    }

    return manifest
