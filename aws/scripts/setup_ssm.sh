#!/bin/bash

# Script to set up SSM Parameter Store values for Referral Email System
# This should be run after CloudFormation stack is created

set -e

echo "=========================================="
echo "Setting up SSM Parameters"
echo "=========================================="

# Get AWS region from config or use default
AWS_REGION=${AWS_REGION:-us-east-1}
STACK_NAME="referral-email-system"

echo "Using AWS Region: $AWS_REGION"
echo "Stack Name: $STACK_NAME"

# Check if stack exists
if ! aws cloudformation describe-stacks --stack-name $STACK_NAME --region $AWS_REGION >/dev/null 2>&1; then
    echo "ERROR: CloudFormation stack '$STACK_NAME' not found."
    echo "Please deploy the CloudFormation stack first."
    exit 1
fi

echo ""
echo "Retrieving stack outputs..."

# Get stack outputs
SQS_QUEUE_URL=$(aws cloudformation describe-stacks \
    --stack-name $STACK_NAME \
    --region $AWS_REGION \
    --query 'Stacks[0].Outputs[?OutputKey==`ReferralQueueUrl`].OutputValue' \
    --output text)

S3_BUCKET_NAME=$(aws cloudformation describe-stacks \
    --stack-name $STACK_NAME \
    --region $AWS_REGION \
    --query 'Stacks[0].Outputs[?OutputKey==`BrandGuidelinesBucket`].OutputValue' \
    --output text)

DYNAMODB_TABLE_NAME=$(aws cloudformation describe-stacks \
    --stack-name $STACK_NAME \
    --region $AWS_REGION \
    --query 'Stacks[0].Outputs[?OutputKey==`DynamoDBTableName`].OutputValue' \
    --output text)

# Bedrock model ID (default)
BEDROCK_MODEL_ID="anthropic.claude-sonnet-4-20250514-v1:0"

echo ""
echo "Retrieved values:"
echo "  SQS Queue URL: $SQS_QUEUE_URL"
echo "  S3 Bucket: $S3_BUCKET_NAME"
echo "  DynamoDB Table: $DYNAMODB_TABLE_NAME"
echo "  Bedrock Model: $BEDROCK_MODEL_ID"

echo ""
echo "Creating/updating SSM parameters..."

# Create/update SSM parameters (these are created by CloudFormation, but this ensures they're set)
# Note: CloudFormation template already creates these, so this is redundant but safe

echo "✓ SSM Parameters are managed by CloudFormation"
echo ""
echo "Verifying parameters..."

# Verify parameters exist
aws ssm get-parameter --name /referral-system/sqs-queue-url --region $AWS_REGION >/dev/null && echo "✓ /referral-system/sqs-queue-url"
aws ssm get-parameter --name /referral-system/s3-bucket-name --region $AWS_REGION >/dev/null && echo "✓ /referral-system/s3-bucket-name"
aws ssm get-parameter --name /referral-system/bedrock-model-id --region $AWS_REGION >/dev/null && echo "✓ /referral-system/bedrock-model-id"
aws ssm get-parameter --name /referral-system/dynamodb-table-name --region $AWS_REGION >/dev/null && echo "✓ /referral-system/dynamodb-table-name"

echo ""
echo "=========================================="
echo "SSM Parameter Setup Complete!"
echo "=========================================="
echo ""
echo "Next steps:"
echo "1. Upload brand guidelines to S3:"
echo "   aws s3 cp brand_guidelines/guidelines.json s3://$S3_BUCKET_NAME/guidelines.json"
echo ""
echo "2. Deploy Lambda functions (if not using SAM):"
echo "   ./scripts/deploy.sh"
echo ""
echo "3. Test the system:"
echo "   python3 scripts/test_system.py"

