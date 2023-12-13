from os import path
from constructs import Construct
from aws_cdk import (
    Stack,
    Tags,
    Duration,
    aws_lambda,
    aws_lambda_python_alpha,
    aws_apigatewayv2_alpha as apigwv2,
    aws_apigatewayv2_integrations_alpha as apigwv2_integrations,
    aws_s3,
    aws_ec2,
    aws_dynamodb,
    RemovalPolicy,
    CfnOutput,
)


class LambdaStack(Stack):
    def __init__(
        self, scope: Construct, construct_id: str, vpc: aws_ec2.Vpc, **kwargs
    ) -> None:
        super().__init__(scope, construct_id, **kwargs)

        Tags.of(self).add("stack_name", construct_id)

        bucket = aws_s3.Bucket(
            self,
            f"{construct_id}-bucket",
            block_public_access=aws_s3.BlockPublicAccess.BLOCK_ALL,
            encryption=aws_s3.BucketEncryption.S3_MANAGED,
            removal_policy=RemovalPolicy.DESTROY,
            lifecycle_rules=[
                aws_s3.LifecycleRule(
                    id=f"{construct_id}-s3-lifecycle-rule", expiration=Duration.days(1)
                )
            ],
        )

        ddb_table = aws_dynamodb.Table(
            self,
            f"{construct_id}-table",
            partition_key=aws_dynamodb.Attribute(
                name="id", type=aws_dynamodb.AttributeType.STRING
            ),
            removal_policy=RemovalPolicy.DESTROY,
            billing_mode=aws_dynamodb.BillingMode.PAY_PER_REQUEST,
        )

        api_lambda = aws_lambda_python_alpha.PythonFunction(
            self,
            f"{construct_id}-api-function",
            runtime=aws_lambda.Runtime.PYTHON_3_9,
            entry="../src/",
            index="app/main.py",
            handler="handler",
            memory_size=512,
            timeout=Duration.seconds(30),
            environment={
                "S3_BUCKET_NAME": bucket.bucket_name,
                "DYNAMODB_TABLE": ddb_table.table_name,
            },
            bundling=aws_lambda_python_alpha.BundlingOptions(
                asset_excludes=["Dockerfile"]
            ),
            vpc=vpc,
        )
        ddb_table.grant_write_data(api_lambda)
        bucket.grant_read_write(api_lambda)

        http_api = apigwv2.HttpApi(
            self, f"{construct_id}-httpApi", api_name=f"{construct_id}-httpApi"
        )

        lambda_integration = apigwv2_integrations.HttpLambdaIntegration(
            f"{construct_id}-lambdaIntegration", handler=api_lambda
        )

        apigwv2.HttpRoute(
            self,
            "ApiGatewayRoute",
            http_api=http_api,
            route_key=apigwv2.HttpRouteKey.with_(
                path="/{proxy+}", method=apigwv2.HttpMethod.ANY
            ),
            integration=lambda_integration,
        )

        CfnOutput(self, "HttpApiUrl", value=http_api.url)
        CfnOutput(self, "LambdaFunctionName", value=api_lambda.function_name)
