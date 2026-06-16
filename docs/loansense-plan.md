# LoanSense — Full Project Plan

## Overview

LoanSense is an agentic underwriting intelligence system for Indian NBFCs and small banks. It jointly assesses credit risk and fraud signals from a loan applicant's data, detects contradictions between those signals, and delivers a structured, explainable decision — Approve / Flag / Reject — with plain-language justification mapped to RBI Fair Practices Code. A bank officer interacts with a React UI, submits an application, and receives a reasoned verdict they can act on or escalate.

**Who it's for:** Loan officers at NBFCs and small banks in India.
**What it replaces:** Two siloed systems (fraud model + credit model) that never talk to each other.
**What makes it non-trivial:** The contradiction detector catches the gap between signals — where synthetic identity fraud hides.

---

## Goals & Non-Goals

### In Scope
- Three ML models: credit risk scorer, fraud signal detector, contradiction detector
- Synthetic India-realistic applicant dataset with injected attack patterns
- Synthetic attack generator: 4 parameterized India-specific fraud patterns
- Agentic reasoning layer using Gemini 1.5 Flash with structured tool calls
- Explainability: structured verdict with RBI Fair Practices Code mapping
- FastAPI backend serving models and agent
- React frontend — clean, functional, demo-ready
- MLflow experiment tracking and model registry
- PostgreSQL for applicant records, model outputs, verdicts, audit logs
- pytest suite covering all major contradiction cases
- README as system design doc — architecture diagram, tradeoffs, ROI playbook
- Drift detection trigger (documented + basic implementation)
- Hosted demo on Railway or Render

### Explicitly Out of Scope (v1)
- Real bureau data integration (CIBIL API) — simulated as a feature
- Active learning / human feedback loop — documented as architecture only
- Full retraining pipeline — MLflow tracking only, retraining documented
- Multi-user auth / role management
- Production-grade security hardening
- Mobile-optimized UI

---

## System Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                        React Frontend                        │
│   Application Form | Verdict Display | Audit Log View        │
└──────────────────────────┬──────────────────────────────────┘
                           │ HTTP (REST)
┌──────────────────────────▼──────────────────────────────────┐
│                       FastAPI Backend                        │
│                                                              │
│  ┌─────────────────┐   ┌──────────────────────────────────┐ │
│  │  /assess route  │──▶│         Agent Orchestrator        │ │
│  └─────────────────┘   │   (Gemini 1.5 Flash + Tools)     │ │
│                         └──────────┬───────────────────────┘ │
│                                    │ tool calls               │
│         ┌──────────────────────────┼──────────────────┐      │
│         ▼                          ▼                   ▼      │
│  ┌─────────────┐  ┌──────────────────────┐  ┌──────────────┐│
│  │ Credit Risk │  │  Fraud Signal        │  │Contradiction ││
│  │   Scorer   │  │    Detector          │  │  Detector    ││
│  │ (XGBoost)  │  │ (XGBoost + rules)    │  │(hybrid)      ││
│  └──────┬──────┘  └──────────┬───────────┘  └──────┬───────┘│
│         └──────────────────────┴──────────────────────┘      │
│                          MLflow Model Registry                │
└─────────────────────────────┬───────────────────────────────┘
                              │
