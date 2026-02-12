"""Tests for init module helper functions."""

import click
import pytest

from gds_idea_app_kit import REPO_PREFIX
from gds_idea_app_kit.init import (
    _apply_template_vars,
    _copy_template,
    _get_templates_dir,
    _run_command,
    _sanitize_app_name,
)

# ---- _sanitize_app_name ----
# Validates that app names are safe for use as DNS subdomain labels
# (the name becomes {name}.gds-idea.click).


def test_sanitize_valid_name():
    """A typical hyphenated name passes through unchanged."""
    assert _sanitize_app_name("my-dashboard") == "my-dashboard"


def test_sanitize_simple_name():
    """A single-word name passes through unchanged."""
    assert _sanitize_app_name("myapp") == "myapp"


def test_sanitize_name_with_numbers():
    """Names containing digits are valid."""
    assert _sanitize_app_name("app-123") == "app-123"


def test_sanitize_strips_repo_prefix():
    """If the user accidentally includes the repo prefix, strip it."""
    assert _sanitize_app_name(f"{REPO_PREFIX}-my-dashboard") == "my-dashboard"


def test_sanitize_lowercases():
    """Mixed-case input is lowercased automatically."""
    assert _sanitize_app_name("My-Dashboard") == "my-dashboard"


def test_sanitize_rejects_empty():
    """Empty string is rejected."""
    with pytest.raises(click.BadParameter, match="cannot be empty"):
        _sanitize_app_name("")


def test_sanitize_rejects_empty_after_prefix_strip():
    """The prefix alone with no name is rejected."""
    with pytest.raises(click.BadParameter, match="cannot be empty"):
        _sanitize_app_name(f"{REPO_PREFIX}-")


def test_sanitize_rejects_leading_hyphen():
    """DNS labels cannot start with a hyphen."""
    with pytest.raises(click.BadParameter, match="start and end"):
        _sanitize_app_name("-my-app")


def test_sanitize_rejects_trailing_hyphen():
    """DNS labels cannot end with a hyphen."""
    with pytest.raises(click.BadParameter, match="start and end"):
        _sanitize_app_name("my-app-")


def test_sanitize_rejects_consecutive_hyphens():
    """Consecutive hyphens are invalid in subdomain labels."""
    with pytest.raises(click.BadParameter, match="consecutive hyphens"):
        _sanitize_app_name("my--app")


def test_sanitize_rejects_purely_numeric():
    """Purely numeric names could be confused with IP addresses."""
    with pytest.raises(click.BadParameter, match="purely numeric"):
        _sanitize_app_name("12345")


def test_sanitize_rejects_underscores():
    """Underscores are not valid in DNS labels."""
    with pytest.raises(click.BadParameter, match="lowercase letters"):
        _sanitize_app_name("my_app")


def test_sanitize_rejects_spaces():
    """Spaces are not valid in DNS labels."""
    with pytest.raises(click.BadParameter, match="lowercase letters"):
        _sanitize_app_name("my app")


def test_sanitize_rejects_too_long():
    """DNS labels are limited to 63 characters."""
    with pytest.raises(click.BadParameter, match="63 characters"):
        _sanitize_app_name("a" * 64)


def test_sanitize_accepts_max_length():
    """Exactly 63 characters is valid."""
    name = "a" * 63
    assert _sanitize_app_name(name) == name


def test_sanitize_single_char():
    """A single letter is a valid name."""
    assert _sanitize_app_name("a") == "a"


def test_sanitize_single_digit_rejected():
    """A single digit is purely numeric and rejected."""
    with pytest.raises(click.BadParameter, match="purely numeric"):
        _sanitize_app_name("1")


# ---- _get_templates_dir ----
# Verifies that bundled template files are accessible via importlib.resources.


def test_get_templates_dir_exists():
    """The templates directory should be bundled with the package."""
    templates = _get_templates_dir()
    assert templates.exists()
    assert templates.is_dir()


def test_get_templates_dir_has_common():
    """The common/ subdirectory contains shared template files."""
    templates = _get_templates_dir()
    assert (templates / "common").is_dir()


def test_get_templates_dir_has_frameworks():
    """Each supported framework has its own template subdirectory."""
    templates = _get_templates_dir()
    assert (templates / "streamlit").is_dir()
    assert (templates / "dash").is_dir()
    assert (templates / "fastapi").is_dir()


# ---- _apply_template_vars ----
# Tests the simple {{placeholder}} substitution used in templates.


def test_apply_vars_replaces_placeholders():
    """A single placeholder is replaced with its value."""
    content = "FROM python:{{python_version}}-slim"
    result = _apply_template_vars(content, {"python_version": "3.13"})
    assert result == "FROM python:3.13-slim"


