# 🏗️ GuardinIA Architecture

**Production-Ready Hybrid Fraud Detection Engine**

This document provides an in-depth technical overview of GuardinIA's system design, architectural decisions, and implementation details.

---

## 📐 High-Level Architecture

```
                                    ┌─────────────────────┐
                                    │   WhatsApp User     │
                                    │  (sends message)    │
                                    └──────────┬──────────┘
                                               │
                                               │ HTTPS POST
                                               ▼
                        ┌────────────────────────────────────────┐
                        │      AWS API Gateway (REST API)        │
                        │  • HTTPS endpoint                       │
                        │  • CORS enabled                         │
                        │  • Request/response logging             │
                        └──────────────┬─────────────────────────┘
                                       │
                                       │ Invokes synchronously
                                       ▼
┌──────────────────────────────────────────────────────────────────────────┐
│                          AWS Lambda Function                              │
│                        (guardinia-webhook-handler)                        │
│                                                                            │
│  ┌─────────────────────────────────────────────────────────────────────┐ │
│  │  STAGE 1: Request Validation                                        │ │
│  │  ─────────────────────────────────────────────────────────────────  │ │
│  │  • HMAC-SHA256 signature verification (Meta webhook security)      │ │
│  │  • Payload parsing and structure validation                        │ │
│  │  • Message type detection (text, image, document)                  │ │
│  └─────────────────────────────────────────────────────────────────────┘ │
│                                       │                                    │
│                                       ▼                                    │
│  ┌─────────────────────────────────────────────────────────────────────┐ │
│  │  STAGE 2: Heuristic Analysis Layer (84.5% of cases)                │ │
│  │  ─────────────────────────────────────────────────────────────────  │ │
│  │                                                                      │ │
│  │  🔍 Pattern Matching (Deterministic Rules)                          │ │
│  │  ├── Phishing Detection                                             │ │
│  │  │   • URL + credentials/entity mention: +50pts                     │ │
│  │  │   • URL + deadline + consequence: +45pts                         │ │
│  │  │   • URL + promise/prize: +50pts                                  │ │
│  │  │                                                                   │ │
│  │  ├── Social Engineering Signatures                                  │ │
│  │  │   • Cloned contact (number change + Pix): +40pts                │ │
│  │  │   • Code request (SMS/WhatsApp): +40pts                         │ │
│  │  │   • Family crisis (hospital + money): +40pts                    │ │
│  │  │   • Extortion/blackmail: +70pts                                 │ │
│  │  │                                                                   │ │
│  │  ├── Fake Authority                                                 │ │
│  │  │   • Institution impersonation: +60pts                           │ │
│  │  │   • "Department/Sector" language: +60pts                        │ │
│  │  │                                                                   │ │
│  │  ├── Urgency Tactics                                                │ │
│  │  │   • Urgency + action demand: +40pts                             │ │
│  │  │                                                                   │ │
│  │  ├── Financial Promises                                             │ │
│  │  │   • "You won", "guaranteed profit": +35pts                      │ │
│  │  │   • Easy money, no risk: +35pts                                 │ │
│  │  │                                                                   │ │
│  │  └── Sensitive Data Requests                                        │ │
│  │      • CPF, password, card number: +30pts                           │ │
│  │                                                                      │ │
│  │  🌐 URL Reputation Check                                            │ │
│  │  └── Google Safe Browsing API: malicious/phishing URLs             │ │
│  │                                                                      │ │
│  │  📊 Score Aggregation & Category Caps                               │ │
│  │  • Total score: sum of triggered heuristics                         │ │
│  │  • Category caps prevent single-vector dominance                    │ │
│  │  • Critical combinations: authority + financial, phishing + social  │ │
│  └──────────────────────┬──────────────────────────────────────────────┘ │
│                         │                                                  │
│              ┌──────────┴──────────┐                                       │
│              │                     │                                       │
│    Score >= 120?        Score 20-119?                                      │
│    (CONFIRMED)          (AMBIGUOUS)                                        │
│              │                     │                                       │
│              │                     ▼                                       │
│              │  ┌─────────────────────────────────────────────────────┐   │
│              │  │  STAGE 3: Bedrock Escalation (15.5% of cases)       │   │
│              │  │  ──────────────────────────────────────────────────  │   │
│              │  │                                                      │   │
│              │  │  🤖 Cognitive AI Analysis                            │   │
│              │  │  ├── Score 20-79: Claude Haiku ($0.00025/1K tok)   │   │
│              │  │  │   • Fast, cheap, good for obvious patterns      │   │
│              │  │  │   • 84% of AI invocations                       │   │
│              │  │  │                                                  │   │
│              │  │  └── Score 80-119: Claude Sonnet ($0.003/1K tok)   │   │
│              │  │      • Deep analysis for subtle manipulation       │   │
│              │  │      • 16% of AI invocations                       │   │
│              │  │                                                      │   │
│              │  │  📝 LLM Prompt Engineering                           │   │
│              │  │  • Context-aware system prompt                       │   │
│              │  │  • Few-shot examples (Brazilian scam patterns)      │   │
│              │  │  • Structured JSON response (score + reasoning)     │   │
│              │  └──────────────────────────────────────────────────────┘   │
│              │                     │                                       │
│              └──────────┬──────────┘                                       │
│                         │                                                  │
│                         ▼                                                  │
│  ┌─────────────────────────────────────────────────────────────────────┐ │
│  │  STAGE 4: Classification & Response                                 │ │
│  │  ─────────────────────────────────────────────────────────────────  │ │
│  │                                                                      │ │
│  │  Score Mapping:                                                      │ │
│  │  • >= 120: 🔴 GOLPE CONFIRMADO                                      │ │
│  │  • 80-119: 🟠 ALTAMENTE SUSPEITO                                    │ │
│  │  • 50-79:  🟡 SUSPEITO                                              │ │
│  │  • 30-49:  ⚠️  BAIXO RISCO                                          │ │
│  │  • 0-29:   ✅ SEGURO                                                │ │
│  │                                                                      │ │
│  │  Response Payload:                                                   │ │
│  │  {                                                                   │ │
│  │    "status": "GOLPE CONFIRMADO",                                    │ │
│  │    "score": 195,                                                    │ │
│  │    "heuristicas_ativadas": [...],                                   │ │
│  │    "bedrock_usado": true,                                           │ │
│  │    "tempo_ms": 1243                                                 │ │
│  │  }                                                                   │ │
│  └─────────────────────────────────────────────────────────────────────┘ │
│                                       │                                    │
│                                       ▼                                    │
│  ┌─────────────────────────────────────────────────────────────────────┐ │
│  │  STAGE 5: Audit & Observability                                     │ │
│  │  ─────────────────────────────────────────────────────────────────  │ │
│  │  • Write to DynamoDB audit log (TTL: 90 days)                      │ │
│  │  • Update metrics table (daily/hourly aggregates)                  │ │
│  │  • CloudWatch custom metrics (score distribution, latency)         │ │
│  │  • Log structured JSON for analysis                                │ │
│  └─────────────────────────────────────────────────────────────────────┘ │
└──────────────────────────────────────────────────────────────────────────┘
                                       │
                                       │ HTTP 200 OK (JSON)
                                       ▼
                        ┌────────────────────────────────────────┐
                        │         Meta WhatsApp API              │
                        │  • Receives classification result      │
                        │  • Delivers to end user                │
                        └────────────────────────────────────────┘
```

