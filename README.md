# gds-idea-app-kit

CLI tool for scaffolding and maintaining GDS IDEA web apps on AWS.

Generates projects with:
- **Streamlit**, **Dash**, or **FastAPI** framework
- AWS CDK infrastructure (ECS Fargate behind ALB with Cognito auth)
- VS Code dev container for local development
- Production-ready multi-stage Dockerfile

## Prerequisites

Install with [Homebrew](https://brew.sh/):

```bash
brew install uv node git docker aws-cdk
```

You also need SSH access to the `co-cddo` GitHub organisation (for private CDK construct dependencies).

## Installation

`idea-app` is installed as a global CLI tool, not as a per-project dependency:

```bash
uv tool install "gds-idea-app-kit @ git+https://github.com/co-cddo/gds-idea-app-kit"
```

To upgrade to the latest version:

```bash
uv tool upgrade gds-idea-app-kit
```

Verify it's working:

```bash
idea-app --version
```

## New project

Scaffold a new project with `idea-app init`:

```bash
idea-app init streamlit my-dashboard
```

This creates a directory `gds-idea-app-my-dashboard/` containing:

- `app.py` -- CDK entry point
- `cdk.json` -- CDK configuration
- `app_src/` -- your application code, Dockerfile, and dependencies
- `.devcontainer/` -- VS Code dev container configuration
- `dev_mocks/` -- mock auth data for local development
- `.gitignore` -- pre-configured for Python, CDK, and dev artifacts

The tool runs `cdk init`, `uv init`, copies template files, installs CDK dependencies, and makes an initial git commit. All of this happens automatically.

### Options

```bash
idea-app init <framework> <app-name> [--python 3.13]
```

- `framework`: `streamlit`, `dash`, or `fastapi`
- `app-name`: short name for your app (lowercase, hyphens ok). The `gds-idea-app-` prefix is added automatically.
- `--python`: Python version for the project (default: 3.13)

### After init

```bash
cd gds-idea-app-my-dashboard

# Create the GitHub repo (requires gh CLI):
gh repo create co-cddo/gds-idea-app-my-dashboard --private --source . --push

# Or add a remote manually:
git remote add origin git@github.com:co-cddo/gds-idea-app-my-dashboard.git
git push -u origin main
```

Then open the project in VS Code and reopen in the dev container when prompted.

## Migrating an existing project

If you have a project created from the [gds-idea-app-templates](https://github.com/co-cddo/gds-idea-app-templates) template repository, migrate it to `idea-app`:

```bash
cd gds-idea-app-my-existing-project
idea-app migrate
```

The command is interactive and will:

1. Read your existing `[tool.webapp]` configuration
2. Ask you to confirm before making changes
3. Build a manifest from your current tracked files
4. Remove old `template/` directory, `[project.scripts]`, and `[build-system]` sections
5. Offer to update your files to the latest templates (with a dry-run preview first)

Run this on a clean branch so you can review the changes:

```bash
git checkout -b migrate-to-idea-app
idea-app migrate
git diff
git add -A && git commit -m "Migrate to idea-app"
```

## Updating template files

When `idea-app` is upgraded with new template changes (Dockerfile improvements, devcontainer updates, etc.), update your project:

```bash
cd gds-idea-app-my-dashboard
idea-app update
```

The update command manages files like the Dockerfile, devcontainer config, and docker-compose. It does not touch your application code, `cdk.json`, or `pyproject.toml`.

### How updates work

Each tracked file is compared against the manifest hash from the last update:

| File state | What happens |
|---|---|
| Unchanged since last update | Overwritten with the latest template |
| Locally modified | Skipped. A `.new` file is written alongside for you to review |
| Missing from project | Created |

When files are skipped, you'll see instructions to compare and merge:

```
diff app_src/Dockerfile app_src/Dockerfile.new
```

### Options

```bash
idea-app update [--dry-run] [--force]
```

- `--dry-run`: show what would change without writing anything
- `--force`: overwrite all files, including ones you've modified locally

## Other commands

### smoke-test

Build and health-check the production Docker image:

```bash
idea-app smoke-test              # build + health check
idea-app smoke-test --build-only # just build, skip health check
idea-app smoke-test --wait       # keep running after health check, press Enter to stop
```

### provide-role

Provide AWS credentials to the dev container by assuming the configured IAM role:

```bash
idea-app provide-role                  # assume role from [tool.webapp.dev]
idea-app provide-role --use-profile    # pass through current AWS profile instead
idea-app provide-role --duration 7200  # session duration in seconds (default: 3600)
```

Configure the role ARN in your project's `pyproject.toml`:

```toml
[tool.webapp.dev]
aws_role_arn = "arn:aws:iam::123456789012:role/your-dev-role"
aws_region = "eu-west-2"
```

## Development

```bash
# Clone and install dev dependencies
git clone git@github.com:co-cddo/gds-idea-app-kit.git
cd gds-idea-app-kit
uv sync

# Run unit tests
uv run pytest

# Run integration tests (requires CDK and network access)
uv run pytest -m integration

# Run all tests
uv run pytest -m ""

# Lint and format
uv run ruff check src/ tests/
uv run ruff format src/ tests/
```
