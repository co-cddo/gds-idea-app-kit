def test_cdk_dependencies_installed():
    """Verify CDK dependencies are correctly installed."""
    from gds_idea_cdk_constructs import AppConfig, DeploymentConfig  # noqa: F401
    from gds_idea_cdk_constructs.web_app import WebApp  # noqa: F401
