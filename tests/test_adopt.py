"""Tests for the adopt command."""

import os
from unittest.mock import MagicMock, patch

import pytest

from gds_idea_app_kit.adopt import run_adopt
from gds_idea_app_kit.manifest import MANIFEST_KEY, read_manifest

# ---- fixtures ----


@pytest.fixture()
def cdk_project(tmp_path):
    """Create a minimal existing CDK project directory."""
    pyproject = tmp_path / "pyproject.toml"
    pyproject.write_text('[project]\nname = "gds-idea-app-my-infra"\nversion = "0.1.0"\n\n[tool]\n')
    cdk_json = tmp_path / "cdk.json"
    cdk_json.write_text('{"app": "python3 app.py"}')
    gitignore = tmp_path / ".gitignore"
    gitignore.write_text("*.pyc\n__pycache__/\n")
    return tmp_path


# ---- validation ----


def test_adopt_fails_without_pyproject(tmp_path, capsys):
    """adopt exits with an error when no pyproject.toml exists."""
    os.chdir(tmp_path)
    (tmp_path / "cdk.json").write_text("{}")

    with pytest.raises(SystemExit):
        run_adopt()

    captured = capsys.readouterr()
    assert "No pyproject.toml" in captured.err


def test_adopt_without_cdk_json_takes_python_path(tmp_path, capsys):
    """adopt without cdk.json triggers the Python package path."""
    os.chdir(tmp_path)
    (tmp_path / "pyproject.toml").write_text(
        '[project]\nname = "gds-idea-pkg-test"\nversion = "0.1.0"\n\n'
        "[build-system]\n"
        'requires = ["hatchling"]\n'
        'build-backend = "hatchling.build"\n'
    )

    with (
        patch("gds_idea_app_kit.adopt.check_tool_is_current"),
        patch("gds_idea_app_kit.adopt.check_prerequisites"),
        patch("gds_idea_app_kit.adopt._run_command", return_value=MagicMock()),
    ):
        run_adopt()

    captured = capsys.readouterr()
    assert "Adopting Python package: test" in captured.out


def test_adopt_fails_with_existing_manifest(cdk_project, capsys):
    """adopt exits with an error when a manifest already exists."""
    os.chdir(cdk_project)
    pyproject = cdk_project / "pyproject.toml"
    pyproject.write_text(
        f'[project]\nname = "test"\nversion = "0.1.0"\n\n'
        f"[tool.{MANIFEST_KEY}]\n"
        f'framework = "infra"\n'
        f'app_name = "test"\n'
    )

    with pytest.raises(SystemExit):
        run_adopt()

    captured = capsys.readouterr()
    assert "already has a" in captured.err


def test_adopt_fails_without_project_name(tmp_path, capsys):
    """adopt exits with an error when [project].name is missing."""
    os.chdir(tmp_path)
    (tmp_path / "pyproject.toml").write_text('[project]\nversion = "0.1.0"\n')
    (tmp_path / "cdk.json").write_text("{}")

    with (
        patch("gds_idea_app_kit.adopt.check_tool_is_current"),
        patch("gds_idea_app_kit.adopt.check_prerequisites"),
        pytest.raises(SystemExit),
    ):
        run_adopt()

    captured = capsys.readouterr()
    assert "Could not read project name" in captured.err


# ---- successful adopt ----


def test_adopt_creates_ci_cd_files(cdk_project):
    """adopt creates CI/CD workflow files."""
    os.chdir(cdk_project)

    with (
        patch("gds_idea_app_kit.adopt.check_tool_is_current"),
        patch("gds_idea_app_kit.adopt.check_prerequisites"),
        patch("gds_idea_app_kit.adopt._run_command", return_value=MagicMock()),
    ):
        run_adopt()

    assert (cdk_project / ".github" / "workflows" / "ci_cd_cdk_app.yml").exists()
    assert (cdk_project / ".github" / "workflows" / "ci_pr_cdk_app.yml").exists()
    assert (cdk_project / ".github" / "CODEOWNERS").exists()
    assert (cdk_project / ".github" / "dependabot.yml").exists()


def test_adopt_creates_licence(cdk_project):
    """adopt creates a LICENCE file."""
    os.chdir(cdk_project)

    with (
        patch("gds_idea_app_kit.adopt.check_tool_is_current"),
        patch("gds_idea_app_kit.adopt.check_prerequisites"),
        patch("gds_idea_app_kit.adopt._run_command", return_value=MagicMock()),
    ):
        run_adopt()

    assert (cdk_project / "LICENCE").exists()


