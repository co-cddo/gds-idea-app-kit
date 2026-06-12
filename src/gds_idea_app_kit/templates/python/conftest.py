"""Shared test configuration and fixtures."""


def pytest_configure(config):
    """Register custom markers."""
    config.addinivalue_line("markers", "integration: tests that require external services")
