"""
Unit tests for Webhook Handler Lambda function.
"""

import json
import pytest
import sys
import os
from unittest.mock import Mock, patch, MagicMock

# Add lambda function directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../lambda/webhook_handler'))

import lambda_function


class TestWebhookHandler:
    """Test cases for webhook handler."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.valid_payload = {
            "event_type": "service_completed",
            "customer": {
                "id": "CUST-12345",
                "first_name": "John",
                "last_name": "Smith",
                "email": "john.smith@example.com",
                "phone": "+1-555-0123",
                "address": {
                    "street": "123 Main St",
                    "city": "Austin",
                    "state": "TX",
                    "zip": "78701"
                }
            },
            "service": {
                "type": "Quarterly Pest Control",
                "date": "2024-12-10",
                "technician": "Mike Johnson",
                "satisfaction_score": 5,
                "next_service": "2025-03-10"
            },
            "referral_eligible": True,
            "customer_lifetime_value": "high",
            "services_count": 8
        }
        
        self.api_gateway_event = {
            "body": json.dumps(self.valid_payload),
            "headers": {
                "Content-Type": "application/json"
            },
            "httpMethod": "POST"
        }
    
    def test_validate_webhook_payload_valid(self):
        """Test validation with valid payload."""
        is_valid, error_msg = lambda_function.validate_webhook_payload(self.valid_payload)
        assert is_valid == True
        assert error_msg == ""
    
    def test_validate_webhook_payload_missing_event_type(self):
        """Test validation with missing event_type."""
        payload = self.valid_payload.copy()
        del payload['event_type']
        
        is_valid, error_msg = lambda_function.validate_webhook_payload(payload)
        assert is_valid == False
        assert "event_type" in error_msg
    
    def test_validate_webhook_payload_missing_customer_field(self):
        """Test validation with missing customer email."""
        payload = self.valid_payload.copy()
        del payload['customer']['email']
        
        is_valid, error_msg = lambda_function.validate_webhook_payload(payload)
        assert is_valid == False
        assert "email" in error_msg
    
    def test_validate_webhook_payload_invalid_email(self):
        """Test validation with invalid email format."""
        payload = self.valid_payload.copy()
        payload['customer']['email'] = "invalid-email"
        
        is_valid, error_msg = lambda_function.validate_webhook_payload(payload)
        assert is_valid == False
        assert "email" in error_msg.lower()
    
    def test_validate_webhook_payload_not_referral_eligible(self):
        """Test validation with referral_eligible = False."""
        payload = self.valid_payload.copy()
        payload['referral_eligible'] = False
        
        is_valid, error_msg = lambda_function.validate_webhook_payload(payload)
        assert is_valid == False
        assert "eligible" in error_msg.lower()
    
    @patch('lambda_function.sqs_client')
    def test_send_to_sqs_success(self, mock_sqs):
        """Test successful SQS message sending."""
        mock_sqs.send_message.return_value = {
            'MessageId': 'test-message-id-123'
        }
        
        queue_url = 'https://sqs.us-east-1.amazonaws.com/123456789012/test-queue'
        response = lambda_function.send_to_sqs(queue_url, self.valid_payload)
        
        assert response['MessageId'] == 'test-message-id-123'
        mock_sqs.send_message.assert_called_once()
    
    @patch('lambda_function.ssm_client')
    @patch('lambda_function.sqs_client')
    def test_lambda_handler_success(self, mock_sqs, mock_ssm):
        """Test successful Lambda handler execution."""
        # Mock SSM parameter
        mock_ssm.get_parameter.return_value = {
            'Parameter': {
                'Value': 'https://sqs.us-east-1.amazonaws.com/123456789012/test-queue'
            }
        }
        
        # Mock SQS send
        mock_sqs.send_message.return_value = {
            'MessageId': 'test-message-id-123'
        }
        
        # Execute handler
        response = lambda_function.lambda_handler(self.api_gateway_event, None)
        
        # Verify response
        assert response['statusCode'] == 200
        body = json.loads(response['body'])
        assert body['messageId'] == 'test-message-id-123'
        assert body['customer_email'] == 'john.smith@example.com'
    
    @patch('lambda_function.ssm_client')
    def test_lambda_handler_invalid_payload(self, mock_ssm):
        """Test Lambda handler with invalid payload."""
        invalid_event = {
            "body": json.dumps({"event_type": "test"})  # Missing required fields
        }
        
        response = lambda_function.lambda_handler(invalid_event, None)
        
        assert response['statusCode'] == 400
        body = json.loads(response['body'])
        assert 'error' in body
    
    @patch('lambda_function.ssm_client')
    def test_lambda_handler_invalid_json(self, mock_ssm):
        """Test Lambda handler with invalid JSON."""
        invalid_event = {
            "body": "not valid json {"
        }
        
        response = lambda_function.lambda_handler(invalid_event, None)
        
        assert response['statusCode'] == 400
        body = json.loads(response['body'])
        assert 'error' in body
    
    def test_get_parameter_caching(self):
        """Test SSM parameter caching."""
        with patch('lambda_function.ssm_client') as mock_ssm:
            mock_ssm.get_parameter.return_value = {
                'Parameter': {'Value': 'test-value'}
            }
            
            # First call should fetch from SSM
            value1 = lambda_function.get_parameter('/test/param')
            assert value1 == 'test-value'
            assert mock_ssm.get_parameter.call_count == 1
            
            # Second call should use cache
            value2 = lambda_function.get_parameter('/test/param')
            assert value2 == 'test-value'
            assert mock_ssm.get_parameter.call_count == 1  # Still 1, not 2


if __name__ == '__main__':
    pytest.main([__file__, '-v'])

