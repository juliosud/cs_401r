#!/usr/bin/env python3
"""
Query script for retrieving and viewing generated referral messages from DynamoDB.
Provides various filtering and display options.
"""

import json
import sys
import argparse
import boto3
from datetime import datetime
from typing import List, Dict, Any
from decimal import Decimal

# Initialize AWS clients
cloudformation = boto3.client('cloudformation')
dynamodb = boto3.resource('dynamodb')

# Configuration
STACK_NAME = 'referral-email-system'


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


def decimal_default(obj):
    """JSON serializer for Decimal objects."""
    if isinstance(obj, Decimal):
        return float(obj)
    raise TypeError


def get_table_name() -> str:
    """Retrieve DynamoDB table name from CloudFormation stack."""
    try:
        response = cloudformation.describe_stacks(StackName=STACK_NAME)
        outputs = response['Stacks'][0]['Outputs']
        for output in outputs:
            if output['OutputKey'] == 'DynamoDBTableName':
                return output['OutputValue']
        raise ValueError("DynamoDB table name not found in stack outputs")
    except Exception as e:
        print(f"Error: Failed to get table name: {str(e)}", file=sys.stderr)
        sys.exit(1)


def format_timestamp(timestamp: int) -> str:
    """Convert Unix timestamp to readable format."""
    return datetime.fromtimestamp(timestamp).strftime('%Y-%m-%d %H:%M:%S')


def print_separator():
    """Print a separator line."""
    print(f"{Colors.HEADER}{'='*80}{Colors.ENDC}")


def print_message_summary(item: Dict[str, Any], index: int = None):
    """Print a summary of a message."""
    if index is not None:
        print(f"\n{Colors.BOLD}Message #{index}{Colors.ENDC}")
    else:
        print(f"\n{Colors.BOLD}Message{Colors.ENDC}")
    
    print_separator()
    
    # Status with color coding
    status = item.get('status', 'unknown').upper()
    if status == 'APPROVED':
        status_color = Colors.OKGREEN
    elif status == 'REJECTED':
        status_color = Colors.FAIL
    else:
        status_color = Colors.WARNING
    
    print(f"Status: {status_color}{Colors.BOLD}{status}{Colors.ENDC}")
    print(f"Message ID: {item.get('messageId', 'N/A')}")
    print(f"Created: {item.get('createdAt', 'N/A')}")
    print(f"Customer: {item.get('customerName', 'N/A')} ({item.get('customerEmail', 'N/A')})")
    print(f"Judge Score: {item.get('llmJudgeScore', 'N/A')}/10")
    print(f"Approved: {'Yes' if item.get('judgeApproved') else 'No'}")
    print(f"Retry Count: {item.get('retryCount', 0)}")
    
    if item.get('judgeFeedback'):
        print(f"\n{Colors.OKCYAN}Judge Feedback:{Colors.ENDC}")
        print(f"  {item['judgeFeedback']}")
    
    if item.get('judgeIssues'):
        print(f"\n{Colors.WARNING}Issues:{Colors.ENDC}")
        for issue in item['judgeIssues']:
            print(f"  - {issue}")
    
    print(f"\n{Colors.BOLD}Email Subject:{Colors.ENDC}")
    print(f"  {item.get('emailSubject', 'N/A')}")
    
    print(f"\n{Colors.BOLD}Email Content:{Colors.ENDC}")
    content = item.get('emailContent', 'N/A')
    for line in content.split('\n'):
        print(f"  {line}")
    
    print_separator()


def print_message_list(items: List[Dict[str, Any]]):
    """Print a compact list of messages."""
    if not items:
        print(f"{Colors.WARNING}No messages found.{Colors.ENDC}")
        return
    
    print(f"\n{Colors.BOLD}Found {len(items)} message(s):{Colors.ENDC}\n")
    
    # Table header
    print(f"{Colors.HEADER}{'Index':<6} {'Status':<12} {'Score':<7} {'Customer':<30} {'Created':<20}{Colors.ENDC}")
    print_separator()
    
    for idx, item in enumerate(items, 1):
        status = item.get('status', 'unknown').upper()
        score = item.get('llmJudgeScore', 'N/A')
        customer = f"{item.get('customerName', 'Unknown')[:25]}"
        created = item.get('createdAt', 'N/A')[:19]
        
        # Color code by status
        if status == 'APPROVED':
            status_color = Colors.OKGREEN
        elif status == 'REJECTED':
            status_color = Colors.FAIL
        else:
            status_color = Colors.WARNING
        
        print(f"{idx:<6} {status_color}{status:<12}{Colors.ENDC} {score:<7} {customer:<30} {created:<20}")
    
    print()


def query_all_messages(table_name: str, limit: int = 50) -> List[Dict[str, Any]]:
    """Query all messages from DynamoDB."""
    table = dynamodb.Table(table_name)
    
    try:
        response = table.scan(Limit=limit)
        items = response.get('Items', [])
        
        # Sort by timestamp (most recent first)
        items.sort(key=lambda x: x.get('timestamp', 0), reverse=True)
        
        return items
    except Exception as e:
        print(f"Error: Failed to query messages: {str(e)}", file=sys.stderr)
        sys.exit(1)


def query_by_status(table_name: str, status: str, limit: int = 50) -> List[Dict[str, Any]]:
    """Query messages by status."""
    table = dynamodb.Table(table_name)
    
    try:
        response = table.query(
            IndexName='StatusIndex',
            KeyConditionExpression='#status = :status',
            ExpressionAttributeNames={'#status': 'status'},
            ExpressionAttributeValues={':status': status.lower()},
            ScanIndexForward=False,
            Limit=limit
        )
        return response.get('Items', [])
    except Exception as e:
        print(f"Error: Failed to query messages by status: {str(e)}", file=sys.stderr)
        sys.exit(1)


