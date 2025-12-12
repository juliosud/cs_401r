#!/bin/bash

set -e

STACK_NAME="referral-email-system"
REGION="us-east-1"
ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
BUCKET_NAME="referral-brand-guidelines-${ACCOUNT_ID}"
DEPLOY_BUCKET="cfn-deploy-artifacts-${ACCOUNT_ID}-${REGION}"

echo "=========================================="
echo "Cleaning Up AWS Resources"
echo "=========================================="
echo "Stack: $STACK_NAME"
echo "Region: $REGION"
echo ""

# 1. Empty S3 buckets (required before deletion)
echo "Step 1: Emptying S3 buckets..."
if aws s3 ls "s3://${BUCKET_NAME}" 2>/dev/null; then
    echo "  Emptying brand guidelines bucket..."
    aws s3 rm "s3://${BUCKET_NAME}" --recursive
    echo "  ✓ Brand guidelines bucket emptied"
fi

if aws s3 ls "s3://${DEPLOY_BUCKET}" 2>/dev/null; then
    echo "  Emptying deployment artifacts bucket..."
    aws s3 rm "s3://${DEPLOY_BUCKET}" --recursive
    echo "  ✓ Deployment bucket emptied"
fi

# 2. Delete CloudFormation stack
echo ""
echo "Step 2: Deleting CloudFormation stack..."
if aws cloudformation describe-stacks --stack-name "$STACK_NAME" --region "$REGION" 2>/dev/null; then
    aws cloudformation delete-stack --stack-name "$STACK_NAME" --region "$REGION"
    echo "  Waiting for stack deletion (this takes 2-3 minutes)..."
    aws cloudformation wait stack-delete-complete --stack-name "$STACK_NAME" --region "$REGION"
    echo "  ✓ Stack deleted"
else
    echo "  Stack not found, skipping..."
fi

# 3. Delete deployment bucket
echo ""
echo "Step 3: Deleting deployment bucket..."
if aws s3 ls "s3://${DEPLOY_BUCKET}" 2>/dev/null; then
    aws s3 rb "s3://${DEPLOY_BUCKET}" --force
    echo "  ✓ Deployment bucket deleted"
fi

# 4. Delete CloudWatch log groups
echo ""
echo "Step 4: Deleting CloudWatch logs..."
for log_group in "/aws/lambda/referral-webhook-handler" "/aws/lambda/referral-orchestrator"; do
    if aws logs describe-log-groups --log-group-name-prefix "$log_group" --region "$REGION" 2>/dev/null | grep -q "logGroups"; then
        aws logs delete-log-group --log-group-name "$log_group" --region "$REGION" 2>/dev/null || true
        echo "  ✓ Deleted $log_group"
    fi
done

echo ""
echo "=========================================="
echo "✅ Cleanup Complete!"
echo "=========================================="
echo ""
echo "All AWS resources have been deleted."
echo "Your account is clean and will not incur any charges."
echo ""
echo "Deleted resources:"
echo "  - Lambda functions (2)"
echo "  - API Gateway"
echo "  - SQS queues (2)"
echo "  - DynamoDB table"
echo "  - S3 buckets (2)"
echo "  - CloudWatch logs"
echo "  - IAM roles"
echo "  - SSM parameters"
echo ""

