# Final Project Requirements Analysis

## ✅ **WHAT'S ALREADY BUILT**

### Current AWS Services:
- ✅ **API Gateway** - REST API webhook endpoint
- ✅ **Lambda Functions** - Webhook handler + Orchestrator (2 functions)
- ✅ **SQS** - Message queue + Dead Letter Queue
- ✅ **DynamoDB** - Message storage with GSIs
- ✅ **S3** - Brand guidelines storage (with versioning)
- ✅ **CloudWatch** - Logs and basic metrics
- ✅ **SSM Parameter Store** - Configuration management
- ✅ **IAM Roles** - Permissions for Lambda functions
- ✅ **Bedrock AI** - Nova Pro model for generation + judging

### Current Features:
- ✅ Data ingestion (webhook receives customer data)
- ✅ Basic monitoring (CloudWatch logs/metrics)
- ✅ AI agent system (Generator + Judge agents)
- ✅ Retry logic with feedback loop
- ✅ Infrastructure as Code (CloudFormation)

---

## ❌ **WHAT YOU NEED TO BUILD**

### 1. **Data Ingestion Pipeline** ⚠️ PARTIALLY DONE
**Current:** Simple webhook → SQS → Lambda  
**Need:** Formal data pipeline with validation, transformation, error handling

**Build:**
- **Kinesis Data Streams** or **EventBridge** for event ingestion
- **Lambda data transformer** to normalize/validate customer data
- **Data quality checks** (schema validation, missing fields)
- **Batch processing** for historical data loads

---

### 2. **AI Agent Registry** (Instead of Model Registry) ⚠️ MISSING
**Current:** Hardcoded Bedrock model ID in CloudFormation  
**Need:** Registry to version and manage AI agents

**Build:**
- **DynamoDB table** for agent registry:
  - Agent ID, version, prompt templates, configuration
  - Metadata (created date, performance metrics, approval status)
- **Lambda function** to register new agent versions
- **Versioning system** (v1.0, v1.1, v2.0)
- **A/B testing support** (route X% traffic to new agent)

**Example Structure:**
```json
{
  "agentId": "upsell-generator",
  "version": "2.1",
  "promptTemplate": "s3://.../prompts/v2.1.txt",
  "bedrockModel": "amazon.nova-pro-v1:0",
  "config": {
    "temperature": 0.7,
    "maxTokens": 1000
  },
  "status": "production",
  "performance": {
    "approvalRate": 0.85,
    "avgScore": 8.2
  }
}
```

---

### 3. **Feature Store / Vector Database** ⚠️ MISSING
**Current:** Customer data passed directly to AI  
**Need:** Centralized feature store for customer embeddings and features

**Build:**
- **Amazon OpenSearch** or **Amazon Bedrock Knowledge Bases** (Vector DB)
  - Store customer embeddings (vector representations)
  - Similar customer search (find customers with similar profiles)
  - Historical feature tracking
- **Feature Store** (DynamoDB or S3):
  - Customer features (satisfaction trends, service frequency, property features)
  - Pre-computed aggregations (avg satisfaction, total services, lifetime value)
  - Feature versioning

**Use Cases:**
- Find similar customers for personalization
- Store customer embeddings for RAG (Retrieval Augmented Generation)
- Track feature drift over time

---

### 4. **Model Monitoring** (AI Agent Monitoring) ⚠️ PARTIALLY DONE
**Current:** Basic CloudWatch metrics (approval rate, generation time)  
**Need:** Comprehensive monitoring dashboard

**Build:**
- **CloudWatch Dashboard** with:
  - Agent performance metrics (approval rate, rejection reasons breakdown)
  - Latency metrics (p50, p95, p99)
  - Error rates by agent version
  - Cost tracking (Bedrock API costs)
- **SageMaker Model Monitor** or custom monitoring:
  - Data drift detection (customer data distribution changes)
  - Concept drift (approval rates dropping over time)
  - Anomaly detection (unusual rejection patterns)
- **SNS Alerts** for:
  - Approval rate drops below threshold
  - High error rates
  - Cost anomalies

---

### 5. **Pipeline Services** ⚠️ MISSING
**Current:** Single Lambda orchestrator  
**Need:** Separate pipeline stages

**Build:**

#### **A. Data Preparation Stage**
- **Lambda function:** `data-prep-processor`
- **Tasks:**
  - Validate customer data schema
  - Enrich with features from Feature Store
  - Create customer embeddings
  - Handle missing data
- **Output:** Prepared customer data + embeddings

#### **B. Training/Evaluation Stage** (For AI Agent Tuning)
- **Lambda function:** `agent-evaluator`
- **Tasks:**
  - Test new agent versions on historical data
  - Compare performance (A/B testing)
  - Generate evaluation reports
  - Calculate metrics (approval rate, quality score)
- **Output:** Evaluation metrics, comparison reports

#### **C. Deployment Stage**
- **Lambda function:** `agent-deployer`
- **Tasks:**
  - Register new agent version in Agent Registry
  - Update SSM parameters
  - Gradual rollout (10% → 50% → 100%)
  - Rollback capability
- **Output:** Deployment status, agent version

#### **D. Inference Stage** (Already exists, but enhance)
- **Current:** `orchestrator` Lambda
- **Enhancements:**
  - Pull agent config from Agent Registry
  - Use Feature Store for customer context
  - Log detailed metrics for monitoring

**Pipeline Flow:**
```
Data Ingestion → Data Prep → Feature Store → Agent Registry → Inference → Monitoring
```

---

### 6. **Multiple AWS Accounts** ⚠️ MISSING
**Current:** Single account deployment  
**Need:** Dev, Test, Prod separation

**Build:**
- **3 AWS Accounts:**
  - `dev-account` - Development/testing
  - `test-account` - Staging/pre-production
  - `prod-account` - Production