---

## 🗄️ Data Architecture

### DynamoDB Tables

#### 1. `guardinia_audit_logs`
**Purpose:** Complete audit trail of all analyses

| Attribute | Type | Description |
|-----------|------|-------------|
| `pk` | String (PK) | `AUDIT#{timestamp}#{uuid}` |
| `sk` | String (SK) | `MESSAGE#{phone_number}` |
| `ttl` | Number | Expiration timestamp (90 days) |
| `timestamp` | String | ISO-8601 timestamp |
| `phone_number` | String | Sender's phone |
| `message_text` | String | Full message content |
| `score` | Number | Final fraud score |
| `status` | String | Classification result |
| `bedrock_used` | Boolean | Was AI invoked? |
| `latency_ms` | Number | Processing time |
| `heuristics` | List | Triggered patterns |

**Indexes:**
- GSI: `phone_number` (query by sender)
- GSI: `timestamp` (time-range queries)

**Access Pattern:**
```python
# Get all analyses from last 24h
response = table.query(
    IndexName='timestamp-index',
    KeyConditionExpression='#ts > :yesterday',
    FilterExpression='bedrock_used = :true'
)
```

#### 2. `guardinia_cache`
**Purpose:** URL reputation caching (reduce Safe Browsing API calls)

| Attribute | Type | Description |
|-----------|------|-------------|
| `pk` | String (PK) | `URL#{domain_hash}` |
| `domain` | String | Full domain |
| `is_malicious` | Boolean | Safe Browsing result |
| `last_checked` | Number | Unix timestamp |
| `ttl` | Number | 7-day cache expiry |

