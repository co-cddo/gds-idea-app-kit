"""Tests for the update command."""

import os
from unittest.mock import patch

import pytest

from gds_idea_app_kit.init import _apply_template_vars, _get_templates_dir
from gds_idea_app_kit.manifest import (
    build_manifest,
    get_tracked_files,
    hash_file,
    read_manifest,
    write_manifest,
)
from gds_idea_app_kit.update import _check_version, _parse_version, run_update

# ---- fixtures ----


@pytest.fixture()
def update_project(tmp_path):
    """Create a project directory with manifest and all tracked files for streamlit.

    Returns the project directory path.
    """
    framework = "streamlit"
    app_name = "test-app"
    templates_dir = _get_templates_dir()
    tracked = get_tracked_files(framework)
    template_vars = {
        "app_name": app_name,
        "python_version": "3.13",
        "python_version_nodot": "313",
    }

    # Copy all tracked template files into the project
    for template_src, dest_path in tracked.items():
        template_full = templates_dir / template_src
        dest_full = tmp_path / dest_path
        dest_full.parent.mkdir(parents=True, exist_ok=True)
        content = template_full.read_text()
        content = _apply_template_vars(content, template_vars)
        dest_full.write_text(content)

    # Write pyproject.toml with manifest
    pyproject = tmp_path / "pyproject.toml"
    pyproject.write_text('[project]\nname = "test-app"\nversion = "0.1.0"\n\n[tool]\n')

    manifest = build_manifest(
        framework=framework,
        app_name=app_name,
        tool_version="0.1.0",
        project_dir=tmp_path,
    )
    manifest["python_version"] = "3.13"
    write_manifest(tmp_path, manifest)

    return tmp_path


# ---- _parse_version ----


def test_parse_version_three_part():
    """Parses a standard three-part version string."""
    assert _parse_version("0.1.0") == (0, 1, 0)


def test_parse_version_two_part():
    """Parses a two-part version string."""
    assert _parse_version("1.0") == (1, 0)


def test_parse_version_single():
    """Parses a single-number version string."""
    assert _parse_version("3") == (3,)


def test_parse_version_comparison_minor():
    """Minor version bump compares correctly."""
    assert _parse_version("0.1.0") < _parse_version("0.2.0")


def test_parse_version_comparison_patch():
    """Patch version bump compares correctly."""
    assert _parse_version("0.1.0") < _parse_version("0.1.1")


def test_parse_version_comparison_equal():
    """Equal versions compare as equal."""
    assert _parse_version("1.0.0") == _parse_version("1.0.0")


def test_parse_version_comparison_major_wins():
    """Major version takes precedence over minor and patch."""
    assert _parse_version("2.0.0") > _parse_version("1.9.9")


# ---- _check_version ----


def test_check_version_older_tool_warns(capsys):
    """When installed tool is older than manifest version, prints a warning."""
    with patch("gds_idea_app_kit.update.__version__", "0.1.0"):
        _check_version({"tool_version": "0.2.0"})

    captured = capsys.readouterr()
    assert "0.2.0" in captured.err
    assert "upgrade" in captured.err


def test_check_version_same_version_no_warning(capsys):
    """When versions match, no warning is printed."""
    with patch("gds_idea_app_kit.update.__version__", "0.1.0"):
        _check_version({"tool_version": "0.1.0"})

    captured = capsys.readouterr()
    assert captured.err == ""


def test_check_version_newer_tool_no_warning(capsys):
    """When installed tool is newer, no warning is printed."""
    with patch("gds_idea_app_kit.update.__version__", "0.2.0"):
        _check_version({"tool_version": "0.1.0"})

    captured = capsys.readouterr()
    assert captured.err == ""


# ---- run_update error cases ----


def test_update_no_pyproject(tmp_path, capsys):
    """Exit 1 when no pyproject.toml exists."""
    with pytest.raises(SystemExit):
        os.chdir(tmp_path)
        run_update(dry_run=False)

    captured = capsys.readouterr()
    assert "No pyproject.toml" in captured.err


def test_update_no_manifest(tmp_path, capsys):
    """Exit 1 when pyproject.toml has no manifest section."""
    pyproject = tmp_path / "pyproject.toml"
    pyproject.write_text('[project]\nname = "test-app"\n')

    with pytest.raises(SystemExit):
        os.chdir(tmp_path)
        run_update(dry_run=False)

    captured = capsys.readouterr()
    assert "No [tool.gds-idea-app-kit]" in captured.err


