"""Implementation of the adopt command.

Adds CI/CD workflows, common configuration files, and project tooling
to an existing project that was not originally scaffolded by idea-app.

Supports two project types:
- CDK/infra projects (detected by presence of cdk.json)
- Python packages (pyproject.toml without cdk.json)
"""

import sys
from datetime import datetime
from pathlib import Path

import click
import tomlkit

from gds_idea_app_kit import (
    PKG_REPO_PREFIX,
    REPO_PREFIX,
    __version__,
)
from gds_idea_app_kit.init import (
    _copy_template,
    _get_templates_dir,
    _run_command,
)
from gds_idea_app_kit.manifest import (
    build_manifest,
    read_manifest,
    write_manifest,
)
from gds_idea_app_kit.prerequisites import check_prerequisites
from gds_idea_app_kit.version import check_tool_is_current


def _read_project_name(project_dir: Path) -> str | None:
    """Read the project name from pyproject.toml [project].name.

    Args:
        project_dir: Root directory of the project.

    Returns:
        The project name, or None if not found.
    """
    pyproject_path = project_dir / "pyproject.toml"
    with open(pyproject_path) as f:
        config = tomlkit.load(f)
    return config.get("project", {}).get("name")


def _run_adopt_cdk(project_dir: Path) -> None:
    """Add CI/CD and config files to an existing CDK project.

    Args:
        project_dir: Root directory of the project.
    """
    pyproject_path = project_dir / "pyproject.toml"

    # -- Check prerequisites (no Docker needed for infra) --
    check_prerequisites(only=["cdk", "uv", "git"])

    # -- Determine app name --
    project_name = _read_project_name(project_dir)
    if not project_name:
        click.echo(
            "Error: Could not read project name from [project].name in pyproject.toml.",
            err=True,
        )
        sys.exit(1)

    # Strip the repo prefix if present to get the app name.
    prefix = f"{REPO_PREFIX}-"
    if project_name.startswith(prefix):
        app_name = project_name[len(prefix):]
    else:
        app_name = project_name

    click.echo(f"Adopting CDK project: {app_name}")
    click.echo(f"  Directory: {project_dir.name}/")
    click.echo()

    # -- Prepare template variables --
    template_vars = {
        "app_name": app_name,
        "year": str(datetime.now().year),
    }
    templates = _get_templates_dir()

    # -- Copy common files --
    click.echo("Copying common files...")

    # CI/CD workflows
    _copy_template(
        templates / "common" / "ci_cd_cdk_app.yml",
        project_dir / ".github" / "workflows" / "ci_cd_cdk_app.yml",
    )
    _copy_template(
        templates / "common" / "ci_pr_cdk_app.yml",
        project_dir / ".github" / "workflows" / "ci_pr_cdk_app.yml",
    )

    # CODEOWNERS
    _copy_template(
        templates / "common" / "CODEOWNERS.template",
        project_dir / ".github" / "CODEOWNERS",
    )

    # Dependabot
    _copy_template(
        templates / "common" / "dependabot.yml",
        project_dir / ".github" / "dependabot.yml",
    )

    # LICENCE
    _copy_template(
        templates / "common" / "LICENCE",
        project_dir / "LICENCE",
        variables=template_vars,
    )

    # README -- only if one doesn't already exist
    readme_path = project_dir / "README.md"
    if not readme_path.exists():
        _copy_template(
            templates / "common" / "README.md.template",
            readme_path,
            variables=template_vars,
        )
    else:
        click.echo("  Skipping README.md (already exists)")

    # Append to .gitignore if it exists
    gitignore = project_dir / ".gitignore"
    if gitignore.exists():
        extra = (templates / "common" / "gitignore-extra").read_text()
        with open(gitignore, "a") as f:
            f.write("\n")
            f.write(extra)
    else:
        _copy_template(templates / "common" / "gitignore-extra", gitignore)

    # -- Install gds-idea-cdk-constructs --
    click.echo("Installing gds-idea-cdk-constructs...")
    _run_command(
        [
            "uv",
            "add",
            "gds-idea-cdk-constructs>=0.3.0",
            "--index",
            "gds-idea=https://co-cddo.github.io/gds-idea-pypi/simple/",
        ],
        cwd=project_dir,
    )

    # -- Write [tool.webapp] config --
    click.echo("Writing project configuration...")
    pyproject_path = project_dir / "pyproject.toml"
    with open(pyproject_path) as f:
        config = tomlkit.load(f)

    if "tool" not in config:
        config["tool"] = {}

    webapp = tomlkit.table()
    webapp.add("app_name", app_name)
    webapp.add("framework", "infra")
    config["tool"]["webapp"] = webapp

    with open(pyproject_path, "w") as f:
        tomlkit.dump(config, f)

    # -- Build and write manifest --
    click.echo("Writing manifest...")
    manifest = build_manifest(
        framework="infra",
        app_name=app_name,
        tool_version=__version__,
        project_dir=project_dir,
    )
    write_manifest(project_dir, manifest)

    # -- Sync dependencies --
    click.echo("Syncing dependencies...")
    _run_command(["uv", "sync"], cwd=project_dir)

    # -- Done (don't auto-commit -- let the user review) --
    click.echo()
    click.echo("Done! Files have been added to your project.")
    click.echo()
    click.echo("Review the changes and commit when ready:")
    click.echo("  git add .")
    click.echo('  git commit -m "Adopt project into gds-idea-app-kit"')
    click.echo()
    click.echo("You can now use 'idea-app update' to keep managed files up to date.")


