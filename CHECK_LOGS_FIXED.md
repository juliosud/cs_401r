# Check Logs - Fixed for Git Bash

## The issue: Git Bash interprets `/aws/` as a path. Solution: Quote it!

### Step 1: Check Agent Registry logs
```bash
aws logs tail "/aws/lambda/referral-orchestrator" --region us-east-1 --since 2m --filter-pattern "agent"
```

### Step 2: Check Feature Store logs
```bash
aws logs tail "/aws/lambda/referral-orchestrator" --region us-east-1 --since 2m --filter-pattern "Feature Store"
```

### Alternative: Get all recent logs (no filter)
```bash
aws logs tail "/aws/lambda/referral-orchestrator" --region us-east-1 --since 2m
```

Then search for:
- `"Using agent from registry"`
- `"Feature Store"`

---

## Quick one-liner to see everything:
```bash
aws logs tail "/aws/lambda/referral-orchestrator" --region us-east-1 --since 2m | grep -E "(agent|Feature Store)"
```

