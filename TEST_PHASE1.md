# Quick Test - Agent Registry & Feature Store

## In Git Bash (what you're using):

### Step 1: Generate Test Message
```bash
curl -X POST "https://eh2zqwu4h2.execute-api.us-east-1.amazonaws.com/prod/webhook" \
  -H "Content-Type: application/json" \
  -d '{"event_type": "service_completed", "customer": {"email": "test@example.com", "first_name": "John"}, "service": {"satisfaction_score": 5}}'
```

### Step 2: Wait 10 seconds
```bash
sleep 10
```

### Step 3: Check Logs for Agent Registry
```bash
aws logs tail /aws/lambda/referral-orchestrator --region us-east-1 --since 2m --filter-pattern "agent"
```

**Look for:** `"Using agent from registry: upsell-generator v1.0"`

### Step 4: Check Logs for Feature Store
```bash
aws logs tail /aws/lambda/referral-orchestrator --region us-east-1 --since 2m --filter-pattern "Feature Store"
```

**Look for:** `"Retrieved features"` OR `"No features found"` (both OK!)

---

## That's it! If you see those log messages, both features are working! ✅

