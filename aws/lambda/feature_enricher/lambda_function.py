"""
AWS Lambda function for enriching customer data and updating Feature Store.
Calculates features like satisfaction_avg, service_count, lifetime_value, property_features.
"""

import json
import os
import boto3
import logging
from datetime import datetime, timezone
from typing import Dict, Any, Optional
from decimal import Decimal

# Configure logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)

# Initialize AWS clients
dynamodb = boto3.resource('dynamodb')
ssm_client = boto3.client('ssm')

# Cache for SSM parameters
_parameter_cache = {}


def get_parameter(parameter_name: str) -> str:
    """Retrieve parameter from SSM Parameter Store with caching."""
    if parameter_name not in _parameter_cache:
        try:
            response = ssm_client.get_parameter(Name=parameter_name)
            _parameter_cache[parameter_name] = response['Parameter']['Value']
            logger.info(f"Retrieved parameter: {parameter_name}")
        except Exception as e:
            logger.error(f"Error retrieving parameter {parameter_name}: {str(e)}")
            raise
    return _parameter_cache[parameter_name]


def calculate_satisfaction_avg(customer_data: Dict[str, Any], existing_features: Optional[Dict[str, Any]] = None) -> float:
    """
    Calculate average satisfaction score from service history.
    
    Args:
        customer_data: Current webhook payload with service data
        existing_features: Existing features from Feature Store (if any)
        
    Returns:
        Average satisfaction score (0-5 scale)
    """
    # Get current service satisfaction
    current_score = customer_data.get('service', {}).get('satisfaction_score')
    
    if current_score is None:
        # If no current score, return existing average or default
        if existing_features and 'satisfaction_avg' in existing_features:
            return float(existing_features['satisfaction_avg'])
        return 3.5  # Default neutral score
    
    # If we have existing features, calculate running average
    if existing_features and 'satisfaction_avg' in existing_features and 'service_count' in existing_features:
        existing_avg = float(existing_features['satisfaction_avg'])
        existing_count = int(existing_features['service_count'])
        
        # Calculate new average: (old_avg * old_count + new_score) / (old_count + 1)
        new_count = existing_count + 1
        new_avg = (existing_avg * existing_count + float(current_score)) / new_count
        return round(new_avg, 2)
    
    # First service, return current score
    return float(current_score)


def calculate_service_count(customer_data: Dict[str, Any], existing_features: Optional[Dict[str, Any]] = None) -> int:
    """
    Calculate total service count.
    
    Args:
        customer_data: Current webhook payload
        existing_features: Existing features from Feature Store
        
    Returns:
        Total number of services
    """
    if existing_features and 'service_count' in existing_features:
        return int(existing_features['service_count']) + 1
    
    # Check if services_count is in payload
    services_count = customer_data.get('services_count')
    if services_count:
        return int(services_count)
    
    # First service
    return 1


def get_lifetime_value(customer_data: Dict[str, Any], existing_features: Optional[Dict[str, Any]] = None) -> str:
    """
    Determine customer lifetime value category.
    
    Args:
        customer_data: Current webhook payload
        existing_features: Existing features from Feature Store
        
    Returns:
        Lifetime value category: 'high', 'medium', or 'low'
    """
    # Check if explicitly provided
    lifetime_value = customer_data.get('customer_lifetime_value')
    if lifetime_value:
        return str(lifetime_value).lower()
    
    # Calculate based on service count and satisfaction
    service_count = calculate_service_count(customer_data, existing_features)
    satisfaction = calculate_satisfaction_avg(customer_data, existing_features)
    
    # High: many services and high satisfaction
    if service_count >= 6 and satisfaction >= 4.0:
        return 'high'
    # Medium: moderate services or good satisfaction
    elif service_count >= 3 or satisfaction >= 3.5:
        return 'medium'
    # Low: few services and low satisfaction
    else:
        return 'low'