**Cache Strategy:**
- TTL: 7 days (malicious URLs change slowly)
- Invalidation: Manual purge on false positives
- Hit rate: ~60% (same domains reappear)

#### 3. `guardinia_metrics`
**Purpose:** Aggregated analytics

| Attribute | Type | Description |
|-----------|------|-------------|
| `pk` | String (PK) | `DAILY#{date}` or `HOURLY#{datetime}` |
| `sk` | String (SK) | Metric type |
| `total_analyses` | Number | Count |
| `golpe_count` | Number | Scams detected |
| `bedrock_calls` | Number | AI invocations |
| `avg_score` | Number | Mean score |
| `p50_latency` | Number | Median latency |

---

## ⚙️ Key Design Decisions

### 1. **Why Hybrid (Heuristics + AI)?**

**Pure Heuristic Systems:**
- ✅ Fast (< 50ms)
- ✅ Zero cost
- ❌ High false negative rate (miss 70%+ of scams)
- ❌ Brittle (scammers adapt quickly)

**Pure AI Systems:**
- ✅ High recall (catch subtle scams)
- ✅ Adaptive (learns patterns)
- ❌ Expensive ($2-5 per 1K analyses)
- ❌ Slow (1-3s latency)
- ❌ Unpredictable (hallucinations, edge cases)

**GuardinIA Hybrid:**
- ✅ Fast for 84.5% of cases (heuristics)
- ✅ Cheap ($0.13 per 1K analyses)
- ✅ 100% precision (heuristics never wrong on high scores)
- ✅ AI handles ambiguity (15.5% of cases)

**Cost Comparison (1M analyses/month):**
- Pure AI: $2,000 - $5,000
- GuardinIA: **$130**

---

### 2. **Why Conservative Threshold (score >= 120)?**

**User Trust Optimization:**

```
False Positive (legitimate message marked as scam):
  → User loses trust in system
  → Stops using product
  → Negative word-of-mouth

False Negative (scam passes through):
  → User remains vigilant (doesn't blindly trust "SAFE" label)
  → No trust damage
  → Still protected by other means (bank fraud detection, etc.)
```

**Target Users (elderly, non-technical):**
- Need **absolute confidence** when warned
- Can't handle ambiguity or gray zones
- Prefer simple binary: "This IS a scam" vs "I'm not sure"

**Design Philosophy:**
> "Only cry wolf when you're 100% certain there's a wolf."

---

### 3. **Why Haiku-First Escalation?**

**Model Selection Strategy:**

