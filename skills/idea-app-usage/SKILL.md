---
name: idea-app-usage
description: Use the idea-app CLI to scaffold, update and adopt GDS IDEA projects on AWS. Use when creating a new web app (Streamlit, Dash, FastAPI), static site, CDK infrastructure project or internal Python package, when updating a project after upgrading idea-app, when running a production-image smoke test, or when getting AWS credentials into a dev container.
license: MIT
---

# Skill: idea-app-usage

## What idea-app does

`idea-app` is a CLI tool that scaffolds and maintains GDS IDEA projects on AWS. It generates projects with the right layout, CI/CD workflows, dev container and (for deployed projects) AWS CDK infrastructure, then keeps the files it owns up to date as the templates improve.

## When to use it

- Starting a new project: `idea-app init` (do not scaffold by hand or copy another project).
- A project was created with `idea-app` and the tool has since been upgraded: `idea-app update`.
- An existing CDK or Python project was not created with `idea-app` but should have the standard CI/CD: `idea-app adopt`.
- A project still uses the old `gds-idea-app-templates` template: `idea-app migrate`.
- Checking the production Docker image works before deploying: `idea-app smoke-test`.
- Getting AWS credentials into a dev container: `idea-app provide-role`.

## Project types

| Type | Creates | Directory | Prerequisites |
|------|---------|-----------|---------------|
| `streamlit`, `dash`, `fastapi` | A containerised web app on ECS Fargate behind an ALB with Cognito auth, with CDK infrastructure, Dockerfile, dev container and CI/CD | `gds-idea-app-{name}/` | `uv`, `git`, `cdk`, `docker`, `docker compose` |
| `static` | An Eleventy static site with GOV.UK styling on Lambda and S3 behind an ALB with Cognito auth | `gds-idea-app-{name}/` | same as web apps |
| `infra` | A bare CDK project with CI/CD and no application container | `gds-idea-app-{name}/` | `uv`, `git`, `cdk` |
| `python` | A pure Python package with `src` layout, hatch-vcs versioning, pre-commit hooks and CI/CD | `gds-idea-pkg-{name}/` | `uv`, `git`, `gitleaks` |

## Commands

### idea-app init

Scaffold a new project:

```bash
idea-app init <type> <name> [--python 3.13] [--no-publish]
```

- **name** is lowercase letters, numbers and hyphens, starting and ending with a letter or number, with no consecutive hyphens, at most 63 characters, and not purely numeric. A `gds-idea-app-` prefix typed by mistake is removed for you. Pass the short name for `python` too: the `gds-idea-pkg-` prefix is added for you.
- `--python` sets the Python version (default 3.13). It is the Python version, not the project type.
- `--no-publish` (python projects only) leaves out the workflow that publishes to the internal package index.
- It creates the directory, runs `cdk init` and/or `uv init`, copies the template files, installs dependencies and makes the first git commit. The new repo already has a commit, so do not run `git init`.

After `init`, create the GitHub repo.

Web apps, static sites and infra projects:

```bash
cd gds-idea-app-my-dashboard
gh repo create co-cddo/gds-idea-app-my-dashboard --private --source . --push
```

Python packages (public, so the package index can find them), followed by the repo standards:

```bash
cd gds-idea-pkg-my-library
gh repo create co-cddo/gds-idea-pkg-my-library --public --source . --push
idea-gh init --type python-package
```

### idea-app update

Update the files `idea-app` manages in an existing project:

```bash
idea-app update [--dry-run] [--force]
```

- Each managed file's hash is compared with the manifest stored in `pyproject.toml`.
- Unchanged files are overwritten with the latest template, and missing ones are created.
- Locally modified files are skipped, and a `.new` file is written alongside for you to compare (`diff app_src/Dockerfile app_src/Dockerfile.new`), then delete.
- `--force` overwrites modified files too. `--dry-run` shows what would change and writes nothing.

### idea-app smoke-test

Build and health-check the production Docker image of a web app or static site:

