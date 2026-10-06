# Keeping up to date

When `idea-app` is upgraded with new template improvements, you can update your project's managed files.

## Workflow

```bash
# 1. Upgrade the tool
idea-tools upgrade gds-idea-app-kit

# 2. Preview changes
cd your-project
idea-app update --dry-run

# 3. Apply changes
idea-app update

# 4. Review and commit
git diff
git add -A && git commit -m "Update idea-app managed files"
```

## What gets updated

`idea-app update` manages infrastructure and CI/CD files. It never touches your application code, tests, or CDK configuration.

See [File ownership](../reference/file-ownership.md) for the complete list.

## Upgrading to 0.7.0: dev container changes

Version 0.7.0 changes how the dev container runs your app, so a bug in your code no longer takes the container down. It also moves the Zscaler TLS fix into your `pyproject.toml` files, and keeps development tools out of production images.

**What changed**

- The dev container no longer runs your app as its main process (`"overrideCommand": true`). The app starts from a VS Code task called "Run app", with auto-reload. If it crashes, the traceback is in that terminal and the container keeps running.
- Production images are built with `uv sync --no-default-groups`, so they no longer contain pytest or the Zscaler fix. The production start command uses `uv run --no-sync`, so it never installs packages at start-up.
- `app_src/Dockerfile.dockerignore` keeps `app_src/tests`, `.aws-dev` and local environments out of the image.
- New managed files: `app_src/.vscode/tasks.json`, `app_src/Dockerfile.dockerignore`, `.devcontainer/README.md` and `.aws-dev/README.md`.
- New projects ignore `cdk.context.json` in `.gitignore`.

**What you need to do**

1. Run `idea-app update` and review any `.new` files.
2. Add the Zscaler fix as a default dependency group. The Dockerfile used to install it with `uv pip install`, and a plain `uv sync` removed it again. `idea-app update` prints these commands if your project needs them. Run them in `app_src/` and in the repository root:

    ```bash
    uv add --group zscaler "gds-idea-pkg-zscaler-fix>=0.1.2" \
      --index gds-idea=https://co-cddo.github.io/gds-idea-pypi/simple/
    ```

    Then add this to `pyproject.toml` in the same directory:

    ```toml
    [tool.uv]
    default-groups = ["dev", "zscaler"]
    ```

3. Rebuild the dev container (`Dev Containers: Rebuild Container`), and choose **Allow** when VS Code asks about automatic tasks.
4. Optional: if your project committed `cdk.context.json` and you would rather not, add `cdk.context.json` to `.gitignore` and run `git rm --cached cdk.context.json`. Note that CDK uses this file to make lookups repeatable, so without it CI repeats the lookups on every synth.

## Migrating `app.py` tags to `IdeaTags`

`app.py` is yours, so `idea-app update` does not change it. Projects created before `IdeaTags` was added still have the inline tagging code in `app.py`, and you need to switch them over by hand.

New projects are scaffolded with `IdeaTags` from `gds-idea-cdk-constructs` (version 0.7.0 or later). It applies the standard tags (`Environment`, `ManagedBy`, `Repository`, `AppName` and optionally `Owner`) to every stack and resource in the app, and checks the values when the app starts, so a placeholder like `TBA` is caught before you deploy.

**1. Upgrade the library**

```bash
uv add "gds-idea-cdk-constructs>=0.7.0" --index gds-idea=https://co-cddo.github.io/gds-idea-pypi/simple/
```

**2. Replace the tag code in `app.py`**

Before:

```python
from aws_cdk import Tags

Tags.of(app).add("Environment", dep_config.environment.friendly_name)
Tags.of(app).add("ManagedBy", "cdk")
Tags.of(app).add("Repository", "TBA")
Tags.of(app).add("AppName", app_config.app_name)
```

After:

```python
from gds_idea_cdk_constructs import AppConfig, DeploymentConfig, IdeaTags

IdeaTags(
    environment=dep_config.environment,
    app_name=app_config.app_name,
    repository="gds-idea-app-my-dashboard",
    owners=["Your Name"],  # optional
).apply(app)
```

Things to know:

- `repository` is the **repository name only**, for example `gds-idea-app-my-dashboard`. Do not include the organisation (`co-cddo/`), a URL or `.git`.
- `owners` is optional. Give one entry per person, and use names rather than email addresses. Commas are not allowed in AWS tag values, so do not put several owners in one string. Multiple owners are joined with `+` in the `Owner` tag.
- `ManagedBy` is now always lowercase `cdk`.
- Extra tags can be added with `extra_tags={"Name": "My App"}`.
- Remove the `Tags` import from `aws_cdk` if nothing else uses it.

See the [tagging documentation](https://co-cddo.github.io/gds-idea-cdk-constructs-new/api/tagging/) for the full details.

## Handling conflicts

If you've locally modified a managed file, `update` will:

1. Skip the file (your changes are preserved)
2. Write a `.new` file alongside with the latest template version
3. Print instructions to compare them

```bash
# Compare your version with the new template:
diff app_src/Dockerfile app_src/Dockerfile.new

# If you want to accept the new version:
mv app_src/Dockerfile.new app_src/Dockerfile

# If you want to keep yours, just delete the .new file:
rm app_src/Dockerfile.new
```

## Force update

To overwrite all files, including locally modified ones:

```bash
idea-app update --force
```

!!! warning
    This will discard any local changes to managed files. Use with caution.

## Version tracking

The tool version and file hashes are stored in `pyproject.toml` under `[tool.gds-idea-app-kit]`. This is how `update` detects which files have been locally modified.

```toml
[tool.gds-idea-app-kit]
framework = "streamlit"
app_name = "my-dashboard"
tool_version = "0.5.0"

[tool.gds-idea-app-kit.files]
"app_src/Dockerfile" = "sha256:abc123..."
".devcontainer/devcontainer.json" = "sha256:def456..."
```