┌─────────────────────────────▼───────────────────────────────┐
│                        PostgreSQL                            │
│   applicants | model_outputs | agent_verdicts | audit_logs  │
└─────────────────────────────────────────────────────────────┘
```

**Data flow for a single assessment:**
1. Officer submits application via React form
2. FastAPI `/assess` receives structured applicant JSON
3. Agent Orchestrator calls three model tools in sequence
4. Models return scores + signals to the agent
5. Agent reasons over outputs, detects contradictions
6. Agent returns structured verdict (decision + justification + signals)
7. Verdict stored in PostgreSQL with full audit trail
8. React UI renders the verdict with signal breakdown

---

## Tech Stack

| Layer | Choice | Rationale |
|-------|--------|-----------|
| Language | Python 3.11 | Stable, wide ML ecosystem support |
| ML Models | XGBoost + sklearn | Industry standard for tabular credit/fraud data |
| Agent LLM | Gemini 1.5 Flash | Free tier sufficient, strong function calling |
| Backend | FastAPI | Async, automatic OpenAPI docs, Pydantic validation |
| Database | PostgreSQL | Appropriate for financial audit trails, structured queries |
| Experiment Tracking | MLflow | Model versioning, experiment comparison, registry |
| Frontend | React + Tailwind | Clean UI without heavy framework overhead |
| Testing | pytest | Unit + integration tests for contradiction cases |
| Hosting | Railway / Render | Free tier, supports PostgreSQL + FastAPI |
| Data Generation | SDV + Faker | Synthetic India-realistic applicant generation |
| Explainability | SHAP + custom verdict template | SHAP for signal attribution, custom layer for RBI mapping |
| Environment | python-dotenv | Secure credential management |

---

## Component Deep Dive

### 1. Synthetic Data + Attack Generator

**Dataset foundation:**
- Home Credit Default Risk (Kaggle) — credit risk features and target
- IEEE-CIS Fraud Detection (Kaggle) — transaction-level fraud signals
- Engineer a unified feature set bridging both

**India-realistic synthetic layer (SDV + Faker):**
- Income ranges: ₹15,000–₹2,50,000/month
- Loan purposes: home renovation, education, business capital, medical, vehicle
- Employer types: salaried (private/govt), self-employed, gig worker
- CIBIL-like score: simulated 300–900 range with realistic distribution
- UPI/IMPS transaction history: velocity, merchant categories, anomaly flags

**Synthetic attack generator — 4 parameterized India-specific fraud patterns:**

| Attack Pattern | Description | Signals It Produces |
|---------------|-------------|-------------------|
| Stolen PAN + fabricated employment | Real PAN, fake employer + income | Income-bureau mismatch, new employer with no GST trail |
| Fragmented bureau footprint | Thin credit file, multiple recent enquiries | Low CIBIL + high enquiry velocity + large loan ask |
| UPI/IMPS velocity spike | Normal profile, sudden transaction surge pre-application | Transaction velocity anomaly vs. declared income |
| Synthetic identity — clean constructed profile | Fabricated identity with no real contradictions except recency | All scores clean but account age < 6 months across all products |

Each pattern is parameterized so you can generate N synthetic fraudulent applicants per pattern for training and evaluation.

**Class imbalance strategy:**
- Fraud base rate: ~2-3% (realistic for Indian lending)
- SMOTE for oversampling minority class during training
- Document this tradeoff explicitly in README

---

### 2. Three ML Models

**Model A — Credit Risk Scorer**
- Target: probability of default (binary)
- Features: income, loan amount, EMI-to-income ratio, CIBIL score, employment type, loan tenure, existing obligations
- Algorithm: XGBoost classifier
- Output: `credit_risk_score` (0–1), `risk_band` (Low/Medium/High)

**Model B — Fraud Signal Detector**
- Target: fraud flag (binary)
- Features: transaction velocity, account age, enquiry count, income-declaration vs. bureau mismatch, employer verification flag, UPI pattern anomalies
- Algorithm: XGBoost + rule-based pre-filter
- Output: `fraud_probability` (0–1), `fraud_signals` (list of triggered flags)

**Model C — Contradiction Detector (the core IP)**

This is the hybrid approach — not naive ensembling:

```
Layer 1 — Statistical Anomaly Detection
  Isolation Forest on the joint feature space
  Flags applicants that are outliers when credit + fraud features are considered together

Layer 2 — Rule-Based Cross-Checks
  Explicit contradiction rules:
  - CIBIL > 750 BUT account_age < 6 months → synthetic identity flag
  - declared_income > ₹1L BUT transaction_avg < ₹10K → income fabrication flag
  - fraud_probability > 0.4 AND credit_risk_score < 0.2 → high-priority contradiction
  - enquiry_count > 5 in 30 days AND new_to_credit = True → bust-out pattern

