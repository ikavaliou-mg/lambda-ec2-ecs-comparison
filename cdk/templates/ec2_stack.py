from os import path
from constructs import Construct
from aws_cdk import (
    Stack,
    Tags,
    Duration,
    aws_ec2,
    aws_autoscaling,
    aws_elasticloadbalancingv2 as elb2,
    aws_apigatewayv2_alpha as apigwv2,
    aws_apigatewayv2_integrations_alpha as apigwv2_integrations,
    aws_s3,
    aws_dynamodb,
    aws_cloudwatch,
    RemovalPolicy,
    CfnOutput,
)


class Ec2Stack(Stack):
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

        ec2_sg = aws_ec2.SecurityGroup(
            self, f"{construct_id}-ec2", vpc=vpc, allow_all_outbound=True
        )

        asg = aws_autoscaling.AutoScalingGroup(
            self,
            f"{construct_id}-ASG",
            vpc=vpc,
            instance_type=aws_ec2.InstanceType.of(
                aws_ec2.InstanceClass.M6G, aws_ec2.InstanceSize.MEDIUM
            ),
            machine_image=aws_ec2.MachineImage.latest_amazon_linux2023(
                cpu_type=aws_ec2.AmazonLinuxCpuType.ARM_64
            ),
            allow_all_outbound=True,
            health_check=aws_autoscaling.HealthCheck.ec2(),
            security_group=ec2_sg,
            desired_capacity=2,
            min_capacity=2,
            max_capacity=50,
            group_metrics=[aws_autoscaling.GroupMetrics.all()],
            instance_monitoring=aws_autoscaling.Monitoring.DETAILED,
            init=aws_ec2.CloudFormationInit.from_elements(
                aws_ec2.InitFile.from_asset(
                    "/tmp/imported/requirements.txt", "../src/requirements.txt"
                ),
                aws_ec2.InitFile.from_asset(
                    "/tmp/imported/main.py", "../src/app/main.py"
                ),
                aws_ec2.InitFile.from_asset(
                    "/tmp/imported/init.sh", "ec2_scripts/ec2_scenario/init.sh"
                ),
                aws_ec2.InitCommand.shell_command("chmod 755 tmp/imported/init.sh"),
                aws_ec2.InitCommand.shell_command(
                    f"tmp/imported/init.sh {bucket.bucket_name} {ddb_table.table_name}"
                ),
            ),
            signals=aws_autoscaling.Signals.wait_for_all(timeout=Duration.minutes(5)),
        )

        max_cpu_metric = aws_cloudwatch.Metric(
            metric_name="CPUUtilization",
            namespace="AWS/EC2",
            dimensions_map={"AutoScalingGroupName": asg.auto_scaling_group_name},
            period=Duration.minutes(1),
            statistic=aws_cloudwatch.Stats.MAXIMUM,
        )
        asg.scale_on_metric(
            "KeepSpareCPU",
            metric=max_cpu_metric,
            scaling_steps=[
                aws_autoscaling.ScalingInterval(upper=15, change=-3),
                aws_autoscaling.ScalingInterval(upper=25, change=-1),
                aws_autoscaling.ScalingInterval(lower=40, change=+1),
                aws_autoscaling.ScalingInterval(lower=60, change=+3),
                aws_autoscaling.ScalingInterval(lower=80, change=+5),
            ],
            cooldown=Duration.seconds(60),
            estimated_instance_warmup=Duration.seconds(60),
            adjustment_type=aws_autoscaling.AdjustmentType.CHANGE_IN_CAPACITY,
        )

        ddb_table.grant_write_data(asg.role)
        bucket.grant_read_write(asg.role)

        lb = elb2.ApplicationLoadBalancer(
            self, f"{construct_id}-LB", vpc=vpc, internet_facing=False
        )
        listener = lb.add_listener(
            f"{construct_id}-Listener",
            port=80,
        )
        listener.add_targets(
            "ApplicationFleet",
            port=80,
            targets=[asg],
            health_check=elb2.HealthCheck(
                path="/health",
                unhealthy_threshold_count=10,
                timeout=Duration.seconds(30),
                interval=Duration.seconds(60),
            ),
        )

        http_api = apigwv2.HttpApi(
            self, f"{construct_id}-httpApi", api_name=f"{construct_id}-httpApi"
        )

        alb_gateway_integration = apigwv2_integrations.HttpAlbIntegration(
            f"{construct_id}-albIntegration",
            listener=listener,
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
        CfnOutput(self, "ASGName", value=asg.auto_scaling_group_name)
