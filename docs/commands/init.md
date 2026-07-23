# idea-app init

Scaffold a new project.

## Usage

```bash
idea-app init <type> <name> [--python VERSION] [--no-publish]
```

## Arguments

| Argument | Description |
|---|---|
| `type` | Project type: `streamlit`, `dash`, `fastapi`, `static`, `infra`, or `python` |
| `name` | Short name for your project (lowercase, hyphens allowed) |

## Options

| Option | Default | Description |
|---|---|---|
| `--python` | `3.13` | Python version for the project |
| `--no-publish` | off | Skip the gds-idea-pypi publish workflow (python projects only) |

## Project types

### Web applications (streamlit, dash, fastapi)

Creates a containerised web app deployed to AWS ECS Fargate behind an ALB with Cognito authentication.

```bash
idea-app init streamlit my-dashboard
idea-app init dash analytics-tool
idea-app init fastapi data-api
```

**Directory:** `gds-idea-app-{name}/`

**Includes:** CDK infrastructure, Dockerfile, devcontainer, CI/CD workflows, dev mocks for local auth.

**Prerequisites:** `uv`, `git`, `cdk`, `docker`, `docker compose`

### Static site (static)

Creates an [Eleventy](https://www.11ty.dev) static site with GOV.UK community styling, deployed to AWS Lambda + S3 behind an ALB with Cognito authentication.

```bash
idea-app init static my-docs
```

**Directory:** `gds-idea-app-{name}/`

**Includes:**

- Eleventy site with [`@x-govuk/govuk-eleventy-plugin`](https://x-govuk.github.io/govuk-eleventy-plugin/) styling
- A "Your Account" page demonstrating the `/.auth/user` endpoint (via `StaticSite`'s `cognito-auth` integration)
- Multi-stage Dockerfile (`development` for local preview, `build` for the Lambda that regenerates the site)
- Build handler (construct-managed — runs the build command and uploads to S3)
- Devcontainer with Eleventy live reload and a mocked `/.auth/user` endpoint (`dev_mocks/user.json`) for local testing
- CI/CD workflows (same as web apps — `cdk deploy` on merge)

Unlike streamlit/dash/fastapi, static sites have no long-running application container in production — the build runs once (or on a schedule) inside a Lambda function, and a separate Lambda serves the built files from S3.

**Prerequisites:** `uv`, `git`, `cdk`, `docker`, `docker compose`

### Infrastructure only (infra)

Creates a bare CDK project with no containerised application.

```bash
idea-app init infra shared-resources
```

**Directory:** `gds-idea-app-{name}/`

**Includes:** CDK infrastructure scaffold, CI/CD workflows.

**Prerequisites:** `uv`, `git`, `cdk`

### Python package (python)

Creates a pure Python package with src layout, hatch-vcs versioning, pre-commit hooks, and CI/CD.

```bash
idea-app init python my-library
idea-app init python my-library --no-publish
```

**Directory:** `gds-idea-pkg-{name}/`

**Includes:**

- `src/{package_name}/` layout with hatchling + hatch-vcs
- Pre-commit hooks (ruff, gitleaks, file hygiene)
- CI/CD workflows (lint, test, build, auto-release, PyPI publish)
- Dependabot, CODEOWNERS, MIT licence

**Prerequisites:** `uv`, `git`, `gitleaks`

**Versioning:** Automatic from git tags via hatch-vcs. No manual version field in pyproject.toml. The auto-release workflow creates tags based on PR labels (`bump:major`, `bump:minor`, or patch by default).

## Name handling

The project name is validated as a DNS subdomain label:

- Lowercase letters, numbers, and hyphens only
- Must start and end with a letter or number
- No consecutive hyphens (`--`)
- Maximum 63 characters
- Cannot be purely numeric

If you accidentally include the prefix (e.g. `gds-idea-app-my-app`), it is stripped automatically.

## What happens during init

1. Validates the name and checks prerequisites
2. Creates the project directory
3. Runs `cdk init` and/or `uv init` depending on type
4. Copies template files (workflows, Dockerfile, devcontainer, etc.)
5. Installs dependencies
6. Makes the initial git commit
7. Prints next steps

## After init

=== "Web app / Infra"

    ```bash
    cd gds-idea-app-my-dashboard

    # Create the GitHub repo:
    gh repo create co-cddo/gds-idea-app-my-dashboard --private --source . --push

    # Open in VS Code and reopen in dev container when prompted
    ```

=== "Python package"

    ```bash
    cd gds-idea-pkg-my-library

    # Create the GitHub repo:
    gh repo create co-cddo/gds-idea-pkg-my-library --public --source . --push

    # Configure repo settings and branch protection:
    idea-gh init --type python-package

    # Check compliance:
    idea-gh audit
    ```
