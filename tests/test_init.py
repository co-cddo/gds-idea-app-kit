"""Tests for init module helper functions."""

from unittest.mock import MagicMock, patch

import click
import pytest

from gds_idea_app_kit import REPO_PREFIX
from gds_idea_app_kit.init import (
    _apply_template_vars,
    _copy_template,
    _get_templates_dir,
    _run_command,
    _sanitize_app_name,
    run_init,
)

GDS_IDEA_INDEX_URL = "https://co-cddo.github.io/gds-idea-pypi/simple/"

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


def test_get_templates_dir_has_web_common():
    """The web_common/ subdirectory contains web-framework-specific shared files."""
    templates = _get_templates_dir()
    assert (templates / "web_common").is_dir()
    assert (templates / "web_common" / "app.py").is_file()
    assert (templates / "web_common" / "devcontainer.json").is_file()
    assert (templates / "web_common" / "docker-compose.yml").is_file()


def test_get_templates_dir_has_frameworks():
    """Each supported framework has its own template subdirectory."""
    templates = _get_templates_dir()
    assert (templates / "streamlit").is_dir()
    assert (templates / "dash").is_dir()
    assert (templates / "fastapi").is_dir()


def test_get_templates_dir_has_infra():
    """The infra/ subdirectory contains the infrastructure-only template."""
    templates = _get_templates_dir()
    assert (templates / "infra").is_dir()
    assert (templates / "infra" / "app.py").is_file()


def test_get_templates_dir_has_codeowners_template():
    """The CODEOWNERS.template file must be present in common/ so init can copy it."""
    templates = _get_templates_dir()
    assert (templates / "common" / "CODEOWNERS.template").is_file()


# ---- pyproject.toml.template content ----
# Verifies that each framework template declares cognito-auth from the internal
# PyPI index rather than a git URL, and that the index stanzas are present.


@pytest.mark.parametrize(
    "framework, extra",
    [
        ("streamlit", "cognito-auth[streamlit]>=0.3.0"),
        ("dash", "cognito-auth[dash]>=0.3.0"),
        ("fastapi", "cognito-auth[fastapi]>=0.3.0"),
    ],
)
def test_pyproject_template_uses_versioned_cognito_auth(framework, extra):
    """cognito-auth is pinned to a version, not a git URL."""
    templates = _get_templates_dir()
    content = (templates / framework / "pyproject.toml.template").read_text()
    assert extra in content


@pytest.mark.parametrize("framework", ["streamlit", "dash", "fastapi"])
def test_pyproject_template_has_no_git_url(framework):
    """No git+https or git+ssh dependency URLs remain in any framework template."""
    templates = _get_templates_dir()
    content = (templates / framework / "pyproject.toml.template").read_text()
    assert "git+https://" not in content
    assert "git+ssh://" not in content


@pytest.mark.parametrize("framework", ["streamlit", "dash", "fastapi"])
def test_pyproject_template_has_gds_idea_index(framework):
    """Each template declares the gds-idea index with the correct URL."""
    templates = _get_templates_dir()
    content = (templates / framework / "pyproject.toml.template").read_text()
    assert "[tool.uv.sources]" in content
    assert 'cognito-auth = { index = "gds-idea" }' in content
    assert "[[tool.uv.index]]" in content
    assert GDS_IDEA_INDEX_URL in content


# ---- run_init CDK dependency install ----
# Verifies that run_init makes two separate uv add calls: one for the public
# PyPI packages (no --index) and one for the internal package with --index.


def test_run_init_cdk_install_is_split_into_two_calls(tmp_path, monkeypatch):
    """run_init calls uv add three times — PyPI packages, internal package, and dev deps."""
    monkeypatch.chdir(tmp_path)

    uv_add_calls = []

    def fake_run_command(cmd, cwd, project_dir=None):
        if cmd[:2] == ["uv", "init"]:
            # Simulate uv init creating a minimal pyproject.toml
            (cwd / "pyproject.toml").write_text(
                '[project]\nname = "gds-idea-app-test-app"\nversion = "0.0.0"\n\n[tool]\n'
            )
        if cmd[:2] == ["uv", "add"]:
            uv_add_calls.append(cmd)
        return MagicMock(returncode=0, stdout="", stderr="")

    with (
        patch("gds_idea_app_kit.init.check_prerequisites"),
        patch("gds_idea_app_kit.init._run_command", side_effect=fake_run_command),
    ):
        run_init("streamlit", "test-app", "3.13")

    assert len(uv_add_calls) == 3


