"""Manifest management for tracking tool-owned files in [tool.gds-idea-app-kit].

The manifest lives in pyproject.toml under the [tool.gds-idea-app-kit] section and tracks:
- Project metadata (framework, app_name, tool_version)
- SHA256 hashes of tool-owned files (for change detection during updates)
"""

import hashlib
from pathlib import Path

import tomlkit

# Key used in pyproject.toml [tool.*] section
MANIFEST_KEY = "gds-idea-app-kit"

# Files that `update` manages, keyed by source location in the templates directory.
# The dict maps template source path -> destination path in the project.
TOOL_OWNED_FILES = {
    "common/devcontainer.json": ".devcontainer/devcontainer.json",
    "common/docker-compose.yml": ".devcontainer/docker-compose.yml",
    "dev_mocks/dev_mock_authoriser.json": "dev_mocks/dev_mock_authoriser.json",
    "dev_mocks/dev_mock_user.json": "dev_mocks/dev_mock_user.json",
}

# Framework-specific files that `update` manages.
# The framework name is substituted at runtime.
FRAMEWORK_OWNED_FILES = {
    "Dockerfile": "app_src/Dockerfile",
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
        framework: The framework name (streamlit, dash, fastapi).

    Returns:
        Dict mapping template source paths to project destination paths.
    """
    files = dict(TOOL_OWNED_FILES)
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
        framework: The framework name (streamlit, dash, fastapi).
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
