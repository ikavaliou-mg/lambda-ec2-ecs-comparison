from os import path
from constructs import Construct
from aws_cdk import (
    Stack,
    Tags,
    aws_ecs_patterns,
    aws_ecs,
    aws_ec2,
    aws_apigatewayv2_alpha as apigwv2,
    aws_apigatewayv2_integrations_alpha as apigwv2_integrations,
    aws_s3,
    aws_dynamodb,
    aws_cloudwatch,
    aws_applicationautoscaling,
    RemovalPolicy,
    CfnOutput,
    Duration,
)


class EcsStack(Stack):
    def __init__(
        self,
        scope: Construct,
        construct_id: str,
        vpc: aws_ec2.Vpc,
        vpc_link=apigwv2.VpcLink,
        **kwargs,
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

        cluster = aws_ecs.Cluster(
            self, f"{construct_id}-EcsCluster", vpc=vpc, container_insights=True
        )

        image = aws_ecs_patterns.ApplicationLoadBalancedTaskImageOptions(
            image=aws_ecs.ContainerImage.from_asset(
                directory="../src",
            ),
            environment={
                "S3_BUCKET_NAME": bucket.bucket_name,
                "DYNAMODB_TABLE": ddb_table.table_name,
            },
        )

        load_balanced_fargate_service = (
            aws_ecs_patterns.ApplicationLoadBalancedFargateService(
                self,
                f"{construct_id}-service",
                cluster=cluster,
                desired_count=2,
                cpu=1024,
                memory_limit_mib=2048,
                task_image_options=image,
                load_balancer_name=f"{construct_id}-alb",
                public_load_balancer=False,
                runtime_platform=aws_ecs.RuntimePlatform(
                    operating_system_family=aws_ecs.OperatingSystemFamily.LINUX,
                    cpu_architecture=aws_ecs.CpuArchitecture.ARM64,
                ),
            )
        )
        scaling = load_balanced_fargate_service.service.auto_scale_task_count(
            min_capacity=2, max_capacity=50
        )
        max_cpu_metric = aws_cloudwatch.Metric(
            metric_name="CPUUtilization",
            namespace="AWS/ECS",
            dimensions_map={
                "ServiceName": load_balanced_fargate_service.service.service_name,
                "ClusterName": load_balanced_fargate_service.cluster.cluster_name,
            },
            period=Duration.minutes(1),
            statistic=aws_cloudwatch.Stats.MAXIMUM,
        )
        scaling.scale_on_metric(
            "KeepSpareCPU",
            metric=max_cpu_metric,
            scaling_steps=[
                aws_applicationautoscaling.ScalingInterval(upper=15, change=-3),
                aws_applicationautoscaling.ScalingInterval(upper=25, change=-1),
                aws_applicationautoscaling.ScalingInterval(lower=40, change=+1),
                aws_applicationautoscaling.ScalingInterval(lower=60, change=+3),
                aws_applicationautoscaling.ScalingInterval(lower=80, change=+5),
            ],
            cooldown=Duration.seconds(60),
            adjustment_type=aws_applicationautoscaling.AdjustmentType.CHANGE_IN_CAPACITY,
            datapoints_to_alarm=1,
        )
        load_balanced_fargate_service.target_group.configure_health_check(
            path="/health",
            unhealthy_threshold_count=10,
            timeout=Duration.seconds(30),
            interval=Duration.seconds(60),
        )
        ddb_table.grant_write_data(
            load_balanced_fargate_service.task_definition.task_role
        )
        bucket.grant_read_write(load_balanced_fargate_service.task_definition.task_role)

        http_api = apigwv2.HttpApi(
            self, f"{construct_id}-httpApi", api_name=f"{construct_id}-httpApi"
        )

        alb_gateway_integration = apigwv2_integrations.HttpAlbIntegration(
            f"{construct_id}-albIntegration",
            listener=load_balanced_fargate_service.listener,
            method=apigwv2.HttpMethod.ANY,
            vpc_link=vpc_link,
        )

        apigwv2.HttpRoute(
            self,
            "ApiGatewayRoute",
            http_api=http_api,
            route_key=apigwv2.HttpRouteKey.with_(
                path="/{proxy+}", method=apigwv2.HttpMethod.ANY
            ),
            integration=alb_gateway_integration,
        )

        CfnOutput(self, "HttpApiUrl", value=http_api.url)
        CfnOutput(
            self,
            "EcsServiceName",
            value=load_balanced_fargate_service.service.service_name,
        )
        CfnOutput(
            self,
            "EcsClusterName",
            value=load_balanced_fargate_service.cluster.cluster_name,
        )