def _configure_pyproject_python(project_dir: Path, package_name: str) -> None:
    """Add hatch-vcs, ruff, and pytest config to pyproject.toml for a Python package.

    Sections that already exist are skipped with a warning message.

    Args:
        project_dir: Root directory of the project.
        package_name: The Python import name (underscored form of app_name).
    """
    pyproject_path = project_dir / "pyproject.toml"
    with open(pyproject_path) as f:
        config = tomlkit.load(f)

    if "tool" not in config:
        config["tool"] = {}

    # -- hatch-vcs setup --
    build_requires = config.get("build-system", {}).get("requires", [])
    has_hatch_vcs = any("hatch-vcs" in r for r in build_requires)

    if has_hatch_vcs:
        click.echo("  Skipping hatch-vcs (already configured)")
    else:
        click.echo("  Adding hatch-vcs for tag-based versioning...")

        # Add hatch-vcs to build-system requires
        if "build-system" not in config:
            config["build-system"] = {
                "requires": ["hatchling", "hatch-vcs"],
                "build-backend": "hatchling.build",
            }
        else:
            requires = list(config["build-system"].get("requires", []))
            if "hatch-vcs" not in requires:
                requires.append("hatch-vcs")
            config["build-system"]["requires"] = requires

        # Remove static version and add dynamic
        if "version" in config.get("project", {}):
            del config["project"]["version"]
        config["project"]["dynamic"] = ["version"]

        # Add [tool.hatch.version] source = "vcs"
        if "hatch" not in config["tool"]:
            config["tool"]["hatch"] = {}

        hatch_version = tomlkit.table()
        hatch_version.add("source", "vcs")
        config["tool"]["hatch"]["version"] = hatch_version

        # Add [tool.hatch.build.hooks.vcs] version-file
        if "build" not in config["tool"]["hatch"]:
            config["tool"]["hatch"]["build"] = {}

        hatch_build = config["tool"]["hatch"]["build"]
        if "hooks" not in hatch_build:
            hooks_vcs = tomlkit.table()
            hooks_vcs.add("version-file", f"src/{package_name}/_version.py")
            hooks_table = tomlkit.table()
            hooks_table.add("vcs", hooks_vcs)
            hatch_build["hooks"] = hooks_table

        click.echo("    WARNING: Switched to hatch-vcs tag-based versioning.")
        click.echo("    Ensure this repo has a git tag (e.g. v0.1.0) before publishing.")

    # -- ruff config --
    if "ruff" in config.get("tool", {}):
        click.echo("  Skipping [tool.ruff] (already configured)")
    else:
        click.echo("  Adding [tool.ruff] configuration...")
        ruff = tomlkit.table()
        ruff.add("line-length", 120)
        ruff.add("target-version", "py313")
        ruff.add("exclude", [f"src/{package_name}/_version.py"])
        ruff_lint = tomlkit.table()
        ruff_lint.add("select", ["E", "F", "I", "B", "UP", "N"])
        ruff.add("lint", ruff_lint)
        ruff_isort = tomlkit.table()
        ruff_isort.add("known-first-party", [package_name])
        ruff["lint"].add("isort", ruff_isort)
        config["tool"]["ruff"] = ruff

    # -- pytest config --
    if "pytest" in config.get("tool", {}):
        click.echo("  Skipping [tool.pytest.ini_options] (already configured)")
    else:
        click.echo("  Adding [tool.pytest.ini_options] configuration...")
        pytest_table = tomlkit.table()
        ini_options = tomlkit.table()
        ini_options.add("testpaths", ["tests"])
        ini_options.add("addopts", ["-ra", "--strict-markers", "--strict-config"])
        ini_options.add(
            "markers",
            ["integration: tests that require external services"],
        )
        pytest_table.add("ini_options", ini_options)
        config["tool"]["pytest"] = pytest_table

    with open(pyproject_path, "w") as f:
        tomlkit.dump(config, f)


