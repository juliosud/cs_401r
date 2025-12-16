#!/usr/bin/env python3
"""
Script to register the initial agent in Agent Registry after deployment.
This sets up the default agent so the system works immediately.
"""

import json
import sys
import boto3
from datetime import datetime, timezone

# Initialize AWS clients
cloudformation = boto3.client('cloudformation')
dynamodb = boto3.resource('dynamodb')
ssm = boto3.client('ssm')

# Get environment from command line or default to dev
ENVIRONMENT = sys.argv[1] if len(sys.argv) > 1 else 'dev'
STACK_NAME = f'referral-email-system-{ENVIRONMENT}'


def get_table_name() -> str:
    """Get Agent Registry table name from CloudFormation stack."""
    try:
        response = cloudformation.describe_stacks(StackName=STACK_NAME)
        outputs = response['Stacks'][0]['Outputs']
        for output in outputs:
            if output['OutputKey'] == 'AgentRegistryTableName':
                return output['OutputValue']
        # Fallback to SSM (try environment-specific first)
        try:
            response = ssm.get_parameter(Name=f'/referral-system/{ENVIRONMENT}/agent-registry-table-name')
            return response['Parameter']['Value']
        except:
            # Fallback to old path for backward compatibility
            try:
                response = ssm.get_parameter(Name='/referral-system/agent-registry-table-name')
                return response['Parameter']['Value']
            except:
                return 'AgentRegistry'  # Final fallback
    except Exception as e:
        print(f"Error: Failed to get table name: {str(e)}", file=sys.stderr)
        return 'AgentRegistry'  # Fallback


def get_default_model_id() -> str:
    """Get default Bedrock model ID from SSM."""
    try:
        # Try environment-specific first
        try:
            response = ssm.get_parameter(Name=f'/referral-system/{ENVIRONMENT}/bedrock-model-id')
            return response['Parameter']['Value']
        except:
            # Fallback to old path
            response = ssm.get_parameter(Name='/referral-system/bedrock-model-id')
            return response['Parameter']['Value']
    except Exception:
        return 'amazon.nova-pro-v1:0'  # Default fallback


def register_initial_agent():
    """Register the initial production agent."""
    table_name = get_table_name()
    model_id = get_default_model_id()
    
    table = dynamodb.Table(table_name)
    
    # Check if agent already exists
    try:
        response = table.get_item(
            Key={
                'agentId': 'upsell-generator',
                'version': '1.0'
            }
        )
        if 'Item' in response:
            print(f"[OK] Agent 'upsell-generator' v1.0 already exists in registry")
            return
    except Exception as e:
        print(f"Warning: Could not check for existing agent: {e}")
    
    # Register initial agent
    agent_record = {
        'agentId': 'upsell-generator',
        'version': '1.0',
        'bedrockModel': model_id,
        'status': 'production',
        'createdAt': datetime.now(timezone.utc).isoformat(),
        'updatedAt': datetime.now(timezone.utc).isoformat(),
        'description': 'Initial production agent - migrated from SSM parameter',
        'performance': {}
    }
    
    try:
        table.put_item(Item=agent_record)
        print(f"[OK] Successfully registered initial agent:")
        print(f"  Agent ID: upsell-generator")
        print(f"  Version: 1.0")
        print(f"  Model: {model_id}")
        print(f"  Status: production")
        print(f"  Table: {table_name}")
    except Exception as e:
        print(f"[ERROR] Error registering agent: {str(e)}", file=sys.stderr)
        sys.exit(1)


if __name__ == '__main__':
    print(f"Registering initial agent in Agent Registry (Environment: {ENVIRONMENT})...")
    register_initial_agent()
    print(f"\n[OK] Agent Registry setup complete for {ENVIRONMENT} environment!")
    print("\nThe orchestrator will now use this agent from the registry.")
    print("You can register new versions using the register_agent Lambda function.")

