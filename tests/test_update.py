"""Tests for the update command."""

import os
from pathlib import Path
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
from gds_idea_app_kit.update import (
    Action,
    FileUpdate,
    _apply_updates,
    _check_version,
    _classify_file,
    _parse_version,
    _plan_updates,
    _report_updates,
    run_update,
)

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
    # The key thing is no files show as skipped
    assert "Skipped:" not in captured.out


def test_update_modified_file_writes_new(update_project, capsys):
    """Locally modified files get a .new file written alongside with review instructions."""
    # Modify one tracked file
    dockerfile = update_project / "app_src" / "Dockerfile"
    dockerfile.write_text("# User modified this file\n")

    os.chdir(update_project)
    run_update(dry_run=False)

    captured = capsys.readouterr()
    assert "Skipped: app_src/Dockerfile (locally modified)" in captured.out
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
    """Summary line reports the count of locally modified files."""
    # Modify two tracked files
    dockerfile = update_project / "app_src" / "Dockerfile"
    dockerfile.write_text("# modified\n")
    devcontainer = update_project / ".devcontainer" / "devcontainer.json"
    devcontainer.write_text("// modified\n")

    os.chdir(update_project)
    run_update(dry_run=False)

    captured = capsys.readouterr()
    assert "2 file(s) were locally modified and skipped" in captured.out


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


# ---- run_update --force ----


def test_update_force_overwrites_modified_file(update_project, capsys):
    """Force mode overwrites locally modified files instead of writing .new."""
    dockerfile = update_project / "app_src" / "Dockerfile"
    dockerfile.write_text("# User modified this file\n")

    os.chdir(update_project)
    run_update(dry_run=False, force=True)

    captured = capsys.readouterr()
    # Should show as updated, not skipped
    assert "Updated: app_src/Dockerfile" in captured.out
    assert "Skipped:" not in captured.out
    # No .new file should be created
    assert not (update_project / "app_src" / "Dockerfile.new").exists()
    # Original should be overwritten with template content
    assert "# User modified" not in dockerfile.read_text()
    assert "FROM python:" in dockerfile.read_text()


def test_update_force_no_new_files_created(update_project):
    """Force mode never creates .new files."""
    # Modify all tracked files
    for dest_path in get_tracked_files("streamlit").values():
        dest_full = update_project / dest_path
        if dest_full.exists():
            dest_full.write_text("# modified\n")

    os.chdir(update_project)
    run_update(dry_run=False, force=True)

    # No .new files anywhere
    new_files = list(update_project.rglob("*.new"))
    assert new_files == []


def test_update_force_updates_manifest(update_project):
    """Force mode updates the manifest with new hashes after overwriting."""
    dockerfile = update_project / "app_src" / "Dockerfile"
    dockerfile.write_text("# User modified this file\n")

    os.chdir(update_project)
    run_update(dry_run=False, force=True)

    manifest = read_manifest(update_project)
    assert hash_file(dockerfile) == manifest["files"]["app_src/Dockerfile"]


# ---- _classify_file ----


def test_classify_missing_file_returns_create(tmp_path):
    """A file that doesn't exist on disk is classified as CREATE."""
    dest_full = tmp_path / "missing.txt"
    action = _classify_file(dest_full, {}, "missing.txt", force=False)
    assert action == Action.CREATE


def test_classify_unchanged_file_returns_update(tmp_path):
    """A file whose hash matches the manifest is classified as UPDATE."""
    dest_full = tmp_path / "file.txt"
    dest_full.write_text("original content")
    file_hash = hash_file(dest_full)

    action = _classify_file(dest_full, {"file.txt": file_hash}, "file.txt", force=False)
    assert action == Action.UPDATE


def test_classify_modified_file_returns_skip(tmp_path):
    """A file whose hash differs from the manifest is classified as SKIP."""
    dest_full = tmp_path / "file.txt"
    dest_full.write_text("modified content")

    action = _classify_file(dest_full, {"file.txt": "old-hash"}, "file.txt", force=False)
    assert action == Action.SKIP


def test_classify_modified_file_with_force_returns_force(tmp_path):
    """A modified file with --force is classified as FORCE, not SKIP."""
    dest_full = tmp_path / "file.txt"
    dest_full.write_text("modified content")

    action = _classify_file(dest_full, {"file.txt": "old-hash"}, "file.txt", force=True)
    assert action == Action.FORCE


def test_classify_file_not_in_manifest_returns_update(tmp_path):
    """A file that exists but has no manifest entry is classified as UPDATE."""
    dest_full = tmp_path / "file.txt"
    dest_full.write_text("some content")

    action = _classify_file(dest_full, {}, "file.txt", force=False)
    assert action == Action.UPDATE


# ---- _plan_updates ----


