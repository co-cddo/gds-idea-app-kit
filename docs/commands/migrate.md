# idea-app migrate

Migrate an existing project from the old [gds-idea-app-templates](https://github.com/co-cddo/gds-idea-app-templates) pattern to `idea-app`.

## Usage

```bash
idea-app migrate
```

Run this from inside an existing project directory.

## What it does

The command is interactive and will:

1. Read your existing `[tool.webapp]` configuration
2. Ask you to confirm before making changes
3. Build a manifest from your current tracked files
4. Remove the old `template/` directory, `[project.scripts]`, and `[build-system]` sections
5. Offer to update your files to the latest templates (with a dry-run preview first)

## Recommended workflow

Run on a clean branch so you can review the changes:

```bash
git checkout -b migrate-to-idea-app
idea-app migrate
git diff
git add -A && git commit -m "Migrate to idea-app"
```

## When to use

Use `migrate` if your project was originally created from the `gds-idea-app-templates` template repository and still has the old structure (a `template/` directory, entry points in `[project.scripts]`, etc.).

If your project is a standalone CDK project that was never created from the templates, use [`idea-app adopt`](adopt.md) instead.