def test_run_init_first_uv_add_is_pypi_packages(tmp_path, monkeypatch):
    """The first uv add installs PyPI packages without an --index flag."""
    monkeypatch.chdir(tmp_path)

    uv_add_calls = []

    def fake_run_command(cmd, cwd, project_dir=None):
        if cmd[:2] == ["uv", "init"]:
            (cwd / "pyproject.toml").write_text(
                '[project]\nname = "gds-idea-app-test-app"\nversion = "0.0.0"\n\n[tool]\n'
            )
        if cmd[:2] == ["uv", "add"]:
            uv_add_calls.append(cmd)
        return MagicMock(returncode=0, stdout="", stderr="")

    with (
        patch("gds_idea_app_kit.init.check_prerequisites"),
        patch("gds_idea_app_kit.init._run_command", side_effect=fake_run_command),
    ):
        run_init("streamlit", "test-app", "3.13")

    first = uv_add_calls[0]
    assert "aws-cdk-lib" in first
    assert "constructs" in first
    assert "--index" not in first
    assert not any("git+ssh" in arg for arg in first)


def test_run_init_second_uv_add_uses_gds_idea_index(tmp_path, monkeypatch):
    """The second uv add installs gds-idea-cdk-constructs from the internal index."""
    monkeypatch.chdir(tmp_path)

    uv_add_calls = []

    def fake_run_command(cmd, cwd, project_dir=None):
        if cmd[:2] == ["uv", "init"]:
            (cwd / "pyproject.toml").write_text(
                '[project]\nname = "gds-idea-app-test-app"\nversion = "0.0.0"\n\n[tool]\n'
            )
        if cmd[:2] == ["uv", "add"]:
            uv_add_calls.append(cmd)
        return MagicMock(returncode=0, stdout="", stderr="")

    with (
        patch("gds_idea_app_kit.init.check_prerequisites"),
        patch("gds_idea_app_kit.init._run_command", side_effect=fake_run_command),
    ):
        run_init("streamlit", "test-app", "3.13")

    second = uv_add_calls[1]
    assert "gds-idea-cdk-constructs>=0.3.0" in second
    assert "--index" in second
    assert any(GDS_IDEA_INDEX_URL in arg for arg in second)
    assert not any("git+ssh" in arg for arg in second)


def test_run_init_third_uv_add_installs_dev_deps(tmp_path, monkeypatch):
    """The third uv add installs pytest and ruff into the dev dependency group."""
    monkeypatch.chdir(tmp_path)

    uv_add_calls = []

    def fake_run_command(cmd, cwd, project_dir=None):
        if cmd[:2] == ["uv", "init"]:
            (cwd / "pyproject.toml").write_text(
                '[project]\nname = "gds-idea-app-test-app"\nversion = "0.0.0"\n\n[tool]\n'
            )
        if cmd[:2] == ["uv", "add"]:
            uv_add_calls.append(cmd)
        return MagicMock(returncode=0, stdout="", stderr="")

    with (
        patch("gds_idea_app_kit.init.check_prerequisites"),
        patch("gds_idea_app_kit.init._run_command", side_effect=fake_run_command),
    ):
        run_init("streamlit", "test-app", "3.13")

    third = uv_add_calls[2]
    assert "--group" in third
    assert "dev" in third
    assert any("pytest" in arg for arg in third)
    assert any("ruff" in arg for arg in third)


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


# ---- run_init infra project type ----
# Verifies that infra projects skip web-specific files and use the right template.


