#!/usr/bin/env python3
import os

import aws_cdk as cdk
from aws_cdk import Duration
from aws_cdk import aws_events as events
from gds_idea_cdk_constructs import AppConfig, DeploymentConfig, IdeaTags
from gds_idea_cdk_constructs.static_site import AuthType, StaticSite, StaticSiteProperties

app = cdk.App()
cdk_env = cdk.Environment(
    account=os.environ["CDK_DEFAULT_ACCOUNT"],
    region=os.environ["CDK_DEFAULT_REGION"],
)

app_config = AppConfig.from_pyproject()
dep_config = DeploymentConfig(cdk_env)

IdeaTags(
    environment=dep_config.environment,
    app_name=app_config.app_name,
    repository="{{repository}}",
    # owners=["Your Name"],  # optional: names, not email addresses
).apply(app)

stack = StaticSite(
    app,
    deployment_config=dep_config,
    app_config=app_config,
    authentication=AuthType.INTERNAL_ACCESS,
    docker_context_path="site_src",
    dockerfile_path="Dockerfile",
    static_site_props=StaticSiteProperties(
        build_command="npx @11ty/eleventy",
        build_schedule=events.Schedule.rate(Duration.hours(6)),
    ),
)
app.synth()
