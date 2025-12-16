"""
AWS Lambda function for orchestrating LLM-powered referral email generation.
Processes SQS messages, calls Bedrock LLMs, and stores results in DynamoDB.
"""

import json
import os
import boto3
import logging
import time
import uuid
from datetime import datetime
from typing import Dict, Any, Optional
from decimal import Decimal

# Configure logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)

# Initialize AWS clients
ssm_client = boto3.client('ssm')
s3_client = boto3.client('s3')
bedrock_client = boto3.client('bedrock-runtime')
dynamodb = boto3.resource('dynamodb')
cloudwatch = boto3.client('cloudwatch')

# Cache for SSM parameters
_parameter_cache = {}

# Maximum retry attempts for LLM generation
MAX_RETRIES = 2


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


def get_active_agent(agent_id: str = 'upsell-generator') -> Dict[str, Any]:
    """
    Get the active (production) agent from Agent Registry.
    Falls back to SSM parameter if Agent Registry is empty.
    
    Args:
        agent_id: Agent identifier (default: 'upsell-generator')
        
    Returns:
        Dictionary with agent configuration (model_id, promptTemplate, etc.)
    """
    try:
        # Get table name from SSM
        registry_table_name = get_parameter('/referral-system/agent-registry-table-name')
        registry_table = dynamodb.Table(registry_table_name)
        
        # Query for production agent
        response = registry_table.query(
            IndexName='StatusIndex',
            KeyConditionExpression='#status = :status',
            ExpressionAttributeNames={'#status': 'status'},
            ExpressionAttributeValues={
                ':status': 'production',
                ':agent_id': agent_id
            },
            FilterExpression='agentId = :agent_id',
            ScanIndexForward=False,  # Most recent version first
            Limit=1
        )
        
        if response['Items']:
            agent = response['Items'][0]
            logger.info(f"Using agent from registry: {agent_id} v{agent['version']}")
            return {
                'model_id': agent['bedrockModel'],
                'version': agent['version'],
                'promptTemplate': agent.get('promptTemplate'),
                'config': agent.get('config', {})
            }
        else:
            logger.warning(f"No production agent found in registry for {agent_id}, falling back to SSM")
            # Fallback to SSM parameter (backward compatibility)
            model_id = get_parameter('/referral-system/bedrock-model-id')
            return {
                'model_id': model_id,
                'version': 'legacy',
                'promptTemplate': None,
                'config': {}
            }
    except Exception as e:
        logger.warning(f"Error querying Agent Registry: {str(e)}, falling back to SSM")
        # Fallback to SSM parameter (backward compatibility)
        try:
            model_id = get_parameter('/referral-system/bedrock-model-id')
            return {
                'model_id': model_id,
                'version': 'legacy',
                'promptTemplate': None,
                'config': {}
            }
        except Exception as fallback_error:
            logger.error(f"Failed to get model ID from SSM: {str(fallback_error)}")
            raise


def get_customer_features(customer_email: str) -> Optional[Dict[str, Any]]:
    """
    Get customer features from Feature Store.
    Returns None if Feature Store is not available or customer not found.
    
    Args:
        customer_email: Customer email address
        
    Returns:
        Dictionary with customer features, or None if not available
    """
    if not customer_email:
        return None
    
    try:
        # Get table name from SSM
        features_table_name = get_parameter('/referral-system/customer-features-table-name')
        features_table = dynamodb.Table(features_table_name)
        
        # Query Feature Store
        response = features_table.get_item(Key={'customerEmail': customer_email})
        
        if 'Item' in response:
            item = response['Item']
            logger.info(f"Retrieved features from Feature Store for {customer_email}")
            return {
                'satisfaction_avg': float(item.get('satisfaction_avg', 0)),
                'service_count': int(item.get('service_count', 0)),
                'lifetime_value': item.get('lifetime_value', 'unknown'),
                'property_features': item.get('property_features', {})
            }
        else:
            logger.info(f"No features found in Feature Store for {customer_email}")
            return None
    except Exception as e:
        # Feature Store not available - backward compatible
        logger.warning(f"Could not retrieve features from Feature Store: {str(e)}")
        return None


