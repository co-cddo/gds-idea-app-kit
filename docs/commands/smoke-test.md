# idea-app smoke-test

Build and health-check the production Docker image locally.

## Usage

```bash
idea-app smoke-test [--build-only] [--wait]
```

Run this from inside a web app project directory.

## Options

| Option | Description |
|---|---|
| `--build-only` | Only build the Docker image, skip the health check |
| `--wait` | Keep the container running after the health check passes (press Enter to stop) |

## What it does

1. Builds the production Docker image using `docker compose`
2. Starts the container
3. Polls the health endpoint until it responds (or times out)
4. Reports success or failure
5. Stops the container (unless `--wait` is used)

## Health check endpoints

| Framework | Endpoint |
|---|---|
| Streamlit | `/_stcore/health` |
| Dash | `/health` |
| FastAPI | `/health` |

## Examples

```bash
# Full build + health check:
idea-app smoke-test

# Just verify the image builds:
idea-app smoke-test --build-only

# Build, check, then keep running for manual testing:
idea-app smoke-test --wait
# App is now running at http://localhost:8080
# Press Enter to stop
```

!!! note
    This command is only available for web app projects (streamlit, dash, fastapi). It requires Docker and Docker Compose.