def test_adopt_skips_existing_readme(cdk_project, capsys):
    """adopt does not overwrite an existing README.md."""
    os.chdir(cdk_project)
    readme = cdk_project / "README.md"
    readme.write_text("# My existing README\n")

    with (
        patch("gds_idea_app_kit.adopt.check_tool_is_current"),
        patch("gds_idea_app_kit.adopt.check_prerequisites"),
        patch("gds_idea_app_kit.adopt._run_command", return_value=MagicMock()),
    ):
        run_adopt()

    assert readme.read_text() == "# My existing README\n"
    captured = capsys.readouterr()
    assert "Skipping README.md" in captured.out


def test_adopt_creates_readme_when_missing(cdk_project):
    """adopt creates a README.md when one doesn't exist."""
    os.chdir(cdk_project)

    with (
        patch("gds_idea_app_kit.adopt.check_tool_is_current"),
        patch("gds_idea_app_kit.adopt.check_prerequisites"),
        patch("gds_idea_app_kit.adopt._run_command", return_value=MagicMock()),
    ):
        run_adopt()

    assert (cdk_project / "README.md").exists()


def test_adopt_appends_to_gitignore(cdk_project):
    """adopt appends extra entries to an existing .gitignore."""
    os.chdir(cdk_project)
    original = (cdk_project / ".gitignore").read_text()

    with (
        patch("gds_idea_app_kit.adopt.check_tool_is_current"),
        patch("gds_idea_app_kit.adopt.check_prerequisites"),
        patch("gds_idea_app_kit.adopt._run_command", return_value=MagicMock()),
    ):
        run_adopt()

    content = (cdk_project / ".gitignore").read_text()
    assert content.startswith(original)
    assert len(content) > len(original)


def test_adopt_installs_constructs_from_index(cdk_project):
    """adopt installs gds-idea-cdk-constructs from the internal PyPI index."""
    os.chdir(cdk_project)

    uv_add_calls = []

    def fake_run_command(cmd, cwd, project_dir=None):
        if cmd[:2] == ["uv", "add"]:
            uv_add_calls.append(cmd)
        return MagicMock(returncode=0, stdout="", stderr="")

    with (
        patch("gds_idea_app_kit.adopt.check_tool_is_current"),
        patch("gds_idea_app_kit.adopt.check_prerequisites"),
        patch("gds_idea_app_kit.adopt._run_command", side_effect=fake_run_command),
    ):
        run_adopt()

    assert len(uv_add_calls) == 1
    cmd = uv_add_calls[0]
    assert "gds-idea-cdk-constructs>=0.3.0" in cmd
    assert "--index" in cmd
    assert any("gds-idea-pypi" in arg for arg in cmd)


def test_adopt_writes_manifest(cdk_project):
    """adopt writes a manifest to pyproject.toml."""
    os.chdir(cdk_project)

    with (
        patch("gds_idea_app_kit.adopt.check_tool_is_current"),
        patch("gds_idea_app_kit.adopt.check_prerequisites"),
        patch("gds_idea_app_kit.adopt._run_command", return_value=MagicMock()),
    ):
        run_adopt()

    manifest = read_manifest(cdk_project)
    assert manifest["framework"] == "infra"
    assert manifest["app_name"] == "my-infra"


def test_adopt_writes_webapp_config(cdk_project):
    """adopt writes [tool.webapp] section to pyproject.toml."""
    os.chdir(cdk_project)

    with (
        patch("gds_idea_app_kit.adopt.check_tool_is_current"),
        patch("gds_idea_app_kit.adopt.check_prerequisites"),
        patch("gds_idea_app_kit.adopt._run_command", return_value=MagicMock()),
    ):
        run_adopt()

    content = (cdk_project / "pyproject.toml").read_text()
    assert "[tool.webapp]" in content
    assert 'framework = "infra"' in content


