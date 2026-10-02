# Getting started

This guide walks you through creating your first project with `idea-app`.

## Install the tool

```bash
idea-tools install gds-idea-app-kit
```

Or without `idea-tools`:

```bash
uv tool install gds-idea-app-kit --index gds-idea=https://co-cddo.github.io/gds-idea-pypi/simple/
```

Verify:

```bash
idea-app --version
```

## Choose your project type

| I want to... | Use |
|---|---|
| Build a web dashboard with Streamlit | `idea-app init streamlit` |
| Build a web dashboard with Dash | `idea-app init dash` |
| Build a web API with FastAPI | `idea-app init fastapi` |
| Deploy AWS infrastructure only | `idea-app init infra` |
| Create a reusable Python library | `idea-app init python` |

## Create a web app

```bash
idea-app init streamlit my-dashboard
```

This creates `gds-idea-app-my-dashboard/` with everything configured:

```
gds-idea-app-my-dashboard/
├── app.py                  # CDK entry point
├── cdk.json
├── pyproject.toml
├── app_src/
│   ├── Dockerfile
│   ├── pyproject.toml
│   └── streamlit_app.py   # Your app code starts here
├── .devcontainer/
├── dev_mocks/
├── .github/workflows/
├── tests/
└── LICENCE
```

### Push to GitHub

```bash
cd gds-idea-app-my-dashboard
gh repo create co-cddo/gds-idea-app-my-dashboard --private --source . --push
```

### Start developing

Open the project in VS Code. When prompted, reopen in the dev container.

The app starts automatically in a terminal called "Run app", with auto-reload, and is served at <http://localhost:8080>. VS Code asks once whether to allow automatic tasks; choose **Allow**.

Provide AWS credentials:

```bash
idea-app provide-role
```

Test the production image:

```bash
idea-app smoke-test --wait
# Visit http://localhost:8080
```

### When your code has an error

The app runs from a VS Code task, not as the container's main process. If your code has an error, the traceback appears in the "Run app" terminal and the dev container keeps running. Fix the code and run the task again (**Terminal > Run Task... > Run app**). You do not need to rebuild the container.

See `.devcontainer/README.md` in your project for the full dev container guide.

## Create a Python package

```bash
idea-app init python my-library
```

This creates `gds-idea-pkg-my-library/` with:

```
gds-idea-pkg-my-library/
├── src/my_library/__init__.py
├── tests/
├── pyproject.toml
├── .pre-commit-config.yaml
├── .github/workflows/
├── LICENCE
└── README.md
```

### Push to GitHub

```bash
cd gds-idea-pkg-my-library
gh repo create co-cddo/gds-idea-pkg-my-library --public --source . --push
idea-gh init --type python-package
```

### Start developing

```bash
# Install dependencies
uv sync

# Run tests
uv run pytest

# Pre-commit hooks are already active
git checkout -b feat/my-feature
# ... make changes ...
git add . && git commit  # hooks auto-fix formatting
```

## Next steps

- [Python packages guide](python-packages.md) for details on the Python scaffold
- [Keeping up to date](keeping-up-to-date.md) for upgrading managed files
- [File ownership](../reference/file-ownership.md) to understand which files you own vs the tool manages
