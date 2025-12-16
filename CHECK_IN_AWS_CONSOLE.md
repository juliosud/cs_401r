# Check Agent Registry & Feature Store in AWS Console

## ✅ **1. Check Agent Registry**

### **Go to DynamoDB:**
1. Open AWS Console → **DynamoDB** → **Tables**
2. Click on **`AgentRegistry`** table
3. Click **"Explore table items"**
4. **Look for:** 
   - ✅ Should see: `upsell-generator` with `version: 1.0`
   - ✅ Should see: `status: production`
   - ✅ Should see: `bedrockModel: amazon.nova-pro-v1:0`

**If you see this = Agent Registry is working! ✅**

---

## ✅ **2. Check Feature Store**

### **Go to DynamoDB:**
1. Open AWS Console → **DynamoDB** → **Tables**
2. Click on **`CustomerFeatures`** table
3. Click **"Explore table items"**
4. **Look for:**
   - ✅ Table exists and is **ACTIVE** = Feature Store is deployed!
   - ✅ Empty table is OK (will populate as services complete)

**If table exists = Feature Store is deployed! ✅**

---

## ✅ **3. Check CloudWatch Logs (Most Important!)**

### **Go to CloudWatch:**
1. Open AWS Console → **CloudWatch** → **Log groups**
2. Click on **`/aws/lambda/referral-orchestrator`**
3. Click **"Latest log stream"** (most recent one)
4. **Search for:**
   - ✅ `"Using agent from registry"` = Agent Registry working!
   - ✅ `"Feature Store"` = Feature Store being queried!
   - ✅ `"Retrieved features"` OR `"No features found"` = Feature Store working!

---

## ✅ **4. Check Generated Message**

### **Go to DynamoDB:**
1. Open AWS Console → **DynamoDB** → **Tables**
2. Click on **`ReferralMessages`** table
3. Click **"Explore table items"**
4. Click on the **most recent message**
5. **Look for:**
   - ✅ `agentVersion: "1.0"` = Agent Registry was used!

---

## 🎯 **Quick Checklist:**

- [ ] **AgentRegistry table** has `upsell-generator` v1.0 → ✅ Agent Registry deployed
- [ ] **CustomerFeatures table** exists → ✅ Feature Store deployed
- [ ] **CloudWatch logs** show `"Using agent from registry"` → ✅ Agent Registry working
- [ ] **CloudWatch logs** show `"Feature Store"` → ✅ Feature Store working
- [ ] **ReferralMessages** has `agentVersion: "1.0"` → ✅ Agent Registry integrated

---

## ✅ **If all checked = Everything is working!**

