def test_app_imports():
    """Verify the application module is importable."""
    import dash_app  # noqa: F401


def test_health_without_auth_headers():
    """The load balancer health check has no login headers and must still return 200."""
    import dash_app

    response = dash_app.server.test_client().get("/health")
    assert response.status_code == 200
