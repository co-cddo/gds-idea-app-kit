# Dev container

This directory configures the VS Code dev container for this project. It is
managed by `idea-app`; run `idea-app update` to refresh this file.

## Quick start

1. Install [VS Code](https://code.visualstudio.com/) and the
   [Dev Containers extension](https://marketplace.visualstudio.com/items?itemName=ms-vscode-remote.remote-containers).
2. Open the repository in VS Code and choose **Reopen in Container** when
   prompted (or run `Dev Containers: Reopen in Container`).
3. The first build takes a while. Later starts are quick.
4. If VS Code asks whether to allow automatic tasks, choose **Allow**. The app
   starts in a terminal called "Run app", and is available at
   <http://localhost:8080>.
5. If you need AWS access, run `idea-app provide-role` on your host. See
   `.aws-dev/README.md`.

## Running the app

The app does not run as the container's main process. The container stays up
whatever your code does, and the app runs from a VS Code task called **Run app**
(defined in `app_src/.vscode/tasks.json`). It has auto-reload switched on, so
changes you save are picked up.

If your code has an error, the traceback appears in the "Run app" terminal. Fix
the code and run the task again: **Terminal > Run Task... > Run app**. You do not
need to rebuild or restart the container.

If you declined automatic tasks, start the app yourself with that command. You
can also run any other command in a terminal in the container, for example
`uv run pytest`.

Dash: the task runs gunicorn with `--reload`. For Dash's in-browser debug tools,
stop the task and run `uv run python dash_app.py` instead.

## Configuration files

### `docker-compose.yml` - runtime configuration

This is the source of truth for runtime settings, used by both the dev
container and `idea-app smoke-test`. Edit it to:

- add environment variables (`environment`)
- change port mappings (`ports`)
- add volume mounts (`volumes`)

### `devcontainer.json` - VS Code settings

VS Code-only settings: extensions and editor configuration. Runtime settings
belong in `docker-compose.yml`.

Keep `"overrideCommand": true` in this file. It is what stops a crash in your
app from stopping the container.

Dev container `features` are not supported with the way this project builds its
image, so do not add any.

## What is mounted

| Host | Container | Notes |
|---|---|---|
| `app_src/` | `/app` | Your code. Edits apply immediately. |
| `dev_mocks/` | `/app/dev_mocks` | Mock authentication files. |
| `.aws-dev/` | `/home/appuser/.aws` | Read-only AWS credentials. |
| (volume) | `/home/appuser/.cache/uv` | uv cache, kept across rebuilds. |
| (volume) | `/app/.venv` | The container's own virtual environment. |

## Authentication in development

With `COGNITO_AUTH_DEV_MODE=true` (the default here), the app reads mock users
from `dev_mocks/` instead of calling Cognito.

## Dependencies

Edit `app_src/pyproject.toml`, then run `uv sync` in a container terminal (or
rebuild the container). A plain `uv sync` keeps the development groups: pytest
and the Zscaler TLS fix (see `default-groups` in `app_src/pyproject.toml`).
Production images are built without them.

## Common tasks

- **Rebuild the container:** `Dev Containers: Rebuild Container`.
- **The container's packages look stale:** the `/app/.venv` volume can outlive
  changes. Run `docker compose -f .devcontainer/docker-compose.yml down -v`
  on the host, then reopen in the container.
- **Test the production image:** run `idea-app smoke-test` on the host.

## Further reading

- [Dev Containers documentation](https://code.visualstudio.com/docs/devcontainers/containers)
- [uv documentation](https://docs.astral.sh/uv/)
- [gds-idea-app-kit](https://github.com/co-cddo/gds-idea-app-kit)
