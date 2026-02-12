# gds-idea-app-kit

CLI tool for scaffolding and maintaining GDS IDEA web apps on AWS.

Generates projects with:
- **Streamlit**, **Dash**, or **FastAPI** framework
- AWS CDK infrastructure (ECS Fargate behind ALB with Cognito auth)
- VS Code dev container for local development
- Production-ready multi-stage Dockerfile

## Installation

```bash
uv tool install "gds-idea-app-kit @ git+https://github.com/co-cddo/gds-idea-app-kit"
```

## Usage

```bash
# Scaffold a new project
idea-app init streamlit my-dashboard

# Update tool-managed files in an existing project
cd gds-idea-app-my-dashboard
idea-app update

# Build and health-check the production Docker image
idea-app smoke-test

# Provide AWS credentials to dev container
idea-app provide-role
```

## Commands

| Command | Description |
|---------|-------------|
| `idea-app init <framework> <name> [--python 3.13]` | Scaffold a new project |
| `idea-app update [--dry-run]` | Update tool-owned files (Dockerfile, devcontainer, etc.) |
| `idea-app smoke-test [--build-only] [--wait]` | Docker build + health check |
| `idea-app provide-role [--use-profile] [--duration N]` | AWS credential provisioning for dev container |

## Development

See [PLAN.md](PLAN.md) for design details and implementation plan.

```bash
# Install dev dependencies
uv sync

# Run tests
uv run pytest

# Lint and format
uv run ruff check src/ tests/
uv run ruff format src/ tests/
```
