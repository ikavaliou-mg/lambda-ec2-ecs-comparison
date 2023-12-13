from os import path
from constructs import Construct
from aws_cdk import Stack, Tags, aws_ec2, aws_apigatewayv2_alpha as apigwv2


class SharedInfraStack(Stack):
    def __init__(self, scope: Construct, construct_id: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)
        vpc: aws_ec2.Vpc
        vpc_link: apigwv2.VpcLink

        Tags.of(self).add("stack_name", construct_id)
        self.vpc = aws_ec2.Vpc(self, f"{construct_id}-Vpc", max_azs=2)

        self.vpc_link = apigwv2.VpcLink(
            self,
            f"{construct_id}-APIGWVpcLinkToPrivateHTTPEndpoint",
            vpc=self.vpc,
            vpc_link_name=f"{construct_id}-APIGWVpcLinkToPrivateHTTPEndpoint",
        )
        vpc_link_sg = aws_ec2.SecurityGroup(
            self, f"{construct_id}-vpcLinkSG", vpc=self.vpc, allow_all_outbound=True
        )
        vpc_link_sg.add_ingress_rule(aws_ec2.Peer.any_ipv4(), aws_ec2.Port.tcp(80))
        vpc_link_sg.add_ingress_rule(aws_ec2.Peer.any_ipv4(), aws_ec2.Port.tcp(443))
        self.vpc_link.add_security_groups(vpc_link_sg)
