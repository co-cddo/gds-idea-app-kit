# gds-idea-app-kit - Implementation Plan

## Overview

CLI tool (`idea-app`) for scaffolding and maintaining GDS IDEA web apps
deployed to AWS with Cognito auth behind an ALB. Replaces the template
repository pattern with a package-based approach.

Install: `uv tool install "gds-idea-app-kit @ git+https://github.com/co-cddo/gds-idea-app-kit"`

## Commands

### `idea-app init <framework> <app-name> [--python 3.13]`

Creates `gds-idea-app-{app-name}/` with a fully scaffolded project.

1. Validate inputs (framework: streamlit/dash/fastapi, name: alphanumeric + hyphens)
2. Strip `gds-idea-app-` prefix if user accidentally included it
3. mkdir `gds-idea-app-{app-name}/`
4. `cdk init app --language python --generate-only` (catch missing cdk, print install instructions)
5. `uv init`
6. Delete: requirements.txt, requirements-dev.txt, source.bat, hello.py, generated stack module
7. Overwrite app.py with our template
8. Rewrite test file to reference WebApp stack
9. Merge into pyproject.toml: CDK deps, gds-idea-app-kit as dev dep, [tool.gds-idea] manifest
10. Append to .gitignore
11. Copy framework files into app_src/
12. Copy .devcontainer/, dev_mocks/
13. Apply template variables ({{app_name}}, {{python_version}})
14. uv sync
15. git add && git commit
16. Print next steps (including gh repo create / manual git remote instructions for co-cddo org)

Default Python: 3.13, overridable with --python.
Directory naming: always `gds-idea-app-{name}`.

### `idea-app update [--dry-run]`

Updates tool-owned files in existing projects.

1. Read [tool.gds-idea] from pyproject.toml
2. Warn if tool version is newer than manifest version (suggest upgrading)
3. For each tool-owned file: compare hash to manifest, overwrite if unchanged, skip if modified
4. Update manifest version
5. --dry-run shows changes without applying

File ownership:

| Category | Files | Behavior |
|----------|-------|----------|
| Tool-owned | app_src/Dockerfile, .devcontainer/*, dev_mocks/* | Overwrite if hash matches |
| Shared | Both pyproject.toml files | Skip if modified, warn |
| User-owned | app.py, app_src/*_app.py, cdk.json, tests/ | Never touch |

### `idea-app smoke-test [--build-only] [--wait]`

Docker build + health check. --build-only skips health check. --wait keeps container running.

### `idea-app provide-role [--use-profile] [--duration N]`

AWS credential provisioning for dev container. Default duration: 1 hour.

## Package structure

```
gds-idea-app-kit/
├── pyproject.toml
├── src/
│   └── gds_idea_app_kit/
│       ├── __init__.py
│       ├── cli.py
│       ├── init.py
│       ├── update.py
│       ├── smoke_test.py
│       ├── provide_role.py
│       ├── manifest.py
│       └── templates/
│           ├── common/          (app.py, gitignore-extra, devcontainer.json, docker-compose.yml)
│           ├── dev_mocks/       (dev_mock_authoriser.json, dev_mock_user.json)
│           ├── streamlit/       (Dockerfile, pyproject.toml, streamlit_app.py)
│           ├── dash/            (Dockerfile, pyproject.toml, dash_app.py)
│           └── fastapi/         (Dockerfile, pyproject.toml, fastapi_app.py)
└── tests/
    ├── conftest.py
    ├── test_init.py
    ├── test_update.py
    ├── test_manifest.py
    └── test_smoke_test.py
```

## Tech decisions

- click for CLI framework (CliRunner for testing)
- tomlkit for pyproject.toml read/write (preserves formatting)
- boto3 for provide-role (direct dependency, not optional)
- Simple str.replace() for template variables, no Jinja2
- cdk init runs first (requires empty dir), then uv init on top
- cdk.json comes from cdk init (always current feature flags), never updated by idea-app update
- Manifest stored in pyproject.toml [tool.gds-idea] section
- Repo naming enforced: gds-idea-app-{name}
- GitHub org: co-cddo (in printed instructions)
- Default Python: 3.13 (hardcoded in package, overridable with --python)
- On missing cdk: catch error, print install instructions (npm/brew)

## Implementation phases

1. Package skeleton (pyproject.toml, cli.py with click group, Ruff config, git init)
2. Template files (copy from dumper repo, add {{placeholders}})
3. Core modules (manifest.py, init.py, update.py)
4. Port smoke_test.py and provide_role.py to click
5. Tests (unit: init/update/manifest, integration: smoke-test with Docker)
6. CI (GitHub Actions: lint, unit tests, integration tests with Docker)
