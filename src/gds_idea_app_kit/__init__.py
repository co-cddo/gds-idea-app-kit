"""GDS IDEA App Kit - CLI tool for scaffolding and maintaining web apps on AWS."""

from importlib.metadata import version

__version__ = version("gds-idea-app-kit")

# Default Python version for new projects. Update this when a new stable CPython is released.
DEFAULT_PYTHON_VERSION = "3.13"

# GitHub org used in printed instructions for repo creation.
GITHUB_ORG = "co-cddo"

# Prefix applied to all generated project directories: gds-idea-app-{name}
REPO_PREFIX = "gds-idea-app"
