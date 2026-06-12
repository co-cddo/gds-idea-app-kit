# Project structure

Generated project layouts for each project type.

## Web app (streamlit, dash, fastapi)

```
gds-idea-app-{name}/
├── app.py                          # CDK entry point (WebApp construct)
├── cdk.json                        # CDK configuration
├── pyproject.toml                  # Root: CDK deps + manifest
├── app_src/
│   ├── Dockerfile                  # Multi-stage: development + production
│   ├── pyproject.toml              # App dependencies
│   ├── {framework}_app.py          # Your application code
│   └── tests/
│       └── test_app.py             # App-level tests
├── .devcontainer/
│   ├── devcontainer.json           # VS Code dev container config
│   └── docker-compose.yml          # Dev container services
├── dev_mocks/
│   ├── dev_mock_authoriser.json    # Mock Cognito authoriser
│   └── dev_mock_user.json          # Mock authenticated user
├── tests/
│   └── test_app.py                 # CDK stack tests
├── .github/
│   ├── CODEOWNERS
│   ├── dependabot.yml
│   └── workflows/
│       ├── ci_cd_cdk_app.yml       # Deploy on push to dev/prod
│       └── ci_pr_cdk_app.yml       # PR checks
├── .gitignore
├── LICENCE
├── README.md
└── uv.lock
```

## Infrastructure only (infra)

```
gds-idea-app-{name}/
├── app.py                          # CDK entry point (bare Stack)
├── cdk.json                        # CDK configuration
├── pyproject.toml                  # CDK deps + manifest
├── tests/
│   └── test_app.py                 # CDK stack tests
├── .github/
│   ├── CODEOWNERS
│   ├── dependabot.yml
│   └── workflows/
│       ├── ci_cd_cdk_app.yml
│       └── ci_pr_cdk_app.yml
├── .gitignore
├── LICENCE
├── README.md
└── uv.lock
```

## Python package (python)

```
gds-idea-pkg-{name}/
├── src/
│   └── {package_name}/
│       └── __init__.py             # Package entry point
├── tests/
│   ├── __init__.py
│   └── conftest.py                 # Shared fixtures + markers
├── pyproject.toml                  # hatchling + hatch-vcs + ruff + pytest
├── .pre-commit-config.yaml         # ruff, gitleaks, file hygiene
├── .github/
│   ├── CODEOWNERS
│   ├── dependabot.yml
│   └── workflows/
│       ├── ci.yml                  # Lint + test + build
│       └── release.yml             # Tag + release + publish on merge
├── .gitignore
├── LICENCE
├── README.md
└── uv.lock
```
