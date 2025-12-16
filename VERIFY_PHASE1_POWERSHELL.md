# Verify Phase 1 Features - PowerShell Commands

## 🧪 **Quick Verification (PowerShell)**

Run these commands in PowerShell to verify Agent Registry and Feature Store:

---

## ✅ **1. Verify Agent Registry**

### **Check if Agent is Registered:**
```powershell
aws dynamodb get-item --table-name AgentRegistry --key '{\"agentId\": {\"S\": \"upsell-generator\"}, \"version\": {\"S\": \"1.0\"}}' --region us-east-1
```

**Expected:** Should show agent with `status: production`

### **Check All Agents:**
```powershell
aws dynamodb scan --table-name AgentRegistry --region us-east-1
```

---

## ✅ **2. Verify Feature Store**

### **Check Feature Store Table Exists:**
```powershell
aws dynamodb describe-table --table-name CustomerFeatures --region us-east-1 --query "Table.TableStatus"
```

**Expected:** `"ACTIVE"`

### **Check if Any Features Stored:**
```powershell
aws dynamodb scan --table-name CustomerFeatures --region us-east-1 --max-items 5
```

**Expected:** Empty initially (will populate as services complete)

---

## ✅ **3. Test End-to-End (Generate a Message)**

### **Send Test Webhook:**
```powershell
$body = @{
    event_type = "service_completed"
    customer = @{
        email = "test@example.com"
        first_name = "John"
        last_name = "Smith"
    }
    service = @{
        type = "Quarterly Pest Control"
        satisfaction_score = 5
    }
} | ConvertTo-Json -Depth 10

Invoke-RestMethod -Uri "https://eh2zqwu4h2.execute-api.us-east-1.amazonaws.com/prod/webhook" -Method Post -Body $body -ContentType "application/json"
```

**Or use curl (if available):**
```powershell
curl.exe -X POST "https://eh2zqwu4h2.execute-api.us-east-1.amazonaws.com/prod/webhook" -H "Content-Type: application/json" -d '{\"event_type\": \"service_completed\", \"customer\": {\"email\": \"test@example.com\", \"first_name\": \"John\"}, \"service\": {\"satisfaction_score\": 5}}'
```

---

## ✅ **4. Check CloudWatch Logs (MOST IMPORTANT!)**

### **Check Orchestrator Logs for Agent Registry:**
```powershell
aws logs tail /aws/lambda/referral-orchestrator --region us-east-1 --since 10m --filter-pattern "agent"
```

**Look for:**
- ✅ `"Using agent from registry: upsell-generator v1.0"`
- ✅ `"Using agent version: 1.0, model: amazon.nova-pro-v1:0"`

### **Check Orchestrator Logs for Feature Store:**
```powershell
aws logs tail /aws/lambda/referral-orchestrator --region us-east-1 --since 10m --filter-pattern "Feature Store"
```

**Look for:**
- ✅ `"Retrieved features from Feature Store for {email}"` (if features exist)
- ✅ `"No features found in Feature Store for {email}"` (if empty - this is OK!)
- ✅ `"Using features from Feature Store: satisfaction=X, services=Y, LTV=Z"` (if features found)

### **Get Recent Logs (Last 5 minutes):**
```powershell
aws logs tail /aws/lambda/referral-orchestrator --region us-east-1 --since 5m
```

---

## ✅ **5. Verify Generated Message Has Agent Version**

### **Query DynamoDB for Latest Message:**
```powershell
aws dynamodb scan --table-name ReferralMessages --region us-east-1 --max-items 1 --query "Items[0]"
```

**Look for:**
- ✅ `"agentVersion": {"S": "1.0"}` (from Agent Registry!)

### **Or Use Python Script:**
```powershell
cd final-project
python aws/scripts/query_messages.py --list-all --detailed
```

**Check output for:**
- ✅ `agentVersion: "1.0"` in the message data

---

## 🎯 **Quick Verification Checklist (PowerShell)**

Run these commands in order:

