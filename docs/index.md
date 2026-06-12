# idea-app

CLI tool for scaffolding and maintaining GDS IDEA projects on AWS.

## What it does

`idea-app` generates fully configured projects with CI/CD, infrastructure, and development tooling already set up. It supports:

- **Web applications** (Streamlit, Dash, FastAPI) deployed to AWS ECS Fargate with Cognito authentication
- **Infrastructure-only** projects using AWS CDK
- **Python packages** with src layout, automated versioning, and publishing to the internal PyPI index

## Installation

`idea-app` is installed as a global CLI tool via the [GDS IDEA package index](https://co-cddo.github.io/gds-idea-pypi/).

**Recommended (using `idea-tools`):**

```bash
idea-tools install gds-idea-app-kit
```

**Alternative (without `idea-tools`):**

```bash
uv tool install gds-idea-app-kit --index gds-idea=https://co-cddo.github.io/gds-idea-pypi/simple/
```

**Upgrade to latest:**

```bash
idea-tools upgrade gds-idea-app-kit
# or: uv tool upgrade gds-idea-app-kit
```

**Verify installation:**

```bash
idea-app --version
```

## Prerequisites

Install with [Homebrew](https://brew.sh/):

```bash
brew install uv git
```

Additional tools are needed depending on project type:

| Project type | Additional prerequisites |
|---|---|
| Web apps (streamlit, dash, fastapi) | `docker`, `docker-compose`, `aws-cdk`, `node` |
| Infrastructure (infra) | `aws-cdk`, `node` |
| Python packages (python) | `gitleaks` |

`idea-app init` checks all prerequisites before creating a project and tells you what to install if anything is missing.

## Quick start

=== "Web app"

    ```bash
    idea-app init streamlit my-dashboard
    cd gds-idea-app-my-dashboard
    gh repo create co-cddo/gds-idea-app-my-dashboard --private --source . --push
    ```

=== "Python package"

    ```bash
    idea-app init python my-library
    cd gds-idea-pkg-my-library
    gh repo create co-cddo/gds-idea-pkg-my-library --public --source . --push
    idea-gh init --type python-package
    ```

=== "Infrastructure only"

    ```bash
    idea-app init infra my-infra
    cd gds-idea-app-my-infra
    gh repo create co-cddo/gds-idea-app-my-infra --private --source . --push
    ```

## Commands

| Command | Description |
|---|---|
| [`idea-app init`](commands/init.md) | Scaffold a new project |
| [`idea-app update`](commands/update.md) | Update tool-managed files |
| [`idea-app smoke-test`](commands/smoke-test.md) | Build and health-check the Docker image |
| [`idea-app provide-role`](commands/provide-role.md) | Provide AWS credentials to the dev container |
| [`idea-app migrate`](commands/migrate.md) | Migrate from old template repo pattern |
| [`idea-app adopt`](commands/adopt.md) | Add CI/CD to an existing CDK project |