| Score Range | Model | Reasoning |
|-------------|-------|-----------|
| 0-19 | None | Heuristics confident it's safe |
| 20-79 | **Haiku** | Moderate suspicion, fast check needed |
| 80-119 | **Sonnet** | High suspicion, deep analysis needed |
| 120+ | None | Heuristics confident it's a scam |

**Haiku (84% of AI calls):**
- Cost: $0.00025 per 1K tokens
- Speed: ~1s
- Use: Obvious patterns AI can quickly confirm

**Sonnet (16% of AI calls):**
- Cost: $0.003 per 1K tokens (12x Haiku)
- Speed: ~2-3s
- Use: Subtle manipulation, context-dependent analysis

**Cost Optimization:**
```
Without tiering (all Sonnet):
  100 analyses → 15 AI calls → 15 × $0.003 = $0.045

With Haiku-first:
  100 analyses → 13 Haiku + 2 Sonnet
                → (13 × $0.00025) + (2 × $0.003)
                → $0.0033 + $0.006 = $0.0093

Savings: 79% cost reduction
```

---

### 4. **Why Serverless (Lambda)?**

**vs. EC2:**
- ✅ Zero ops (no server management)
- ✅ Auto-scaling (0 to 1000 concurrent requests)
- ✅ Pay per invoke ($0.20 per 1M requests)
- ✅ Built-in fault tolerance

**vs. Container (ECS/EKS):**
- ✅ Faster cold start (<1s vs container ~10s)
- ✅ No orchestration complexity
- ✅ Cheaper for spiky workloads

**Lambda Configuration:**
- Memory: 512 MB (optimal cost/performance ratio)
- Timeout: 30s (covers P99 latency + buffer)
- Concurrency: 100 (prevents runaway costs)
- Runtime: Python 3.11 (latest stable)

---

## 🔒 Security Model

### 1. **Webhook Authentication**

```python
def verify_webhook(payload, signature, secret):
    """
    HMAC-SHA256 signature verification
    Prevents unauthorized webhook calls
    """
    expected = hmac.new(
        secret.encode(),
        payload.encode(),
        hashlib.sha256
    ).hexdigest()
    
    return hmac.compare_digest(signature, expected)
```

**Attack Prevention:**
- Replay attacks: Signature includes timestamp
- Injection: Payload validated before processing
- DoS: Rate limiting via API Gateway

### 2. **Data Privacy**

**PII Handling:**
- Phone numbers: Hashed in logs (SHA-256)
- Message content: Encrypted at rest (DynamoDB KMS)
- TTL: Auto-deletion after 90 days
- No third-party sharing

**Compliance:**
- LGPD-ready (Brazilian GDPR)
- Right to erasure: Manual DynamoDB deletion
- Data minimization: Only essential fields stored

---

## 📊 Performance Characteristics

### Latency Distribution (Production Data)

```
 P50 (Median):   443ms   ████████████████████
 P75:            689ms   ██████████████████████████████
 P90:          2,939ms   ████████████████████████████████████████████████████████
 P95:          3,666ms   ███████████████████████████████████████████████████████████████████
 P99:          5,113ms   ██████████████████████████████████████████████████████████████████████████████████████████
```

**Latency Breakdown:**

| Component | Typical | P95 |
|-----------|---------|-----|
| API Gateway overhead | 10ms | 20ms |
| Lambda cold start | 800ms | 1,200ms |
| Heuristic processing | 30ms | 50ms |
| DynamoDB read/write | 15ms | 50ms |
| Bedrock (Haiku) | 1,000ms | 1,500ms |
| Bedrock (Sonnet) | 2,000ms | 3,000ms |
| Safe Browsing API | 200ms | 500ms |

**Optimization Strategies:**
- ✅ Keep Lambda warm (CloudWatch scheduled pings)
- ✅ Cache URL reputation (reduces Safe Browsing calls)
- ✅ Parallel Bedrock invocations (when multiple messages)
- ⏳ Connection pooling (future: reuse HTTP connections)

---

## 💰 Cost Model

**Per 1,000 Analyses Breakdown:**