def get_brand_guidelines(bucket_name: str) -> str:
    """
    Fetch brand guidelines from S3 bucket.
    
    Args:
        bucket_name: Name of the S3 bucket
        
    Returns:
        Brand guidelines as formatted string
    """
    try:
        response = s3_client.get_object(
            Bucket=bucket_name,
            Key='guidelines.json'
        )
        guidelines_data = json.loads(response['Body'].read().decode('utf-8'))
        
        # Format guidelines for LLM prompt
        formatted_guidelines = f"""
Brand Voice: {guidelines_data.get('brand_voice', '')}
Tone: {guidelines_data.get('tone', '')}
Key Messages: {', '.join(guidelines_data.get('key_messages', []))}
Formatting Guidelines: {', '.join(guidelines_data.get('formatting', []))}

Do Not Include:
{chr(10).join(['- ' + item for item in guidelines_data.get('avoid', [])])}

Preferred Language:
{chr(10).join(['- ' + item for item in guidelines_data.get('preferred_language', [])])}
"""
        logger.info("Brand guidelines retrieved successfully")
        return formatted_guidelines
    except Exception as e:
        logger.error(f"Error fetching brand guidelines: {str(e)}")
        raise


def format_customer_data(customer_data: Dict[str, Any]) -> str:
    """
    Convert customer data to JSON string for LLM.
    
    Args:
        customer_data: Customer data from webhook (any structure)
        
    Returns:
        JSON string of customer data
    """
    # Return the raw customer data as formatted JSON for the LLM
    return json.dumps(customer_data, indent=2)


def format_customer_features(features: Optional[Dict[str, Any]]) -> str:
    """
    Format customer features for inclusion in AI prompt.
    
    Args:
        features: Customer features from Feature Store, or None
        
    Returns:
        Formatted string with features, or empty string if None
    """
    if not features:
        return ""
    
    feature_text = "\n\nCUSTOMER INSIGHTS (from Feature Store):\n"
    feature_text += f"- Average Satisfaction Score: {features.get('satisfaction_avg', 'N/A')}/5.0\n"
    feature_text += f"- Total Services Completed: {features.get('service_count', 0)}\n"
    feature_text += f"- Customer Lifetime Value: {features.get('lifetime_value', 'unknown').upper()}\n"
    
    property_features = features.get('property_features', {})
    if property_features:
        feature_text += f"- Property Location: {property_features.get('city', 'N/A')}, {property_features.get('state', 'N/A')}\n"
        if property_features.get('property_type'):
            feature_text += f"- Property Type: {property_features.get('property_type')}\n"
        if property_features.get('square_feet'):
            feature_text += f"- Property Size: {property_features.get('square_feet')} sq ft\n"
    
    feature_text += "\nUse these insights to personalize the message and select the most relevant service."
    
    return feature_text


