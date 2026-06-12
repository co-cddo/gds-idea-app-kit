# File ownership

`idea-app` manages certain files and leaves others entirely to you. This page documents which is which.

## Web app projects (streamlit, dash, fastapi)

### Managed by idea-app (updated by `idea-app update`)

| File | Purpose |
|---|---|
| `.github/workflows/ci_cd_cdk_app.yml` | CI/CD orchestrator |
| `.github/workflows/ci_pr_cdk_app.yml` | PR checks orchestrator |
| `.github/CODEOWNERS` | Code review requirements |
| `.github/dependabot.yml` | Dependency update configuration |
| `.devcontainer/devcontainer.json` | Dev container configuration |
| `.devcontainer/docker-compose.yml` | Dev container compose file |
| `dev_mocks/dev_mock_authoriser.json` | Mock auth data for local dev |
| `dev_mocks/dev_mock_user.json` | Mock user data for local dev |
| `app_src/Dockerfile` | Production Docker image |
| `LICENCE` | MIT licence |

### User-owned (never touched by idea-app)

| File | Purpose |
|---|---|
| `app.py` | CDK entry point |
| `cdk.json` | CDK configuration |
| `pyproject.toml` | Root project dependencies (except manifest section) |
| `app_src/{framework}_app.py` | Your application code |
| `app_src/pyproject.toml` | App dependencies |
| `tests/` | Your test files |
| `README.md` | Your documentation |

## Infrastructure projects (infra)

### Managed by idea-app

| File | Purpose |
|---|---|
| `.github/workflows/ci_cd_cdk_app.yml` | CI/CD orchestrator |
| `.github/workflows/ci_pr_cdk_app.yml` | PR checks orchestrator |
| `.github/CODEOWNERS` | Code review requirements |
| `.github/dependabot.yml` | Dependency update configuration |
| `LICENCE` | MIT licence |

### User-owned

| File | Purpose |
|---|---|
| `app.py` | CDK entry point |
| `cdk.json` | CDK configuration |
| `pyproject.toml` | Project dependencies |
| `tests/` | Your test files |

## Python packages (python)

### Managed by idea-app

| File | Purpose |
|---|---|
| `.github/workflows/ci.yml` | CI orchestrator (lint, test, build) |
| `.github/workflows/auto-release.yml` | Auto-release orchestrator |
| `.github/workflows/gds-idea-pypi-publish.yml` | PyPI publish orchestrator |
| `.github/CODEOWNERS` | Code review requirements |
| `.github/dependabot.yml` | Dependency update configuration |
| `.pre-commit-config.yaml` | Pre-commit hook configuration |
| `LICENCE` | MIT licence |

### User-owned

| File | Purpose |
|---|---|
| `pyproject.toml` | Package metadata and dependencies |
| `src/{package_name}/` | Your package code |
| `tests/` | Your test files |
| `README.md` | Your documentation |

## The manifest

The manifest is stored in `pyproject.toml` under `[tool.gds-idea-app-kit]`. It records:

- Which framework/type was used
- Which version of `idea-app` generated the project
- SHA256 hashes of all managed files at the time they were last written

This is how `idea-app update` knows whether you've locally modified a managed file.