def _run_adopt_python(project_dir: Path, no_publish: bool) -> None:
    """Add CI/CD, pre-commit, and tooling config to an existing Python package.

    Args:
        project_dir: Root directory of the project.
        no_publish: If True, use release workflow without publish step.
    """
    # -- Check prerequisites --
    check_prerequisites(only=["uv", "git", "gitleaks"])

    # -- Determine app name --
    project_name = _read_project_name(project_dir)
    if not project_name:
        click.echo(
            "Error: Could not read project name from [project].name in pyproject.toml.",
            err=True,
        )
        sys.exit(1)

    # Strip the pkg repo prefix if present to get the app name.
    prefix = f"{PKG_REPO_PREFIX}-"
    if project_name.startswith(prefix):
        app_name = project_name[len(prefix):]
    else:
        app_name = project_name

    # Derive package import name (underscore form)
    package_name = app_name.replace("-", "_")

    click.echo(f"Adopting Python package: {app_name}")
    click.echo(f"  Directory: {project_dir.name}/")
    click.echo(f"  Package: {package_name}")
    click.echo(f"  Publish: {'no' if no_publish else 'yes'}")
    click.echo()

    # -- Prepare template variables --
    template_vars = {
        "app_name": app_name,
        "year": str(datetime.now().year),
    }
    templates = _get_templates_dir()

    # -- Copy managed files --
    click.echo("Copying managed files...")

    # CI workflow
    _copy_template(
        templates / "python" / "ci.yml",
        project_dir / ".github" / "workflows" / "ci.yml",
    )

    # Release workflow (with or without publish)
    if no_publish:
        _copy_template(
            templates / "python" / "release_no_publish.yml",
            project_dir / ".github" / "workflows" / "release.yml",
        )
    else:
        _copy_template(
            templates / "python" / "release.yml",
            project_dir / ".github" / "workflows" / "release.yml",
        )

    # CODEOWNERS
    _copy_template(
        templates / "python" / "CODEOWNERS.template",
        project_dir / ".github" / "CODEOWNERS",
    )

    # Dependabot
    _copy_template(
        templates / "python" / "dependabot.yml",
        project_dir / ".github" / "dependabot.yml",
    )

    # Pre-commit config
    _copy_template(
        templates / "python" / "pre-commit-config.yaml",
        project_dir / ".pre-commit-config.yaml",
    )

    # LICENCE
    _copy_template(
        templates / "common" / "LICENCE",
        project_dir / "LICENCE",
        variables=template_vars,
    )

    # README -- only if one doesn't already exist
    readme_path = project_dir / "README.md"
    if not readme_path.exists():
        _copy_template(
            templates / "python" / "README.md.template",
            readme_path,
            variables=template_vars,
        )
    else:
        click.echo("  Skipping README.md (already exists)")

    # .gitignore -- append Python-specific entries if it exists, otherwise copy template
    gitignore = project_dir / ".gitignore"
    gitignore_template = templates / "python" / "gitignore"
    if gitignore.exists():
        # Append entries from template that aren't already present
        existing = gitignore.read_text()
        template_content = gitignore_template.read_text()
        new_entries = []
        for line in template_content.splitlines():
            stripped = line.strip()
            if stripped and not stripped.startswith("#") and stripped not in existing:
                new_entries.append(line)
        if new_entries:
            with open(gitignore, "a") as f:
                f.write("\n# Added by idea-app adopt\n")
                f.write("\n".join(new_entries))
                f.write("\n")
            click.echo(f"  Appended {len(new_entries)} entries to .gitignore")
        else:
            click.echo("  Skipping .gitignore (entries already present)")
    else:
        _copy_template(gitignore_template, gitignore)

    # -- Configure pyproject.toml (hatch-vcs, ruff, pytest) --
    click.echo("Configuring pyproject.toml...")
    _configure_pyproject_python(project_dir, package_name)

    # -- Install dev dependencies --
    click.echo("Installing dev dependencies...")
    _run_command(
        ["uv", "add", "--group", "dev", "pytest>=9.0.0", "ruff>=0.14.0", "pre-commit"],
        cwd=project_dir,
    )

    # -- Sync dependencies --
    click.echo("Syncing dependencies...")
    _run_command(["uv", "sync"], cwd=project_dir)

    # -- Install pre-commit hooks --
    click.echo("Installing pre-commit hooks...")
    _run_command(
        ["uv", "run", "pre-commit", "install"],
        cwd=project_dir,
    )

    # -- Build and write manifest --
    click.echo("Writing manifest...")
    manifest = build_manifest(
        framework="python",
        app_name=app_name,
        tool_version=__version__,
        project_dir=project_dir,
    )
    write_manifest(project_dir, manifest)

    # -- Done (don't auto-commit -- let the user review) --
    click.echo()
    click.echo("Done! Files have been added to your project.")
    click.echo()
    click.echo("Review the changes and commit when ready:")
    click.echo("  git add .")
    click.echo('  git commit -m "Adopt project into gds-idea-app-kit"')
    click.echo()
    click.echo("You can now use 'idea-app update' to keep managed files up to date.")