def call_bedrock_generator(model_id: str, customer_data_str: str, brand_guidelines: str, retry_count: int = 0, previous_feedback: str = None, customer_features: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """
    Call Bedrock LLM to generate service upsell message.
    
    Args:
        model_id: Bedrock model identifier
        customer_data_str: Formatted customer data
        brand_guidelines: Brand guidelines text (includes service catalog)
        retry_count: Current retry attempt
        previous_feedback: Feedback from previous rejection (if any)
        customer_features: Customer features from Feature Store (optional)
        
    Returns:
        Dictionary with generated message content and metadata
    """
    feedback_note = ""
    if retry_count > 0 and previous_feedback:
        feedback_note = f"\n\nIMPORTANT - Previous attempt was rejected:\n{previous_feedback}\nPlease address these issues and select a different service if needed."

    # Format features for prompt
    features_text = format_customer_features(customer_features)

    # Format features for prompt
    features_text = format_customer_features(customer_features)

    prompt = f"""You are creating a personalized service upsell message for a pest control customer.

Customer Data (JSON):
{customer_data_str}

Company Information & Service Catalog (JSON):
{brand_guidelines}{features_text}

Your task:
1. Analyze the customer data provided (it may have various fields - use what's available)
2. Look for patterns in service_history, property_info, current_plan, etc.
3. Select ONE service from the catalog that would genuinely benefit this customer
4. Create a brief, personalized message (150-200 words) that:
   - References POSITIVE details from their data (loyal customer, property features, service frequency)
   - Explains why this additional service makes sense for them
   - Highlights 2-3 key benefits relevant to their situation
   - Includes a soft call-to-action
   - Maintains the brand voice (professional, friendly, reassuring)

CRITICAL - What NOT to mention in the message:
- DO NOT mention any complaints, issues, or negative experiences from service notes
- DO NOT reference dissatisfaction, late arrivals, or service problems
- DO NOT bring up past issues even if they're in the data
- DO NOT make the customer feel like you're tracking negative things
- Focus ONLY on positive aspects (loyalty, satisfaction, property needs, service patterns)

Example: If data shows "Customer complained about late technician" → Don't mention this in the message at all

Important:
- Work with whatever fields are present in the customer data
- Check current_plan to avoid recommending what they already have
- If service_history exists, analyze patterns but only reference positive ones
- If property_info exists, use it to inform recommendations
- Use customer's first name if available
{feedback_note}

Output ONLY the message body text. No subject line, no "Dear [Name]" greeting - start directly with the content."""

    try:
        start_time = time.time()
        
        # Use Converse API for Amazon Nova models
        response = bedrock_client.converse(
            modelId=model_id,
            messages=[
                {
                    "role": "user",
                    "content": [{"text": prompt}]
        }
            ],
            inferenceConfig={
                "maxTokens": 1000,
                "temperature": 0.7 if retry_count == 0 else 0.8
            }
        )
        
        generation_time = time.time() - start_time
        
        # Extract generated text from Converse API response
        generated_text = response['output']['message']['content'][0]['text']
        
        logger.info(f"Email generated successfully in {generation_time:.2f}s")
        
        # Publish generation time metric
        cloudwatch.put_metric_data(
            Namespace='ReferralSystem',
            MetricData=[
                {
                    'MetricName': 'GenerationTime',
                    'Value': generation_time,
                    'Unit': 'Seconds',
                    'Timestamp': datetime.utcnow()
                }
            ]
        )
        
        return {
            'email_content': generated_text.strip(),
            'generation_time': generation_time,
            'model_id': model_id,
            'retry_count': retry_count
        }
        
    except Exception as e:
        logger.error(f"Error calling Bedrock generator: {str(e)}")
        raise


def call_bedrock_judge(model_id: str, generated_email: str, brand_guidelines: str, customer_data_str: str) -> Dict[str, Any]:
    """
    Call Bedrock LLM to judge/validate generated upsell message.
    
    Args:
        model_id: Bedrock model identifier
        generated_email: Message content to judge
        brand_guidelines: Brand guidelines text (includes service catalog)
        customer_data_str: Customer context for appropriateness check
        
    Returns:
        Dictionary with judgment results
    """
    # Get current date for comparison
    from datetime import datetime as dt
    current_date = dt.utcnow().strftime('%Y-%m-%d')
    
    prompt = f"""You are a message quality judge evaluating whether this service upsell message should be sent.

CURRENT DATE: {current_date}

Customer Data (JSON - may have variable fields):
{customer_data_str}

Generated Message:
{generated_email}

Company Information & Service Catalog (JSON):
{brand_guidelines}

Evaluate on THREE dimensions:

1. CUSTOMER APPROPRIATENESS: Should we send ANY upsell to this customer right now?
   
   STEP 1 - Check recent upsell timing:
   - Look for "last_upsell_sent" field in the customer data
   - If field is PRESENT: Calculate days between last_upsell_sent and CURRENT DATE ({current_date})
     * Example: last_upsell_sent: "2025-11-18", current: "2025-12-12" = 24 days → REJECT (< 30 days)
     * Example: last_upsell_sent: "2025-10-01", current: "2025-12-12" = 72 days → OK (> 30 days)
     * If within 30 days, IMMEDIATELY REJECT with reason "appropriateness"
   - If field is NOT PRESENT or null: This is OK, proceed to other checks
   
   STEP 2 - Analyze customer satisfaction (work with whatever fields are present):
   - Look for satisfaction_score in service_history (reject if most recent is < 4)
   - Check service notes for active complaints, refunds, frustration, late arrivals
   - Check payment_status if present (reject if not "current")
   - Look for patterns in service_history showing dissatisfaction
   
   REJECT if:
   - Last upsell sent within 30 days (if field exists)
   - Most recent satisfaction score < 4/5
   - Service notes mention complaints, issues, late arrivals, frustration
   - Unresolved service problems
   - Payment issues
   
   APPROVE if:
   - No last_upsell_sent field OR it's > 30 days ago
   - Recent satisfaction scores 4-5/5
   - No active complaints or issues in notes
   - Positive service experience
   - Customer in good standing

2. SERVICE VALIDITY: Is the recommended service legitimate and appropriate?
   
   Check the service catalog to verify:
   - Service exists in catalog
   - Customer doesn't already have this service (check service_history)
   - Service makes sense given customer data (property_info, service patterns, etc.)
   - Upsell triggers in catalog align with customer's situation
   
   REJECT if:
   - Service not in catalog
   - Customer already has it
   - Doesn't match customer's needs based on available data
   
   APPROVE if:
   - Service exists and is appropriate
   - Genuinely beneficial based on customer data
   - Makes logical sense

3. BRAND & MESSAGE QUALITY: Does it match brand standards?
   - Professional, friendly, reassuring tone
   - No pushy sales language
   - Personalized using customer data
   - Clear value proposition
   - Appropriate length (150-200 words)

Respond with JSON only:
{{
  "approved": true/false,
  "score": 1-10,
  "issues": ["list any problems"],
  "feedback": "brief explanation of decision with specific references to customer data",
  "reason": "appropriateness" or "service_validity" or "brand" (primary rejection reason if false)
}}"""

    try:
        start_time = time.time()
        
        # Use Converse API for Amazon Nova models
        response = bedrock_client.converse(
            modelId=model_id,
            messages=[
                {
                    "role": "user",
                    "content": [{"text": prompt}]
        }
            ],
            inferenceConfig={
                "maxTokens": 500,
                "temperature": 0.3
            }
        )
        
        judgment_time = time.time() - start_time
        
        # Extract and parse judgment from Converse API response
        judgment_text = response['output']['message']['content'][0]['text'].strip()
        
        # Extract JSON from response (handle markdown code blocks)
        if '```json' in judgment_text:
            judgment_text = judgment_text.split('```json')[1].split('```')[0].strip()
        elif '```' in judgment_text:
            judgment_text = judgment_text.split('```')[1].split('```')[0].strip()
        
        judgment = json.loads(judgment_text)
        
        logger.info(f"Email judged: approved={judgment.get('approved')}, score={judgment.get('score')}")
        
        # Publish approval metric
        cloudwatch.put_metric_data(
            Namespace='ReferralSystem',
            MetricData=[
                {
                    'MetricName': 'ApprovalRate',
                    'Value': 1 if judgment.get('approved') else 0,
                    'Unit': 'None',
                    'Timestamp': datetime.utcnow()
                },
                {
                    'MetricName': 'JudgeScore',
                    'Value': judgment.get('score', 0),
                    'Unit': 'None',
                    'Timestamp': datetime.utcnow()
                }
            ]
        )
        
        return {
            'approved': judgment.get('approved', False),
            'score': judgment.get('score', 0),
            'issues': judgment.get('issues', []),
            'feedback': judgment.get('feedback', ''),
            'judgment_time': judgment_time
        }
        
    except Exception as e:
        logger.error(f"Error calling Bedrock judge: {str(e)}")
        # Default to rejected if judge fails
        return {
            'approved': False,
            'score': 0,
            'issues': ['Judge evaluation failed'],
            'feedback': f'Error: {str(e)}',
            'judgment_time': 0
        }


def generate_email_subject(customer_name: str) -> str:
    """
    Generate message subject line.
    
    Args:
        customer_name: Customer's first name
        
    Returns:
        Message subject line
    """
    import random
    subjects = [
        f"{customer_name}, Enhance Your Home Protection",
        f"Additional Protection Options for Your Home, {customer_name}",
        f"{customer_name}, Here's How We Can Better Protect Your Home",
        f"Recommended Service Upgrade for {customer_name}",
        f"{customer_name}, Take Your Pest Protection to the Next Level"
    ]
    return random.choice(subjects)


def store_in_dynamodb(table_name: str, message_data: Dict[str, Any]) -> None:
    """
    Store generated message and metadata in DynamoDB.
    
    Args:
        table_name: DynamoDB table name
        message_data: Complete message data to store
    """
    try:
        table = dynamodb.Table(table_name)
        
        # Convert float values to Decimal for DynamoDB
        def convert_floats(obj):
            if isinstance(obj, float):
                return Decimal(str(obj))
            elif isinstance(obj, dict):
                return {k: convert_floats(v) for k, v in obj.items()}
            elif isinstance(obj, list):
                return [convert_floats(item) for item in obj]
            return obj
        
        message_data = convert_floats(message_data)
        
        table.put_item(Item=message_data)
        logger.info(f"Message stored in DynamoDB: {message_data['messageId']}")
        
    except Exception as e:
        logger.error(f"Error storing message in DynamoDB: {str(e)}")
        raise


def process_message(message_body: Dict[str, Any]) -> Dict[str, Any]:
    """
    Process a single SQS message through the complete workflow.
    
    Args:
        message_body: Parsed SQS message body
        
    Returns:
        Processing result dictionary
    """
    webhook_payload = message_body['webhook_payload']
    customer = webhook_payload.get('customer', {})
    
    # Try to get customer identifier for logging
    customer_id = customer.get('email') or customer.get('id') or 'unknown'
    customer_email = customer.get('email') or 'unknown@example.com'
    logger.info(f"Processing upsell message for customer: {customer_id}")
    
    # Get configuration
    bucket_name = get_parameter('/referral-system/s3-bucket-name')
    table_name = get_parameter('/referral-system/dynamodb-table-name')
    
    # Get active agent from Agent Registry (with fallback to SSM)
    active_agent = get_active_agent('upsell-generator')
    model_id = active_agent['model_id']
    agent_version = active_agent['version']
    logger.info(f"Using agent version: {agent_version}, model: {model_id}")
    
    # Fetch brand guidelines
    brand_guidelines = get_brand_guidelines(bucket_name)
    
    # Query Feature Store for customer features
    customer_features = get_customer_features(customer_email)
    if customer_features:
        logger.info(f"Using features from Feature Store: satisfaction={customer_features.get('satisfaction_avg')}, services={customer_features.get('service_count')}, LTV={customer_features.get('lifetime_value')}")
    else:
        logger.info("No features found in Feature Store - proceeding without features")
    
    # Format customer data
    customer_data_str = format_customer_data(webhook_payload)
    
    # Generate and validate email (with retries)
    retry_count = 0
    approved = False
    final_email_content = None
    final_judgment = None
    generation_result = None
    previous_feedback = None
    
    while retry_count <= MAX_RETRIES and not approved:
        # Generate email
        generation_result = call_bedrock_generator(
            model_id=model_id,
            customer_data_str=customer_data_str,
            brand_guidelines=brand_guidelines,
            retry_count=retry_count,
            previous_feedback=previous_feedback,
            customer_features=customer_features
        )
        
        # Judge email
        judgment_result = call_bedrock_judge(
            model_id=model_id,
            generated_email=generation_result['email_content'],
            brand_guidelines=brand_guidelines,
            customer_data_str=customer_data_str
        )
        
        if judgment_result['approved']:
            approved = True
            final_email_content = generation_result['email_content']
            final_judgment = judgment_result
            logger.info(f"Email approved on attempt {retry_count + 1}")
        else:
            rejection_reason = judgment_result.get('reason', 'brand')
            logger.warning(f"Email rejected on attempt {retry_count + 1} (reason: {rejection_reason}): {judgment_result['feedback']}")
            
            # If rejected for appropriateness (not brand), don't retry - can't be fixed
            if rejection_reason == 'appropriateness':
                logger.info("Rejection due to customer appropriateness - skipping retries")
                final_judgment = judgment_result
                final_email_content = generation_result['email_content']
                break
            
            # Store feedback for next retry
            previous_feedback = judgment_result['feedback']
            retry_count += 1
            final_judgment = judgment_result
            final_email_content = generation_result['email_content']
    
    # Generate subject line
    email_subject = generate_email_subject(customer.get('first_name', 'Valued Customer'))
    
    # Prepare DynamoDB record
    message_id = str(uuid.uuid4())
    timestamp = int(datetime.utcnow().timestamp())
    
    # Build customer name from available fields
    customer_name = f"{customer.get('first_name', '')} {customer.get('last_name', '')}".strip() or 'Unknown Customer'
    customer_email = customer.get('email') or customer.get('id') or 'unknown@example.com'
    
    dynamodb_item = {
        'messageId': message_id,
        'timestamp': timestamp,
        'customerEmail': customer_email,
        'customerName': customer_name,
        'emailContent': final_email_content,
        'emailSubject': email_subject,
        'llmGeneratorScore': Decimal(str(generation_result.get('generation_time', 0))),
        'llmJudgeScore': final_judgment.get('score', 0),
        'judgeApproved': final_judgment.get('approved', False),
        'judgeFeedback': final_judgment.get('feedback', ''),
        'judgeIssues': final_judgment.get('issues', []),
        'rejectionReason': final_judgment.get('reason', 'N/A'),
        'createdAt': datetime.utcnow().isoformat(),
        'status': 'approved' if approved else 'rejected',
        'retryCount': retry_count,
        'agentVersion': agent_version,  # Track which agent version generated this
        'customerData': webhook_payload
    }
    
    # Store in DynamoDB
    store_in_dynamodb(table_name, dynamodb_item)
    
    # Publish metrics
    cloudwatch.put_metric_data(
        Namespace='ReferralSystem',
        MetricData=[
            {
                'MetricName': 'MessagesGenerated',
                'Value': 1,
                'Unit': 'Count',
                'Timestamp': datetime.utcnow()
            },
            {
                'MetricName': 'RetryRate',
                'Value': retry_count,
                'Unit': 'Count',
                'Timestamp': datetime.utcnow()
            }
        ]
    )
    
    return {
        'message_id': message_id,
        'customer_email': customer['email'],
        'approved': approved,
        'retry_count': retry_count
    }


def lambda_handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """
    Main Lambda handler function for SQS event processing.
    
    Args:
        event: SQS event object
        context: Lambda context object
        
    Returns:
        Processing result dictionary
    """
    logger.info(f"Received SQS event with {len(event.get('Records', []))} records")
    
    results = []
    errors = []
    
    for record in event.get('Records', []):
        try:
            # Parse message body
            message_body = json.loads(record['body'])
            
            # Process message
            result = process_message(message_body)
            results.append(result)
            
            logger.info(f"Successfully processed message: {result['message_id']}")
            
        except Exception as e:
            logger.error(f"Error processing message: {str(e)}", exc_info=True)
            errors.append({
                'message_id': record.get('messageId'),
                'error': str(e)
            })
    
    # Log summary
    logger.info(f"Processed {len(results)} messages successfully, {len(errors)} errors")
    
    # If any errors occurred, raise exception to trigger retry
    if errors:
        raise Exception(f"Failed to process {len(errors)} messages: {errors}")
    
    return {
        'statusCode': 200,
        'body': json.dumps({
            'processed': len(results),
            'results': results
        })
    }