# ---- run_update file handling ----


def test_update_unchanged_files_get_overwritten(update_project, capsys):
    """Files whose hash matches the manifest are overwritten with latest template."""
    os.chdir(update_project)
    run_update(dry_run=False)

    captured = capsys.readouterr()
    # All files match their manifest hashes, so all should be updated
    # The key thing is no files show as modified
    assert "Modified:" not in captured.out


def test_update_modified_file_writes_new(update_project, capsys):
    """Modified files get a .new file written alongside with review instructions."""
    # Modify one tracked file
    dockerfile = update_project / "app_src" / "Dockerfile"
    dockerfile.write_text("# User modified this file\n")

    os.chdir(update_project)
    run_update(dry_run=False)

    captured = capsys.readouterr()
    assert "Modified: app_src/Dockerfile" in captured.out
    assert "app_src/Dockerfile.new" in captured.out
    assert "diff app_src/Dockerfile app_src/Dockerfile.new" in captured.out


def test_update_modified_file_new_has_template_content(update_project):
    """The .new file contains the latest template content, not the user's version."""
    # Modify one tracked file
    dockerfile = update_project / "app_src" / "Dockerfile"
    dockerfile.write_text("# User modified this file\n")

    os.chdir(update_project)
    run_update(dry_run=False)

    new_file = update_project / "app_src" / "Dockerfile.new"
    assert new_file.exists()
    content = new_file.read_text()
    # Should have template content (Dockerfile starts with a comment header)
    assert "# User modified" not in content
    assert "FROM python:" in content


def test_update_modified_file_original_unchanged(update_project):
    """The original modified file is not overwritten."""
    dockerfile = update_project / "app_src" / "Dockerfile"
    dockerfile.write_text("# User modified this file\n")

    os.chdir(update_project)
    run_update(dry_run=False)

    assert dockerfile.read_text() == "# User modified this file\n"


def test_update_modified_summary_count(update_project, capsys):
    """Summary line reports the count of modified files."""
    # Modify two tracked files
    dockerfile = update_project / "app_src" / "Dockerfile"
    dockerfile.write_text("# modified\n")
    devcontainer = update_project / ".devcontainer" / "devcontainer.json"
    devcontainer.write_text("// modified\n")

    os.chdir(update_project)
    run_update(dry_run=False)

    captured = capsys.readouterr()
    assert "2 file(s) had local modifications" in captured.out


def test_update_missing_file_is_created(update_project, capsys):
    """Files missing from the project are created fresh."""
    dockerfile = update_project / "app_src" / "Dockerfile"
    dockerfile.unlink()

    os.chdir(update_project)
    run_update(dry_run=False)

    captured = capsys.readouterr()
    assert "Created: app_src/Dockerfile" in captured.out
    assert dockerfile.exists()


def test_update_dry_run_makes_no_changes(update_project, capsys):
    """Dry run reports what would change but doesn't modify files or write .new files."""
    # Delete a file and modify another
    dockerfile = update_project / "app_src" / "Dockerfile"
    dockerfile.unlink()
    devcontainer = update_project / ".devcontainer" / "devcontainer.json"
    devcontainer.write_text("// modified\n")

    manifest_before = read_manifest(update_project)

    os.chdir(update_project)
    run_update(dry_run=True)

    # Deleted file should still be missing
    assert not dockerfile.exists()
    # No .new file should have been created
    assert not (update_project / ".devcontainer" / "devcontainer.json.new").exists()
    # Manifest should be unchanged
    manifest_after = read_manifest(update_project)
    assert manifest_before == manifest_after

    captured = capsys.readouterr()
    assert "No changes made (dry run)" in captured.out


def test_update_manifest_is_refreshed_after_changes(update_project):
    """After updating files, the manifest hashes are refreshed."""
    dockerfile = update_project / "app_src" / "Dockerfile"
    dockerfile.unlink()

    os.chdir(update_project)
    run_update(dry_run=False)

    manifest = read_manifest(update_project)
    assert "app_src/Dockerfile" in manifest.get("files", {})
    assert hash_file(dockerfile) == manifest["files"]["app_src/Dockerfile"]
