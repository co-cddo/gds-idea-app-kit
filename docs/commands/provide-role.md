# idea-app provide-role

Provide AWS credentials to the dev container by assuming an IAM role.

## Usage

```bash
idea-app provide-role [--use-profile] [--duration SECONDS]
```

Run this from the **host machine** (not inside the dev container).

## Options

| Option | Default | Description |
|---|---|---|
| `--use-profile` | off | Pass through current AWS profile instead of assuming a role |
| `--duration` | `3600` | Session duration in seconds for role assumption |

## Configuration

Add the role ARN and region to your project's `pyproject.toml`:

```toml
[tool.webapp.dev]
aws_role_arn = "arn:aws:iam::123456789012:role/your-dev-role"
aws_region = "eu-west-2"
```

## What it does

1. Reads the role ARN from `[tool.webapp.dev]` in `pyproject.toml`
2. Assumes the role using your current AWS credentials (via boto3 STS)
3. Writes temporary credentials to `.aws-dev/` (which is mounted into the dev container)

The credentials expire after the configured duration (default: 1 hour).

## Examples

```bash
# Assume the configured role:
idea-app provide-role

# Use your current AWS profile directly (no role assumption):
idea-app provide-role --use-profile

# Longer session (2 hours):
idea-app provide-role --duration 7200
```

!!! note
    This command is only relevant for web app projects that use a dev container. The `.aws-dev/` directory is git-ignored.
