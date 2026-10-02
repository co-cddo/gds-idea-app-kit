# ============================================================================
# Multi-stage Dockerfile for Dash Application
# ============================================================================
# Production build (default): docker build -t app .
# Dev container build:        docker build --target development -t app:dev .
# ============================================================================

# Base stage - common setup
FROM python:{{python_version}}-slim AS base

WORKDIR /app

ARG USERNAME=appuser
ARG USER_UID=1000
ARG USER_GID=$USER_UID

# Install UV (pinned to major version)
COPY --from=ghcr.io/astral-sh/uv:0.9 /uv /usr/local/bin/uv

# Create non-root user and set ownership of /app
RUN groupadd --gid $USER_GID $USERNAME \
    && useradd --uid $USER_UID --gid $USER_GID -m $USERNAME \
    && chown -R $USERNAME:$USERNAME /app

# Copy dependency files with correct ownership
COPY --chown=$USERNAME:$USERNAME app_src/pyproject.toml ./
COPY --chown=$USERNAME:$USERNAME app_src/uv.loc[k] ./

# Install minimal base packages (needed by both dev and prod)
# If your build fails with 'gcc not found' or similar compilation errors,
# uncomment build-essential below to add C/C++ compilers:
RUN apt-get update \
    && apt-get install -y --no-install-recommends \
    ca-certificates \
    git \
    # build-essential \
    && rm -rf /var/lib/apt/lists/*

# Switch to non-root user for dependency installation
USER $USERNAME

# Install production dependencies only. Default dependency groups (dev tools, the
# Zscaler fix) are excluded here so they can never reach the production image;
# the development stage adds them back below.
RUN uv sync --no-default-groups

# Copy application code
COPY --chown=$USERNAME:$USERNAME app_src/ .

EXPOSE 8080

# ============================================================================
# Development stage - for dev containers (NOT DEFAULT)
# ============================================================================
FROM base AS development

# ARG values do not carry over from the base stage, so re-declare it here.
ARG USERNAME=appuser

# Switch back to root to install dev-only packages
USER root

# Grant passwordless sudo for development flexibility
RUN apt-get update \
    && apt-get install -y --no-install-recommends sudo \
    && rm -rf /var/lib/apt/lists/* \
    && echo $USERNAME ALL=\(root\) NOPASSWD:ALL > /etc/sudoers.d/$USERNAME \
    && chmod 0440 /etc/sudoers.d/$USERNAME

USER $USERNAME

# Install the development dependency groups (pytest, and the Zscaler TLS fix).
# These are default groups in app_src/pyproject.toml, so a plain `uv sync`
# keeps them. The base stage (and therefore production) excludes them.
RUN uv sync

# The dev container does not run this command: devcontainer.json sets
# overrideCommand so a crashing app can't stop the container, and the app is
# started by the "Run app" VS Code task instead. This CMD applies when the
# development target is run directly (e.g. `docker compose up`), with reload on.
CMD ["uv", "run", "gunicorn", "dash_app:server", "-b", "0.0.0.0:8080", "--workers", "1", "--reload", "--timeout", "120", "--no-control-socket"]

# ============================================================================
# Production stage - secure, minimal, non-root (DEFAULT)
# ============================================================================
FROM base AS production

# --no-sync: run exactly what was installed at build time, never re-resolve or
# install packages when the container starts.
CMD ["uv", "run", "--no-sync", "gunicorn", "dash_app:server", "-b", "0.0.0.0:8080", "--workers", "1", "--preload", "--timeout", "120", "--no-control-socket"]
