"""GDS IDEA App Kit - CLI tool for scaffolding and maintaining CDK projects on AWS."""

from importlib.metadata import version

__version__ = version("gds-idea-app-kit")

# Default Python version for new projects. Update this when a new stable CPython is released.
DEFAULT_PYTHON_VERSION = "3.13"

# GitHub org used in printed instructions for repo creation.
GITHUB_ORG = "co-cddo"

# Prefix applied to all generated project directories: gds-idea-app-{name}
REPO_PREFIX = "gds-idea-app"

# Prefix applied to generated Python package project directories: gds-idea-pkg-{name}
PKG_REPO_PREFIX = "gds-idea-pkg"

# Web frameworks that produce a containerised web app with devcontainer and
# dev-mock support.  The "infra" project type is infrastructure-only and
# skips all of these extras.
WEB_FRAMEWORKS = {"streamlit", "dash", "fastapi"}
