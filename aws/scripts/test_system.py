#!/usr/bin/env python3
"""
Integration testing script for Referral Email System.
Tests the complete workflow from webhook to DynamoDB storage.
"""

import json
import sys
import time
import boto3
import requests
from datetime import datetime
from typing import Dict, Any, List

# Initialize AWS clients
cloudformation = boto3.client('cloudformation')
dynamodb = boto3.resource('dynamodb')
sqs = boto3.client('sqs')
logs = boto3.client('logs')

# Configuration
STACK_NAME = 'referral-email-system'
MOCK_DATA_DIR = 'mock_data'
TEST_TIMEOUT = 60  # seconds


class Colors:
    """ANSI color codes for terminal output."""
    HEADER = '\033[95m'
    OKBLUE = '\033[94m'
    OKCYAN = '\033[96m'
    OKGREEN = '\033[92m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'


def print_header(message: str):
    """Print a formatted header."""
    print(f"\n{Colors.HEADER}{Colors.BOLD}{'='*60}{Colors.ENDC}")
    print(f"{Colors.HEADER}{Colors.BOLD}{message}{Colors.ENDC}")
    print(f"{Colors.HEADER}{Colors.BOLD}{'='*60}{Colors.ENDC}\n")


def print_success(message: str):
    """Print a success message."""
    print(f"{Colors.OKGREEN}✓ {message}{Colors.ENDC}")


def print_error(message: str):
    """Print an error message."""
    print(f"{Colors.FAIL}✗ {message}{Colors.ENDC}")


def print_info(message: str):
    """Print an info message."""
    print(f"{Colors.OKCYAN}ℹ {message}{Colors.ENDC}")


def print_warning(message: str):
    """Print a warning message."""
    print(f"{Colors.WARNING}⚠ {message}{Colors.ENDC}")


def get_stack_outputs() -> Dict[str, str]:
    """Retrieve CloudFormation stack outputs."""
    try:
        response = cloudformation.describe_stacks(StackName=STACK_NAME)
        outputs = response['Stacks'][0]['Outputs']
        return {output['OutputKey']: output['OutputValue'] for output in outputs}
    except Exception as e:
        print_error(f"Failed to get stack outputs: {str(e)}")
        sys.exit(1)


def load_mock_payload(filename: str) -> Dict[str, Any]:
    """Load a mock webhook payload from file."""
    try:
        with open(f'{MOCK_DATA_DIR}/{filename}', 'r') as f:
            return json.load(f)
    except Exception as e:
        print_error(f"Failed to load mock payload {filename}: {str(e)}")
        sys.exit(1)


def send_webhook(url: str, payload: Dict[str, Any]) -> Dict[str, Any]:
    """Send webhook POST request."""
    try:
        response = requests.post(
            url,
            json=payload,
            headers={'Content-Type': 'application/json'},
            timeout=10
        )
        response.raise_for_status()
        return {
            'status_code': response.status_code,
            'body': response.json()
        }
    except Exception as e:
        print_error(f"Failed to send webhook: {str(e)}")
        raise


def check_queue_depth(queue_url: str) -> int:
    """Check SQS queue depth."""
    try:
        response = sqs.get_queue_attributes(
            QueueUrl=queue_url,
            AttributeNames=['ApproximateNumberOfMessages', 'ApproximateNumberOfMessagesNotVisible']
        )
        visible = int(response['Attributes'].get('ApproximateNumberOfMessages', 0))
        in_flight = int(response['Attributes'].get('ApproximateNumberOfMessagesNotVisible', 0))
        return visible + in_flight
    except Exception as e:
        print_error(f"Failed to check queue depth: {str(e)}")
        return -1


def wait_for_processing(table_name: str, customer_email: str, timeout: int = TEST_TIMEOUT) -> Dict[str, Any]:
    """Wait for message to be processed and stored in DynamoDB."""
    table = dynamodb.Table(table_name)
    start_time = time.time()
    
    while time.time() - start_time < timeout:
        try:
            # Query by customer email using GSI
            response = table.query(
                IndexName='CustomerEmailIndex',
                KeyConditionExpression='customerEmail = :email',
                ExpressionAttributeValues={':email': customer_email},
                ScanIndexForward=False,  # Most recent first
                Limit=1
            )
            
            if response['Items']:
                return response['Items'][0]
            
            time.sleep(2)
        except Exception as e:
            print_error(f"Error querying DynamoDB: {str(e)}")
            time.sleep(2)
    
    return None


