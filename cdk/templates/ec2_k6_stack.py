from os import path
from constructs import Construct
from aws_cdk import Stack, Tags, aws_ec2, aws_iam, Duration


class Ec2K6Stack(Stack):
    def __init__(
        self, scope: Construct, construct_id: str, vpc: aws_ec2.Vpc, **kwargs
    ) -> None:
        super().__init__(scope, construct_id, **kwargs)
        Tags.of(self).add("stack_name", construct_id)

        cw_agent_role = aws_iam.Role(
            self,
            f"{construct_id}-role",
            assumed_by=aws_iam.ServicePrincipal("ec2.amazonaws.com"),
        )
        cw_agent_role.add_managed_policy(
            aws_iam.ManagedPolicy.from_aws_managed_policy_name(
                "AmazonAPIGatewayInvokeFullAccess"
            )
        )
        cw_agent_role.add_managed_policy(
            aws_iam.ManagedPolicy.from_aws_managed_policy_name(
                "CloudWatchAgentServerPolicy"
            )
        )
        cw_agent_role.add_managed_policy(
            aws_iam.ManagedPolicy.from_aws_managed_policy_name(
                "AWSCloudFormationReadOnlyAccess"
            )
        )
        cw_agent_role.add_managed_policy(
            aws_iam.ManagedPolicy.from_aws_managed_policy_name("CloudWatchFullAccess")
        )

        ec2_sg = aws_ec2.SecurityGroup(
            self, f"{construct_id}-sg", vpc=vpc, allow_all_outbound=True
        )
        ec2_sg.add_ingress_rule(aws_ec2.Peer.any_ipv4(), aws_ec2.Port.tcp(22))
        ec2_sg.add_ingress_rule(aws_ec2.Peer.any_ipv4(), aws_ec2.Port.tcp(443))

        ec2 = aws_ec2.Instance(
            self,
            f"{construct_id}-instance",
            vpc=vpc,
            vpc_subnets=aws_ec2.SubnetSelection(subnet_type=aws_ec2.SubnetType.PUBLIC),
            instance_type=aws_ec2.InstanceType.of(
                aws_ec2.InstanceClass.M4, aws_ec2.InstanceSize.LARGE
            ),
            machine_image=aws_ec2.MachineImage.latest_amazon_linux2(),
            allow_all_outbound=True,
            detailed_monitoring=True,
            role=cw_agent_role,
            security_group=ec2_sg,
            ssm_session_permissions=True,
            init=aws_ec2.CloudFormationInit.from_elements(
                aws_ec2.InitFile.from_asset(
                    "/tmp/imported/init.sh", "ec2_scripts/k6_server/init.sh"
                ),
                aws_ec2.InitFile.from_asset(
                    "/tmp/imported/statsd.json", "ec2_scripts/k6_server/statsd.json"
                ),
                aws_ec2.InitFile.from_asset(
                    "/tmp/imported/script-template.js",
                    "../load-testing/script-template.js",
                ),
                aws_ec2.InitFile.from_asset(
                    "/tmp/imported/run_k6.sh",
                    "../load-testing/run_k6.sh",
                ),
                aws_ec2.InitFile.from_asset(
                    "/tmp/imported/dashboard-template.json",
                    "../load-testing/dashboard-template.json",
                ),
                aws_ec2.InitCommand.shell_command("chmod 755 /tmp/imported/init.sh"),
                aws_ec2.InitCommand.shell_command(
                    "chmod 777 /tmp/imported/statsd.json"
                ),
                aws_ec2.InitCommand.shell_command(
                    "chmod 777 /tmp/imported/script-template.js"
                ),
                aws_ec2.InitCommand.shell_command(
                    "chmod 777 /tmp/imported/dashboard-template.json"
                ),
                aws_ec2.InitCommand.shell_command("chmod 777 /tmp/imported/run_k6.sh"),
                aws_ec2.InitCommand.shell_command(f"/tmp/imported/init.sh"),
            ),
            resource_signal_timeout=Duration.minutes(20),
        )
