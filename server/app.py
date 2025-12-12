"""
Simple Flask server to query DynamoDB and serve data to React UI.
"""

from flask import Flask, jsonify
from flask_cors import CORS
import boto3
from decimal import Decimal
import json

app = Flask(__name__)
CORS(app)  # Enable CORS for React frontend

# Initialize AWS clients
dynamodb = boto3.resource('dynamodb')
cloudformation = boto3.client('cloudformation')

# Cache for table name
_table_name = None


def get_table_name():
    """Get DynamoDB table name from CloudFormation stack."""
    global _table_name
    if _table_name is None:
        try:
            response = cloudformation.describe_stacks(StackName='referral-email-system')
            outputs = response['Stacks'][0]['Outputs']
            for output in outputs:
                if output['OutputKey'] == 'DynamoDBTableName':
                    _table_name = output['OutputValue']
                    break
        except Exception as e:
            print(f"Error getting table name: {e}")
            _table_name = 'ReferralMessages'  # Fallback
    return _table_name


def decimal_default(obj):
    """JSON serializer for Decimal objects."""
    if isinstance(obj, Decimal):
        return float(obj)
    raise TypeError


@app.route('/messages', methods=['GET'])
def get_messages():
    """Get all messages from DynamoDB."""
    try:
        table_name = get_table_name()
        table = dynamodb.Table(table_name)
        
        # Scan table (limit to recent 50 messages)
        response = table.scan(Limit=50)
        items = response.get('Items', [])
        
        # Sort by timestamp (most recent first)
        items.sort(key=lambda x: x.get('timestamp', 0), reverse=True)
        
        # Convert Decimal to float for JSON serialization
        items_json = json.loads(json.dumps(items, default=decimal_default))
        
        return jsonify(items_json)
    except Exception as e:
        print(f"Error fetching messages: {e}")
        return jsonify({'error': str(e)}), 500


@app.route('/health', methods=['GET'])
def health():
    """Health check endpoint."""
    return jsonify({'status': 'ok'})


@app.route('/service-catalog', methods=['GET'])
def get_service_catalog():
    """Get service catalog from brand guidelines."""
    try:
        # Read the guidelines file
        with open('aws/brand_guidelines/guidelines.json', 'r') as f:
            guidelines = json.load(f)
        
        # Extract just the service catalog
        service_catalog = guidelines.get('service_catalog', {})
        
        return jsonify(service_catalog)
    except FileNotFoundError:
        # Fallback if running from different directory
        try:
            with open('../aws/brand_guidelines/guidelines.json', 'r') as f:
                guidelines = json.load(f)
            service_catalog = guidelines.get('service_catalog', {})
            return jsonify(service_catalog)
        except Exception as e:
            print(f"Error loading service catalog: {e}")
            return jsonify({'error': 'Service catalog not found'}), 404
    except Exception as e:
        print(f"Error fetching service catalog: {e}")
        return jsonify({'error': str(e)}), 500


if __name__ == '__main__':
    print("Starting Flask server on http://localhost:8000")
    print("Make sure your AWS credentials are configured!")
    app.run(host='0.0.0.0', port=8000, debug=True)

