# CI/CD workflows

All scaffolded projects use reusable workflows from the [gds-idea-workflows-catalogue](https://github.com/co-cddo/gds-idea-workflows-catalogue). The project contains thin orchestrator files that call these shared workflows.

## Web app / Infrastructure workflows

### `ci_cd_cdk_app.yml` (push to dev/prod)

Triggered on push to `dev` or `prod` branches. Runs CI checks then deploys:

1. **Build** — verifies the project builds
2. **Lint** — ruff check and format
3. **Test** — pytest
4. **Deploy** — CDK synth + deploy to the appropriate environment

### `ci_pr_cdk_app.yml` (pull requests)

Triggered on PRs to `dev` or `prod`. Runs checks without deploying:

1. **PR source check** — PRs to `prod` must come from `dev`
2. **Build** — verifies the project builds
3. **Version check** — pyproject.toml version has been bumped
4. **Lint** — ruff check and format
5. **Test** — pytest
6. **CDK diff** — posts infrastructure diff as a PR comment

## Python package workflows

### `ci.yml` (pull requests to main)

Calls three reusable workflows:

| Workflow | What it does |
|---|---|
| `ci_pkg_lint.yml` | `uv sync --all-extras` then `ruff check` + `ruff format --check` |
| `ci_pkg_test.yml` | Matrix test across Python 3.11, 3.12, 3.13, 3.14 with `pytest -m "not integration"` |
| `ci_pkg_build.yml` | `uv build` with full git history (for hatch-vcs) |

### `release.yml` (push to main)

A two-job workflow calling reusable workflows in sequence:

**Job 1: release** — calls `auto_tag_release.yml`:

1. Checks if HEAD already has a tag (skip if so)
2. Reads labels from the merged PR
3. Computes the next semver version:
    - `bump:major` → major bump
    - `bump:minor` → minor bump
    - _(default)_ → patch bump
4. Creates a git tag and GitHub release with auto-generated notes
5. Outputs the tag name for the publish job

**Job 2: publish** (only if a tag was created) — calls `gds_idea_pypi_publish.yml`:

1. Checks out the tagged commit
2. Builds wheel and sdist with `uv build`
3. Uploads artifacts to the GitHub release
4. Generates a GitHub App token (if configured)
5. Triggers a rebuild of the [gds-idea-pypi](https://co-cddo.github.io/gds-idea-pypi/) index

If `--no-publish` was used during scaffold, only the release job is present.

## Workflow catalogue

All reusable workflows live in [`co-cddo/gds-idea-workflows-catalogue`](https://github.com/co-cddo/gds-idea-workflows-catalogue) under `.github/workflows/`.

### CDK app workflows

| Workflow | Purpose |
|---|---|
| `ci_build.yml` | Build check |
| `ci_lint.yml` | Lint with ruff |
| `ci_tests.yml` | Run pytest |
| `ci_pr_dev.yml` | Enforce branching policy |
| `ci_pyproject_version.yml` | Version bump check |
| `ci_cdk_diff.yml` | CDK diff on PRs |
| `cd_workflow_cdk.yml` | CDK deploy |

### Python package workflows

| Workflow | Purpose |
|---|---|
| `ci_pkg_lint.yml` | Lint with ruff |
| `ci_pkg_test.yml` | Test across Python matrix |
| `ci_pkg_build.yml` | Build wheel/sdist |
| `auto_tag_release.yml` | Label-based semver tagging |
| `gds_idea_pypi_publish.yml` | Build, upload, trigger index rebuild |