- **AWS Organizations** or **Control Tower** for account management
- **Cross-account IAM roles** for:
  - CI/CD pipeline to deploy across accounts
  - Monitoring aggregation (CloudWatch cross-account)
- **Deployment scripts** that deploy to specific account:
  ```bash
  ./deploy.sh --account dev
  ./deploy.sh --account test
  ./deploy.sh --account prod
  ```

**Account Structure:**
```
dev-account:
  - Test agent versions
  - Development data
  - Lower cost resources

test-account:
  - Pre-production testing
  - Production-like data
  - Full monitoring

prod-account:
  - Production traffic
  - Production data
  - Full monitoring + alerts
```

---

### 7. **Scalability Documentation** ⚠️ MISSING
**Current:** Serverless (auto-scales, but not documented)  
**Need:** Written scalability plan

**Document:**
- **Current capacity:**
  - Lambda: 1000 concurrent executions
  - API Gateway: 10,000 requests/second
  - DynamoDB: On-demand (unlimited)
  - SQS: Unlimited messages
  
- **Scaling strategies:**
  - **Horizontal scaling:** Add more Lambda functions (automatic)
  - **Vertical scaling:** Increase Lambda memory/timeout
  - **Caching:** Add ElastiCache for Feature Store queries
  - **CDN:** CloudFront for API Gateway
  - **Database:** DynamoDB auto-scaling, read replicas
  - **Queue:** Multiple SQS queues by priority
  
- **Architecture changes for scale:**
  - **10x scale:** Current architecture (no changes)
  - **100x scale:** Add ElastiCache, CloudFront, DynamoDB read replicas
  - **1000x scale:** Add Kinesis Data Streams, ECS/Fargate for heavy processing, Multi-region deployment

---

### 8. **Unique Service/Approach** ⚠️ NEED TO ADD
**Current:** Standard serverless + Bedrock  
**Need:** Something unique/extends class experience

**Ideas:**

#### **Option A: Bedrock Knowledge Bases (RAG)**
- Store customer service history in Knowledge Base
- AI agent retrieves similar customer cases
- Generates messages based on successful past examples
- **Unique:** Combines RAG with agent orchestration

#### **Option B: Amazon Bedrock Agents**
- Use Bedrock Agents framework (not just Converse API)
- Multi-agent system (Generator, Judge, Validator agents)
- Agent-to-agent communication
- **Unique:** True multi-agent architecture

#### **Option C: Real-time Streaming with Kinesis**
- Stream customer events in real-time
- Process with Kinesis Analytics
- Real-time feature updates
- **Unique:** Real-time ML/AI pipeline

#### **Option D: Cost Optimization with Spot Instances**
- Use EC2 Spot for batch processing
- Cost savings for non-critical workloads
- **Unique:** Cost-aware AI pipeline

---

## 📋 **IMPLEMENTATION CHECKLIST**

### Phase 1: Core Pipeline (Week 1-2)
- [ ] Set up Kinesis Data Streams for ingestion
- [ ] Create Data Preparation Lambda
- [ ] Build Feature Store (OpenSearch or DynamoDB)
- [ ] Create Agent Registry (DynamoDB table + Lambda)

### Phase 2: Monitoring & Evaluation (Week 2-3)
- [ ] Build Agent Evaluator Lambda
- [ ] Create CloudWatch Dashboard
- [ ] Set up SNS alerts
- [ ] Implement data drift detection

### Phase 3: Multi-Account & Deployment (Week 3-4)
- [ ] Set up 3 AWS accounts (dev/test/prod)
- [ ] Create cross-account IAM roles
- [ ] Build deployment pipeline
- [ ] Test cross-account deployment

### Phase 4: Unique Feature (Week 4)
- [ ] Implement chosen unique service (RAG/Agents/Streaming)
- [ ] Document architecture
- [ ] Create scalability documentation

### Phase 5: Documentation & Testing (Week 5)
- [ ] Write architecture diagrams
- [ ] Document scalability plan
- [ ] Create test scenarios
- [ ] Final presentation prep

---

## 🎯 **RECOMMENDED UNIQUE FEATURE: Bedrock Knowledge Bases (RAG)**

**Why:** Extends class experience with RAG, practical for production

**Implementation:**
1. **Create Bedrock Knowledge Base:**
   - Data source: S3 bucket with customer service history
   - Embeddings: Amazon Titan Embeddings
   - Vector store: OpenSearch Serverless

2. **Enhance Orchestrator:**
   - Before generating message, query Knowledge Base
   - Find similar customers and their successful upsells
   - Include examples in prompt to AI agent

3. **Benefits:**
   - Better personalization (learns from past successes)
   - Consistent messaging (uses proven templates)
   - Unique combination of RAG + Agent orchestration

---

## 📊 **FINAL PROJECT DELIVERABLES**

1. **Working System:**
   - ✅ Data ingestion pipeline
   - ✅ Agent Registry
   - ✅ Feature Store
   - ✅ Monitoring dashboard
   - ✅ Multi-account deployment
   - ✅ Unique feature (RAG/Agents/etc.)

2. **Documentation:**
   - Architecture diagrams (draw.io or Lucidchart)
   - Scalability plan (written document)
   - Deployment guide
   - API documentation

3. **Presentation:**
   - Demo of system
   - Architecture walkthrough
   - Scalability discussion
   - Unique feature showcase

---

## 💡 **QUICK WINS (Start Here)**

1. **Agent Registry** - Easiest to implement, high impact
2. **CloudWatch Dashboard** - Visual monitoring, quick to build
3. **Feature Store** - Use DynamoDB (already familiar)
4. **Multi-Account** - Use AWS Organizations (free tier)

Then tackle the unique feature and scalability docs.