def test_apply_vars_multiple_placeholders():
    """Multiple different placeholders are all replaced."""
    content = 'name = "{{app_name}}"\ntarget = "py{{python_version_nodot}}"'
    result = _apply_template_vars(content, {"app_name": "my-app", "python_version_nodot": "313"})
    assert result == 'name = "my-app"\ntarget = "py313"'


def test_apply_vars_no_placeholders():
    """Content without placeholders is returned unchanged."""
    content = "no placeholders here"
    result = _apply_template_vars(content, {"app_name": "my-app"})
    assert result == "no placeholders here"


def test_apply_vars_empty_variables():
    """An empty variables dict leaves placeholders in place."""
    content = "{{app_name}} stays"
    result = _apply_template_vars(content, {})
    assert result == "{{app_name}} stays"


def test_apply_vars_repeated_placeholder():
    """The same placeholder appearing twice is replaced in both locations."""
    content = "{{app_name}} and {{app_name}}"
    result = _apply_template_vars(content, {"app_name": "foo"})
    assert result == "foo and foo"


# ---- _copy_template ----
# Tests the file copy helper that reads a template, optionally applies
# variable substitution, and writes to a destination path.


def test_copy_template_simple(tmp_path):
    """A plain file is copied verbatim when no variables are given."""
    src = tmp_path / "src" / "template.txt"
    src.parent.mkdir()
    src.write_text("hello world")

    dest = tmp_path / "dest" / "output.txt"
    _copy_template(src, dest)

    assert dest.read_text() == "hello world"


def test_copy_template_creates_parent_dirs(tmp_path):
    """Missing parent directories at the destination are created automatically."""
    src = tmp_path / "template.txt"
    src.write_text("content")

    dest = tmp_path / "deep" / "nested" / "dir" / "output.txt"
    _copy_template(src, dest)

    assert dest.exists()
    assert dest.read_text() == "content"


def test_copy_template_with_variables(tmp_path):
    """Placeholders in the template are replaced when variables are provided."""
    src = tmp_path / "template.txt"
    src.write_text("FROM python:{{python_version}}-slim")

    dest = tmp_path / "output.txt"
    _copy_template(src, dest, variables={"python_version": "3.12"})

    assert dest.read_text() == "FROM python:3.12-slim"


def test_copy_template_without_variables(tmp_path):
    """When variables=None, placeholders are left as-is (no substitution)."""
    src = tmp_path / "template.txt"
    src.write_text("no {{placeholders}} replaced")

    dest = tmp_path / "output.txt"
    _copy_template(src, dest, variables=None)

    assert dest.read_text() == "no {{placeholders}} replaced"


# ---- _run_command ----
# Wraps subprocess.run with error handling: catches missing commands
# (especially cdk with install instructions) and prints a cleanup
# command on failure.


def test_run_command_success(tmp_path):
    """A successful command returns the CompletedProcess result."""
    result = _run_command(["echo", "hello"], cwd=tmp_path)
    assert result.returncode == 0
    assert "hello" in result.stdout


def test_run_command_failed_prints_cleanup(tmp_path, capsys):
    """A failing command prints stderr and a cleanup rm -rf suggestion."""
    with pytest.raises(SystemExit):
        _run_command(["false"], cwd=tmp_path, project_dir=tmp_path)

    captured = capsys.readouterr()
    assert "rm -rf" in captured.err
    assert str(tmp_path) in captured.err


def test_run_command_missing_cdk_prints_install_instructions(tmp_path, capsys):
    """When cdk is not found, prints npm/brew install instructions."""
    with pytest.raises(SystemExit):
        _run_command(["cdk-nonexistent-binary"], cwd=tmp_path)

    captured = capsys.readouterr()
    assert "not installed" in captured.err


def test_run_command_missing_cdk_specific_message(tmp_path, capsys):
    """The cdk-specific error message includes npm and brew install options."""
    with pytest.raises(SystemExit):
        _run_command(["cdk"], cwd=tmp_path)

    # cdk might actually be installed -- only check the error path
    # if it actually failed with FileNotFoundError


def test_run_command_missing_arbitrary_binary(tmp_path, capsys):
    """A missing non-cdk binary prints a generic 'not installed' error."""
    with pytest.raises(SystemExit):
        _run_command(["totally-nonexistent-command-xyz"], cwd=tmp_path)

    captured = capsys.readouterr()
    assert "totally-nonexistent-command-xyz" in captured.err
    assert "not installed" in captured.err