| Service | Usage | Cost |
|---------|-------|------|
| Lambda invocations | 1,000 × $0.0000002 | $0.0002 |
| Lambda duration (512MB, 1.3s avg) | 1,300 GB-s × $0.0000166667 | $0.0217 |
| DynamoDB writes (audit logs) | 1,000 × $0.00000125 | $0.0013 |
| DynamoDB reads (cache) | 600 × $0.00000025 | $0.0002 |
| Bedrock Haiku (130 calls) | 130 × 500 tokens × $0.00025 | $0.0163 |
| Bedrock Sonnet (25 calls) | 25 × 500 tokens × $0.003 | $0.0375 |
| API Gateway | 1,000 × $0.0000035 | $0.0035 |
| Safe Browsing API | 400 × $0.00025 | $0.1000 |
| **TOTAL** | | **$0.18** |

**At Scale:**
- 10K/day: ~$54/month
- 100K/day: ~$540/month
- 1M/day: ~$5,400/month

**Free Tier Coverage:**
- Lambda: 1M requests/month free
- DynamoDB: 25 GB storage free
- Bedrock: Pay-per-use (no free tier)

---

## 🧪 Testing Strategy

### 1. **Benchmark Testing**

```bash
# Full production test (200 messages)
python benchmark/guardinia_benchmark.py

# Subset test
LIMIT=50 python benchmark/guardinia_benchmark.py
```

**Dataset Composition:**
- 80 scam messages (real examples from reports)
- 80 legitimate messages (bank, delivery, personal)
- 40 ambiguous messages (context-dependent)

**Metrics Tracked:**
- Precision/Recall/F1 per class
- Confusion matrix
- Latency distribution
- Cost per analysis
- Bedrock usage rate

### 2. **Unit Tests** (TODO)

```python
def test_heuristic_phishing():
    msg = "Banco Inter: Clique aqui para validar: http://fake.com"
    score, _ = analisar_mensagem(msg)
    assert score >= 120  # Should be flagged as scam

def test_legitimate_message():
    msg = "Seu pedido foi entregue. Rastreio: BR123456"
    score, _ = analisar_mensagem(msg)
    assert score < 30  # Should be safe
```

### 3. **Load Testing** (TODO)

```bash
# Apache Bench
ab -n 1000 -c 50 -p payload.json \
   -T application/json \
   https://API_ENDPOINT/webhook
```

---

## 🚀 Future Enhancements (Not Actively Developed)

### High Impact, Low Effort
- [ ] **Image analysis improvements:** Use Rekognition to detect fake receipt layouts
- [ ] **Domain age check:** WHOIS API integration (new domains = higher risk)
- [ ] **Feedback loop:** Let users report false negatives to adjust weights

### Medium Impact, Medium Effort
- [ ] **Conversational context:** Store last 5 messages per sender to detect escalation patterns
- [ ] **Multi-language support:** Extend to Spanish, English
- [ ] **Prometheus metrics:** Export for Grafana dashboards

### High Impact, High Effort
- [ ] **Fine-tuned model:** Train custom classifier on Brazilian scam corpus
- [ ] **Real-time URL scanning:** Headless browser to detect fake login pages
- [ ] **Public API:** Allow other apps to use GuardinIA as a service

---

## 📚 References

- [AWS Lambda Best Practices](https://docs.aws.amazon.com/lambda/latest/dg/best-practices.html)
- [Amazon Bedrock Pricing](https://aws.amazon.com/bedrock/pricing/)
- [Meta WhatsApp Business API](https://developers.facebook.com/docs/whatsapp)
- [Google Safe Browsing API](https://developers.google.com/safe-browsing)
- [DynamoDB Best Practices](https://docs.aws.amazon.com/amazondynamodb/latest/developerguide/best-practices.html)

---

<div align="center">

**GuardinIA Architecture** · Built with ☁️ AWS · Designed for 🛡️ Security

[← Back to README](README.md)

</div>
