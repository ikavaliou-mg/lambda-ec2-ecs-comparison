#!/bin/bash
sudo yum -y update
sudo yum -y upgrade

echo "Installing go..."
sudo wget -q https://go.dev/dl/go1.21.3.linux-amd64.tar.gz 
sudo tar -xf go1.21.3.linux-amd64.tar.gz
export GOPATH=/home
export GOCACHE=/go/cache
export PATH=/go/bin:$PATH
echo "export GOPATH=/home" >> ~/.bash_profile
echo "export GOCACHE=/go/cache" >> ~/.bash_profile
echo "export PATH=/go/bin:$PATH" >> ~/.bash_profile
source ~/.bashrc
echo $PATH

echo "Installing k6..."
sudo yum -y install https://dl.k6.io/rpm/repo.rpm
sudo yum -y install k6 --nogpgcheck

echo "Installing xk6..."
go version
go install go.k6.io/xk6/cmd/xk6@latest
export PATH=$(go env GOPATH)/bin:$PATH
echo "export PATH=/go/bin:$PATH" >> ~/.bash_profile
source ~/.bashrc

echo "Building xk6 for statsd output..."
sudo mkdir /testing
cd /testing
sudo chown -R ec2-user /testing
xk6 build --with github.com/LeonAdato/xk6-output-statsd
sudo cp /tmp/imported/script-template.js script-template.js
sudo cp /tmp/imported/dashboard-template.json dashboard-template.json
sudo cp /tmp/imported/run_k6.sh run_k6.sh
sudo sysctl -w net.ipv4.ip_local_port_range="1024 65535"
sudo sysctl -w net.ipv4.tcp_tw_reuse=1
sudo sysctl -w net.ipv4.tcp_timestamps=1
sudo ulimit -n 250000

echo "Installing amazon-cloudwatch-agent..."
sudo yum -y install amazon-cloudwatch-agent
cd /opt/aws/amazon-cloudwatch-agent/etc/
sudo cp /tmp/imported/statsd.json statsd.json
amazon-cloudwatch-agent-ctl -a fetch-config -m ec2 -s -c file:/opt/aws/amazon-cloudwatch-agent/etc/statsd.json
amazon-cloudwatch-agent-ctl -a status