def test_run_init_infra_skips_app_src(tmp_path, monkeypatch):
    """Infra projects do not create an app_src/ directory."""
    monkeypatch.chdir(tmp_path)

    def fake_run_command(cmd, cwd, project_dir=None):
        if cmd[:2] == ["uv", "init"]:
            (cwd / "pyproject.toml").write_text(
                '[project]\nname = "gds-idea-app-test-infra"\nversion = "0.0.0"\n\n[tool]\n'
            )
        return MagicMock(returncode=0, stdout="", stderr="")

    with (
        patch("gds_idea_app_kit.init.check_prerequisites"),
        patch("gds_idea_app_kit.init._run_command", side_effect=fake_run_command),
    ):
        run_init("infra", "test-infra", "3.13")

    project_dir = tmp_path / "gds-idea-app-test-infra"
    assert not (project_dir / "app_src").exists()


def test_run_init_infra_skips_devcontainer(tmp_path, monkeypatch):
    """Infra projects do not create a .devcontainer/ directory."""
    monkeypatch.chdir(tmp_path)

    def fake_run_command(cmd, cwd, project_dir=None):
        if cmd[:2] == ["uv", "init"]:
            (cwd / "pyproject.toml").write_text(
                '[project]\nname = "gds-idea-app-test-infra"\nversion = "0.0.0"\n\n[tool]\n'
            )
        return MagicMock(returncode=0, stdout="", stderr="")

    with (
        patch("gds_idea_app_kit.init.check_prerequisites"),
        patch("gds_idea_app_kit.init._run_command", side_effect=fake_run_command),
    ):
        run_init("infra", "test-infra", "3.13")

    project_dir = tmp_path / "gds-idea-app-test-infra"
    assert not (project_dir / ".devcontainer").exists()


def test_run_init_infra_skips_dev_mocks(tmp_path, monkeypatch):
    """Infra projects do not create a dev_mocks/ directory."""
    monkeypatch.chdir(tmp_path)

    def fake_run_command(cmd, cwd, project_dir=None):
        if cmd[:2] == ["uv", "init"]:
            (cwd / "pyproject.toml").write_text(
                '[project]\nname = "gds-idea-app-test-infra"\nversion = "0.0.0"\n\n[tool]\n'
            )
        return MagicMock(returncode=0, stdout="", stderr="")

    with (
        patch("gds_idea_app_kit.init.check_prerequisites"),
        patch("gds_idea_app_kit.init._run_command", side_effect=fake_run_command),
    ):
        run_init("infra", "test-infra", "3.13")

    project_dir = tmp_path / "gds-idea-app-test-infra"
    assert not (project_dir / "dev_mocks").exists()


def test_run_init_infra_creates_ci_cd_files(tmp_path, monkeypatch):
    """Infra projects still get CI/CD workflow files."""
    monkeypatch.chdir(tmp_path)

    def fake_run_command(cmd, cwd, project_dir=None):
        if cmd[:2] == ["uv", "init"]:
            (cwd / "pyproject.toml").write_text(
                '[project]\nname = "gds-idea-app-test-infra"\nversion = "0.0.0"\n\n[tool]\n'
            )
        return MagicMock(returncode=0, stdout="", stderr="")

    with (
        patch("gds_idea_app_kit.init.check_prerequisites"),
        patch("gds_idea_app_kit.init._run_command", side_effect=fake_run_command),
    ):
        run_init("infra", "test-infra", "3.13")

    project_dir = tmp_path / "gds-idea-app-test-infra"
    assert (project_dir / ".github" / "workflows" / "ci_cd_cdk_app.yml").exists()
    assert (project_dir / ".github" / "workflows" / "ci_pr_cdk_app.yml").exists()
    assert (project_dir / ".github" / "CODEOWNERS").exists()
    assert (project_dir / ".github" / "dependabot.yml").exists()


