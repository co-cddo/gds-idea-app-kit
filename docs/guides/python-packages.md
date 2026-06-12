# Python packages

This guide covers the Python package scaffold in detail.

## Overview

`idea-app init python` creates a distributable Python package with:

- **src layout** (`src/{package_name}/`)
- **hatch-vcs** for automatic versioning from git tags
- **Pre-commit hooks** for code quality enforcement
- **CI/CD** via reusable workflows from the shared catalogue
- **Auto-release** with label-based semver bumps
- **Publishing** to the internal gds-idea-pypi index

## Creating a package

```bash
idea-app init python my-library
```

This creates `gds-idea-pkg-my-library/` with package name `my_library`.

### Naming

- **Repo name:** `gds-idea-pkg-{name}` (prefix added automatically)
- **Package name:** `{name}` with hyphens replaced by underscores
- Example: `idea-app init python data-utils` creates repo `gds-idea-pkg-data-utils`, package `data_utils`

### Opting out of PyPI publishing

If your package doesn't need to be published to the internal index:

```bash
idea-app init python my-tool --no-publish
```

This omits the `gds-idea-pypi-publish.yml` workflow.

## Versioning

Versions are **never set manually**. The project uses [hatch-vcs](https://github.com/ofek/hatch-vcs) which derives the version from git tags.

The scaffold creates an initial `v0.0.0` tag. After that, the auto-release workflow handles version bumps automatically.

### How version bumps work

When a PR is merged to `main`:

1. The `auto-release.yml` workflow runs
2. It reads labels from the merged PR
3. Based on the label, it computes the next version:

| PR label | Bump | Example |
|---|---|---|
| `bump:major` | Major | `1.2.3` → `2.0.0` |
| `bump:minor` | Minor | `1.2.3` → `1.3.0` |
| _(none)_ | Patch | `1.2.3` → `1.2.4` |

4. Creates a git tag and GitHub release
5. The `gds-idea-pypi-publish.yml` workflow fires on the release, builds the wheel, and publishes to the index

### Getting the version in code

```python
from importlib.metadata import version
__version__ = version("gds-idea-pkg-my-library")
```

Or use the auto-generated `_version.py`:

```python
from my_library._version import __version__
```

## Pre-commit hooks

The scaffold installs pre-commit hooks automatically. They run on every `git commit`:

| Hook | What it does |
|---|---|
| `check-yaml` | Validates YAML syntax |
| `check-toml` | Validates TOML syntax |
| `check-merge-conflict` | Catches leftover conflict markers |
| `end-of-file-fixer` | Ensures files end with a newline |
| `trailing-whitespace` | Strips trailing whitespace |
| `no-commit-to-branch` | Prevents direct commits to `main` |
| `ruff --fix` | Auto-fixes lint issues |
| `ruff format` | Auto-formats code |
| `gitleaks` | Scans for leaked secrets |

### If hooks modify files

If ruff or the fixers modify files, the commit is aborted. Review the changes, `git add` them, and commit again:

```bash
git commit -m "my change"
# hooks fix trailing whitespace...
# commit aborted

git add -A
git commit -m "my change"
# hooks pass, commit succeeds
```

### Running hooks manually

```bash
uv run pre-commit run --all-files
```

### Branch protection

The `no-commit-to-branch` hook prevents direct commits to `main`. Always work on a feature branch:

```bash
git checkout -b feat/my-feature
```

## CI/CD workflows

The scaffolded project has three workflows:

### `ci.yml` (on pull requests to main)

Calls reusable workflows from the shared catalogue:

- **Lint** — ruff check + format verification
- **Test** — pytest across Python 3.11, 3.12, 3.13, 3.14
- **Build** — `uv build` to verify the package builds

### `auto-release.yml` (on push to main)

Creates a git tag and GitHub release based on PR labels.

### `gds-idea-pypi-publish.yml` (on release published)

Builds the wheel, uploads to the GitHub release, and triggers a rebuild of the gds-idea-pypi index.

## Adding dependencies

```bash
# Runtime dependency:
uv add httpx

# Dev dependency:
uv add --group dev pytest-cov
```

## Project structure

```
gds-idea-pkg-{name}/
├── .github/
│   ├── CODEOWNERS
│   ├── dependabot.yml
│   └── workflows/
│       ├── ci.yml
│       ├── auto-release.yml
│       └── gds-idea-pypi-publish.yml
├── .gitignore
├── .pre-commit-config.yaml
├── LICENCE
├── README.md
├── pyproject.toml
├── src/
│   └── {package_name}/
│       └── __init__.py
├── tests/
│   ├── __init__.py
│   └── conftest.py
└── uv.lock
```