```powershell
# 1. Check Agent Registry
aws dynamodb get-item --table-name AgentRegistry --key '{\"agentId\": {\"S\": \"upsell-generator\"}, \"version\": {\"S\": \"1.0\"}}' --region us-east-1

# 2. Check Feature Store table exists
aws dynamodb describe-table --table-name CustomerFeatures --region us-east-1 --query "Table.TableStatus"

# 3. Generate a test message (wait 10 seconds after this)
$testBody = '{\"event_type\": \"service_completed\", \"customer\": {\"email\": \"verify@test.com\", \"first_name\": \"Test\"}, \"service\": {\"satisfaction_score\": 5}}'
curl.exe -X POST "https://eh2zqwu4h2.execute-api.us-east-1.amazonaws.com/prod/webhook" -H "Content-Type: application/json" -d $testBody

# 4. Wait 10 seconds, then check logs for Agent Registry
Start-Sleep -Seconds 10
aws logs tail /aws/lambda/referral-orchestrator --region us-east-1 --since 2m --filter-pattern "agent"

# 5. Check logs for Feature Store
aws logs tail /aws/lambda/referral-orchestrator --region us-east-1 --since 2m --filter-pattern "Feature Store"

# 6. Verify message has agentVersion
cd final-project
python aws/scripts/query_messages.py --list-all --detailed
```

---

## ✅ **Expected Results**

### **Agent Registry:**
- ✅ Agent `upsell-generator` v1.0 exists in DynamoDB
- ✅ Status: `production`
- ✅ Logs show: `"Using agent from registry"`
- ✅ Messages have: `agentVersion: "1.0"`

### **Feature Store:**
- ✅ Table `CustomerFeatures` exists and is ACTIVE
- ✅ Logs show: `"Retrieved features"` OR `"No features found"` (both OK!)
- ✅ If features exist: Logs show `"Using features from Feature Store: satisfaction=..."`

---

## 📝 **Step-by-Step Verification**

### **Step 1: Verify Agent Registry (30 seconds)**
```powershell
aws dynamodb get-item --table-name AgentRegistry --key '{\"agentId\": {\"S\": \"upsell-generator\"}, \"version\": {\"S\": \"1.0\"}}' --region us-east-1
```
**✅ Success if:** You see JSON with `"status": {"S": "production"}`

### **Step 2: Verify Feature Store Table (30 seconds)**
```powershell
aws dynamodb describe-table --table-name CustomerFeatures --region us-east-1 --query "Table.TableStatus"
```
**✅ Success if:** Output is `"ACTIVE"`

### **Step 3: Generate Test Message (1 minute)**
```powershell
curl.exe -X POST "https://eh2zqwu4h2.execute-api.us-east-1.amazonaws.com/prod/webhook" -H "Content-Type: application/json" -d '{\"event_type\": \"service_completed\", \"customer\": {\"email\": \"test@example.com\", \"first_name\": \"John\"}, \"service\": {\"satisfaction_score\": 5}}'
```
**✅ Success if:** No error (may take 10-15 seconds to process)

### **Step 4: Check Logs for Agent Registry (30 seconds)**
```powershell
Start-Sleep -Seconds 10
aws logs tail /aws/lambda/referral-orchestrator --region us-east-1 --since 2m --filter-pattern "agent"
```
**✅ Success if:** You see `"Using agent from registry: upsell-generator v1.0"`

### **Step 5: Check Logs for Feature Store (30 seconds)**
```powershell
aws logs tail /aws/lambda/referral-orchestrator --region us-east-1 --since 2m --filter-pattern "Feature Store"
```
**✅ Success if:** You see either:
- `"Retrieved features from Feature Store"` (features exist)
- `"No features found in Feature Store"` (empty - this is OK!)

### **Step 6: Verify Message Stored (30 seconds)**
```powershell
cd final-project
python aws/scripts/query_messages.py --list-all --detailed
```
**✅ Success if:** Latest message shows `agentVersion: "1.0"`

---

## 🎉 **All Tests Pass = Phase 1 Working!**

If all 6 steps show success, your Agent Registry and Feature Store are working correctly!

