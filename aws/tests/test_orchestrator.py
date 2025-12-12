"""
Unit tests for Orchestrator Lambda function.
"""

import json
import pytest
import sys
import os
from unittest.mock import Mock, patch, MagicMock
from decimal import Decimal

# Add lambda function directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../lambda/orchestrator'))

import lambda_function


class TestOrchestrator:
    """Test cases for orchestrator function."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.customer_data = {
            "event_type": "service_completed",
            "customer": {
                "id": "CUST-12345",
                "first_name": "John",
                "last_name": "Smith",
                "email": "john.smith@example.com",
                "address": {
                    "city": "Austin",
                    "state": "TX"
                }
            },
            "service": {
                "type": "Quarterly Pest Control",
                "date": "2024-12-10",
                "technician": "Mike Johnson",
                "satisfaction_score": 5,
                "next_service": "2025-03-10"
            },
            "customer_lifetime_value": "high",
            "services_count": 8
        }
        
        self.brand_guidelines = """
        Brand Voice: Friendly and professional
        Tone: Conversational
        Key Messages: Reliability, expertise, satisfaction
        """
        
        self.sqs_event = {
            "Records": [
                {
                    "messageId": "test-message-id",
                    "body": json.dumps({
                        "webhook_payload": self.customer_data,
                        "received_at": "2024-12-10T10:00:00",
                        "source": "webhook_handler"
                    })
                }
            ]
        }
    
    def test_format_customer_data(self):
        """Test customer data formatting."""
        formatted = lambda_function.format_customer_data(self.customer_data)
        
        assert "John Smith" in formatted
        assert "Austin, TX" in formatted
        assert "Quarterly Pest Control" in formatted
        assert "high" in formatted
    
    def test_generate_email_subject(self):
        """Test email subject generation."""
        subject = lambda_function.generate_email_subject("John")
        
        assert "John" in subject
        assert "Referral" in subject or "referral" in subject
    
    @patch('lambda_function.s3_client')
    def test_get_brand_guidelines(self, mock_s3):
        """Test fetching brand guidelines from S3."""
        guidelines = {
            "brand_voice": "Friendly",
            "tone": "Conversational",
            "key_messages": ["reliability", "expertise"],
            "formatting": ["short paragraphs"],
            "avoid": ["aggressive sales"],
            "preferred_language": ["use 'you'"]
        }
        
        mock_s3.get_object.return_value = {
            'Body': Mock(read=Mock(return_value=json.dumps(guidelines).encode()))
        }
        
        result = lambda_function.get_brand_guidelines('test-bucket')
        
        assert "Friendly" in result
        assert "Conversational" in result
        mock_s3.get_object.assert_called_once()
    
    @patch('lambda_function.bedrock_client')
    @patch('lambda_function.cloudwatch')
    def test_call_bedrock_generator(self, mock_cloudwatch, mock_bedrock):
        """Test Bedrock LLM generator call."""
        mock_response = {
            'body': Mock(
                read=Mock(return_value=json.dumps({
                    'content': [{
                        'text': 'This is a test referral email content...'
                    }]
                }).encode())
            )
        }
        mock_bedrock.invoke_model.return_value = mock_response
        
        result = lambda_function.call_bedrock_generator(
            'anthropic.claude-sonnet-4-20250514-v1:0',
            "Customer: John Smith",
            self.brand_guidelines
        )
        
        assert 'email_content' in result
        assert result['email_content'] == 'This is a test referral email content...'
        assert 'generation_time' in result
        mock_bedrock.invoke_model.assert_called_once()
    
    @patch('lambda_function.bedrock_client')
    @patch('lambda_function.cloudwatch')
    def test_call_bedrock_judge_approved(self, mock_cloudwatch, mock_bedrock):
        """Test Bedrock LLM judge call with approval."""
        judgment = {
            "approved": True,
            "score": 9,
            "issues": [],
            "feedback": "Excellent email"
        }
        
        mock_response = {
            'body': Mock(
                read=Mock(return_value=json.dumps({
                    'content': [{
                        'text': json.dumps(judgment)
                    }]
                }).encode())
            )
        }
        mock_bedrock.invoke_model.return_value = mock_response
        
        result = lambda_function.call_bedrock_judge(
            'anthropic.claude-sonnet-4-20250514-v1:0',
            'Test email content',
            self.brand_guidelines
        )
        
        assert result['approved'] == True
        assert result['score'] == 9
        assert result['feedback'] == "Excellent email"
    
    @patch('lambda_function.bedrock_client')
    @patch('lambda_function.cloudwatch')
    def test_call_bedrock_judge_rejected(self, mock_cloudwatch, mock_bedrock):
        """Test Bedrock LLM judge call with rejection."""
        judgment = {
            "approved": False,
            "score": 5,
            "issues": ["Too aggressive", "Missing key message"],
            "feedback": "Needs improvement"
        }
        
        mock_response = {
            'body': Mock(
                read=Mock(return_value=json.dumps({
                    'content': [{
                        'text': json.dumps(judgment)
                    }]
                }).encode())
            )
        }
        mock_bedrock.invoke_model.return_value = mock_response
        
        result = lambda_function.call_bedrock_judge(
            'anthropic.claude-sonnet-4-20250514-v1:0',
            'Test email content',
            self.brand_guidelines
        )
        
        assert result['approved'] == False
        assert result['score'] == 5
        assert len(result['issues']) == 2
    
    @patch('lambda_function.dynamodb')
    def test_store_in_dynamodb(self, mock_dynamodb):
        """Test storing message in DynamoDB."""
        mock_table = Mock()
        mock_dynamodb.Table.return_value = mock_table
        
        message_data = {
            'messageId': 'test-123',
            'customerEmail': 'test@example.com',
            'emailContent': 'Test content',
            'status': 'approved'
        }
        
        lambda_function.store_in_dynamodb('TestTable', message_data)
        
        mock_table.put_item.assert_called_once()
    
    @patch('lambda_function.get_parameter')
    @patch('lambda_function.get_brand_guidelines')
    @patch('lambda_function.call_bedrock_generator')
    @patch('lambda_function.call_bedrock_judge')
    @patch('lambda_function.store_in_dynamodb')
    @patch('lambda_function.cloudwatch')
    def test_process_message_approved(self, mock_cw, mock_store, mock_judge, 
                                      mock_generator, mock_guidelines, mock_param):
        """Test complete message processing with approval."""
        # Setup mocks
        mock_param.side_effect = [
            'test-bucket',
            'anthropic.claude-sonnet-4-20250514-v1:0',
            'TestTable'
        ]
        mock_guidelines.return_value = self.brand_guidelines
        mock_generator.return_value = {
            'email_content': 'Test email content',
            'generation_time': 2.5,
            'model_id': 'test-model',
            'retry_count': 0
        }
        mock_judge.return_value = {
            'approved': True,
            'score': 9,
            'issues': [],
            'feedback': 'Great email',
            'judgment_time': 1.2
        }
        
        # Process message
        message_body = {
            'webhook_payload': self.customer_data,
            'received_at': '2024-12-10T10:00:00'
        }
        
        result = lambda_function.process_message(message_body)
        
        # Verify results
        assert result['approved'] == True
        assert result['retry_count'] == 0
        assert result['customer_email'] == 'john.smith@example.com'
        mock_store.assert_called_once()
    
    @patch('lambda_function.get_parameter')
    @patch('lambda_function.get_brand_guidelines')
    @patch('lambda_function.call_bedrock_generator')
    @patch('lambda_function.call_bedrock_judge')
    @patch('lambda_function.store_in_dynamodb')
    @patch('lambda_function.cloudwatch')
    def test_process_message_with_retry(self, mock_cw, mock_store, mock_judge, 
                                       mock_generator, mock_guidelines, mock_param):
        """Test message processing with retry logic."""
        # Setup mocks
        mock_param.side_effect = [
            'test-bucket',
            'anthropic.claude-sonnet-4-20250514-v1:0',
            'TestTable'
        ]
        mock_guidelines.return_value = self.brand_guidelines
        mock_generator.return_value = {
            'email_content': 'Test email content',
            'generation_time': 2.5,
            'model_id': 'test-model',
            'retry_count': 0
        }
        
        # First attempt rejected, second approved
        mock_judge.side_effect = [
            {
                'approved': False,
                'score': 5,
                'issues': ['Issue 1'],
                'feedback': 'Needs work',
                'judgment_time': 1.0
            },
            {
                'approved': True,
                'score': 8,
                'issues': [],
                'feedback': 'Better',
                'judgment_time': 1.0
            }
        ]
        
        # Process message
        message_body = {
            'webhook_payload': self.customer_data,
            'received_at': '2024-12-10T10:00:00'
        }
        
        result = lambda_function.process_message(message_body)
        
        # Verify retry occurred
        assert result['approved'] == True
        assert result['retry_count'] == 1
        assert mock_generator.call_count == 2
        assert mock_judge.call_count == 2


if __name__ == '__main__':
    pytest.main([__file__, '-v'])

