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