Layer 3 — Probabilistic Reconciliation
  A lightweight meta-model (Logistic Regression) trained on:
  - credit_risk_score
  - fraud_probability
  - anomaly_score (from Layer 1)
  - rule_flags (count + severity from Layer 2)
  Output: contradiction_score (0–1) + contradiction_type (enum)
```

Why this beats naive ensembling: naive ensembling averages scores, which means a high credit score cancels a moderate fraud score. This hybrid explicitly preserves and surfaces the *tension* between signals — which is the actual information.

---

### 3. Agent Reasoning Layer

**What the agent does:**
Receives model outputs and reasons over them. Does not run the models — calls them as tools. Produces a structured verdict.

**Tool call schema (JSON):**

```json
{
  "tools": [
    {
      "name": "get_credit_risk_score",
      "description": "Returns credit risk score and risk band for an applicant",
      "parameters": {
        "applicant_id": "string"
      }
    },
    {
      "name": "get_fraud_signals",
      "description": "Returns fraud probability and triggered fraud signal flags",
      "parameters": {
        "applicant_id": "string"
      }
    },
    {
      "name": "get_contradiction_score",
      "description": "Returns contradiction score, type, and specific cross-signal anomalies",
      "parameters": {
        "applicant_id": "string"
      }
    }
  ]
}
```

**System prompt structure (summarized — full prompt to be developed during build):**

```
You are an underwriting intelligence agent for an Indian NBFC.
Your job is to assess loan applications by querying three risk models
and reasoning over their outputs.

You must:
1. Call all three model tools before forming a verdict
2. When credit and fraud signals conflict, treat the conflict itself as evidence
3. Produce a structured verdict in the exact JSON schema provided
4. Map every decision reason to an RBI Fair Practices Code category
5. Never approve an application with contradiction_score > 0.6

Output schema: { decision, confidence, primary_reason, risk_signals, rbi_mapping, what_would_change }
```

**Verdict output schema:**

```json
{
  "decision": "APPROVE | FLAG_FOR_REVIEW | REJECT",
  "confidence": 0.87,
  "primary_reason": "Plain language explanation of the primary driver",
  "risk_signals": [
    { "signal": "income_bureau_mismatch", "severity": "HIGH", "detail": "..." },
    { "signal": "transaction_velocity_anomaly", "severity": "MEDIUM", "detail": "..." }
  ],
  "rbi_mapping": {
    "category": "Fair Practices Code — Credit Assessment",
    "requirement": "Lender must communicate reason for rejection",
    "satisfied_by": "primary_reason field above"
  },
  "what_would_change": "If verified employment documents confirm stated income, risk band would reduce to Medium."
}
```

---

### 4. Explainability — Two Concrete RBI Sample Verdicts

**Sample 1 — Rejection with RBI mapping:**

```
Decision: REJECT
Primary Reason: Declared monthly income of ₹85,000 is inconsistent with
average UPI transaction volume of ₹8,200/month over the past 6 months.
Combined with a CIBIL enquiry count of 7 in 30 days, this application
presents a high-probability income fabrication pattern.

RBI Fair Practices Code mapping:
→ Section 3(vii): Lender must communicate in writing the reasons for
  rejection of loan applications. This verdict satisfies that requirement.

What would change this decision:
Submission of last 6 months' salary slips and Form 16 reducing the
income-transaction gap to under 40% would move this to FLAG_FOR_REVIEW.
```

**Sample 2 — Flag with contradiction highlighted:**

```
Decision: FLAG_FOR_REVIEW
Primary Reason: Credit score of 781 (Low Risk) conflicts with account
age of 4 months across all credit products. This is a known pattern
in synthetic identity fraud. Manual verification of PAN and address
proof against original documents is required before proceeding.

RBI Fair Practices Code mapping:
→ Section 3(vi): Lender must verify KYC documents. This flag triggers
  mandatory document verification workflow.
