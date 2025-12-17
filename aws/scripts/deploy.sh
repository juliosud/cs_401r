#!/bin/bash

# Deployment script for Referral Email System
# This script packages and deploys Lambda functions and creates infrastructure

set -e

echo "=========================================="
echo "Deploying Referral Email System"
echo "=========================================="

# Configuration
AWS_REGION=${AWS_REGION:-us-east-1}
PROJECT_ROOT=$(pwd)

# Parse command line arguments
ACCOUNT="dev"  # Default to dev

while [[ $# -gt 0 ]]; do
    case $1 in
        --account)
            ACCOUNT="$2"
            shift 2
            ;;
        *)
            echo "Unknown option: $1"
            echo "Usage: $0 [--account dev|test|prod]"
            exit 1
            ;;
    esac
done

# Validate account (nOTE: sHOW THIS)
if [[ ! "$ACCOUNT" =~ ^(dev|test|prod)$ ]]; then
    echo "ERROR: Account must be dev, test, or prod"
    exit 1
fi

# Set stack name based on account
STACK_NAME="referral-email-system-${ACCOUNT}"

echo "AWS Region: $AWS_REGION"
echo "Stack Name: $STACK_NAME"
echo "Project Root: $PROJECT_ROOT"

# Check prerequisites
echo ""
echo "Checking prerequisites..."

if ! command -v aws &> /dev/null; then
    echo "ERROR: AWS CLI not found. Please install AWS CLI."
    exit 1
fi
echo "✓ AWS CLI found"

if ! command -v sam &> /dev/null; then
    echo "WARNING: SAM CLI not found. Will use CloudFormation instead."
    USE_SAM=false
else
    echo "✓ SAM CLI found"
    USE_SAM=true
fi

if ! command -v python &> /dev/null; then
    echo "ERROR: Python 3 not found."
    exit 1
fi
echo "✓ Python 3 found"

# Check AWS credentials
if ! aws sts get-caller-identity --region $AWS_REGION >/dev/null 2>&1; then
    echo "ERROR: AWS credentials not configured or invalid."
    exit 1
fi
echo "✓ AWS credentials valid"

echo ""
echo "=========================================="
echo "Step 1: Installing Lambda dependencies"
echo "=========================================="

# Install dependencies for Webhook Handler
echo "Installing dependencies for Webhook Handler..."
cd "$PROJECT_ROOT/aws/lambda/webhook_handler"
pip3 install -r requirements.txt -t . --upgrade >/dev/null 2>&1 || pip3 install -r requirements.txt -t .
echo "✓ Webhook Handler dependencies installed"

# Install dependencies for Orchestrator
echo "Installing dependencies for Orchestrator..."
cd "$PROJECT_ROOT/aws/lambda/orchestrator"
pip3 install -r requirements.txt -t . --upgrade >/dev/null 2>&1 || pip3 install -r requirements.txt -t .
echo "✓ Orchestrator dependencies installed"

# Install dependencies for Feature Enricher
echo "Installing dependencies for Feature Enricher..."
cd "$PROJECT_ROOT/aws/lambda/feature_enricher"
pip3 install -r requirements.txt -t . --upgrade >/dev/null 2>&1 || pip3 install -r requirements.txt -t .
echo "✓ Feature Enricher dependencies installed"

# Install dependencies for Register Agent (if exists)
if [ -f "$PROJECT_ROOT/aws/lambda/register_agent/requirements.txt" ]; then
    echo "Installing dependencies for Register Agent..."
    cd "$PROJECT_ROOT/aws/lambda/register_agent"
    pip3 install -r requirements.txt -t . --upgrade >/dev/null 2>&1 || pip3 install -r requirements.txt -t .
    echo "✓ Register Agent dependencies installed"
fi

cd "$PROJECT_ROOT"

echo ""
echo "=========================================="
echo "Step 2: Deploying CloudFormation Stack"
echo "=========================================="

if [ "$USE_SAM" = true ]; then
    echo "Using SAM CLI for deployment..."
    
    cd cloudformation
    
    sam build --use-container
    
    sam deploy \
        --stack-name $STACK_NAME \
        --region $AWS_REGION \
        --capabilities CAPABILITY_NAMED_IAM \
        --resolve-s3 \
        --no-confirm-changeset \
        --no-fail-on-empty-changeset \
        --parameter-overrides Environment=$ACCOUNT
    
    cd "$PROJECT_ROOT"
