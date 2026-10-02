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
| `.devcontainer/README.md` | Dev container guide |
| `.aws-dev/README.md` | Explains the AWS credentials directory |
| `dev_mocks/dev_mock_authoriser.json` | Mock auth data for local dev |
| `dev_mocks/dev_mock_user.json` | Mock user data for local dev |
| `app_src/Dockerfile` | Docker image (development and production targets) |
| `app_src/Dockerfile.dockerignore` | Keeps tests, credentials and local environments out of the image |
| `app_src/.vscode/tasks.json` | "Run app" task that starts the app in the dev container with auto-reload |
| `LICENCE` | MIT licence |

### User-owned (never touched by idea-app)

| File | Purpose |
|---|---|
| `app.py` | CDK entry point |
| `cdk.json` | CDK configuration |
| `pyproject.toml` | Root project dependencies (except manifest section) |
| `app_src/{framework}_app.py` | Your application code |
| `app_src/pyproject.toml` | App dependencies (including the `zscaler` and `dev` groups) |
| `tests/` | Your test files |
| `README.md` | Your documentation |

## Static site projects (static)

### Managed by idea-app (updated by `idea-app update`)

| File | Purpose |
|---|---|
| `.github/workflows/ci_cd_cdk_app.yml` | CI/CD orchestrator |
| `.github/workflows/ci_pr_cdk_app.yml` | PR checks orchestrator |
| `.github/CODEOWNERS` | Code review requirements |
| `.github/dependabot.yml` | Dependency update configuration |
| `.devcontainer/devcontainer.json` | Dev container configuration |
| `.devcontainer/docker-compose.yml` | Dev container compose file |
| `site_src/Dockerfile` | Multi-stage build (development + Lambda build target) |
| `site_src/handler.py` | Build Lambda handler — runs the build command and uploads to S3 |
| `LICENCE` | MIT licence |

### User-owned (never touched by idea-app)

| File | Purpose |
|---|---|
| `app.py` | CDK entry point (`StaticSite` construct configuration) |
| `cdk.json` | CDK configuration |
| `pyproject.toml` | Root project dependencies (except manifest section) |
| `site_src/package.json` | Eleventy and plugin dependencies |
| `site_src/eleventy.config.js` | Eleventy configuration |
| `site_src/src/` | Your site content |
| `dev_mocks/user.json` | Mock `/.auth/user` response for local development |
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
| `.github/workflows/release.yml` | Release + publish orchestrator |
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