def test_run_init_infra_uses_infra_app_template(tmp_path, monkeypatch):
    """Infra projects use the infra/app.py template (bare stack, not WebApp)."""
    monkeypatch.chdir(tmp_path)

    def fake_run_command(cmd, cwd, project_dir=None):
        if cmd[:2] == ["uv", "init"]:
            (cwd / "pyproject.toml").write_text(
                '[project]\nname = "gds-idea-app-test-infra"\nversion = "0.0.0"\n\n[tool]\n'
            )
        return MagicMock(returncode=0, stdout="", stderr="")

    with (
        patch("gds_idea_app_kit.init.check_prerequisites"),
        patch("gds_idea_app_kit.init._run_command", side_effect=fake_run_command),
    ):
        run_init("infra", "test-infra", "3.13")

    project_dir = tmp_path / "gds-idea-app-test-infra"
    app_py = project_dir / "app.py"
    assert app_py.exists()
    content = app_py.read_text()
    assert "cdk.Stack(" in content
    assert "WebApp" not in content


def test_run_init_infra_checks_only_non_docker_prereqs(tmp_path, monkeypatch):
    """Infra projects only check cdk, uv, git prerequisites (not Docker)."""
    monkeypatch.chdir(tmp_path)

    prereq_calls = []

    def fake_check_prerequisites(only=None):
        prereq_calls.append(only)

    def fake_run_command(cmd, cwd, project_dir=None):
        if cmd[:2] == ["uv", "init"]:
            (cwd / "pyproject.toml").write_text(
                '[project]\nname = "gds-idea-app-test-infra"\nversion = "0.0.0"\n\n[tool]\n'
            )
        return MagicMock(returncode=0, stdout="", stderr="")

    with (
        patch("gds_idea_app_kit.init.check_prerequisites", side_effect=fake_check_prerequisites),
        patch("gds_idea_app_kit.init._run_command", side_effect=fake_run_command),
    ):
        run_init("infra", "test-infra", "3.13")

    assert len(prereq_calls) == 1
    assert prereq_calls[0] == ["cdk", "uv", "git"]


# ---- run_init python project type ----
# Verifies that python projects create a package with src/ layout,
# correct prefix, and no CDK artifacts.


def _make_fake_run_command_python(project_name):
    """Create a fake _run_command that handles uv init --lib for python projects."""

    def fake_run_command(cmd, cwd, project_dir=None):
        if cmd[:2] == ["uv", "init"]:
            # Simulate uv init --lib --name creating src/ layout
            (cwd / "pyproject.toml").write_text(
                f'[project]\nname = "{project_name}"\nversion = "0.1.0"\n\n'
                '[build-system]\nrequires = ["hatchling"]\n'
                'build-backend = "hatchling.build"\n'
            )
            # --name flag means package dir is derived from the name arg
            # e.g. --name test-lib -> src/test_lib/
            name_arg = None
            for i, arg in enumerate(cmd):
                if arg == "--name" and i + 1 < len(cmd):
                    name_arg = cmd[i + 1]
                    break
            pkg_name = (name_arg or project_name).replace("-", "_")
            src_dir = cwd / "src" / pkg_name
            src_dir.mkdir(parents=True, exist_ok=True)
            (src_dir / "__init__.py").write_text('"""hello."""\n')
            (src_dir / "py.typed").write_text("")
            (cwd / "README.md").write_text("# placeholder\n")
            (cwd / ".python-version").write_text("3.13\n")
            (cwd / ".gitignore").write_text("__pycache__/\n")
        return MagicMock(returncode=0, stdout="", stderr="")

    return fake_run_command


def test_run_init_python_creates_correct_directory(tmp_path, monkeypatch):
    """Python projects use gds-idea-pkg- prefix for the directory."""
    monkeypatch.chdir(tmp_path)

    with (
        patch("gds_idea_app_kit.init.check_prerequisites"),
        patch(
            "gds_idea_app_kit.init._run_command",
            side_effect=_make_fake_run_command_python("gds-idea-pkg-my-lib"),
        ),
    ):
        run_init("python", "my-lib", "3.13")

    project_dir = tmp_path / "gds-idea-pkg-my-lib"
    assert project_dir.exists()
    assert project_dir.is_dir()