else
    echo "Using CloudFormation CLI for deployment..."
    
    # Create S3 bucket for deployment artifacts (if it doesn't exist)
    AWS_ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
    DEPLOY_BUCKET="cfn-deploy-artifacts-${AWS_ACCOUNT_ID}-${AWS_REGION}"
    if ! aws s3 ls "s3://${DEPLOY_BUCKET}" 2>/dev/null; then
        echo "Creating deployment bucket..."
        aws s3 mb "s3://${DEPLOY_BUCKET}" --region $AWS_REGION 2>/dev/null || true
    fi
    
    # Package the template (uploads Lambda code to S3)
    echo "Packaging Lambda functions..."
    aws cloudformation package \
        --template-file aws/cloudformation/template.yaml \
        --s3-bucket ${DEPLOY_BUCKET} \
        --output-template-file aws/cloudformation/packaged-template.yaml \
        --region $AWS_REGION
    
    # Check if stack exists
    if aws cloudformation describe-stacks --stack-name $STACK_NAME --region $AWS_REGION >/dev/null 2>&1; then
        echo "Stack exists, updating..."
        
        aws cloudformation update-stack \
            --stack-name $STACK_NAME \
            --region $AWS_REGION \
            --template-body file://aws/cloudformation/packaged-template.yaml \
            --capabilities CAPABILITY_NAMED_IAM CAPABILITY_AUTO_EXPAND
        
        echo "Waiting for stack update to complete..."
        aws cloudformation wait stack-update-complete \
            --stack-name $STACK_NAME \
            --region $AWS_REGION
    else
        echo "Creating new stack..."
        
        aws cloudformation create-stack \
            --stack-name $STACK_NAME \
            --region $AWS_REGION \
            --template-body file://aws/cloudformation/packaged-template.yaml \
            --capabilities CAPABILITY_NAMED_IAM CAPABILITY_AUTO_EXPAND \
            --parameters ParameterKey=Environment,ParameterValue=$ACCOUNT
        
        echo "Waiting for stack creation to complete..."
        aws cloudformation wait stack-create-complete \
            --stack-name $STACK_NAME \
            --region $AWS_REGION
    fi
fi

echo "✓ CloudFormation stack deployed"

echo ""
echo "=========================================="
echo "Step 3: Uploading Brand Guidelines to S3"
echo "=========================================="

# Get S3 bucket name from stack outputs
S3_BUCKET=$(aws cloudformation describe-stacks \
    --stack-name $STACK_NAME \
    --region $AWS_REGION \
    --query 'Stacks[0].Outputs[?OutputKey==`BrandGuidelinesBucket`].OutputValue' \
    --output text)

echo "S3 Bucket: $S3_BUCKET"

aws s3 cp aws/brand_guidelines/guidelines.json s3://$S3_BUCKET/guidelines.json --region $AWS_REGION
echo "✓ Brand guidelines uploaded"

echo ""
echo "=========================================="
echo "Step 4: Verifying Deployment"
echo "=========================================="

# Get stack outputs
API_ENDPOINT=$(aws cloudformation describe-stacks \
    --stack-name $STACK_NAME \
    --region $AWS_REGION \
    --query 'Stacks[0].Outputs[?OutputKey==`WebhookUrl`].OutputValue' \
    --output text)

DLQ_URL=$(aws cloudformation describe-stacks \
    --stack-name $STACK_NAME \
    --region $AWS_REGION \
    --query 'Stacks[0].Outputs[?OutputKey==`DeadLetterQueueUrl`].OutputValue' \
    --output text)

DYNAMODB_TABLE=$(aws cloudformation describe-stacks \
    --stack-name $STACK_NAME \
    --region $AWS_REGION \
    --query 'Stacks[0].Outputs[?OutputKey==`DynamoDBTableName`].OutputValue' \
    --output text)

echo "✓ Deployment verified"

echo ""
echo "=========================================="
echo "Step 5: Registering Initial Agent"
echo "=========================================="

# Register initial agent in Agent Registry
echo "Registering initial agent in Agent Registry..."
cd "$PROJECT_ROOT"
# Try python3 first, fallback to python (Windows compatibility)
if command -v python3 &> /dev/null 2>&1; then
    python3 aws/scripts/register_initial_agent.py && echo "✓ Initial agent registered" || echo "⚠ Warning: Could not register initial agent automatically."
elif command -v python &> /dev/null 2>&1; then
    python aws/scripts/register_initial_agent.py && echo "✓ Initial agent registered" || echo "⚠ Warning: Could not register initial agent automatically."
else
    echo "⚠ Warning: Python not found. Skipping initial agent registration."
    echo "   You can register manually by running: python aws/scripts/register_initial_agent.py"
fi

cd "$PROJECT_ROOT"

echo ""
echo "=========================================="
echo "Deployment Complete!"
echo "=========================================="
echo ""
echo "Stack Outputs:"
echo "  Webhook URL: $API_ENDPOINT"
echo "  S3 Bucket: $S3_BUCKET"
echo "  DynamoDB Table: $DYNAMODB_TABLE"
echo "  Dead Letter Queue: $DLQ_URL"
echo ""
echo "Next steps:"
echo "1. Test the webhook endpoint:"
echo "   curl -X POST \"$API_ENDPOINT\" \\"
echo "     -H \"Content-Type: application/json\" \\"
echo "     -d @mock_data/webhook_payload_1.json"
echo ""
echo "2. Monitor CloudWatch Logs:"
echo "   aws logs tail /aws/lambda/referral-webhook-handler --follow"
echo "   aws logs tail /aws/lambda/referral-orchestrator --follow"
echo ""
echo "3. Query generated messages:"
echo "   python scripts/query_messages.py --list-all"
echo ""
echo "4. Run automated tests:"
echo "   python scripts/test_system.py"

