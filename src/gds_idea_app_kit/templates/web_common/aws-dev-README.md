# AWS dev container credentials

This directory holds temporary AWS credentials for the dev container. It is
managed by `idea-app`; run `idea-app update` to refresh this file.

## How it works

1. On your **host machine** (not inside the container), sign in to AWS and make
   sure `AWS_PROFILE` is set to the profile you want to use.
2. Run `idea-app provide-role`. If the project has a dev role configured under
   `[tool.webapp.dev]` in `pyproject.toml`, it assumes that role. Otherwise, or
   with `--use-profile`, it passes your current profile's credentials through.
3. The credentials are written to `credentials` and `config` in this directory.
4. This directory is mounted read-only into the dev container at
   `/home/appuser/.aws/`, so the AWS CLI and SDKs in the container pick the
   credentials up automatically.

The mount is live, so you can run `idea-app provide-role` before or after the
container starts, and refresh credentials without restarting it.

## Files

- `credentials` - temporary access key, secret key and session token
- `config` - region and output format

Both are generated. Do not edit them by hand.

## Security

- Everything in this directory is git-ignored except this README.
- Credentials are temporary. A role assumed by `provide-role` lasts 1 hour by
  default (change it with `--duration`). With `--use-profile`, they last as long
  as your profile's session.
- The container mounts them read-only.
- Credentials exist only on your machine.

## Refreshing

When the credentials expire, sign in again on the host and re-run
`idea-app provide-role`.