```

---

### 5. MLOps Layer

**MLflow setup:**
- Track all training runs: parameters, metrics, artifacts
- Register best model per component in MLflow Model Registry
- Serve models via FastAPI (load from registry at startup)
- Version all three models independently

**Drift detection (basic implementation):**
- Log prediction distributions per week to PostgreSQL
- Compare current week's score distribution against training baseline using PSI (Population Stability Index)
- If PSI > 0.2 on any model, log a `drift_alert` to audit_logs table
- Alert is visible in the React UI admin panel
- Full retraining pipeline: documented as architecture, not implemented in v1

**What this demonstrates:**
You're not just training models. You're thinking about what happens when the real world changes — which is what companies actually care about.

---

### 6. Database Schema (PostgreSQL)

```sql
-- Core applicant record
applicants (
  id UUID PRIMARY KEY,
  created_at TIMESTAMPTZ,
  name TEXT,
  pan_hash TEXT,          -- hashed, never store raw PAN
  monthly_income NUMERIC,
  loan_amount NUMERIC,
  loan_purpose TEXT,
  employment_type TEXT,
  cibil_score_simulated INTEGER,
  raw_features JSONB      -- full feature vector for model inference
)

-- Individual model outputs
model_outputs (
  id UUID PRIMARY KEY,
  applicant_id UUID REFERENCES applicants(id),
  model_name TEXT,        -- 'credit_risk' | 'fraud_signal' | 'contradiction'
  model_version TEXT,
  score NUMERIC,
  signals JSONB,
  created_at TIMESTAMPTZ
)

-- Agent verdicts
agent_verdicts (
  id UUID PRIMARY KEY,
  applicant_id UUID REFERENCES applicants(id),
  decision TEXT,          -- 'APPROVE' | 'FLAG_FOR_REVIEW' | 'REJECT'
  confidence NUMERIC,
  primary_reason TEXT,
  risk_signals JSONB,
  rbi_mapping JSONB,
  what_would_change TEXT,
  created_at TIMESTAMPTZ
)

-- Full audit trail
audit_logs (
  id UUID PRIMARY KEY,
  applicant_id UUID REFERENCES applicants(id),
  event_type TEXT,        -- 'assessment_started' | 'model_called' | 'verdict_issued' | 'drift_alert'
  event_data JSONB,
  created_at TIMESTAMPTZ
)
```

---

### 7. React Frontend

**Pages:**
- `/` — Dashboard: recent assessments, verdict summary stats, drift alert banner if triggered
- `/assess` — Application form: structured input for all applicant fields
- `/verdict/:id` — Verdict display: decision badge, signal breakdown, RBI mapping, audit trail
- `/audit` — Audit log view: full event history per applicant

**Design direction:**
Clean, professional, data-dense. Financial product aesthetic — not a startup landing page. Dark sidebar, white content area, color-coded verdict badges (green/amber/red). No unnecessary animation. Typography that reads well in a professional setting.

---

### 8. Testing Strategy

**pytest suite — contradiction cases (non-negotiable):**

```python
# These must pass deterministically every time

test_high_cibil_new_account_flags_synthetic_identity()
# Input: cibil=790, account_age_months=3, loan_amount=500000
# Expected: decision=FLAG_FOR_REVIEW, contradiction_type=SYNTHETIC_IDENTITY

test_income_transaction_mismatch_rejects()
# Input: declared_income=85000, avg_transaction=8200, enquiry_count=7
# Expected: decision=REJECT, signal=income_fabrication

test_clean_profile_approves()
# Input: cibil=720, income=60000, account_age=48, fraud_prob=0.05
# Expected: decision=APPROVE

test_high_contradiction_score_never_approves()
# Input: contradiction_score=0.75 (any combination)
# Expected: decision != APPROVE (invariant test)

