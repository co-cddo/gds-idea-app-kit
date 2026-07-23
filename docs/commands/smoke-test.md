# idea-app smoke-test

Build and check the production Docker image locally.

## Usage

```bash
idea-app smoke-test [--build-only] [--wait]
```

Run this from inside a web app or static site project directory.

## Options

| Option | Description |
|---|---|
| `--build-only` | Only build the Docker image, skip the health check |
| `--wait` | Keep the container running after the health check passes (press Enter to stop) |

## What it does

1. Builds the Docker image using `docker compose` (production target for web apps, development target for static sites — see [note](#static-sites) below)
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
| Static site | `/` (site root) |

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
    This command requires Docker and Docker Compose.

## Static sites

Static site projects have no "production" Docker stage — the deployed artifact is a Lambda function that runs a build command once, not a long-running container. `idea-app smoke-test` builds and runs the **development** target instead (the same one used by the devcontainer) and checks that the site root responds with `200`.

This validates that:

- The Eleventy config and plugins load correctly (catches import errors, missing options, version mismatches)
- The site actually renders and serves at `http://localhost:8080/`

It does **not** exercise the `build` target's Lambda-specific environment (Node install method, `ELEVENTY_OUTPUT_DIR`, container-image base). For full confidence before deploying, also run:

```bash
docker build --target build -t smoke-test-build site_src/
docker run --rm --entrypoint bash smoke-test-build -c "npx @11ty/eleventy"
```
