"""
AWS Lambda function for handling webhook requests.
Receives webhook payloads, validates them, and sends to SQS queue.
"""

import json
import os
import boto3
import logging
from datetime import datetime
from typing import Dict, Any

# Configure logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)

# Initialize AWS clients
ssm_client = boto3.client('ssm')
sqs_client = boto3.client('sqs')

# Cache for SSM parameters
_parameter_cache = {}

# Get environment from Lambda environment variable
ENVIRONMENT = os.environ.get('ENVIRONMENT', 'dev')

def get_parameter(parameter_name: str) -> str:
    """
    Retrieve parameter from SSM Parameter Store with caching.
    Supports environment-specific parameters with backward compatibility.
    
    Args:
        parameter_name: Name of the SSM parameter (base name, will try env-specific first)
        
    Returns:
        Parameter value as string
    """
    # Construct environment-specific parameter name
    if parameter_name.startswith('/referral-system/'):
        env_specific_name = parameter_name.replace('/referral-system/', f'/referral-system/{ENVIRONMENT}/')
    else:
        env_specific_name = parameter_name
    
    # Try environment-specific parameter first, then fallback to old path
    for param_name in [env_specific_name, parameter_name]:
        if param_name in _parameter_cache:
            return _parameter_cache[param_name]
        
        try:
            response = ssm_client.get_parameter(
                Name=param_name,
                WithDecryption=True
            )
            _parameter_cache[param_name] = response['Parameter']['Value']
            logger.info(f"Retrieved parameter: {param_name}")
            return _parameter_cache[param_name]
        except ssm_client.exceptions.ParameterNotFound:
            continue
        except Exception as e:
            logger.error(f"Error retrieving parameter {param_name}: {str(e)}")
            raise
    
    raise ValueError(f"Parameter not found: {parameter_name} or {env_specific_name}")


def validate_webhook_payload(payload: Dict[str, Any]) -> tuple[bool, str]:
    """
    Validate the incoming webhook payload structure.
    Accepts any JSON structure - validation happens in the orchestrator/LLM.
    
    Args:
        payload: The webhook payload dictionary
        
    Returns:
        Tuple of (is_valid, error_message)
    """
    # Basic validation - just ensure we have some data
    if not payload or not isinstance(payload, dict):
        return False, "Payload must be a non-empty JSON object"
    
    # Optional: Check for customer identifier (email or id) for logging
    customer = payload.get('customer', {})
    customer_id = customer.get('email') or customer.get('id') or 'unknown'
    
    logger.info(f"Payload validation successful for customer: {customer_id}")
    return True, ""


def send_to_sqs(queue_url: str, payload: Dict[str, Any]) -> Dict[str, Any]:
    """
    Send validated payload to SQS queue.
    
    Args:
        queue_url: SQS queue URL
        payload: Validated webhook payload
        
    Returns:
        SQS send_message response
    """
    message_body = {
        'webhook_payload': payload,
        'received_at': datetime.utcnow().isoformat(),
        'source': 'webhook_handler'
    }
    
    # Extract identifiers for message attributes (with fallbacks)
    customer = payload.get('customer', {})
    customer_email = customer.get('email') or customer.get('id') or 'unknown'
    event_type = payload.get('event_type', 'service_completed')
    
    try:
        response = sqs_client.send_message(
            QueueUrl=queue_url,
            MessageBody=json.dumps(message_body),
            MessageAttributes={
                'customer_identifier': {
                    'StringValue': customer_email,
                    'DataType': 'String'
                },
                'event_type': {
                    'StringValue': event_type,
                    'DataType': 'String'
                }
            }
        )
        logger.info(f"Message sent to SQS: {response['MessageId']}")
        return response
    except Exception as e:
        logger.error(f"Error sending message to SQS: {str(e)}")
        raise


def lambda_handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """
    Main Lambda handler function.
    
    Args:
        event: API Gateway event object
        context: Lambda context object
        
    Returns:
        API Gateway response object
    """
    logger.info(f"Received webhook request: {json.dumps(event)}")
    
    try:
        # Parse request body
        if 'body' in event:
            if isinstance(event['body'], str):
                body = json.loads(event['body'])
            else:
                body = event['body']
        else:
            body = event
        
        # Validate payload
        is_valid, error_message = validate_webhook_payload(body)
        if not is_valid:
            logger.warning(f"Invalid payload: {error_message}")
            return {
                'statusCode': 400,
                'headers': {
                    'Content-Type': 'application/json',
                    'Access-Control-Allow-Origin': '*'
                },
                'body': json.dumps({
                    'error': 'Invalid payload',
                    'message': error_message
                })
            }
        
        # Get SQS queue URL from SSM
        queue_url = get_parameter('/referral-system/sqs-queue-url')
        
        # Send to SQS
        sqs_response = send_to_sqs(queue_url, body)
        
        # Extract customer identifier for response
        customer = body.get('customer', {})
        customer_identifier = customer.get('email') or customer.get('id') or 'unknown'
        
        # Return success response
        response = {
            'statusCode': 200,
            'headers': {
                'Content-Type': 'application/json',
                'Access-Control-Allow-Origin': '*'
            },
            'body': json.dumps({
                'message': 'Webhook received successfully',
                'messageId': sqs_response['MessageId'],
                'customer_identifier': customer_identifier,
                'timestamp': datetime.utcnow().isoformat()
            })
        }
        
        logger.info(f"Webhook processed successfully for {customer_identifier}")
        return response
        
    except json.JSONDecodeError as e:
        logger.error(f"JSON decode error: {str(e)}")
        return {
            'statusCode': 400,
            'headers': {
                'Content-Type': 'application/json',
                'Access-Control-Allow-Origin': '*'
            },
            'body': json.dumps({
                'error': 'Invalid JSON',
                'message': str(e)
            })
        }
        
    except Exception as e:
        logger.error(f"Unexpected error: {str(e)}", exc_info=True)
        return {
            'statusCode': 500,
            'headers': {
                'Content-Type': 'application/json',
                'Access-Control-Allow-Origin': '*'
            },
            'body': json.dumps({
                'error': 'Internal server error',
                'message': 'An unexpected error occurred processing your request'
            })
        }