def test_adopt_strips_repo_prefix_from_app_name(tmp_path):
    """adopt strips the gds-idea-app- prefix from the project name."""
    os.chdir(tmp_path)
    (tmp_path / "pyproject.toml").write_text(
        '[project]\nname = "gds-idea-app-my-project"\nversion = "0.1.0"\n\n[tool]\n'
    )
    (tmp_path / "cdk.json").write_text("{}")
    (tmp_path / ".gitignore").write_text("")

    with (
        patch("gds_idea_app_kit.adopt.check_tool_is_current"),
        patch("gds_idea_app_kit.adopt.check_prerequisites"),
        patch("gds_idea_app_kit.adopt._run_command", return_value=MagicMock()),
    ):
        run_adopt()

    manifest = read_manifest(tmp_path)
    assert manifest["app_name"] == "my-project"


def test_adopt_does_not_auto_commit(cdk_project):
    """adopt does not run git commit -- user should review changes first."""
    os.chdir(cdk_project)

    git_calls = []

    def fake_run_command(cmd, cwd, project_dir=None):
        if cmd[0] == "git":
            git_calls.append(cmd)
        return MagicMock(returncode=0, stdout="", stderr="")

    with (
        patch("gds_idea_app_kit.adopt.check_tool_is_current"),
        patch("gds_idea_app_kit.adopt.check_prerequisites"),
        patch("gds_idea_app_kit.adopt._run_command", side_effect=fake_run_command),
    ):
        run_adopt()

    # No git add or git commit calls
    assert not any("commit" in cmd for cmd in git_calls)


# ---- Python package adopt ----


@pytest.fixture()
def python_project(tmp_path):
    """Create a minimal existing Python package directory."""
    pyproject = tmp_path / "pyproject.toml"
    pyproject.write_text(
        "[project]\n"
        'name = "gds-idea-pkg-mylib"\n'
        'version = "0.2.0"\n'
        'requires-python = ">=3.11"\n\n'
        "[build-system]\n"
        'requires = ["hatchling"]\n'
        'build-backend = "hatchling.build"\n'
    )
    gitignore = tmp_path / ".gitignore"
    gitignore.write_text("*.pyc\n__pycache__/\n")
    return tmp_path


def test_adopt_python_creates_workflows(python_project):
    """adopt creates CI and release workflow files for Python packages."""
    os.chdir(python_project)

    with (
        patch("gds_idea_app_kit.adopt.check_tool_is_current"),
        patch("gds_idea_app_kit.adopt.check_prerequisites"),
        patch("gds_idea_app_kit.adopt._run_command", return_value=MagicMock()),
    ):
        run_adopt()

    assert (python_project / ".github" / "workflows" / "ci.yml").exists()
    assert (python_project / ".github" / "workflows" / "release.yml").exists()
    assert (python_project / ".github" / "CODEOWNERS").exists()
    assert (python_project / ".github" / "dependabot.yml").exists()
    assert (python_project / ".pre-commit-config.yaml").exists()
    assert (python_project / "LICENCE").exists()


def test_adopt_python_writes_manifest(python_project):
    """adopt writes a manifest with framework='python'."""
    os.chdir(python_project)

    with (
        patch("gds_idea_app_kit.adopt.check_tool_is_current"),
        patch("gds_idea_app_kit.adopt.check_prerequisites"),
        patch("gds_idea_app_kit.adopt._run_command", return_value=MagicMock()),
    ):
        run_adopt()

    manifest = read_manifest(python_project)
    assert manifest["framework"] == "python"
    assert manifest["app_name"] == "mylib"


def test_adopt_python_strips_pkg_prefix(python_project):
    """adopt strips the gds-idea-pkg- prefix to derive app_name."""
    os.chdir(python_project)

    with (
        patch("gds_idea_app_kit.adopt.check_tool_is_current"),
        patch("gds_idea_app_kit.adopt.check_prerequisites"),
        patch("gds_idea_app_kit.adopt._run_command", return_value=MagicMock()),
    ):
        run_adopt()

    manifest = read_manifest(python_project)
    assert manifest["app_name"] == "mylib"


def test_adopt_python_adds_hatch_vcs(python_project):
    """adopt adds hatch-vcs configuration to pyproject.toml."""
    os.chdir(python_project)

    with (
        patch("gds_idea_app_kit.adopt.check_tool_is_current"),
        patch("gds_idea_app_kit.adopt.check_prerequisites"),
        patch("gds_idea_app_kit.adopt._run_command", return_value=MagicMock()),
    ):
        run_adopt()

    import tomlkit

    with open(python_project / "pyproject.toml") as f:
        config = tomlkit.load(f)

    # hatch-vcs in build requires
    assert "hatch-vcs" in config["build-system"]["requires"]
    # static version removed, dynamic added
    assert "version" not in config["project"]
    assert "version" in config["project"].get("dynamic", [])
    # hatch version source
    assert config["tool"]["hatch"]["version"]["source"] == "vcs"


