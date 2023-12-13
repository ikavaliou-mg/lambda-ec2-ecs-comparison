## Description

This project is used to compare AWS offerings for API deployment.

The project contains a sample solution utilising Python FastAPI with an endpoint used to write to DynamoDb and S3 bucket.

It is deliberately using the same codebase in three CDK stacks to deploy isolated APIs using AWS Lambda, Amazon ECS, and Amazon EC2 services. The code is not optimised for any of those solutions in order to demonstrate a capability of easy migrations.

## Pre-requisites

- Python 3.9, pip3
- NodeJs, npm
- k6
- Colima, docker
- CLI access to AWS environment (e.g. `aws sso login`)

## Setup

Create a virtual environment from the root:

```
python3 -m venv .venv
. .venv/bin/activate
```

Install dependencies for cdk:

```
pip install -r requirements.txt
```

Navigate to `src` folder and install dependencies for the main application:

```
cd src
pip install -r requirements.txt
```

Navigate to `cdk` folder and make sure CDK templates can be sythesized:

```
cd ../cdk
cdk synth
```

Deploy stacks using `cdk deploy` command followed by name of the stack (e.g. `cdk deploy cost-comparison-ec2-k6`) or `--all`
`cost-comparison-ec2-k6` stack should be deployed last or once all other stacks exist

## Load Testing

Open the AWS terminal, connect to the `cost-comparison-ec2-k6` EC2 instance, and run the following command:

```
. /testing/run_k6.sh
```

Take a note of the Execution ID (in the format YYYYMMDD-HHMMSS UTC time) and use it as a filter in CloudWatch dashboard called "cost-comparison"

For long-term running tests, use screen to run as a background service:

```
screen -d -m ./testing/run_k6.sh
```
