#!/bin/bash
sudo yum update -y
sudo dnf install --assumeyes python3-pip

echo $1
echo $2
export AWS_DEFAULT_REGION=ap-southeast-2
export S3_BUCKET_NAME=$1
export DYNAMODB_TABLE=$2

cd /
mkdir api
cd api
cp /tmp/imported/requirements.txt requirements.txt
cp /tmp/imported/main.py main.py

python3 -m venv .venv
. .venv/bin/activate
pip install -r requirements.txt
pip install gunicorn

gunicorn --worker-class uvicorn.workers.UvicornWorker --bind '0.0.0.0:80' --daemon main:app