#!/usr/bin/env python3
import os

import aws_cdk as cdk
from gds_idea_cdk_constructs import AppConfig, DeploymentConfig, IdeaTags

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

stack = cdk.Stack(app, f"{app_config.app_name}-stack", env=cdk_env)

# Add your infrastructure here
# Example:
#   from aws_cdk import aws_s3 as s3
#   s3.Bucket(stack, "MyBucket")

app.synth()