def get_cloudwatch_logs(log_group: str, minutes: int = 5) -> List[str]:
    """Retrieve recent CloudWatch logs."""
    try:
        end_time = int(time.time() * 1000)
        start_time = end_time - (minutes * 60 * 1000)
        
        response = logs.filter_log_events(
            logGroupName=log_group,
            startTime=start_time,
            endTime=end_time,
            limit=50
        )
        
        return [event['message'] for event in response.get('events', [])]
    except Exception as e:
        print_warning(f"Could not retrieve logs from {log_group}: {str(e)}")
        return []


def run_single_test(test_name: str, webhook_url: str, table_name: str, payload_file: str) -> bool:
    """Run a single test case."""
    print_info(f"Running test: {test_name}")
    print(f"  Payload file: {payload_file}")
    
    # Load payload
    payload = load_mock_payload(payload_file)
    customer_email = payload['customer']['email']
    customer_name = f"{payload['customer']['first_name']} {payload['customer']['last_name']}"
    
    print(f"  Customer: {customer_name} ({customer_email})")
    
    # Send webhook
    print("  Sending webhook...", end=" ")
    try:
        webhook_response = send_webhook(webhook_url, payload)
        if webhook_response['status_code'] == 200:
            print_success("Webhook accepted")
        else:
            print_error(f"Webhook failed with status {webhook_response['status_code']}")
            return False
    except Exception as e:
        print_error(f"Webhook failed: {str(e)}")
        return False
    
    # Wait for processing
    print("  Waiting for processing...", end=" ")
    sys.stdout.flush()
    
    result = wait_for_processing(table_name, customer_email)
    
    if result is None:
        print_error("Timeout - message not processed")
        return False
    
    print_success(f"Processed in {int(time.time())} seconds")
    
    # Validate result
    print("  Validating results...")
    
    checks = [
        ("Message ID exists", 'messageId' in result),
        ("Email content generated", result.get('emailContent') and len(result['emailContent']) > 0),
        ("Email subject generated", result.get('emailSubject') and len(result['emailSubject']) > 0),
        ("Status set", result.get('status') in ['approved', 'rejected', 'pending']),
        ("Judge score exists", 'llmJudgeScore' in result),
        ("Customer data stored", 'customerData' in result),
    ]
    
    all_passed = True
    for check_name, check_result in checks:
        if check_result:
            print(f"    {Colors.OKGREEN}✓{Colors.ENDC} {check_name}")
        else:
            print(f"    {Colors.FAIL}✗{Colors.ENDC} {check_name}")
            all_passed = False
    
    # Display results
    print("\n  Generated Content:")
    print(f"    Status: {Colors.BOLD}{result.get('status', 'unknown').upper()}{Colors.ENDC}")
    print(f"    Judge Score: {result.get('llmJudgeScore', 'N/A')}/10")
    print(f"    Approved: {result.get('judgeApproved', False)}")
    print(f"    Retry Count: {result.get('retryCount', 0)}")
    
    if result.get('emailSubject'):
        print(f"    Subject: {result['emailSubject'][:80]}...")
    
    if result.get('emailContent'):
        content = result['emailContent']
        preview = content[:200] + "..." if len(content) > 200 else content
        print(f"    Content Preview:\n")
        for line in preview.split('\n'):
            print(f"      {line}")
    
    if result.get('judgeFeedback'):
        print(f"    Judge Feedback: {result['judgeFeedback']}")
    
    print()
    return all_passed


