#!/bin/bash
cd /testing
EC2_API_URL=$(aws cloudformation describe-stacks --stack-name cost-comparison-ec2 --region ap-southeast-2 --query 'Stacks[0].Outputs[?OutputKey==`HttpApiUrl`].OutputValue' --output text)
ECS_API_URL=$(aws cloudformation describe-stacks --stack-name cost-comparison-ecs --region ap-southeast-2 --query 'Stacks[0].Outputs[?OutputKey==`HttpApiUrl`].OutputValue' --output text)
LAMBDA_API_URL=$(aws cloudformation describe-stacks --stack-name cost-comparison-lambda --region ap-southeast-2 --query 'Stacks[0].Outputs[?OutputKey==`HttpApiUrl`].OutputValue' --output text)

ECS_SERVICE_NAME=$(aws cloudformation describe-stacks --stack-name cost-comparison-ecs --region ap-southeast-2 --query 'Stacks[0].Outputs[?OutputKey==`EcsServiceName`].OutputValue' --output text)
ECS_CLUSTER_NAME=$(aws cloudformation describe-stacks --stack-name cost-comparison-ecs --region ap-southeast-2 --query 'Stacks[0].Outputs[?OutputKey==`EcsClusterName`].OutputValue' --output text)
EC2_ASG_NAME=$(aws cloudformation describe-stacks --stack-name cost-comparison-ec2 --region ap-southeast-2 --query 'Stacks[0].Outputs[?OutputKey==`ASGName`].OutputValue' --output text)
LAMBDA_FUNCTION_NAME=$(aws cloudformation describe-stacks --stack-name cost-comparison-lambda --region ap-southeast-2 --query 'Stacks[0].Outputs[?OutputKey==`LambdaFunctionName`].OutputValue' --output text)
SERVER_HOSTNAME=$(hostname)

sudo sh -c "sed -e 's@EC2_API_URL@$EC2_API_URL@g ; s@ECS_API_URL@$ECS_API_URL@g ; s@LAMBDA_API_URL@$LAMBDA_API_URL@g ; s@ECS_SERVICE_NAME@$ECS_SERVICE_NAME@g ; s@ECS_CLUSTER_NAME@$ECS_CLUSTER_NAME@g ; s@EC2_ASG_NAME@$EC2_ASG_NAME@g ; s@LAMBDA_FUNCTION_NAME@$LAMBDA_FUNCTION_NAME@g ; s@SERVER_HOSTNAME@$SERVER_HOSTNAME@g' dashboard-template.json > dashboard.json"
aws cloudwatch put-dashboard --dashboard-name cost-comparison --dashboard-body file://dashboard.json --region ap-southeast-2

EXECUTION_ID=$(date +'%Y%m%d-%H%M%S')
sudo sh -c "sed -e 's@EXECUTION_ID@$EXECUTION_ID@g ; s@EC2_API_URL@$EC2_API_URL@g ; s@ECS_API_URL@$ECS_API_URL@g ; s@LAMBDA_API_URL@$LAMBDA_API_URL@g' script-template.js > script.js"
echo "**********************************************************"
echo "Use Execution ID $EXECUTION_ID to filter CloudWatch metrics"
echo "**********************************************************"
K6_STATSD_ENABLE_TAGS=true ./k6 run --out output-statsd script.js --no-thresholds --no-summary