@pytest.fixture()
def plan_project(tmp_path):
    """Create a minimal project with templates for plan testing.

    Returns a dict with project_dir, templates_dir, tracked, template_vars,
    and manifest_hashes for use in _plan_updates calls.
    """
    framework = "streamlit"
    templates_dir = _get_templates_dir()
    tracked = get_tracked_files(framework)
    template_vars = {
        "app_name": "test-app",
        "python_version": "3.13",
        "python_version_nodot": "313",
    }

    # Copy all tracked files into the project
    for template_src, dest_path in tracked.items():
        template_full = templates_dir / template_src
        dest_full = tmp_path / dest_path
        dest_full.parent.mkdir(parents=True, exist_ok=True)
        content = template_full.read_text()
        content = _apply_template_vars(content, template_vars)
        dest_full.write_text(content)

    # Build manifest hashes from the files we just wrote
    manifest_hashes = {}
    for _, dest_path in tracked.items():
        dest_full = tmp_path / dest_path
        if dest_full.exists():
            manifest_hashes[dest_path] = hash_file(dest_full)

    return {
        "project_dir": tmp_path,
        "tracked": tracked,
        "templates_dir": templates_dir,
        "template_vars": template_vars,
        "manifest_hashes": manifest_hashes,
    }


def test_plan_all_unchanged_returns_all_update(plan_project):
    """When all files match manifest hashes, every item is ACTION.UPDATE."""
    plan = _plan_updates(**plan_project, force=False)

    assert len(plan) > 0
    assert all(item.action == Action.UPDATE for item in plan)


def test_plan_missing_file_returns_create(plan_project):
    """A file deleted from the project is planned as CREATE."""
    dockerfile = plan_project["project_dir"] / "app_src" / "Dockerfile"
    dockerfile.unlink()

    plan = _plan_updates(**plan_project, force=False)

    create_items = [item for item in plan if item.action == Action.CREATE]
    assert any(item.dest_path == "app_src/Dockerfile" for item in create_items)


def test_plan_modified_file_returns_skip(plan_project):
    """A locally modified file is planned as SKIP."""
    dockerfile = plan_project["project_dir"] / "app_src" / "Dockerfile"
    dockerfile.write_text("# user modified\n")

    plan = _plan_updates(**plan_project, force=False)

    skipped = [item for item in plan if item.action == Action.SKIP]
    assert any(item.dest_path == "app_src/Dockerfile" for item in skipped)


def test_plan_modified_file_with_force_returns_force(plan_project):
    """A locally modified file with force=True is planned as FORCE."""
    dockerfile = plan_project["project_dir"] / "app_src" / "Dockerfile"
    dockerfile.write_text("# user modified\n")

    plan = _plan_updates(**plan_project, force=True)

    forced = [item for item in plan if item.action == Action.FORCE]
    assert any(item.dest_path == "app_src/Dockerfile" for item in forced)
    # No SKIP items when force is used
    assert not any(item.action == Action.SKIP for item in plan)


def test_plan_contains_rendered_content(plan_project):
    """Plan items contain the rendered template content with variables substituted."""
    plan = _plan_updates(**plan_project, force=False)

    dockerfile_item = next(item for item in plan if item.dest_path == "app_src/Dockerfile")
    # Template variables should be substituted in the content
    assert "{{app_name}}" not in dockerfile_item.new_content
    assert "{{python_version}}" not in dockerfile_item.new_content


def test_plan_skips_missing_templates(plan_project):
    """Template files that don't exist in the package are silently excluded."""
    # Add a fake entry to tracked that has no template file
    plan_project["tracked"]["nonexistent/template.txt"] = "nonexistent/output.txt"

    plan = _plan_updates(**plan_project, force=False)

    assert not any(item.dest_path == "nonexistent/output.txt" for item in plan)


def test_plan_items_have_correct_dest_full(plan_project):
    """Each plan item has dest_full pointing to the absolute path in the project."""
    plan = _plan_updates(**plan_project, force=False)

    for item in plan:
        expected = plan_project["project_dir"] / item.dest_path
        assert item.dest_full == expected


# ---- _apply_updates ----


def test_apply_create_writes_file(tmp_path):
    """CREATE action writes the file to disk."""
    dest_full = tmp_path / "new_file.txt"
    plan = [FileUpdate("new_file.txt", dest_full, "hello world", Action.CREATE)]

    _apply_updates(plan)

    assert dest_full.exists()
    assert dest_full.read_text() == "hello world"


def test_apply_create_makes_parent_dirs(tmp_path):
    """CREATE action creates parent directories if needed."""
    dest_full = tmp_path / "deep" / "nested" / "file.txt"
    plan = [FileUpdate("deep/nested/file.txt", dest_full, "content", Action.CREATE)]

    _apply_updates(plan)

    assert dest_full.exists()
    assert dest_full.read_text() == "content"


