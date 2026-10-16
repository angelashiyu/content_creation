#!/usr/bin/env bash
# Start one pipeline run now instead of waiting for the schedule.
set -euo pipefail

STACK=${STACK:-genai-post}

output() {
  aws cloudformation describe-stacks --stack-name "$STACK" \
    --query "Stacks[0].Outputs[?OutputKey=='$1'].OutputValue" --output text
}

VPC=$(aws ec2 describe-vpcs --filters Name=is-default,Values=true --query 'Vpcs[0].VpcId' --output text)
SUBNETS=$(aws ec2 describe-subnets --filters Name=vpc-id,Values="$VPC" Name=default-for-az,Values=true \
  --query 'Subnets[].SubnetId' --output text | tr '\t' ',')

aws ecs run-task \
  --cluster "$(output ClusterName)" \
  --task-definition "$(output TaskDefinitionArn)" \
  --launch-type FARGATE \
  --network-configuration "awsvpcConfiguration={subnets=[$SUBNETS],securityGroups=[$(output SecurityGroupId)],assignPublicIp=ENABLED}" \
  --query 'tasks[0].taskArn' --output text

echo "Started. Follow the logs with: aws logs tail /ecs/genai-post --follow"
