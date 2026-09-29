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