def test_adopt_python_skips_existing_ruff(python_project, capsys):
    """adopt skips [tool.ruff] if already present."""
    os.chdir(python_project)

    # Add existing ruff config
    pyproject = python_project / "pyproject.toml"
    content = pyproject.read_text()
    content += "\n[tool.ruff]\nline-length = 88\n"
    pyproject.write_text(content)

    with (
        patch("gds_idea_app_kit.adopt.check_tool_is_current"),
        patch("gds_idea_app_kit.adopt.check_prerequisites"),
        patch("gds_idea_app_kit.adopt._run_command", return_value=MagicMock()),
    ):
        run_adopt()

    captured = capsys.readouterr()
    assert "Skipping [tool.ruff]" in captured.out

    # Original config preserved
    import tomlkit

    with open(pyproject) as f:
        config = tomlkit.load(f)
    assert config["tool"]["ruff"]["line-length"] == 88


def test_adopt_python_skips_existing_hatch_vcs(python_project, capsys):
    """adopt skips hatch-vcs setup if already configured."""
    os.chdir(python_project)

    # Add hatch-vcs to build-system requires
    pyproject = python_project / "pyproject.toml"
    pyproject.write_text(
        "[project]\n"
        'name = "gds-idea-pkg-mylib"\n'
        'dynamic = ["version"]\n'
        'requires-python = ">=3.11"\n\n'
        "[build-system]\n"
        'requires = ["hatchling", "hatch-vcs"]\n'
        'build-backend = "hatchling.build"\n'
    )

    with (
        patch("gds_idea_app_kit.adopt.check_tool_is_current"),
        patch("gds_idea_app_kit.adopt.check_prerequisites"),
        patch("gds_idea_app_kit.adopt._run_command", return_value=MagicMock()),
    ):
        run_adopt()

    captured = capsys.readouterr()
    assert "Skipping hatch-vcs" in captured.out


def test_adopt_python_no_publish_flag(python_project):
    """adopt --no-publish uses the release_no_publish template."""
    os.chdir(python_project)

    with (
        patch("gds_idea_app_kit.adopt.check_tool_is_current"),
        patch("gds_idea_app_kit.adopt.check_prerequisites"),
        patch("gds_idea_app_kit.adopt._run_command", return_value=MagicMock()),
    ):
        run_adopt(no_publish=True)

    release_yml = python_project / ".github" / "workflows" / "release.yml"
    content = release_yml.read_text()
    # The no-publish variant should NOT contain gds_idea_pypi_publish
    assert "gds_idea_pypi_publish" not in content


def test_adopt_python_installs_dev_deps(python_project):
    """adopt installs pytest, ruff, and pre-commit as dev dependencies."""
    os.chdir(python_project)

    uv_add_calls = []

    def fake_run_command(cmd, cwd, project_dir=None):
        if cmd[:2] == ["uv", "add"]:
            uv_add_calls.append(cmd)
        return MagicMock(returncode=0, stdout="", stderr="")

    with (
        patch("gds_idea_app_kit.adopt.check_tool_is_current"),
        patch("gds_idea_app_kit.adopt.check_prerequisites"),
        patch("gds_idea_app_kit.adopt._run_command", side_effect=fake_run_command),
    ):
        run_adopt()

    assert len(uv_add_calls) == 1
    cmd = uv_add_calls[0]
    assert "--group" in cmd
    assert "dev" in cmd
    assert any("pytest" in arg for arg in cmd)
    assert any("ruff" in arg for arg in cmd)
    assert "pre-commit" in cmd


def test_adopt_python_skips_existing_readme(python_project, capsys):
    """adopt does not overwrite an existing README.md for Python packages."""
    os.chdir(python_project)
    readme = python_project / "README.md"
    readme.write_text("# My library\n")

    with (
        patch("gds_idea_app_kit.adopt.check_tool_is_current"),
        patch("gds_idea_app_kit.adopt.check_prerequisites"),
        patch("gds_idea_app_kit.adopt._run_command", return_value=MagicMock()),
    ):
        run_adopt()

    assert readme.read_text() == "# My library\n"
    captured = capsys.readouterr()
    assert "Skipping README.md" in captured.out