```bash
idea-app smoke-test              # build, health check, then stop
idea-app smoke-test --build-only # only build
idea-app smoke-test --wait       # keep the container running until you press Enter
```

Health check paths: Streamlit `/_stcore/health`, Dash and FastAPI `/health`, static sites `/`. Static sites are built from their `development` target; the web apps from `production`.

### idea-app provide-role

Provide AWS credentials to the dev container:

```bash
idea-app provide-role                   # assume the role from pyproject.toml
idea-app provide-role --use-profile     # pass through the current AWS profile
idea-app provide-role --duration 7200   # session length in seconds (default 3600)
```

It assumes the role set in `pyproject.toml`; without `--use-profile` and with no role configured, it falls back to the current profile:

```toml
[tool.webapp.dev]
aws_role_arn = "arn:aws:iam::123456789012:role/your-dev-role"
aws_region = "eu-west-2"
```

### idea-app migrate

Interactively migrate a project from the old `gds-idea-app-templates` pattern to `idea-app`. Do it on a clean branch so you can review the changes:

```bash
git checkout -b migrate-to-idea-app
idea-app migrate
```

### idea-app adopt

Add the standard CI/CD and configuration to an existing project that `idea-app` did not create. It handles CDK projects (it finds `cdk.json`) and Python packages (a `pyproject.toml` without `cdk.json`):

```bash
idea-app adopt [--no-publish]
```

For a CDK project it copies the workflows, CODEOWNERS and dependabot config, installs `gds-idea-cdk-constructs` (0.7.0 or later) and writes a manifest as an `infra` project.

## File ownership model

`idea-app` manages certain files and leaves the rest to you. `idea-app update` only touches the managed ones.

| Project type | Managed by idea-app | Yours (never touched) |
|--------------|--------------------|-----------------------|
| `streamlit`, `dash`, `fastapi` | `.github/workflows/ci_cd_cdk_app.yml`, `.github/workflows/ci_pr_cdk_app.yml`, `.github/CODEOWNERS`, `.github/dependabot.yml`, `.devcontainer/devcontainer.json`, `.devcontainer/docker-compose.yml`, `.devcontainer/README.md`, `.aws-dev/README.md`, `dev_mocks/dev_mock_authoriser.json`, `dev_mocks/dev_mock_user.json`, `app_src/Dockerfile`, `app_src/Dockerfile.dockerignore`, `app_src/.vscode/tasks.json`, `LICENCE` | `app.py`, `cdk.json`, root `pyproject.toml` (except the manifest section), `app_src/{framework}_app.py`, `app_src/pyproject.toml`, `tests/`, `README.md` |
| `static` | `.github/workflows/ci_cd_cdk_app.yml`, `.github/workflows/ci_pr_cdk_app.yml`, `.github/CODEOWNERS`, `.github/dependabot.yml`, `.devcontainer/devcontainer.json`, `.devcontainer/docker-compose.yml`, `site_src/Dockerfile`, `site_src/handler.py`, `LICENCE` | `app.py`, `cdk.json`, root `pyproject.toml`, `site_src/package.json`, `site_src/eleventy.config.js`, `site_src/src/`, `dev_mocks/user.json`, `tests/`, `README.md` |
| `infra` | `.github/workflows/ci_cd_cdk_app.yml`, `.github/workflows/ci_pr_cdk_app.yml`, `.github/CODEOWNERS`, `.github/dependabot.yml`, `LICENCE` | `app.py`, `cdk.json`, `pyproject.toml`, `tests/` |
| `python` | `.github/workflows/ci.yml`, `.github/workflows/release.yml`, `.github/CODEOWNERS`, `.github/dependabot.yml`, `.pre-commit-config.yaml`, `LICENCE` | `pyproject.toml`, `src/{package_name}/`, `tests/`, `README.md` |

## Project configuration

The project's `pyproject.toml` has two tool sections.

### [tool.webapp]: app identity (web apps)