def run_adopt(no_publish: bool = False) -> None:
    """Add CI/CD and config files to an existing project.

    Auto-detects project type:
    - Has cdk.json -> CDK/infra project
    - No cdk.json -> Python package

    Must be run from inside the project directory. Requires an existing
    pyproject.toml. Will not overwrite an existing manifest (use ``update``
    for projects already managed by idea-app).

    Args:
        no_publish: If True, skip the gds-idea-pypi publish workflow (python only).
    """
    project_dir = Path.cwd()
    pyproject_path = project_dir / "pyproject.toml"
    cdk_json_path = project_dir / "cdk.json"

    # -- Validate project --
    if not pyproject_path.exists():
        click.echo("Error: No pyproject.toml found. Are you in a project root?", err=True)
        sys.exit(1)

    existing_manifest = read_manifest(project_dir)
    if existing_manifest:
        click.echo(
            "Error: This project already has a [tool.gds-idea-app-kit] manifest.",
            err=True,
        )
        click.echo("  Use 'idea-app update' to update managed files.", err=True)
        sys.exit(1)

    # -- Check tool is current --
    check_tool_is_current()

    # -- Detect project type and dispatch --
    if cdk_json_path.exists():
        _run_adopt_cdk(project_dir)
    else:
        _run_adopt_python(project_dir, no_publish=no_publish)