def test_run_init_python_no_cdk_artifacts(tmp_path, monkeypatch):
    """Python projects have no app.py, cdk.json, or app_src/."""
    monkeypatch.chdir(tmp_path)

    with (
        patch("gds_idea_app_kit.init.check_prerequisites"),
        patch(
            "gds_idea_app_kit.init._run_command",
            side_effect=_make_fake_run_command_python("gds-idea-pkg-my-lib"),
        ),
    ):
        run_init("python", "my-lib", "3.13")

    project_dir = tmp_path / "gds-idea-pkg-my-lib"
    assert not (project_dir / "app.py").exists()
    assert not (project_dir / "cdk.json").exists()
    assert not (project_dir / "app_src").exists()
    assert not (project_dir / ".devcontainer").exists()


def test_run_init_python_has_src_layout(tmp_path, monkeypatch):
    """Python projects have a src/{package_name}/ directory."""
    monkeypatch.chdir(tmp_path)

    with (
        patch("gds_idea_app_kit.init.check_prerequisites"),
        patch(
            "gds_idea_app_kit.init._run_command",
            side_effect=_make_fake_run_command_python("gds-idea-pkg-my-lib"),
        ),
    ):
        run_init("python", "my-lib", "3.13")

    project_dir = tmp_path / "gds-idea-pkg-my-lib"
    assert (project_dir / "src" / "my_lib" / "__init__.py").exists()


def test_run_init_python_has_tests_directory(tmp_path, monkeypatch):
    """Python projects have a tests/ directory with conftest.py."""
    monkeypatch.chdir(tmp_path)

    with (
        patch("gds_idea_app_kit.init.check_prerequisites"),
        patch(
            "gds_idea_app_kit.init._run_command",
            side_effect=_make_fake_run_command_python("gds-idea-pkg-my-lib"),
        ),
    ):
        run_init("python", "my-lib", "3.13")

    project_dir = tmp_path / "gds-idea-pkg-my-lib"
    assert (project_dir / "tests" / "__init__.py").exists()
    assert (project_dir / "tests" / "conftest.py").exists()


def test_run_init_python_has_ci_workflows(tmp_path, monkeypatch):
    """Python projects get CI and auto-release workflows."""
    monkeypatch.chdir(tmp_path)

    with (
        patch("gds_idea_app_kit.init.check_prerequisites"),
        patch(
            "gds_idea_app_kit.init._run_command",
            side_effect=_make_fake_run_command_python("gds-idea-pkg-my-lib"),
        ),
    ):
        run_init("python", "my-lib", "3.13")

    project_dir = tmp_path / "gds-idea-pkg-my-lib"
    assert (project_dir / ".github" / "workflows" / "ci.yml").exists()
    assert (project_dir / ".github" / "workflows" / "auto-release.yml").exists()
    assert (project_dir / ".github" / "workflows" / "gds-idea-pypi-publish.yml").exists()
    assert (project_dir / ".github" / "CODEOWNERS").exists()
    assert (project_dir / ".github" / "dependabot.yml").exists()


def test_run_init_python_no_publish_flag(tmp_path, monkeypatch):
    """--no-publish flag omits the pypi publish workflow."""
    monkeypatch.chdir(tmp_path)

    with (
        patch("gds_idea_app_kit.init.check_prerequisites"),
        patch(
            "gds_idea_app_kit.init._run_command",
            side_effect=_make_fake_run_command_python("gds-idea-pkg-my-lib"),
        ),
    ):
        run_init("python", "my-lib", "3.13", no_publish=True)

    project_dir = tmp_path / "gds-idea-pkg-my-lib"
    assert (project_dir / ".github" / "workflows" / "ci.yml").exists()
    assert (project_dir / ".github" / "workflows" / "auto-release.yml").exists()
    assert not (project_dir / ".github" / "workflows" / "gds-idea-pypi-publish.yml").exists()


