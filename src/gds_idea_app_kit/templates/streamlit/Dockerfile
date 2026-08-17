# ============================================================================
# Multi-stage Dockerfile for Streamlit Application
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

# Install dependencies (as non-root user)
RUN uv sync

# Copy application code
COPY --chown=$USERNAME:$USERNAME app_src/ .

EXPOSE 8080

CMD ["uv", "run", "streamlit", "run", "streamlit_app.py", \
     "--server.port", "8080", \
     "--server.address", "0.0.0.0", \
     "--server.headless", "true", \
     "--server.enableCORS", "false", \
     "--browser.gatherUsageStats", "false"]

# ============================================================================
# Development stage - for dev containers (NOT DEFAULT)
# ============================================================================
FROM base AS development

# Switch back to root to install dev-only packages
USER root

# Grant passwordless sudo for development flexibility
RUN apt-get update \
    && apt-get install -y --no-install-recommends sudo \
    && rm -rf /var/lib/apt/lists/* \
    && echo $USERNAME ALL=\(root\) NOPASSWD:ALL > /etc/sudoers.d/$USERNAME \
    && chmod 0440 /etc/sudoers.d/$USERNAME

USER $USERNAME

# Zscaler TLS fix - development stage only, never production.
# The corporate Zscaler proxy re-signs HTTPS with its own CA, which
# Python doesn't trust by default (unlike curl/apt, which do). This
# installs a fix that makes Python trust it. It works by relaxing one
# certificate validation check, so it must never ship in production
# images - hence it's only ever installed here, in the development
# stage, which the production stage below does not build from.
# https://github.com/co-cddo/gds-idea-pkg-zscaler-fix
RUN uv pip install "gds-idea-pkg-zscaler-fix>=0.1.2" \
      --index https://co-cddo.github.io/gds-idea-pypi/simple/

# Wrap the app command so a crash (e.g. a bug introduced while coding)
# doesn't kill the container before you get a chance to see why. On
# failure this prints the exit code and where to look, then keeps the
# container alive briefly so VS Code can still attach and `docker compose
# logs` / `docker logs` stay queryable. Signals are forwarded to the app
# so `docker compose down`/stop still shut down promptly on the happy path.
CMD ["/bin/sh", "-c", "trap 'kill -TERM $PID 2>/dev/null; STOPPING=1' TERM INT; uv run streamlit run streamlit_app.py --server.port 8080 --server.address 0.0.0.0 --server.headless true --server.enableCORS false --browser.gatherUsageStats false & PID=$!; wait $PID; code=$?; if [ $code -ne 0 ] && [ -z \"$STOPPING\" ]; then echo; echo \"=== App failed to start (exit code $code) ===\"; echo 'Traceback is above. Full logs: docker compose -f .devcontainer/docker-compose.yml logs app'; echo 'After fixing, restart with: docker compose -f .devcontainer/docker-compose.yml restart app'; echo 'Container will stay up for 5 minutes so you can attach and inspect.'; sleep 300; fi; exit $code"]

# ============================================================================
# Production stage - secure, minimal, non-root (DEFAULT)
# ============================================================================
FROM base AS production
