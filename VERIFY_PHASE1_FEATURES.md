# Verify Phase 1 Features: Agent Registry & Feature Store

## 🧪 **Quick Verification Commands**

Run these commands to verify Agent Registry and Feature Store are working:

---

## ✅ **1. Verify Agent Registry**

### **Check if Agent is Registered:**
```bash
aws dynamodb get-item \
  --table-name AgentRegistry \
  --key '{"agentId": {"S": "upsell-generator"}, "version": {"S": "1.0"}}' \
  --region us-east-1
```

**Expected Output:**
- Should show agent with `status: production`
- Should show `bedrockModel: amazon.nova-pro-v1:0`

### **Check All Agents:**
```bash
aws dynamodb scan \
  --table-name AgentRegistry \
  --region us-east-1
```

---

## ✅ **2. Verify Feature Store**

### **Check Feature Store Table Exists:**
```bash
aws dynamodb describe-table \
  --table-name CustomerFeatures \
  --region us-east-1 \
  --query "Table.TableStatus"
```

**Expected:** `"ACTIVE"`

### **Check if Any Features Stored:**
```bash
aws dynamodb scan \
  --table-name CustomerFeatures \
  --region us-east-1 \
  --max-items 5
```

**Expected:** Empty initially (will populate as services complete)

---

## ✅ **3. Test End-to-End (Generate a Message)**

### **Send Test Webhook:**
```bash
curl -X POST "https://eh2zqwu4h2.execute-api.us-east-1.amazonaws.com/prod/webhook" \
  -H "Content-Type: application/json" \
  -d "{\"event_type\": \"service_completed\", \"customer\": {\"email\": \"test@example.com\", \"first_name\": \"John\", \"last_name\": \"Smith\"}, \"service\": {\"type\": \"Quarterly Pest Control\", \"satisfaction_score\": 5}}"
```

---

## ✅ **4. Check CloudWatch Logs (Most Important!)**

### **Check Orchestrator Logs for Agent Registry:**
```bash
aws logs tail /aws/lambda/referral-orchestrator \
  --region us-east-1 \
  --since 10m \
  --filter-pattern "agent"
```

**Look for:**
- ✅ `"Using agent from registry: upsell-generator v1.0"`
- ✅ `"Using agent version: 1.0, model: amazon.nova-pro-v1:0"`

### **Check Orchestrator Logs for Feature Store:**
```bash
aws logs tail /aws/lambda/referral-orchestrator \
  --region us-east-1 \
  --since 10m \
  --filter-pattern "Feature Store"
```

**Look for:**
- ✅ `"Retrieved features from Feature Store for {email}"` (if features exist)
- ✅ `"No features found in Feature Store for {email}"` (if empty - this is OK!)
- ✅ `"Using features from Feature Store: satisfaction=X, services=Y, LTV=Z"` (if features found)

### **Get Recent Logs (Last 5 minutes):**
```bash
aws logs tail /aws/lambda/referral-orchestrator \
  --region us-east-1 \
  --since 5m
```

---

## ✅ **5. Verify Generated Message Has Agent Version**

### **Query DynamoDB for Latest Message:**
```bash
aws dynamodb scan \
  --table-name ReferralMessages \
  --region us-east-1 \
  --max-items 1 \
  --query "Items[0]"
```

**Look for:**
- ✅ `"agentVersion": {"S": "1.0"}` (from Agent Registry!)

### **Or Use Python Script:**
```bash
cd final-project
python aws/scripts/query_messages.py --list-all --detailed
```

**Check output for:**
- ✅ `agentVersion: "1.0"` in the message data

---

## ✅ **6. Test Feature Store Population**

### **Manually Populate Feature Store:**
```python
import boto3
import json

lambda_client = boto3.client('lambda', region_name='us-east-1')

# Test payload
payload = {
    "event_type": "service_completed",
    "customer": {
        "email": "test@example.com",
        "first_name": "John",
        "last_name": "Smith"
    },
    "service": {
        "type": "Quarterly Pest Control",
        "satisfaction_score": 5
    },
    "services_count": 3
}

# Call feature enricher
response = lambda_client.invoke(
    FunctionName='referral-feature-enricher',
    Payload=json.dumps({'customer_data': payload})
)

result = json.loads(response['Payload'].read())
print(json.dumps(result, indent=2))
```