test_velocity_spike_flags_for_review()
# Input: upi_velocity_percentile=97, otherwise clean profile
# Expected: decision=FLAG_FOR_REVIEW, signal=transaction_velocity_anomaly
```

**Additional test coverage:**
- FastAPI endpoint tests (input validation, response schema)
- MLflow model loading tests (models load correctly from registry)
- Database write/read tests for verdict storage
- Prompt injection test: malicious text in loan_purpose field does not alter verdict logic

---

### 9. ROI Playbook (README one-pager)

```
Assumptions (conservative ranges):
- Manual review cost per application: ₹600–₹1,200 (analyst time, ~45–90 min)
- Synthetic identity fraud average loss per case: ₹1.5L–₹8L (personal loan range)
- Fraud rate in unsecured lending: 1.5–3% (industry estimate — verify with RBI/CIBIL reports)
- Applications per month at small NBFC: 500–2,000

Expected impact at 1,000 applications/month:
- Fraud cases: 15–30 per month
- Caught by LoanSense (assumed 70% detection rate): 10–21 per month
- Loss prevented: ₹15L–₹1.7Cr per month
- Manual review hours saved (30% reduction in full reviews): 150–300 hrs/month

This is not a revenue projection. It is a plausibility framework
for a business conversation. All numbers require validation against
actual NBFC operational data.
```

---

## Risks & Open Questions

| Risk | Severity | Mitigation |
|------|----------|-----------|
| Gemini free tier rate limits during demo | Medium | Cache model calls, use mock responses for load testing |
| Synthetic data doesn't reflect real fraud distribution | High | Research actual Indian fraud patterns before parameterizing attack generator |
| Agent reasoning inconsistent across runs (LLM non-determinism) | Medium | Set temperature=0, use structured output schema, pytest catches regressions |
| Contradiction detector hybrid is complex to tune | High | Build rule layer first, add statistical layer, add meta-model last — test at each stage |
| Railway/Render free tier cold starts slow demo | Low | Keep a warm-up script, note in README |
| Prompt injection via loan_purpose field | Medium | Sanitize all user text before LLM context, add test case |

---

## Architecture Tradeoffs (for README)

| Decision | Tradeoff | Why We Made It |
|----------|----------|----------------|
| Synthetic data only | Cannot prove real-world accuracy | Privacy constraints; class imbalance injected to simulate reality |
| XGBoost over deep learning | Less expressive for complex patterns | Tabular data, interpretability, faster training, industry standard |
| Gemini Flash over GPT-4o | Less capable reasoning | Free tier sufficient for structured verdict generation |
| Monolithic FastAPI over microservices | Harder to scale independently | Solo project; microservices would add ops overhead without benefit |
| Rule-based cross-checks hardcoded | Brittle to new fraud patterns | Explicit rules are auditable and explainable — appropriate for regulated domain |

---

## Out of Scope — Future Roadmap

- CIBIL API integration (real bureau data)
- Active learning: officer feedback loop retrains contradiction rules
- Multi-NBFC deployment: tenant isolation, per-client model versions
- WhatsApp/SMS applicant verification flow (common in Indian lending)
- Real-time streaming pipeline for transaction data (Kafka)
- Model fairness audit: check for bias across income/geography segments

---

## Build Sequence (Recommended Order)

```
Week 1-2:   Domain research + data sourcing + synthetic dataset v1
Week 3:     Attack generator — 4 fraud patterns parameterized
Week 4-5:   Credit risk model + fraud signal model (train, evaluate, MLflow)
Week 6-7:   Contradiction detector — rule layer first, then statistical, then meta-model
Week 8:     FastAPI backend — model serving endpoints
Week 9-10:  Agent reasoning layer — Gemini tool calls + system prompt iteration
Week 11:    pytest suite — all contradiction cases passing
Week 12:    React frontend — form + verdict display
Week 13:    PostgreSQL integration + audit trail
Week 14:    MLflow model registry + drift detection trigger
Week 15:    Deployment on Railway/Render + hosted demo
Week 16:    README as system design doc + ROI playbook + polish
```

Buffer for rework, debugging, and iteration is baked into this sequence. The agent layer (weeks 9-10) will almost certainly need more time than estimated — plan for it.
