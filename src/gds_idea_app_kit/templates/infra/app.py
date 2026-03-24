#!/usr/bin/env python3
import os

import aws_cdk as cdk
from aws_cdk import (
    Tags,
)
from gds_idea_cdk_constructs import AppConfig, DeploymentConfig

app = cdk.App()

cdk_env = cdk.Environment(
    account=os.environ["CDK_DEFAULT_ACCOUNT"],
    region=os.environ["CDK_DEFAULT_REGION"],
)

app_config = AppConfig.from_pyproject()
dep_config = DeploymentConfig(cdk_env)

stack = cdk.Stack(app, f"{app_config.app_name}-stack", env=cdk_env)

# Add your infrastructure here
# Example:
#   from aws_cdk import aws_s3 as s3
#   s3.Bucket(stack, "MyBucket")

Tags.of(app).add("Environment", dep_config.environment.friendly_name)
Tags.of(app).add("ManagedBy", "cdk")
Tags.of(app).add("Repository", "TBA")
Tags.of(app).add("AppName", app_config.app_name)

app.synth()
