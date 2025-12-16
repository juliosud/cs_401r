"""
AWS Lambda function for registering new AI agent versions in the Agent Registry.
Allows versioning and management of AI agents (Generator, Judge, etc.)
"""

import json
import os
import boto3
import logging
from datetime import datetime
from typing import Dict, Any, Optional

# Configure logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)

# Initialize AWS clients
dynamodb = boto3.resource('dynamodb')
ssm_client = boto3.client('ssm')

# Cache for SSM parameters
_parameter_cache = {}


def get_parameter(parameter_name: str) -> str:
    """
    Retrieve parameter from SSM Parameter Store with caching.
    
    Args:
        parameter_name: Name of the SSM parameter
        
    Returns:
        Parameter value as string
    """
    if parameter_name not in _parameter_cache:
        try:
            response = ssm_client.get_parameter(
                Name=parameter_name,
                WithDecryption=True
            )
            _parameter_cache[parameter_name] = response['Parameter']['Value']
            logger.info(f"Retrieved parameter: {parameter_name}")
        except Exception as e:
            logger.error(f"Error retrieving parameter {parameter_name}: {str(e)}")
            raise
    
    return _parameter_cache[parameter_name]


def validate_agent_config(agent_config: Dict[str, Any]) -> tuple[bool, str]:
    """
    Validate agent configuration.
    
    Args:
        agent_config: Agent configuration dictionary
        
    Returns:
        Tuple of (is_valid, error_message)
    """
    required_fields = ['agentId', 'version', 'bedrockModel']
    
    for field in required_fields:
        if field not in agent_config:
            return False, f"Missing required field: {field}"
    
    # Validate status if provided
    if 'status' in agent_config:
        valid_statuses = ['draft', 'testing', 'production']
        if agent_config['status'] not in valid_statuses:
            return False, f"Invalid status. Must be one of: {valid_statuses}"
    
    # Validate version format (should be semantic versioning like "1.0", "2.1", etc.)
    version = agent_config['version']
    if not isinstance(version, str) or not version.replace('.', '').isdigit():
        return False, "Version must be a string in format like '1.0', '2.1', etc."
    
    return True, ""


def register_agent(agent_config: Dict[str, Any]) -> Dict[str, Any]:
    """
    Register a new agent version in the Agent Registry.
    
    Args:
        agent_config: Agent configuration dictionary
        
    Returns:
        Registration result dictionary
    """
    # Get table name from SSM
    table_name = get_parameter('/referral-system/agent-registry-table-name')
    table = dynamodb.Table(table_name)
    
    agent_id = agent_config['agentId']
    version = agent_config['version']
    
    # Prepare agent record
    agent_record = {
        'agentId': agent_id,
        'version': version,
        'bedrockModel': agent_config['bedrockModel'],
        'status': agent_config.get('status', 'draft'),
        'createdAt': datetime.utcnow().isoformat(),
        'updatedAt': datetime.utcnow().isoformat(),
        'performance': agent_config.get('performance', {}),
    }
    
    # Add optional fields
    if 'promptTemplate' in agent_config:
        agent_record['promptTemplate'] = agent_config['promptTemplate']
    
    if 'config' in agent_config:
        agent_record['config'] = agent_config['config']
    
    if 'description' in agent_config:
        agent_record['description'] = agent_config['description']
    
    # Check if agent version already exists
    try:
        existing = table.get_item(
            Key={
                'agentId': agent_id,
                'version': version
            }
        )
        
        if 'Item' in existing:
            # Update existing record
            agent_record['updatedAt'] = datetime.utcnow().isoformat()
            table.put_item(Item=agent_record)
            logger.info(f"Updated existing agent: {agent_id} v{version}")
            return {
                'success': True,
                'action': 'updated',
                'agentId': agent_id,
                'version': version
            }
    except Exception as e:
        logger.warning(f"Error checking for existing agent: {str(e)}")
    
    # Create new record
    table.put_item(Item=agent_record)
    logger.info(f"Registered new agent: {agent_id} v{version}")
    
    return {
        'success': True,
        'action': 'created',
        'agentId': agent_id,
        'version': version
    }


def lambda_handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """
    Main Lambda handler function.
    
    Args:
        event: Event object containing agent configuration
        context: Lambda context object
        
    Returns:
        Response dictionary
    """
    logger.info(f"Received agent registration request: {json.dumps(event)}")
    
    try:
        # Parse event (could be direct invocation or API Gateway)
        if 'body' in event:
            if isinstance(event['body'], str):
                agent_config = json.loads(event['body'])
            else:
                agent_config = event['body']
        else:
            agent_config = event
        
        # Validate configuration
        is_valid, error_message = validate_agent_config(agent_config)
        if not is_valid:
            logger.error(f"Invalid agent configuration: {error_message}")
            return {
                'statusCode': 400,
                'headers': {
                    'Content-Type': 'application/json',
                    'Access-Control-Allow-Origin': '*'
                },
                'body': json.dumps({
                    'error': 'Invalid agent configuration',
                    'message': error_message
                })
            }
        
        # Register agent
        result = register_agent(agent_config)
        
        return {
            'statusCode': 200,
            'headers': {
                'Content-Type': 'application/json',
                'Access-Control-Allow-Origin': '*'
            },
            'body': json.dumps(result)
        }
        
    except Exception as e:
        logger.error(f"Error registering agent: {str(e)}", exc_info=True)
        return {
            'statusCode': 500,
            'headers': {
                'Content-Type': 'application/json',
                'Access-Control-Allow-Origin': '*'
            },
            'body': json.dumps({
                'error': 'Internal server error',
                'message': str(e)
            })
        }