def run_all_tests():
    """Run all integration tests."""
    print_header("Referral Email System - Integration Tests")
    
    # Get stack outputs
    print_info("Retrieving stack configuration...")
    outputs = get_stack_outputs()
    
    webhook_url = outputs.get('WebhookUrl')
    table_name = outputs.get('DynamoDBTableName')
    queue_url = outputs.get('ReferralQueueUrl')
    
    if not all([webhook_url, table_name, queue_url]):
        print_error("Missing required stack outputs")
        sys.exit(1)
    
    print_success("Stack configuration retrieved")
    print(f"  Webhook URL: {webhook_url}")
    print(f"  DynamoDB Table: {table_name}")
    print(f"  SQS Queue: {queue_url}")
    
    # Check initial queue depth
    initial_depth = check_queue_depth(queue_url)
    print_info(f"Initial queue depth: {initial_depth}")
    
    # Define test cases
    test_cases = [
        ("High-Value Customer - Quarterly Service", "webhook_payload_1.json"),
        ("Termite Treatment Customer", "webhook_payload_2.json"),
        ("Long-Term Monthly Customer", "webhook_payload_3.json"),
    ]
    
    # Run tests
    results = []
    print_header("Running Test Cases")
    
    for test_name, payload_file in test_cases:
        try:
            success = run_single_test(test_name, webhook_url, table_name, payload_file)
            results.append((test_name, success))
            
            # Brief pause between tests
            if len(results) < len(test_cases):
                time.sleep(3)
        except Exception as e:
            print_error(f"Test failed with exception: {str(e)}")
            results.append((test_name, False))
    
    # Summary
    print_header("Test Summary")
    
    passed = sum(1 for _, success in results if success)
    total = len(results)
    
    for test_name, success in results:
        status = f"{Colors.OKGREEN}PASSED{Colors.ENDC}" if success else f"{Colors.FAIL}FAILED{Colors.ENDC}"
        print(f"  {status}: {test_name}")
    
    print(f"\n{Colors.BOLD}Results: {passed}/{total} tests passed{Colors.ENDC}")
    
    # Performance metrics
    print_header("System Metrics")
    
    try:
        cloudwatch = boto3.client('cloudwatch')
        
        # Get approval rate
        response = cloudwatch.get_metric_statistics(
            Namespace='ReferralSystem',
            MetricName='ApprovalRate',
            StartTime=datetime.utcnow().replace(hour=0, minute=0, second=0),
            EndTime=datetime.utcnow(),
            Period=3600,
            Statistics=['Average']
        )
        
        if response['Datapoints']:
            avg_approval = response['Datapoints'][-1]['Average'] * 100
            print_info(f"LLM Judge Approval Rate: {avg_approval:.1f}%")
        
        # Get generation time
        response = cloudwatch.get_metric_statistics(
            Namespace='ReferralSystem',
            MetricName='GenerationTime',
            StartTime=datetime.utcnow().replace(hour=0, minute=0, second=0),
            EndTime=datetime.utcnow(),
            Period=3600,
            Statistics=['Average', 'Maximum']
        )
        
        if response['Datapoints']:
            avg_time = response['Datapoints'][-1]['Average']
            max_time = response['Datapoints'][-1]['Maximum']
            print_info(f"Average Generation Time: {avg_time:.2f}s")
            print_info(f"Maximum Generation Time: {max_time:.2f}s")
    
    except Exception as e:
        print_warning(f"Could not retrieve metrics: {str(e)}")
    
    # Final queue depth
    final_depth = check_queue_depth(queue_url)
    print_info(f"Final queue depth: {final_depth}")
    
    print_header("Testing Complete")
    
    if passed == total:
        print_success(f"All tests passed! System is working correctly.")
        return 0
    else:
        print_error(f"Some tests failed. Check logs for details.")
        print_info("\nTroubleshooting:")
        print("  1. Check CloudWatch Logs:")
        print("     aws logs tail /aws/lambda/referral-webhook-handler --follow")
        print("     aws logs tail /aws/lambda/referral-orchestrator --follow")
        print(f"  2. Check Dead Letter Queue:")
        print(f"     aws sqs receive-message --queue-url {outputs.get('DeadLetterQueueUrl')}")
        print("  3. Verify Bedrock access is enabled in your AWS account")
        return 1


if __name__ == '__main__':
    try:
        exit_code = run_all_tests()
        sys.exit(exit_code)
    except KeyboardInterrupt:
        print_warning("\n\nTest interrupted by user")
        sys.exit(130)
    except Exception as e:
        print_error(f"\n\nUnexpected error: {str(e)}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

