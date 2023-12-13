#!/usr/bin/env python3

import aws_cdk as cdk
import os

from templates.shared_infra_stack import SharedInfraStack
from templates.ec2_stack import Ec2Stack
from templates.ecs_stack import EcsStack
from templates.lambda_stack import LambdaStack
from templates.ec2_k6_stack import Ec2K6Stack


app = cdk.App()
env = cdk.Environment(
    account=os.environ["CDK_DEFAULT_ACCOUNT"],
    region=os.environ["CDK_DEFAULT_REGION"],
)
shared_infra_stack = SharedInfraStack(app, "cost-comparison-shared-infra", env=env)

ec2_stack = Ec2Stack(
    app,
    "cost-comparison-ec2",
    env=env,
    vpc=shared_infra_stack.vpc,
    vpc_link=shared_infra_stack.vpc_link,
)
ecs_stack = EcsStack(
    app,
    "cost-comparison-ecs",
    env=env,
    vpc=shared_infra_stack.vpc,
    vpc_link=shared_infra_stack.vpc_link,
)
lambda_stack = LambdaStack(
    app, "cost-comparison-lambda", env=env, vpc=shared_infra_stack.vpc
)
ec2_k6_stack = Ec2K6Stack(
    app, "cost-comparison-ec2-k6", env=env, vpc=shared_infra_stack.vpc
)

ec2_k6_stack.add_dependency(ec2_stack)
ec2_k6_stack.add_dependency(ecs_stack)
ec2_k6_stack.add_dependency(lambda_stack)

app.synth()
