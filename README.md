# AI-Powered Service Upsell System

Serverless system that generates personalized service upsell messages using Amazon Bedrock (Nova Pro AI).

**Architecture:** Webhook → API Gateway → Lambda → SQS → Lambda → Amazon Bedrock (AI Generator + Judge) → DynamoDB

---

## Quick Start (10 minutes)

### Prerequisites

1. **AWS Account** with credentials configured
2. **AWS CLI** installed ([guide](https://docs.aws.amazon.com/cli/latest/userguide/getting-started-install.html))
3. **Python 3.11+** 
4. **Node.js 18+**

### Configure AWS Credentials

```bash
aws configure
# Enter your AWS Access Key ID
# Enter your AWS Secret Access Key
# Region: us-east-1
# Output format: json
```

---

## Step 1: Deploy to AWS (5 minutes)

```bash
# Clone the repo
git clone <your-repo-url>
cd final-project

# Make deploy script executable
chmod +x aws/scripts/deploy.sh

# Deploy all AWS resources
./aws/scripts/deploy.sh
```

**What this creates:**
- ✅ API Gateway webhook endpoint
- ✅ 2 Lambda functions (webhook handler + orchestrator)
- ✅ SQS queue + Dead Letter Queue
- ✅ DynamoDB table for messages
- ✅ S3 bucket for brand guidelines (unique per AWS account)
- ✅ IAM roles and permissions
- ✅ CloudWatch logs

**After deployment completes**, copy the **Webhook URL** from the output:
```
Webhook URL: https://abc123xyz.execute-api.us-east-1.amazonaws.com/prod/webhook
```

---

## Step 2: Configure Frontend (2 minutes)

```bash
# Create environment file for the UI
cd client
cp .env.example .env

# Edit .env and paste your Webhook URL
nano .env
```

Your `.env` should look like:
```bash
VITE_WEBHOOK_URL=https://YOUR-ACTUAL-API-ID.execute-api.us-east-1.amazonaws.com/prod/webhook
```

---

## Step 3: Run the UI (2 minutes)

```bash
# Go back to project root
cd ..

# Install Python dependencies (first time only)
pip3 install -r server/requirements.txt

# Install Node dependencies (first time only)
cd client && npm install && cd ..

# Start the system (runs both backend and frontend)
./START.sh
```

**Open in browser:** http://localhost:3000

You should see the **Guardian Pest Control** UI! 🎉

---

## How to Use

### Generate Messages
1. Select a customer scenario from the dropdown
2. Click **"Show Details"** to see full customer data
3. Click **"Generate Message"**
4. Wait ~10 seconds for AI processing
5. Click **"Show"** on "All Message History" to see result

### View Service Catalog
1. Click **"Service Catalog"** section
2. See all available services the AI can recommend
3. Each service shows triggers, benefits, and ideal customers

### AI Decision Making
- **Approved messages**: Show AI's reasoning for approval
- **Rejected messages**: Show rejection category and detailed reasoning
  - Customer Appropriateness (timing, satisfaction, recent messages)
  - Service Not Valid (not in catalog, already has it)
  - Brand Guidelines (tone, quality issues)

---

## Test Scenarios

The UI includes 7 test scenarios:

| Scenario | Expected Result | Why |
|----------|----------------|-----|
| Happy One-Time Customer | ✅ APPROVE | Good candidate for Quarterly Plan |
| Older Home | ✅ APPROVE | 1920s home needs Termite Protection |
| Service Complaint | ❌ REJECT | Low satisfaction (2/5), complaints in notes |
| Spring Season | ✅ APPROVE | Pool/backyard, asked about mosquitoes |
| Late Technician | ❌ REJECT | Satisfaction 3/5, frustration in notes |
| Attic Noises | ✅ APPROVE | Hearing wildlife, asked about services |
| Recurring Issues | ✅ APPROVE | Needs Monthly Plan upgrade |
| Recent Upsell Sent | ❌ REJECT | Last message sent < 30 days ago |

---

## AWS Costs & Cleanup

### Current Costs
**$0.00/month** - Everything is serverless with generous free tiers:
- Lambda: 1M requests/month FREE
- API Gateway: 1M requests/month FREE  
- DynamoDB: 25GB + operations FREE
- S3: 5GB storage FREE
- SQS: 1M requests/month FREE

### Monitor Costs
```bash
# Check spending
aws ce get-cost-and-usage \
  --time-period Start=$(date -u +%Y-%m-01),End=$(date -u +%Y-%m-%d) \
  --granularity MONTHLY \
  --metrics BlendedCost
```

### Clean Up (When Done)
Delete ALL AWS resources in one command:

```bash
chmod +x aws/scripts/cleanup.sh
./aws/scripts/cleanup.sh
```

This removes everything (Lambdas, API Gateway, SQS, DynamoDB, S3, CloudWatch logs, IAM roles).

---

## Project Structure

```
├── client/                     # React TypeScript UI (port 3000)
│   ├── src/
│   │   ├── App.tsx            # Main UI component
│   │   ├── types.ts           # TypeScript interfaces
│   │   ├── mockData.ts        # Test customer scenarios
│   │   └── App.css            # Dark theme styles
│   ├── .env.example           # Environment config template
│   └── package.json
├── server/                     # Flask backend (port 8000, local dev only)
│   ├── app.py                 # API for UI to query DynamoDB
│   └── requirements.txt
├── aws/
│   ├── lambda/
│   │   ├── webhook_handler/   # Receives webhooks, validates, sends to SQS
│   │   └── orchestrator/      # Processes messages with Bedrock AI
│   ├── cloudformation/
│   │   └── template.yaml      # Infrastructure as Code (all AWS resources)
│   ├── scripts/
│   │   ├── deploy.sh          # Automated deployment
│   │   ├── cleanup.sh         # Delete all AWS resources
│   │   └── query_messages.py  # CLI tool to query DynamoDB
│   └── brand_guidelines/
│       └── guidelines.json    # Service catalog + brand voice for AI
├── mock_data/                  # Example webhook payloads for testing
├── START.sh                    # Start local UI (backend + frontend)
└── README.md
```

---

## Architecture Details

### How It Works

1. **Webhook Received** → API Gateway receives customer data
2. **Validation** → Lambda validates JSON, sends to SQS queue
3. **AI Generator** → Orchestrator Lambda fetches brand guidelines, calls Bedrock to generate upsell message
4. **AI Judge** → Bedrock evaluates if message should be sent:
   - Checks customer appropriateness (timing, satisfaction, recent messages)
   - Validates service exists in catalog
   - Ensures brand quality
5. **Retry Logic** → If rejected for brand/service reasons, retries with feedback (max 2 retries)
6. **Storage** → Saves all messages (approved + rejected) to DynamoDB
7. **Metrics** → Logs to CloudWatch for monitoring

### Key Features

- ✅ **Flexible Data Structure**: Accepts any JSON payload
- ✅ **Smart AI Judge**: Blocks inappropriate messages (low satisfaction, recent upsells, complaints)
- ✅ **Service Catalog**: AI only recommends real services company offers
- ✅ **Feedback Loop**: Generator improves based on judge feedback
- ✅ **Full Logging**: All decisions stored in DynamoDB with reasoning
- ✅ **Real-time Monitoring**: CloudWatch metrics and logs

---

## Troubleshooting

### Deployment Failed
```bash
# Delete the stack and try again
aws cloudformation delete-stack --stack-name referral-email-system
aws cloudformation wait stack-delete-complete --stack-name referral-email-system
./aws/scripts/deploy.sh
```

### UI Not Loading
```bash
# Make sure backend is running
ps aux | grep python | grep app.py

# Make sure frontend is running  
ps aux | grep node | grep vite

# Restart
./START.sh
```

### No Messages Appearing
```bash
# Check Lambda logs
aws logs tail /aws/lambda/referral-orchestrator --follow --region us-east-1

# Query DynamoDB directly
python3 aws/scripts/query_messages.py --list-all
```

### Judge Not Blocking Recent Upsells
The judge receives the current date (2025-12-12) and calculates days. Check CloudWatch logs to see the judge's reasoning.

---

## Customization

### Add New Services
Edit `aws/brand_guidelines/guidelines.json`:
```json
{
  "service_catalog": {
    "specialized_treatments": [
      {
        "name": "Your New Service",
        "description": "What it does",
        "ideal_for": "Who it's for",
        "upsell_triggers": ["when to recommend"],
        "benefits": ["benefit 1", "benefit 2"]
      }
    ]
  }
}
```

Then redeploy:
```bash
./aws/scripts/deploy.sh
```

### Change AI Model
Edit `aws/cloudformation/template.yaml`:
```yaml
BedrockModelId:
  Default: 'amazon.nova-pro-v1:0'  # Change to any Bedrock model
```

Available models:
- `amazon.nova-pro-v1:0` (current, fast, no setup)
- `amazon.nova-lite-v1:0` (cheaper, faster)
- `anthropic.claude-3-haiku-20240307-v1:0` (requires use case form)

### Modify Brand Voice
Edit `aws/brand_guidelines/guidelines.json` → `brand_voice` section

---

## Development Commands

```bash
# Deploy AWS infrastructure
./aws/scripts/deploy.sh

# Start local UI
./START.sh

# Query messages from CLI
python3 aws/scripts/query_messages.py --list-all --detailed

# Clear all messages
python3 -c "import boto3; table = boto3.resource('dynamodb').Table('ReferralMessages'); [table.delete_item(Key={'messageId': i['messageId'], 'timestamp': i['timestamp']}) for i in table.scan()['Items']]; print('Cleared!')"

# View CloudWatch logs
aws logs tail /aws/lambda/referral-orchestrator --follow --region us-east-1

# Clean up everything
./aws/scripts/cleanup.sh
```

---

## Contributing

This system is designed to be flexible and extensible:
- **Any JSON structure** accepted (no required fields)
- **Service catalog driven** (AI only recommends what you define)
- **Transparent AI decisions** (all reasoning logged)
- **Easy to customize** (brand voice, services, triggers)

Perfect for:
- Service upsell automation
- AI-powered customer communication
- Learning AWS serverless + Bedrock
- MLOps project demonstrations

---

## License

MIT License - Use freely for your projects!
