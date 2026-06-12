# idea-app adopt

Add CI/CD and configuration to an existing CDK project that was not created by `idea-app`.

## Usage

```bash
idea-app adopt
```

Run this from inside an existing CDK project directory.

## What it does

1. Copies CI/CD workflow files (`.github/workflows/`)
2. Copies CODEOWNERS and dependabot configuration
3. Installs `gds-idea-cdk-constructs` from the internal PyPI index
4. Writes a manifest to `pyproject.toml` (as `infra` type)

## When to use

Use `adopt` when you have a CDK project that:

- Was created manually or with `cdk init` directly
- Already has its own infrastructure code
- Needs the standard CI/CD workflows and org configuration

If your project was created from the old `gds-idea-app-templates` template repository, use [`idea-app migrate`](migrate.md) instead.