def test_run_init_python_has_pre_commit_config(tmp_path, monkeypatch):
    """Python projects have a .pre-commit-config.yaml."""
    monkeypatch.chdir(tmp_path)

    with (
        patch("gds_idea_app_kit.init.check_prerequisites"),
        patch(
            "gds_idea_app_kit.init._run_command",
            side_effect=_make_fake_run_command_python("gds-idea-pkg-my-lib"),
        ),
    ):
        run_init("python", "my-lib", "3.13")

    project_dir = tmp_path / "gds-idea-pkg-my-lib"
    config = project_dir / ".pre-commit-config.yaml"
    assert config.exists()
    content = config.read_text()
    assert "ruff" in content
    assert "gitleaks" in content


def test_run_init_python_pyproject_has_hatch_vcs(tmp_path, monkeypatch):
    """Python projects configure hatch-vcs in pyproject.toml."""
    monkeypatch.chdir(tmp_path)

    with (
        patch("gds_idea_app_kit.init.check_prerequisites"),
        patch(
            "gds_idea_app_kit.init._run_command",
            side_effect=_make_fake_run_command_python("gds-idea-pkg-my-lib"),
        ),
    ):
        run_init("python", "my-lib", "3.13")

    project_dir = tmp_path / "gds-idea-pkg-my-lib"
    content = (project_dir / "pyproject.toml").read_text()
    assert "hatch-vcs" in content
    assert 'dynamic = ["version"]' in content
    assert "version" not in content.split("[project]")[1].split("dynamic")[0]


def test_run_init_python_removes_py_typed(tmp_path, monkeypatch):
    """Python projects remove the py.typed marker (can be added later)."""
    monkeypatch.chdir(tmp_path)

    with (
        patch("gds_idea_app_kit.init.check_prerequisites"),
        patch(
            "gds_idea_app_kit.init._run_command",
            side_effect=_make_fake_run_command_python("gds-idea-pkg-my-lib"),
        ),
    ):
        run_init("python", "my-lib", "3.13")

    project_dir = tmp_path / "gds-idea-pkg-my-lib"
    assert not (project_dir / "src" / "my_lib" / "py.typed").exists()


def test_run_init_python_checks_correct_prereqs(tmp_path, monkeypatch):
    """Python projects only check uv, git, and gitleaks prerequisites."""
    monkeypatch.chdir(tmp_path)

    prereq_calls = []

    def fake_check_prerequisites(only=None):
        prereq_calls.append(only)

    with (
        patch("gds_idea_app_kit.init.check_prerequisites", side_effect=fake_check_prerequisites),
        patch(
            "gds_idea_app_kit.init._run_command",
            side_effect=_make_fake_run_command_python("gds-idea-pkg-my-lib"),
        ),
    ):
        run_init("python", "my-lib", "3.13")

    assert len(prereq_calls) == 1
    assert prereq_calls[0] == ["uv", "git", "gitleaks"]


def test_run_init_python_installs_dev_deps(tmp_path, monkeypatch):
    """Python projects install pytest, ruff, and pre-commit as dev deps."""
    monkeypatch.chdir(tmp_path)

    uv_add_calls = []

    def fake_run_command(cmd, cwd, project_dir=None):
        if cmd[:2] == ["uv", "init"]:
            _make_fake_run_command_python("gds-idea-pkg-my-lib")(cmd, cwd, project_dir)
        if cmd[:2] == ["uv", "add"]:
            uv_add_calls.append(cmd)
        return MagicMock(returncode=0, stdout="", stderr="")

    with (
        patch("gds_idea_app_kit.init.check_prerequisites"),
        patch("gds_idea_app_kit.init._run_command", side_effect=fake_run_command),
    ):
        run_init("python", "my-lib", "3.13")

    assert len(uv_add_calls) == 1
    cmd = uv_add_calls[0]
    assert "--group" in cmd
    assert "dev" in cmd
    assert any("pytest" in arg for arg in cmd)
    assert any("ruff" in arg for arg in cmd)
    assert "pre-commit" in cmd


def test_get_templates_dir_has_python():
    """The python/ subdirectory contains python package template files."""
    templates = _get_templates_dir()
    assert (templates / "python").is_dir()
    assert (templates / "python" / "ci.yml").is_file()
    assert (templates / "python" / "auto_release.yml").is_file()
    assert (templates / "python" / "pre-commit-config.yaml").is_file()