def extract_property_features(customer_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Extract property-related features from customer data.
    
    Args:
        customer_data: Current webhook payload
        
    Returns:
        Dictionary of property features
    """
    property_features = {}
    
    # Extract from address
    address = customer_data.get('customer', {}).get('address', {})
    if address:
        property_features['city'] = address.get('city')
        property_features['state'] = address.get('state')
        property_features['zip'] = address.get('zip')
    
    # Extract from property_info if available
    property_info = customer_data.get('property_info', {})
    if property_info:
        property_features['property_type'] = property_info.get('type')
        property_features['square_feet'] = property_info.get('square_feet')
        property_features['year_built'] = property_info.get('year_built')
        property_features['pest_issues'] = property_info.get('pest_issues', [])
    
    return property_features


def enrich_customer_features(customer_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Calculate and return all customer features.
    
    Args:
        customer_data: Webhook payload with customer and service data
        
    Returns:
        Dictionary of calculated features
    """
    customer_email = customer_data.get('customer', {}).get('email')
    if not customer_email:
        raise ValueError("Customer email is required")
    
    # Get existing features from Feature Store
    table_name = get_parameter('/referral-system/customer-features-table-name')
    features_table = dynamodb.Table(table_name)
    
    existing_features = None
    try:
        response = features_table.get_item(Key={'customerEmail': customer_email})
        if 'Item' in response:
            existing_features = response['Item']
            logger.info(f"Found existing features for {customer_email}")
    except Exception as e:
        logger.warning(f"Could not retrieve existing features: {str(e)}")
    
    # Calculate features
    satisfaction_avg = calculate_satisfaction_avg(customer_data, existing_features)
    service_count = calculate_service_count(customer_data, existing_features)
    lifetime_value = get_lifetime_value(customer_data, existing_features)
    property_features = extract_property_features(customer_data)
    
    # Build feature record
    feature_record = {
        'customerEmail': customer_email,
        'satisfaction_avg': Decimal(str(satisfaction_avg)),
        'service_count': service_count,
        'lifetime_value': lifetime_value,
        'property_features': property_features,
        'last_updated': datetime.now(timezone.utc).isoformat()
    }
    
    # Add first_seen timestamp if this is a new customer
    if not existing_features:
        feature_record['first_seen'] = datetime.now(timezone.utc).isoformat()
    else:
        feature_record['first_seen'] = existing_features.get('first_seen', feature_record['last_updated'])
    
    return feature_record


def update_feature_store(feature_record: Dict[str, Any]) -> None:
    """
    Update Feature Store with calculated features.
    
    Args:
        feature_record: Feature record to store
    """
    table_name = get_parameter('/referral-system/customer-features-table-name')
    features_table = dynamodb.Table(table_name)
    
    try:
        # Convert Decimal to proper format for DynamoDB
        item = {
            'customerEmail': feature_record['customerEmail'],
            'satisfaction_avg': feature_record['satisfaction_avg'],
            'service_count': feature_record['service_count'],
            'lifetime_value': feature_record['lifetime_value'],
            'property_features': feature_record['property_features'],
            'last_updated': feature_record['last_updated'],
            'first_seen': feature_record.get('first_seen', feature_record['last_updated'])
        }
        
        features_table.put_item(Item=item)
        logger.info(f"Updated Feature Store for {feature_record['customerEmail']}")
    except Exception as e:
        logger.error(f"Error updating Feature Store: {str(e)}")
        raise


def lambda_handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """
    Lambda handler for feature enrichment.
    
    Expected event structure:
    {
        "customer_data": { ... webhook payload ... }
    }
    
    Or can be called directly with webhook payload.
    """
    try:
        # Extract customer data from event
        customer_data = event.get('customer_data') or event
        
        # Calculate features
        feature_record = enrich_customer_features(customer_data)
        
        # Update Feature Store
        update_feature_store(feature_record)
        
        return {
            'statusCode': 200,
            'body': json.dumps({
                'success': True,
                'features': {
                    'customerEmail': feature_record['customerEmail'],
                    'satisfaction_avg': float(feature_record['satisfaction_avg']),
                    'service_count': feature_record['service_count'],
                    'lifetime_value': feature_record['lifetime_value'],
                    'property_features': feature_record['property_features']
                }
            })
        }
    except Exception as e:
        logger.error(f"Error in feature enrichment: {str(e)}")
        return {
            'statusCode': 500,
            'body': json.dumps({
                'success': False,
                'error': str(e)
            })
        }

