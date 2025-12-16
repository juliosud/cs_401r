# Check Logs Now

## Your webhook was received! ✅

Now check if Agent Registry and Feature Store are working:

### Step 1: Wait 10 seconds
```bash
sleep 10
```

### Step 2: Check Agent Registry logs
```bash
aws logs tail /aws/lambda/referral-orchestrator --region us-east-1 --since 2m --filter-pattern "agent"
```

**Look for:** `"Using agent from registry: upsell-generator v1.0"`

### Step 3: Check Feature Store logs
```bash
aws logs tail /aws/lambda/referral-orchestrator --region us-east-1 --since 2m --filter-pattern "Feature Store"
```

**Look for:** 
- `"Retrieved features from Feature Store"` (if features exist)
- OR `"No features found in Feature Store"` (if empty - this is OK!)

---

## If you see those messages = Both features are working! ✅

