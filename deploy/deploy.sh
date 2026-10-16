#!/usr/bin/env bash
# Deploy the stack, then build the image and push it to ECR.
# Re-run after any code change; the next scheduled run picks up the new image.
set -euo pipefail

STACK=${STACK:-genai-post}
SCHEDULE=${SCHEDULE:-"cron(0 9 * * ? *)"}
TIMEZONE=${TIMEZONE:-UTC}
DRY_RUN=${DRY_RUN:-true}

cd "$(dirname "$0")/.."

VPC=$(aws ec2 describe-vpcs --filters Name=is-default,Values=true --query 'Vpcs[0].VpcId' --output text)
if [[ "$VPC" == "None" ]]; then
  echo "No default VPC in this region." >&2
  exit 1
fi
SUBNETS=$(aws ec2 describe-subnets --filters Name=vpc-id,Values="$VPC" Name=default-for-az,Values=true \
  --query 'Subnets[].SubnetId' --output text | tr '\t' ',')

aws cloudformation deploy \
  --stack-name "$STACK" \
  --template-file deploy/template.yaml \
  --capabilities CAPABILITY_IAM \
  --no-fail-on-empty-changeset \
  --parameter-overrides \
    VpcId="$VPC" \
    SubnetIds="$SUBNETS" \
    "ScheduleExpression=$SCHEDULE" \
    ScheduleTimezone="$TIMEZONE" \
    DryRun="$DRY_RUN"

REPO=$(aws cloudformation describe-stacks --stack-name "$STACK" \
  --query "Stacks[0].Outputs[?OutputKey=='RepositoryUri'].OutputValue" --output text)

aws ecr get-login-password | docker login --username AWS --password-stdin "${REPO%%/*}"
docker build --platform linux/arm64 -t "$REPO:latest" .
docker push "$REPO:latest"

echo "Deployed. Image: $REPO:latest"
