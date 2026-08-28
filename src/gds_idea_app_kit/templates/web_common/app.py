#!/usr/bin/env python3
import os

import aws_cdk as cdk
from aws_cdk import (
    Tags,
)
from gds_idea_cdk_constructs import AppConfig, DeploymentConfig
from gds_idea_cdk_constructs.web_app import AuthType, WebApp

app = cdk.App()

cdk_env = cdk.Environment(
    account=os.environ["CDK_DEFAULT_ACCOUNT"],
    region=os.environ["CDK_DEFAULT_REGION"],
)

app_config = AppConfig.from_pyproject()
dep_config = DeploymentConfig(cdk_env)

stack_tags = {
    "Environment": dep_config.environment.friendly_name,
    "ManagedBy": "cdk",
    "Repository": "TBA",  # TODO: Set the name of this repository
    "AppName": app_config.app_name,
    "Owner": "TBA",  # TODO: Set the stack owner(s); separate multiple owners with a comma
}

for key, value in stack_tags.items():
    Tags.of(app).add(key, value)
    Tags.of(app).add(key, value, include_resource_types=["aws:cdk:stack"])


stack = WebApp(
    app,
    deployment_config=dep_config,
    app_config=app_config,
    authentication=AuthType.INTERNAL_ACCESS,
)

app.synth()