def query_by_email(table_name: str, email: str, limit: int = 50) -> List[Dict[str, Any]]:
    """Query messages by customer email."""
    table = dynamodb.Table(table_name)
    
    try:
        response = table.query(
            IndexName='CustomerEmailIndex',
            KeyConditionExpression='customerEmail = :email',
            ExpressionAttributeValues={':email': email},
            ScanIndexForward=False,
            Limit=limit
        )
        return response.get('Items', [])
    except Exception as e:
        print(f"Error: Failed to query messages by email: {str(e)}", file=sys.stderr)
        sys.exit(1)


def get_message_by_id(table_name: str, message_id: str, timestamp: int) -> Dict[str, Any]:
    """Get a specific message by ID and timestamp."""
    table = dynamodb.Table(table_name)
    
    try:
        response = table.get_item(
            Key={
                'messageId': message_id,
                'timestamp': timestamp
            }
        )
        return response.get('Item')
    except Exception as e:
        print(f"Error: Failed to get message: {str(e)}", file=sys.stderr)
        sys.exit(1)


def export_to_json(items: List[Dict[str, Any]], filename: str):
    """Export messages to JSON file."""
    try:
        with open(filename, 'w') as f:
            json.dump(items, f, indent=2, default=decimal_default)
        print(f"{Colors.OKGREEN}✓ Exported {len(items)} message(s) to {filename}{Colors.ENDC}")
    except Exception as e:
        print(f"Error: Failed to export to JSON: {str(e)}", file=sys.stderr)
        sys.exit(1)


def main():
    """Main function."""
    parser = argparse.ArgumentParser(
        description='Query and view generated referral messages from DynamoDB',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # List all messages
  python3 query_messages.py --list-all

  # List only approved messages
  python3 query_messages.py --status approved

  # View messages for specific customer
  python3 query_messages.py --email john.smith@example.com

  # View detailed info with full content
  python3 query_messages.py --list-all --detailed

  # Export messages to JSON
  python3 query_messages.py --status approved --export messages.json

  # Limit number of results
  python3 query_messages.py --list-all --limit 10
        """
    )
    
    parser.add_argument('--list-all', action='store_true',
                       help='List all messages')
    parser.add_argument('--status', choices=['approved', 'rejected', 'pending'],
                       help='Filter by message status')
    parser.add_argument('--email', type=str,
                       help='Filter by customer email')
    parser.add_argument('--message-id', type=str,
                       help='Get specific message by ID')
    parser.add_argument('--detailed', action='store_true',
                       help='Show detailed information for each message')
    parser.add_argument('--limit', type=int, default=50,
                       help='Maximum number of messages to retrieve (default: 50)')
    parser.add_argument('--export', type=str, metavar='FILENAME',
                       help='Export results to JSON file')
    parser.add_argument('--table-name', type=str,
                       help='DynamoDB table name (overrides stack lookup)')
    
    args = parser.parse_args()
    
    # Get table name
    if args.table_name:
        table_name = args.table_name
    else:
        table_name = get_table_name()
    
    print(f"{Colors.BOLD}Referral Email System - Message Query Tool{Colors.ENDC}")
    print(f"Table: {table_name}\n")
    
    # Query messages based on arguments
    items = []
    
    if args.message_id:
        # Get specific message (requires timestamp too, but we'll scan for it)
        all_items = query_all_messages(table_name, limit=1000)
        item = next((i for i in all_items if i.get('messageId') == args.message_id), None)
        if item:
            items = [item]
        else:
            print(f"{Colors.FAIL}Message with ID '{args.message_id}' not found.{Colors.ENDC}")
            sys.exit(1)
    elif args.email:
        items = query_by_email(table_name, args.email, args.limit)
    elif args.status:
        items = query_by_status(table_name, args.status, args.limit)
    elif args.list_all:
        items = query_all_messages(table_name, args.limit)
    else:
        parser.print_help()
        sys.exit(0)
    
    # Display results
    if args.detailed:
        for idx, item in enumerate(items, 1):
            print_message_summary(item, idx)
    else:
        print_message_list(items)
    
    # Export if requested
    if args.export:
        export_to_json(items, args.export)
    
    # Print statistics
    if items:
        print(f"\n{Colors.BOLD}Statistics:{Colors.ENDC}")
        approved = sum(1 for item in items if item.get('status') == 'approved')
        rejected = sum(1 for item in items if item.get('status') == 'rejected')
        pending = sum(1 for item in items if item.get('status') == 'pending')
        avg_score = sum(item.get('llmJudgeScore', 0) for item in items) / len(items)
        
        print(f"  Total messages: {len(items)}")
        print(f"  {Colors.OKGREEN}Approved: {approved}{Colors.ENDC}")
        print(f"  {Colors.FAIL}Rejected: {rejected}{Colors.ENDC}")
        print(f"  {Colors.WARNING}Pending: {pending}{Colors.ENDC}")
        print(f"  Average Judge Score: {avg_score:.1f}/10")
        
        if approved > 0:
            approval_rate = (approved / len(items)) * 100
            print(f"  Approval Rate: {approval_rate:.1f}%")


if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        print(f"\n{Colors.WARNING}Interrupted by user{Colors.ENDC}")
        sys.exit(130)
    except Exception as e:
        print(f"{Colors.FAIL}Unexpected error: {str(e)}{Colors.ENDC}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        sys.exit(1)