def test_apply_update_overwrites_file(tmp_path):
    """UPDATE action overwrites an existing file."""
    dest_full = tmp_path / "file.txt"
    dest_full.write_text("old content")
    plan = [FileUpdate("file.txt", dest_full, "new content", Action.UPDATE)]

    _apply_updates(plan)

    assert dest_full.read_text() == "new content"


def test_apply_force_overwrites_file(tmp_path):
    """FORCE action overwrites an existing file."""
    dest_full = tmp_path / "file.txt"
    dest_full.write_text("user modified")
    plan = [FileUpdate("file.txt", dest_full, "template content", Action.FORCE)]

    _apply_updates(plan)

    assert dest_full.read_text() == "template content"


def test_apply_skip_writes_new_file(tmp_path):
    """SKIP action writes a .new file alongside, leaving the original untouched."""
    dest_full = tmp_path / "file.txt"
    dest_full.write_text("user modified")
    plan = [FileUpdate("file.txt", dest_full, "template content", Action.SKIP)]

    _apply_updates(plan)

    assert dest_full.read_text() == "user modified"
    new_file = tmp_path / "file.txt.new"
    assert new_file.exists()
    assert new_file.read_text() == "template content"


def test_apply_mixed_actions(tmp_path):
    """Multiple actions in a single plan are all applied correctly."""
    create_file = tmp_path / "created.txt"
    update_file = tmp_path / "updated.txt"
    update_file.write_text("old")
    skip_file = tmp_path / "skipped.txt"
    skip_file.write_text("user version")

    plan = [
        FileUpdate("created.txt", create_file, "new file", Action.CREATE),
        FileUpdate("updated.txt", update_file, "new version", Action.UPDATE),
        FileUpdate("skipped.txt", skip_file, "template version", Action.SKIP),
    ]

    _apply_updates(plan)

    assert create_file.read_text() == "new file"
    assert update_file.read_text() == "new version"
    assert skip_file.read_text() == "user version"
    assert (tmp_path / "skipped.txt.new").read_text() == "template version"


# ---- _report_updates ----


def test_report_created_files(capsys):
    """Created files are reported with 'Created:' prefix."""
    plan = [FileUpdate("app_src/Dockerfile", Path("/fake"), "", Action.CREATE)]

    _report_updates(plan, dry_run=False)

    captured = capsys.readouterr()
    assert "Created: app_src/Dockerfile" in captured.out


def test_report_updated_files(capsys):
    """Updated files are reported with 'Updated:' prefix."""
    plan = [FileUpdate("app_src/Dockerfile", Path("/fake"), "", Action.UPDATE)]

    _report_updates(plan, dry_run=False)

    captured = capsys.readouterr()
    assert "Updated: app_src/Dockerfile" in captured.out


def test_report_forced_files_show_as_updated(capsys):
    """FORCE actions are reported as 'Updated:', not 'Forced:'."""
    plan = [FileUpdate("app_src/Dockerfile", Path("/fake"), "", Action.FORCE)]

    _report_updates(plan, dry_run=False)

    captured = capsys.readouterr()
    assert "Updated: app_src/Dockerfile" in captured.out


def test_report_skipped_files_with_review_instructions(capsys):
    """Skipped files show the path, .new path, and diff command."""
    plan = [FileUpdate("app_src/Dockerfile", Path("/fake"), "", Action.SKIP)]

    _report_updates(plan, dry_run=False)

    captured = capsys.readouterr()
    assert "Skipped: app_src/Dockerfile (locally modified)" in captured.out
    assert "app_src/Dockerfile.new" in captured.out
    assert "diff app_src/Dockerfile app_src/Dockerfile.new" in captured.out


def test_report_skipped_summary_count(capsys):
    """Summary reports the count of skipped files."""
    plan = [
        FileUpdate("file1.txt", Path("/fake1"), "", Action.SKIP),
        FileUpdate("file2.txt", Path("/fake2"), "", Action.SKIP),
    ]

    _report_updates(plan, dry_run=False)

    captured = capsys.readouterr()
    assert "2 file(s) were locally modified and skipped" in captured.out


def test_report_skipped_summary_not_shown_in_dry_run(capsys):
    """Dry run does not show the 'locally modified and skipped' summary."""
    plan = [FileUpdate("file.txt", Path("/fake"), "", Action.SKIP)]

    _report_updates(plan, dry_run=True)

    captured = capsys.readouterr()
    assert "locally modified and skipped" not in captured.out


def test_report_empty_plan(capsys):
    """Empty plan reports 'Nothing to update.'."""
    _report_updates([], dry_run=False)

    captured = capsys.readouterr()
    assert "Nothing to update." in captured.out


def test_report_dry_run_footer(capsys):
    """Dry run shows 'No changes made (dry run).' footer."""
    plan = [FileUpdate("file.txt", Path("/fake"), "", Action.UPDATE)]

    _report_updates(plan, dry_run=True)

    captured = capsys.readouterr()
    assert "No changes made (dry run)." in captured.out