### **Then Check Feature Store:**
```bash
aws dynamodb get-item \
  --table-name CustomerFeatures \
  --key '{"customerEmail": {"S": "test@example.com"}}' \
  --region us-east-1
```

**Expected:** Should show features with `satisfaction_avg`, `service_count`, `lifetime_value`

---

## ✅ **7. Full End-to-End Test**

### **Step 1: Generate Message (with Feature Store populated)**
```bash
curl -X POST "https://eh2zqwu4h2.execute-api.us-east-1.amazonaws.com/prod/webhook" \
  -H "Content-Type: application/json" \
  -d @mock_data/webhook_payload_1.json
```

### **Step 2: Check Logs (should show both features)**
```bash
aws logs tail /aws/lambda/referral-orchestrator \
  --region us-east-1 \
  --since 2m \
  --format short
```

**Look for:**
1. ✅ `"Using agent from registry: upsell-generator v1.0"`
2. ✅ `"Retrieved features from Feature Store"` OR `"No features found"` (both OK)
3. ✅ `"Using features from Feature Store: satisfaction=..."` (if features exist)

### **Step 3: Verify Message Stored**
```bash
python aws/scripts/query_messages.py --list-all --detailed | head -50
```

**Check:**
- ✅ Message has `agentVersion: "1.0"`
- ✅ Message was generated successfully

---

## 🎯 **Quick Verification Checklist**

Run these in order:

```bash
# 1. Check Agent Registry
aws dynamodb get-item --table-name AgentRegistry --key '{"agentId": {"S": "upsell-generator"}, "version": {"S": "1.0"}}' --region us-east-1

# 2. Check Feature Store table exists
aws dynamodb describe-table --table-name CustomerFeatures --region us-east-1 --query "Table.TableStatus"

# 3. Generate a test message
curl -X POST "https://eh2zqwu4h2.execute-api.us-east-1.amazonaws.com/prod/webhook" -H "Content-Type: application/json" -d "{\"event_type\": \"service_completed\", \"customer\": {\"email\": \"verify@test.com\", \"first_name\": \"Test\"}, \"service\": {\"satisfaction_score\": 5}}"

# 4. Check logs (wait 10 seconds first)
aws logs tail /aws/lambda/referral-orchestrator --region us-east-1 --since 2m --filter-pattern "agent"

# 5. Check logs for Feature Store
aws logs tail /aws/lambda/referral-orchestrator --region us-east-1 --since 2m --filter-pattern "Feature Store"

# 6. Verify message has agentVersion
python aws/scripts/query_messages.py --list-all --detailed | grep -i "agentVersion"
```

---

## ✅ **Expected Results**

### **Agent Registry:**
- ✅ Agent `upsell-generator` v1.0 exists
- ✅ Status: `production`
- ✅ Logs show: `"Using agent from registry"`
- ✅ Messages have: `agentVersion: "1.0"`

### **Feature Store:**
- ✅ Table `CustomerFeatures` exists and is ACTIVE
- ✅ Logs show: `"Retrieved features"` OR `"No features found"` (both OK)
- ✅ If features exist: Logs show `"Using features from Feature Store: satisfaction=..."`

---

## 🚨 **Troubleshooting**

### **If Agent Registry not found:**
```bash
# Re-register agent
python aws/scripts/register_initial_agent.py
```

### **If Feature Store query fails:**
- Check IAM permissions (should be automatic)
- Check SSM parameter: `/referral-system/customer-features-table-name`
- System should still work (backward compatible)

### **If logs don't show features:**
- Feature Store might be empty (this is OK!)
- System works without features (backward compatible)
- To populate: Call `feature_enricher` Lambda or wait for services to complete

---

## 📊 **Summary**

**To verify everything is working:**

1. ✅ **Agent Registry:** Check DynamoDB + Check logs for "Using agent from registry"
2. ✅ **Feature Store:** Check table exists + Check logs for Feature Store queries
3. ✅ **Integration:** Generate message + Check logs show both features working
4. ✅ **Message Storage:** Verify message has `agentVersion: "1.0"`

**All commands work in Git Bash or Windows CMD (with AWS CLI installed)!**