```toml
[tool.webapp]
app_name = "my-dashboard"
framework = "streamlit"

[tool.webapp.dev]
aws_role_arn = "arn:aws:iam::123456789012:role/your-dev-role"
aws_region = "eu-west-2"
```

### [tool.gds-idea-app-kit]: the manifest

```toml
[tool.gds-idea-app-kit]
framework = "streamlit"
app_name = "my-dashboard"
tool_version = "0.7.1"

[tool.gds-idea-app-kit.files]
"app_src/Dockerfile" = "sha256:..."
".devcontainer/devcontainer.json" = "sha256:..."
```

The manifest records the project type, the `idea-app` version that wrote it, and a hash of each managed file as last written. That is how `idea-app update` tells whether you have modified a file.

## Typical workflows

### Starting a new web app

```bash
idea-app init streamlit my-dashboard
cd gds-idea-app-my-dashboard
gh repo create co-cddo/gds-idea-app-my-dashboard --private --source . --push
# Open in VS Code and reopen in the dev container when prompted
```

### Keeping up to date after upgrading idea-app

```bash
idea-tools upgrade gds-idea-app-kit   # or: uv tool upgrade gds-idea-app-kit
cd gds-idea-app-my-dashboard
idea-app update --dry-run             # preview the changes
idea-app update                       # apply them
git diff                              # review
git add -A && git commit -m "Update idea-app managed files"
```

`init`, `update` and `adopt` check for a newer `idea-app` and tell you how to upgrade.

### Testing the production image locally

```bash
idea-app smoke-test --wait
# The app is running at http://localhost:8080
# Press Enter to stop
```

### Providing AWS credentials to the dev container

```bash
AWS_PROFILE=my-profile idea-app provide-role
# Credentials are written to .aws-dev/ (mounted into the container)
```

## Dev container behaviour (web apps)

- The app is not the container's main process. `devcontainer.json` sets `"overrideCommand": true`, so a crashing app never stops the container. Keep that setting.
- The app runs from the "Run app" VS Code task (`app_src/.vscode/tasks.json`, run when the folder opens, with auto-reload). Errors show in that terminal. To recover, fix the code and re-run the task (Cmd/Ctrl+Shift+B, or Terminal > Run Task). No rebuild is needed.
- `idea-app smoke-test` builds the production image, which is separate from the dev container.
- The Dockerfile has three stages: `base` (`uv sync --no-default-groups`, no CMD), `development` (`uv sync`, with reload) and `production` (`uv run --no-sync`). Production never contains pytest or the Zscaler fix.
- The Zscaler TLS fix is a `zscaler` dependency group in `pyproject.toml`, listed in `[tool.uv] default-groups` alongside `dev`, in both `app_src/` and the repo root. A plain `uv sync` keeps it. Do not install it with `uv pip install`: a later `uv sync` removes it.
- `idea-app update` creates the new managed files in older projects and prints the `uv add --group zscaler` commands if the group is missing. You have to run them yourself, because `pyproject.toml` is yours.
- Older projects (before 0.7.0) run the app as the container's main process, so a crash on startup kills the container. Fix: `idea-app update`, add the Zscaler group, rebuild the container.

## Troubleshooting

### Dev container exits or won't attach

On projects older than 0.7.0 the app is the container's main process, so an import error or bad dependency stops the container. Upgrade with `idea-app update`, then rebuild. On 0.7.0 and later, look in the "Run app" terminal instead.

### "docker compose not found"

Add to `~/.docker/config.json`:

```json
{
  "cliPluginsExtraDirs": ["/opt/homebrew/lib/docker/cli-plugins"]
}
```

### Missing prerequisites

`init` checks that the tools it needs for the chosen type are installed and prints the `brew install` command for any that are missing. To install all of them:

```bash
brew install uv git docker docker-compose aws-cdk gitleaks
```

### "No [tool.gds-idea-app-kit] section found"

You ran `idea-app update` in a project `idea-app` did not create. Use `idea-app adopt`, or `idea-app migrate` if it came from the old templates.
