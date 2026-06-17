# LoanSense — TO-DO.md

---

## Task 1: Domain Research & Project Setup

### Block 1: Domain Research

What it does: Builds the knowledge foundation for the entire project — fraud patterns, RBI guidelines, NBFC lending context. Without this, the attack generator and explainability layer will be shallow.

Prompt for Claude Code:
```
Do not write any code for this block. This is a research task.

Research and produce a markdown document called `docs/domain-research.md` covering:

1. Four India-specific synthetic identity fraud patterns with real detail:
   - Stolen PAN + fabricated employment: how it works, what signals it leaves
   - Fragmented bureau footprint: how it works, what signals it leaves
   - UPI/IMPS velocity spike: how it works, what signals it leaves
   - Synthetic identity (clean constructed profile): how it works, what signals it leaves
   For each pattern: describe the attacker's goal, the steps they take, and the specific data signals that betray the fraud when credit and fraud signals are read together.

2. RBI Fair Practices Code for credit — find the actual document at rbi.org.in. Extract:
   - The section number and text of the requirement to communicate rejection reasons in writing
   - The section number and text of the KYC verification requirement
   - Any other section directly relevant to automated credit decisions

3. NBFC lending context:
   - What does a loan officer at a small NBFC actually do during manual underwriting?
   - What data do they typically have access to?
   - What are the common failure modes (where do they miss fraud)?

4. CIBIL score ranges and their industry interpretation (300–900):
   - What score bands do Indian lenders use?
   - What is considered thin file / no file?

Source everything you can. Where you cannot find a primary source, flag it explicitly as "unverified — needs manual check."
```

Exit condition: `docs/domain-research.md` exists and covers all four sections with sourced or flagged content.

---

### Block 2: Project Scaffolding

What it does: Creates the full directory structure, requirements.txt, .env template, .gitignore, and confirms PostgreSQL + MLflow are running locally before any code is written.

Prompt for Claude Code:
```
Scaffold the LoanSense project directory structure exactly as specified in CLAUDE.md.

Tasks:
1. Create all directories and __init__.py files for Python packages
2. Create requirements.txt with pinned versions for:
   - fastapi, uvicorn, sqlalchemy, alembic, psycopg2-binary
   - xgboost, scikit-learn, shap, imbalanced-learn
   - google-generativeai (Gemini SDK)
   - mlflow
   - sdv, faker
   - pytest, httpx (for FastAPI test client)
   - python-dotenv, pydantic
3. Create .env.template (no real values — placeholders only):
   DATABASE_URL=postgresql://user:password@localhost:5432/loansense
   GEMINI_API_KEY=your_key_here
   MLFLOW_TRACKING_URI=./mlruns
   ENVIRONMENT=development
4. Create .gitignore that includes: .env, mlruns/, __pycache__/, *.pyc, .venv/, data/raw/
5. Create frontend/ with Vite + React + Tailwind scaffolding using: npm create vite@latest frontend -- --template react, then install tailwindcss
6. Verify PostgreSQL is accessible at DATABASE_URL
7. Verify MLflow tracking works by running: mlflow ui --backend-store-uri ./mlruns

Do not write any application logic yet. Structure only.
```

Exit condition: `pip install -r requirements.txt` completes without errors. `mlflow ui` launches. PostgreSQL connection confirmed. Frontend `npm run dev` serves a blank Vite page.

---

## Task 2: Synthetic Dataset & Attack Generator

### Block 3: Dataset Acquisition & Audit

What it does: Downloads the two source datasets and produces a data audit report so the feature engineering decisions are grounded in what's actually in the data.

Prompt for Claude Code:
```
Download and audit the two source datasets:

1. Home Credit Default Risk (Kaggle) — save to ml/data/raw/home_credit/
   Primary file needed: application_train.csv
   If Kaggle CLI is available: kaggle competitions download -c home-credit-default-risk
   Otherwise: provide download instructions in a README note.

2. IEEE-CIS Fraud Detection (Kaggle) — save to ml/data/raw/ieee_cis/
   Primary files: train_transaction.csv, train_identity.csv
   If Kaggle CLI is available: kaggle competitions download -c ieee-fraud-detection

3. Produce ml/data/audit_report.md covering for each dataset:
   - Shape (rows, columns)
   - Target variable distribution (class imbalance ratio)
   - Missing value counts per column (top 20 worst)
   - Feature types (numeric vs categorical)
   - Which features are candidates for the unified LoanSense feature set

Do not process or transform data yet. Audit only.
```

Exit condition: Both datasets exist in ml/data/raw/. `audit_report.md` exists with accurate shape, target distribution, and top missing value columns for each dataset.

---

### Block 4: Unified Feature Engineering

What it does: Engineers a unified feature set from both datasets that represents a realistic loan application — the single input that all three models will consume.

Prompt for Claude Code:
```
Create ml/data/feature_engineering.py that produces a unified feature set combining signals from Home Credit and IEEE-CIS datasets.

Target unified features (engineer or derive each):

Credit risk features (from Home Credit):
- loan_amount (AMT_CREDIT)
- income (AMT_INCOME_TOTAL)
- emi_to_income_ratio (AMT_ANNUITY / AMT_INCOME_TOTAL)
- employment_type (NAME_INCOME_TYPE — encode as categorical)
- loan_tenure_months (derived)
- existing_obligations (AMT_CREDIT - AMT_GOODS_PRICE as proxy)
- cibil_score_simulated (map EXT_SOURCE_2 * 600 + 300 to simulate 300-900 range)

Fraud signal features (from IEEE-CIS or engineered):
- transaction_velocity_30d (TransactionAmt rolling count proxy)
- account_age_months (derived or simulated)
- enquiry_count_30d (simulated — document this)
- income_transaction_ratio (declared income vs avg transaction)
- new_to_credit (account_age_months < 6)
- upi_velocity_percentile (TransactionAmt percentile rank)

Target variables:
- default_flag (TARGET from Home Credit — 1=default, 0=no default)
- fraud_flag (isFraud from IEEE-CIS — joined by engineered applicant_id proxy)

Note: The two datasets cannot be directly joined by a real key. Use a documented
sampling strategy: sample N applicants from Home Credit, assign fraud flags
from IEEE-CIS distribution by matching income/amount bands. Document this
clearly as a synthetic join in the code comments.

Output: ml/data/processed/unified_features.parquet
Also output: ml/data/processed/feature_definitions.md — one line per feature describing what it represents and where it came from.
```

Exit condition: `unified_features.parquet` exists. `feature_definitions.md` describes every column. Running `python ml/data/feature_engineering.py` completes without errors and prints shape of output.

---

### Block 5: India-Realistic Synthetic Layer

What it does: Adds India-realistic distributions on top of the unified dataset — income ranges, CIBIL bands, employment types, UPI patterns — so the synthetic data feels authentic to Indian lending.

Prompt for Claude Code:
```
Create ml/data/synthetic_layer.py that takes unified_features.parquet and applies India-realistic distributions.

Replace or adjust these columns with India-realistic values using numpy random with seed=42:

1. income: sample from a right-skewed distribution
   - 40% of applicants: ₹15,000–₹35,000/month (low income)
   - 35% of applicants: ₹35,000–₹1,00,000/month (middle income)
   - 20% of applicants: ₹1,00,000–₹2,50,000/month (upper middle)
   - 5% of applicants: ₹2,50,000+ (high income)

2. loan_amount: correlated with income (2x–8x monthly income range)

3. cibil_score_simulated:
   - 20% no file (score = 0, flag new_to_credit=True)
   - 30%: 300–599 (poor)
   - 35%: 600–749 (fair to good)
   - 15%: 750–900 (excellent)

4. employment_type: categorical
   - 35% salaried_private
   - 15% salaried_govt
   - 30% self_employed
   - 20% gig_worker

5. loan_purpose: categorical (text field — will pass through agent)
   - home_renovation, education, business_capital, medical, vehicle, personal

6. employer_description: short text strings per employment_type
   (e.g., "Software engineer at mid-size IT firm", "Freelance delivery partner")
   — these are the fields that will be sanitized before LLM injection

7. account_age_months: bimodal
   - 30% new accounts: 1–6 months
   - 70% established: 12–120 months

Output: ml/data/processed/india_synthetic.parquet
Print: final shape, class distribution for default_flag and fraud_flag, income distribution summary.
```

Exit condition: `india_synthetic.parquet` exists. Printed summary confirms India-realistic distributions. Script runs with seed=42 and produces identical output on re-run.

---

### Block 6: Synthetic Attack Generator

What it does: Generates parameterized fraudulent applicants representing 4 India-specific attack patterns. This is the project's most unique data component — used for both training and evaluation.

Prompt for Claude Code:
```
Create ml/attack_generator/generate_attacks.py that generates N synthetic fraudulent applicants per attack pattern.

The generator must be parameterized: generate_attacks(pattern, n=500, seed=42)

Implement all 4 patterns:

Pattern 1: stolen_pan_fabricated_employment
- cibil_score_simulated: high (680–800) — stolen from real person
- income: high declared (₹80,000–₹1,50,000)
- employment_type: salaried_private
- account_age_months: 2–5 (new — attacker just opened accounts)
- upi_velocity_percentile: low (5th–20th) — doesn't match declared income
- income_transaction_ratio: > 8 (income far exceeds transaction evidence)
- employer_description: generic, non-specific ("Works at private company")
- fraud_flag: 1, default_flag: 1

Pattern 2: fragmented_bureau_footprint
- cibil_score_simulated: 0 (no file) or 300–400 (thin)
- new_to_credit: True
- enquiry_count_30d: 6–12 (many recent enquiries across lenders)
- loan_amount: high (₹3,00,000–₹10,00,000)
- income: moderate (appears plausible on its own)
- account_age_months: 1–3
- fraud_flag: 1, default_flag: 1

Pattern 3: upi_velocity_spike
- All credit features: clean (normal applicant profile)
- upi_velocity_percentile: 95th–99th (massive spike)
- transaction_velocity_30d: 3x–10x their 6-month average (simulate as feature)
- income_transaction_ratio: < 0.5 (transactions exceed declared income)
- fraud_flag: 1, default_flag: 0 (may not default — bust-out pattern)

Pattern 4: synthetic_identity_clean
- All individual scores: clean (no single red flag)
- cibil_score_simulated: 720–780
- income: reasonable
- employment_type: salaried_private
- CRITICAL: account_age_months: 2–4 across ALL products
- new_to_credit: True
- enquiry_count_30d: 1–2 (careful attacker)
- fraud_flag: 1, default_flag: 1

Also create: ml/attack_generator/evaluate_attacks.py
- Load all 4 pattern outputs
- Run each through all three trained models (import model loading utils)
- Print detection rate per pattern per model
- This is the evaluation script — not needed until after models are trained

Output per pattern: ml/data/attacks/{pattern_name}.parquet
Also output: ml/data/attacks/combined_attacks.parquet (all patterns concatenated with pattern_label column)

Document every parameter choice with a comment referencing the fraud pattern it simulates.
```

Exit condition: 4 pattern parquet files exist in ml/data/attacks/. `combined_attacks.parquet` contains all patterns with `pattern_label` column. Script is deterministic with seed=42.

---

### Block 7: Final Training Dataset Assembly

What it does: Merges the India-realistic synthetic base with the attack patterns, applies SMOTE, and produces train/val/test splits ready for model training.

Prompt for Claude Code:
```
Create ml/data/prepare_dataset.py that assembles the final training dataset.

Steps:
1. Load india_synthetic.parquet (legitimate applicants)
2. Load combined_attacks.parquet (fraudulent applicants)
3. Concatenate — ensure no column mismatches, fill missing with documented defaults
4. Apply stratified train/val/test split: 70/15/15, stratified on fraud_flag
   seed=42 for reproducibility
5. Apply SMOTE ONLY on the training split (never val or test)
   Target fraud rate after SMOTE: 15–20% (sufficient signal for training)
   Document the pre-SMOTE and post-SMOTE class distribution in comments
6. Save splits:
   ml/data/processed/train.parquet
   ml/data/processed/val.parquet
   ml/data/processed/test.parquet
7. Save a dataset_card.md documenting:
   - Total samples per split
   - Class distribution pre and post SMOTE
   - Feature list with types
   - Known limitations (synthetic join, simulated features)
   - Why SMOTE was applied only to train split

Print final split shapes and class distributions.
```

Exit condition: Three parquet files exist. `dataset_card.md` exists. Printed output shows correct split sizes and realistic fraud rate in val/test (~2-3%).

---

## Task 3: ML Models

### Block 8: Credit Risk Scorer

What it does: Trains the credit risk model, evaluates it, logs the full run to MLflow, and registers the best model in the MLflow Model Registry.

Prompt for Claude Code:
```
Create ml/training/train_credit.py to train the credit risk scorer.

MLflow experiment name: loansense-credit-risk
MLflow model registry name: credit-risk-scorer

Steps:
1. Load train.parquet and val.parquet
2. Define credit risk feature set (from feature_definitions.md — income, loan_amount, emi_to_income_ratio, employment_type, cibil_score_simulated, loan_tenure_months, existing_obligations, account_age_months, new_to_credit)
3. Target: default_flag
4. Encode categoricals with OrdinalEncoder (save encoder artifact)
5. Train XGBoost classifier with these starting hyperparameters:
   n_estimators=200, max_depth=6, learning_rate=0.05, subsample=0.8, colsample_bytree=0.8, scale_pos_weight=(negative_count/positive_count)
6. Evaluate on val set:
   - ROC-AUC, PR-AUC, F1, precision, recall at threshold=0.5
   - Classification report
7. Log to MLflow:
   - All hyperparameters
   - All val metrics
   - Model artifact (XGBoost model + encoder)
   - SHAP feature importance plot as artifact
   - Tag: dataset_version=v1, feature_set=credit_v1
8. Register best model in MLflow Model Registry as credit-risk-scorer version 1

The model's predict_proba output is credit_risk_score (0-1).
Also output risk_band: Low (< 0.3), Medium (0.3–0.6), High (> 0.6).

Print final val metrics.
```

Exit condition: MLflow run logged under loansense-credit-risk experiment. Model registered as credit-risk-scorer in registry. Val ROC-AUC printed. Running the script twice produces the same registered model version.

---

### Block 9: Fraud Signal Detector

What it does: Trains the fraud signal detector with a rule-based pre-filter layer, evaluates it, and registers it in MLflow.

Prompt for Claude Code:
```
Create ml/training/train_fraud.py to train the fraud signal detector.

MLflow experiment name: loansense-fraud-signal
MLflow model registry name: fraud-signal-detector

This model has two layers:

Layer 1 — Rule-based pre-filter (implemented as a Python class, not an ML model):
Apply these rules first. If ANY rule fires, flag the field in fraud_signals list:
- income_transaction_ratio > 6: flag income_fabrication_risk
- enquiry_count_30d > 5: flag high_enquiry_velocity
- account_age_months < 6 AND cibil_score_simulated > 700: flag new_account_high_score
- upi_velocity_percentile > 90: flag transaction_velocity_anomaly

Layer 2 — XGBoost classifier on fraud signal features:
Features: transaction_velocity_30d, account_age_months, enquiry_count_30d, income_transaction_ratio, upi_velocity_percentile, new_to_credit, loan_amount (high ask is a signal)
Target: fraud_flag

Hyperparameters: n_estimators=300, max_depth=5, learning_rate=0.03, scale_pos_weight=(neg/pos)

Final output for any applicant:
- fraud_probability (0-1) from XGBoost
- fraud_signals: list of rule-triggered flags from Layer 1
- Combined: if any rule fires AND fraud_probability > 0.3 → elevated_fraud_risk=True

Evaluate on val set: ROC-AUC, F1, precision, recall, false positive rate (critical — high FPR = legitimate applicants rejected)

Log to MLflow:
- All params and metrics including false_positive_rate
- Rule definitions as tags
- Model + rule config as artifacts
- SHAP plot

Register as fraud-signal-detector version 1.
```

Exit condition: MLflow run logged. Model registered. Val metrics printed including false positive rate. Rule layer correctly flags at least 3 of 4 attack patterns when tested manually on combined_attacks.parquet.

---

### Block 10: Contradiction Detector — Rule Layer

What it does: Implements the first layer of the hybrid contradiction detector — explicit cross-signal rules that catch the tension between fraud and credit signals.

Prompt for Claude Code:
```
Create ml/training/contradiction/rules.py implementing the rule-based cross-check layer.

This is NOT an ML model. It is a deterministic rule engine.

Implement a ContradictionRuleEngine class with method:
check(applicant_features: dict, credit_risk_score: float, fraud_probability: float) -> dict

Rules to implement (each returns a flag with severity and detail):

Rule 1: HIGH_SCORE_NEW_ACCOUNT (severity: HIGH)
Condition: cibil_score_simulated > 700 AND account_age_months < 6
Flag: synthetic_identity_risk
Detail: "CIBIL score of {score} with account age of {age} months is inconsistent — known synthetic identity pattern"

Rule 2: INCOME_TRANSACTION_MISMATCH (severity: HIGH)
Condition: income_transaction_ratio > 5 (declared income >> transaction evidence)
Flag: income_fabrication_risk
Detail: "Declared income implies monthly transactions of ~₹{expected} but observed average is ₹{actual}"

Rule 3: CREDIT_FRAUD_DIVERGENCE (severity: MEDIUM)
Condition: credit_risk_score < 0.25 AND fraud_probability > 0.45
Detail: "Low credit risk score conflicts with elevated fraud probability — signals warrant joint review"
Flag: credit_fraud_signal_divergence

Rule 4: ENQUIRY_BURST_THIN_FILE (severity: HIGH)
Condition: enquiry_count_30d > 5 AND (new_to_credit == True OR cibil_score_simulated < 400)
Flag: bust_out_pattern
Detail: "{n} bureau enquiries in 30 days on a thin credit file — known bust-out fraud pattern"

Rule 5: CLEAN_PROFILE_VELOCITY (severity: MEDIUM)
Condition: upi_velocity_percentile > 92 AND credit_risk_score < 0.3 AND fraud_probability < 0.3
Flag: pre_application_velocity_spike
Detail: "Transaction velocity spike detected on otherwise clean profile — consistent with account warming"

Output from check():
{
  "rule_flags": [list of fired flags with severity and detail],
  "rule_flag_count": int,
  "max_severity": "HIGH" | "MEDIUM" | "NONE",
  "any_high_severity": bool
}

Write unit tests in tests/test_contradiction.py covering all 5 rules with inputs that should fire and inputs that should not.
```

Exit condition: `rules.py` exists. All unit tests in `test_contradiction.py` pass with `pytest tests/test_contradiction.py`. Each rule fires on expected input and does not fire on clean input.

---

### Block 11: Contradiction Detector — Statistical + Meta-Model Layers

What it does: Adds Isolation Forest anomaly detection and a Logistic Regression meta-model on top of the rule layer to produce the final contradiction score.

Prompt for Claude Code:
```
Create ml/training/train_contradiction.py implementing the full hybrid contradiction detector.

MLflow experiment name: loansense-contradiction
MLflow model registry name: contradiction-detector

Build on rules.py from Block 10. Add:

Layer 1 — Isolation Forest (statistical anomaly):
- Train on the joint feature space: all credit features + all fraud features combined
- contamination=0.05 (expect ~5% anomalies)
- Output: anomaly_score (convert decision_function output to 0-1 range)
- Train ONLY on legitimate applicants (fraud_flag=0) so fraud patterns are outliers

Layer 2 — Rule engine:
- Import ContradictionRuleEngine from rules.py
- Run on each applicant
- Extract: rule_flag_count, any_high_severity (as 0/1)

Layer 3 — Meta-model (Logistic Regression):
- Features: [credit_risk_score, fraud_probability, anomaly_score, rule_flag_count, any_high_severity]
- Target: fraud_flag (from training data)
- This learns to weight the signals correctly
- Output: contradiction_score (0-1)

Final ContradictionDetector class must expose:
predict(applicant_features, credit_risk_score, fraud_probability) -> {
  contradiction_score: float,
  anomaly_score: float,
  rule_flags: list,
  contradiction_type: "SYNTHETIC_IDENTITY" | "INCOME_FABRICATION" | "BUST_OUT" | "VELOCITY_ANOMALY" | "SIGNAL_DIVERGENCE" | "NONE"
}

contradiction_type is determined by highest-severity rule flag fired.
If no rules fire but anomaly_score > 0.7: contradiction_type = "SIGNAL_DIVERGENCE"

Evaluate on val set AND on combined_attacks.parquet (attack detection rate per pattern).
Log everything to MLflow. Register as contradiction-detector version 1.

Target: detect at least 3 of 4 attack patterns with contradiction_score > 0.6.
```

Exit condition: MLflow run logged. Model registered. Attack detection rates printed per pattern. `pytest tests/test_contradiction.py` still passes with the full model loaded.

---

## Task 4: FastAPI Backend

### Block 12: Database Setup ✅ Completed

What it does: Creates the PostgreSQL schema, runs Alembic migrations, and verifies all four tables are created correctly.

Prompt for Claude Code:
```
Set up the PostgreSQL database layer for LoanSense.

1. Create backend/app/db/database.py:
   - SQLAlchemy engine using DATABASE_URL from .env
   - SessionLocal factory
   - Base declarative class
   - get_db() dependency for FastAPI

2. Create backend/app/db/models.py with these SQLAlchemy ORM models:

Table: applicants
- id: UUID primary key, default uuid4
- created_at: TIMESTAMPTZ, default now()
- name: Text
- pan_hash: Text (SHA-256 hash of PAN — never raw)
- monthly_income: Numeric
- loan_amount: Numeric
- loan_purpose: Text
- employment_type: Text
- employer_description: Text
- cibil_score_simulated: Integer
- raw_features: JSONB (full feature vector)

Table: model_outputs
- id: UUID primary key
- applicant_id: UUID FK → applicants.id
- model_name: Text ('credit_risk' | 'fraud_signal' | 'contradiction')
- model_version: Text
- score: Numeric
- signals: JSONB
- created_at: TIMESTAMPTZ

Table: agent_verdicts
- id: UUID primary key
- applicant_id: UUID FK → applicants.id
- decision: Text ('APPROVE' | 'FLAG_FOR_REVIEW' | 'REJECT')
- confidence: Numeric
- primary_reason: Text
- risk_signals: JSONB
- rbi_mapping: JSONB
- what_would_change: Text
- created_at: TIMESTAMPTZ

Table: audit_logs
- id: UUID primary key
- applicant_id: UUID FK → applicants.id
- event_type: Text
- event_data: JSONB
- created_at: TIMESTAMPTZ

3. Set up Alembic:
   alembic init alembic
   Configure alembic.ini to use DATABASE_URL from env
   Create initial migration: alembic revision --autogenerate -m "initial schema"
   Run migration: alembic upgrade head

4. Create backend/app/db/crud.py with functions:
   - create_applicant(db, applicant_data) -> Applicant
   - create_model_output(db, applicant_id, model_name, version, score, signals) -> ModelOutput
   - create_verdict(db, applicant_id, verdict_data) -> AgentVerdict
   - create_audit_log(db, applicant_id, event_type, event_data) -> AuditLog
   - get_verdicts_by_applicant(db, applicant_id) -> list[AgentVerdict]
   - get_audit_logs_by_applicant(db, applicant_id) -> list[AuditLog]
   - get_recent_verdicts(db, limit=20) -> list[AgentVerdict]
```

Exit condition: `alembic upgrade head` runs without errors. All four tables visible in PostgreSQL via `\dt`. `pytest tests/test_db.py` passes basic write/read tests for each table.

---

### Block 13: Model Loading & Serving Layer ✅ Completed

What it does: Builds the module that loads all three models from MLflow registry at startup and exposes them as callable functions for the agent's tool calls.

Prompt for Claude Code:
```
Create backend/app/models/loader.py that loads all three models from MLflow registry at FastAPI startup.

Model registry names (from CLAUDE.md):
- credit-risk-scorer
- fraud-signal-detector
- contradiction-detector

Implement:

class ModelRegistry:
    def __init__(self):
        self.credit_model = None
        self.fraud_model = None
        self.contradiction_model = None
        self._loaded = False

    def load_all(self):
        # Load latest Production or Staging version of each model from MLflow registry
        # Store model objects and their versions for audit logging

    def get_credit_score(self, features: dict) -> dict:
        # Returns: { credit_risk_score, risk_band, model_version }

    def get_fraud_signals(self, features: dict) -> dict:
        # Returns: { fraud_probability, fraud_signals, elevated_fraud_risk, model_version }

    def get_contradiction_score(self, features: dict, credit_risk_score: float, fraud_probability: float) -> dict:
        # Returns: { contradiction_score, anomaly_score, rule_flags, contradiction_type, model_version }

# Singleton instance
model_registry = ModelRegistry()

In backend/app/main.py:
- On startup event: call model_registry.load_all()
- If any model fails to load: log error and raise — do not start with missing models

Create tests/test_model_loading.py:
- Test that all three models load without error
- Test that get_credit_score returns expected keys
- Test that get_fraud_signals returns expected keys
- Test that get_contradiction_score returns expected keys
```

Exit condition: `pytest tests/test_model_loading.py` passes. FastAPI startup logs confirm all three models loaded with their versions.

---

### Block 14: FastAPI Routes ✅ Completed

What it does: Implements all four API endpoints with Pydantic validation, input sanitization, and proper error handling.

Prompt for Claude Code:
```
Implement all FastAPI routes for LoanSense.

First, create backend/app/schemas/applicant.py with Pydantic models:

ApplicantInput:
- name: str (min 2, max 100 chars)
- pan_hash: str (SHA-256 hash — frontend hashes before sending)
- monthly_income: float (gt=0, lt=10000000)
- loan_amount: float (gt=0, lt=100000000)
- loan_purpose: Literal["home_renovation","education","business_capital","medical","vehicle","personal"]
- employment_type: Literal["salaried_private","salaried_govt","self_employed","gig_worker"]
- employer_description: str (max 200 chars)
- cibil_score_simulated: int (ge=0, le=900)
- account_age_months: int (ge=0)
- enquiry_count_30d: int (ge=0)
- upi_velocity_percentile: float (ge=0, le=100)
- transaction_velocity_30d: float (ge=0)

CRITICAL: Add a sanitize_text() helper that strips any content that looks like prompt injection from employer_description and loan_purpose before they touch the agent. Flag any input containing: "ignore previous instructions", "system:", "assistant:", or similar LLM control tokens.

Implement these routers:

backend/app/routers/assess.py — POST /assess
- Validate ApplicantInput
- Sanitize text fields
- Create applicant record in DB
- Log audit event: assessment_started
- Call agent orchestrator (stub for now — returns mock verdict)
- Store model outputs and verdict in DB
- Log audit event: verdict_issued
- Return verdict JSON

backend/app/routers/verdicts.py — GET /verdicts/{applicant_id}
- Return all verdicts for an applicant

backend/app/routers/audit.py — GET /audit/{applicant_id}
- Return full audit log for an applicant

backend/app/routers/health.py — GET /health
- Return: { status: "ok", models_loaded: bool, db_connected: bool }

Wire all routers in backend/app/main.py with /api/v1 prefix.
Configure CORS: allow origin from FRONTEND_URL env var only.

Create tests/test_endpoints.py:
- Test POST /assess with valid input returns 200
- Test POST /assess with missing field returns 422
- Test POST /assess with prompt injection in employer_description is sanitized
- Test GET /health returns models_loaded=true after startup
```

Exit condition: `pytest tests/test_endpoints.py` passes. `GET /api/v1/health` returns 200 with models_loaded=true. POST /assess with valid ApplicantInput returns a verdict (mock for now). Prompt injection test passes.

---

## Task 5: Agent Reasoning Layer

### Block 15: Agent Tool Definitions

What it does: Defines the three Gemini function-calling tool schemas that the agent uses to query the ML models.

Prompt for Claude Code:
```
Create backend/app/agent/tools.py defining the three Gemini tool schemas and their implementations.

Using the google-generativeai SDK, define tools as genai.protos.Tool objects:

Tool 1: get_credit_risk_score
Description: "Returns the credit risk score and risk band for the loan applicant. Score ranges from 0 (no risk) to 1 (high risk). Risk bands: Low (<0.3), Medium (0.3-0.6), High (>0.6)."
Parameters: { applicant_id: string }
Implementation: calls model_registry.get_credit_score() and logs result to audit_logs

Tool 2: get_fraud_signals
Description: "Returns fraud probability and specific fraud signal flags triggered for the applicant. Signals include: income_fabrication_risk, high_enquiry_velocity, new_account_high_score, transaction_velocity_anomaly."
Parameters: { applicant_id: string }
Implementation: calls model_registry.get_fraud_signals() and logs result

Tool 3: get_contradiction_score
Description: "Returns the contradiction score quantifying the tension between credit and fraud signals. Also returns the contradiction type and specific rule flags fired. A score above 0.6 indicates a significant contradiction requiring human review."
Parameters: { applicant_id: string }
Implementation: calls model_registry.get_contradiction_score() and logs result

Also implement: execute_tool_call(tool_name: str, applicant_id: str, db: Session) -> dict
This is the dispatcher the orchestrator calls when Gemini returns a function_call response.

Each tool execution must:
1. Call the appropriate model registry function
2. Write to audit_logs: event_type="model_called", event_data={tool_name, result, model_version}
3. Return the result dict to the agent
```

Exit condition: All three tools defined with correct Gemini schema. `execute_tool_call` dispatches correctly for all three tool names. Audit log writes confirmed in test.

---

### Block 16: Agent System Prompt & Orchestrator

What it does: Implements the full agent reasoning loop — system prompt, tool call handling, verdict extraction, and the core rule that contradiction_score > 0.6 never approves.
*(Note: Must replace the mock Agent Verdict currently implemented in the POST /assess route.)*

Prompt for Claude Code:
```
Create backend/app/agent/prompts.py and backend/app/agent/orchestrator.py.

In prompts.py, define SYSTEM_PROMPT as a module-level string:

The system prompt must instruct the agent to:
1. Always call all three tools before forming any verdict — no shortcuts
2. When credit and fraud signals conflict, treat the conflict itself as primary evidence
3. Never approve an application with contradiction_score > 0.6 — this is a hard rule
4. Produce output ONLY in the specified JSON schema — no prose, no markdown
5. Map every decision reason to an RBI Fair Practices Code category
6. The what_would_change field must be specific and actionable, not generic
7. Confidence should reflect genuine certainty — not always 0.9

Include in the prompt: the exact JSON output schema the agent must return.
Include: two worked examples (one approval, one rejection) showing correct reasoning.
Reference the domain-research.md findings on the 4 fraud patterns.

In orchestrator.py, implement:

class AgentOrchestrator:
    def __init__(self, model_registry, db):
        self.model = genai.GenerativeModel(
            model_name="gemini-1.5-flash",
            generation_config={"temperature": 0, "response_mime_type": "application/json"},
            system_instruction=SYSTEM_PROMPT,
            tools=[get_credit_risk_score_tool, get_fraud_signals_tool, get_contradiction_score_tool]
        )

    async def assess(self, applicant_id: str, applicant_context: str) -> dict:
        # 1. Start chat with applicant summary as first user message
        # 2. Handle tool call loop:
        #    - If response contains function_call: execute it, send result back
        #    - Repeat until response contains no function_call
        # 3. Parse final JSON response into verdict schema
        # 4. ENFORCE: if contradiction_score > 0.6 and decision == "APPROVE": override to FLAG_FOR_REVIEW, log override event
        # 5. Return structured verdict dict
        # On Gemini API error: retry once, then return a safe fallback verdict with decision=FLAG_FOR_REVIEW

Wire AgentOrchestrator into the /assess endpoint in routers/assess.py (replace the stub from Block 14).

Add tests/test_agent.py:
- Test that contradiction_score > 0.6 never produces APPROVE (invariant)
- Test that all three tools are called for every assessment (check audit logs)
- Test that malformed Gemini response triggers fallback, not 500 error
```

Exit condition: `pytest tests/test_agent.py` passes including the invariant test. A full assessment via POST /assess triggers all three tool calls (visible in audit_logs). Verdict returned matches JSON schema.

---

### Block 17: Prompt Iteration & Agent Evaluation

What it does: Tests the agent against all 4 attack patterns and iterates the system prompt until detection is satisfactory. This block is expected to take more time than others.

Prompt for Claude Code:
```
Create ml/attack_generator/evaluate_agent.py to evaluate the full agent pipeline against synthetic attack patterns.

Steps:
1. Load combined_attacks.parquet
2. For each attack applicant (sample 50 per pattern = 200 total):
   - Insert applicant into DB via the /assess endpoint (use httpx test client)
   - Collect returned verdict
3. Compute per pattern:
   - Detection rate: % of fraud cases that got FLAG_FOR_REVIEW or REJECT
   - False approval rate: % of fraud cases that got APPROVE (should be 0 after invariant)
   - Average contradiction_score
   - Most common primary_reason text (do the reasons make sense?)
4. Also test on 50 legitimate applicants — compute false flag rate (should be < 15%)
5. Print full evaluation report

Acceptance criteria:
- Pattern 1 (stolen PAN): detection rate > 80%
- Pattern 2 (fragmented bureau): detection rate > 85%
- Pattern 3 (velocity spike): detection rate > 75%
- Pattern 4 (synthetic identity): detection rate > 70%
- False flag rate on legitimate applicants: < 15%

If criteria are not met: adjust system prompt in prompts.py and re-run.
Document which prompt changes improved which metrics in docs/prompt-iteration-log.md.
Run minimum 3 iterations before declaring done.
```

Exit condition: All acceptance criteria met. `prompt-iteration-log.md` documents at least 3 iterations with metrics per iteration. No attack pattern produces APPROVE verdicts.

---

## Task 6: Testing

### Block 18: Full pytest Suite

What it does: Ensures the complete test suite covers all contradiction cases, endpoint validation, model loading, DB operations, and prompt injection — with all tests passing.

Prompt for Claude Code:
```
Consolidate and complete the full pytest suite. All tests from previous blocks should already exist. This block ensures completeness and adds any missing coverage.

Verify and complete tests in:

tests/test_contradiction.py — 5 rule tests (Block 10) + 3 full model tests:
- test_high_cibil_new_account_flags_synthetic_identity: cibil=790, account_age=3 → contradiction_type=SYNTHETIC_IDENTITY
- test_income_transaction_mismatch: income_ratio=8 → rule_flag=income_fabrication_risk
- test_clean_profile_no_contradiction: all clean inputs → contradiction_score < 0.3

tests/test_agent.py — from Block 16 plus:
- test_approve_verdict_structure: valid approval has all required JSON fields
- test_reject_verdict_has_rbi_mapping: rejection verdict always has rbi_mapping field
- test_what_would_change_is_specific: what_would_change is not empty or generic

tests/test_endpoints.py — from Block 14 plus:
- test_full_assessment_flow: POST /assess → GET /verdicts/{id} → GET /audit/{id} all work in sequence
- test_invalid_cibil_score_rejected: cibil_score=950 → 422 validation error
- test_negative_income_rejected: monthly_income=-1 → 422

tests/test_db.py:
- test_applicant_create_and_read
- test_verdict_create_and_read
- test_audit_log_create_and_read
- test_model_output_create_and_read

tests/test_model_loading.py — from Block 13

Security tests:
- test_prompt_injection_in_employer_description: input with "ignore previous instructions" is sanitized before agent call
- test_prompt_injection_in_loan_purpose: same for loan_purpose field

Run full suite: pytest tests/ -v --tb=short
All tests must pass before frontend work begins.
```

Exit condition: `pytest tests/ -v` shows all tests passing. Zero failures. Zero errors. Test count ≥ 25.

---

## Task 7: React Frontend

### Block 19: Frontend Scaffold & Layout

What it does: Sets up the React project with Tailwind, defines the routing structure, and builds the persistent layout shell (sidebar + content area).

Prompt for Claude Code:
```
Set up the LoanSense React frontend with Vite + Tailwind.

Design direction (from CLAUDE.md):
- Dark sidebar (#1a1f2e), white/light content area (#f8fafc)
- Professional, data-dense financial product aesthetic
- Color-coded verdict badges: green (#16a34a) for APPROVE, amber (#d97706) for FLAG_FOR_REVIEW, red (#dc2626) for REJECT
- Font: Inter (import from Google Fonts)
- No unnecessary animation

1. Install dependencies: react-router-dom, axios
2. Configure Tailwind with the color tokens above as custom colors in tailwind.config.js
3. Create frontend/src/api/client.js:
   - Axios instance with baseURL from VITE_API_URL env var
   - Default headers: Content-Type: application/json
   - Error interceptor: log errors, re-throw for component handling

4. Create frontend/src/components/Layout.jsx:
   - Dark left sidebar (w-64) with:
     - LoanSense logo/wordmark at top
     - Nav links: Dashboard, New Assessment, Audit Log
     - Active link highlighted
   - Main content area (flex-1) with padding

5. Set up React Router in frontend/src/App.jsx:
   - / → Dashboard
   - /assess → New Assessment
   - /verdict/:id → Verdict Display
   - /audit → Audit Log
   All routes wrapped in Layout

6. Create placeholder page components for each route (content added in next blocks)

Confirm: npm run dev shows the sidebar with navigation links. Clicking links changes the URL.
```

Exit condition: `npm run dev` runs without errors. Sidebar renders with all four nav links. React Router navigation works between pages.

---

### Block 20: Assessment Form Page

What it does: Builds the loan application form that collects all applicant fields and submits to the /assess endpoint.

Prompt for Claude Code:
```
Build frontend/src/pages/Assess.jsx — the loan application form.

Fields (matching ApplicantInput schema):
- Name (text input)
- Monthly Income in ₹ (number input)
- Loan Amount in ₹ (number input)
- Loan Purpose (select: home_renovation, education, business_capital, medical, vehicle, personal — display as readable labels)
- Employment Type (select: Salaried (Private), Salaried (Government), Self-Employed, Gig Worker)
- Employer Description (textarea, max 200 chars, character counter shown)
- CIBIL Score (number input, 300-900 range, show slider)
- Account Age in Months (number input)
- Bureau Enquiries in Last 30 Days (number input)
- UPI Velocity Percentile (number input 0-100)
- Transaction Velocity 30d (number input)

PAN handling:
- PAN input field (text, masked after entry)
- Hash with SHA-256 in the browser before sending: use Web Crypto API
  const encoder = new TextEncoder()
  const data = encoder.encode(pan)
  const hashBuffer = await crypto.subtle.digest('SHA-256', data)
  const hashArray = Array.from(new Uint8Array(hashBuffer))
  const pan_hash = hashArray.map(b => b.toString(16).padStart(2, '0')).join('')

Form behavior:
- Client-side validation matching Pydantic constraints (required fields, ranges)
- Show field-level error messages on blur
- Submit button disabled while submitting
- On submit: POST to /api/v1/assess
- On success: navigate to /verdict/{applicant_id}
- On error: show error message inline, do not clear form

Layout: two-column form grid on desktop, single column on mobile.
```

Exit condition: Form renders all fields. Client-side validation works for required fields and ranges. Submitting a valid form POSTs to /api/v1/assess and navigates to verdict page on success.

---

### Block 21: Verdict Display Page

What it does: Builds the verdict page that displays the agent's decision with full signal breakdown and RBI mapping.

Prompt for Claude Code:
```
Build frontend/src/pages/Verdict.jsx — the verdict display page.

Fetch verdict: GET /api/v1/verdicts/{applicant_id} on page load.

Layout sections:

1. Decision Banner (full width, color-coded):
   - APPROVE: green background, "✓ Approved" in large text
   - FLAG_FOR_REVIEW: amber background, "⚠ Flagged for Manual Review"
   - REJECT: red background, "✗ Application Rejected"
   - Show confidence as: "Confidence: 87%" below the decision

2. Primary Reason card:
   - Heading: "Decision Basis"
   - Body: primary_reason text in readable prose
   - Subtext: "What would change this decision:" → what_would_change text in italic

3. Risk Signals section:
   - Heading: "Risk Signals Detected"
   - Each signal as a row: signal name | severity badge (HIGH=red, MEDIUM=amber, LOW=green) | detail text
   - If no signals: "No significant risk signals detected"

4. RBI Compliance card:
   - Heading: "Regulatory Basis"
   - Show rbi_mapping.category, rbi_mapping.requirement, rbi_mapping.satisfied_by
   - Small text: "This decision record satisfies RBI Fair Practices Code documentation requirements"

5. Applicant Summary sidebar:
   - Key facts: loan amount, income, CIBIL score, employment type
   - Assessment timestamp

6. Action buttons:
   - "View Audit Trail" → navigates to /audit?applicant_id={id}
   - "New Assessment" → navigates to /assess
   - "Print / Export" → window.print() (basic)

Loading state: skeleton loader while fetching.
Error state: "Verdict not found" with link back to /assess.
```

Exit condition: Verdict page renders correctly for APPROVE, FLAG_FOR_REVIEW, and REJECT decisions (test with mock data). All sections display. Color coding is correct.

---

### Block 22: Dashboard & Audit Log Pages

What it does: Builds the dashboard with recent assessments and stats, and the audit log view with full event history.

Prompt for Claude Code:
```
Build two remaining pages:

frontend/src/pages/Dashboard.jsx:

Fetch: GET /api/v1/verdicts/recent (add this endpoint to backend if not exists — returns last 20 verdicts)

Sections:
1. Stats row (3 cards):
   - Total Assessments Today
   - Approval Rate (% APPROVE)
   - Flagged for Review Count
   Compute from the 20 most recent verdicts (approximate — this is a portfolio demo, not a real BI tool)

2. Drift Alert Banner:
   - GET /api/v1/health — if response includes drift_alert: true, show amber banner: "⚠ Model drift detected — review recommended"
   - Otherwise: hidden

3. Recent Assessments table:
   - Columns: Applicant Name | Loan Amount | Decision (badge) | Confidence | Timestamp | View
   - Clicking View → navigates to /verdict/{applicant_id}
   - Show last 20 entries

frontend/src/pages/Audit.jsx:

Fetch: GET /api/v1/audit/{applicant_id} (applicant_id from query param)

Display:
- Timeline of audit events, newest first
- Each event: timestamp | event_type (formatted readable) | event_data summary
- Event types to display readably:
  assessment_started → "Assessment initiated"
  model_called → "Model queried: {tool_name}"
  verdict_issued → "Verdict issued: {decision}"
  drift_alert → "⚠ Drift alert triggered"

Empty state: "No audit events found for this applicant ID"
```

Exit condition: Dashboard renders with stats and recent verdicts table. Drift alert banner shows when health endpoint returns drift_alert=true. Audit page renders timeline for a valid applicant_id.

---

## Task 8: MLOps

### Block 23: Drift Detection

What it does: Implements PSI-based drift detection that logs alerts to the database when model score distributions shift from baseline.

Prompt for Claude Code:
```
Create ml/drift/psi.py and ml/drift/monitor.py.

In psi.py:
Implement calculate_psi(baseline_scores: np.array, current_scores: np.array, bins=10) -> float

PSI formula:
- Bin both distributions into equal-width bins over [0,1]
- PSI = sum((current% - baseline%) * ln(current% / baseline%))
- Handle zero bins: add small epsilon (1e-4) before log
- Return float PSI value

PSI interpretation thresholds (document in docstring):
- PSI < 0.1: no significant change
- 0.1 ≤ PSI < 0.2: moderate change — monitor
- PSI ≥ 0.2: significant shift — alert

In monitor.py:
Implement run_drift_check(db: Session, model_registry: ModelRegistry)

Steps:
1. Load baseline score distributions (saved during training — store as JSON artifact in MLflow)
2. Query last 7 days of model_outputs from PostgreSQL for each model
3. If fewer than 50 predictions in last 7 days: skip (insufficient data — log a note)
4. Calculate PSI for each model's score distribution vs baseline
5. If any PSI ≥ 0.2: write to audit_logs:
   event_type="drift_alert"
   event_data={ model_name, psi_value, threshold: 0.2, recommendation: "Review model performance" }
6. Return { model_name: psi_value } dict for all models

Add GET /api/v1/drift endpoint in FastAPI:
- Calls run_drift_check
- Returns { drift_detected: bool, details: { model_name: psi_value } }

Update GET /health to include drift_alert: bool from last drift check result.

Write tests/test_drift.py:
- test_psi_identical_distributions_returns_zero
- test_psi_completely_different_distributions_returns_high
- test_psi_threshold_0_2_triggers_alert
```

Exit condition: `pytest tests/test_drift.py` passes. GET /api/v1/drift returns valid JSON. Health endpoint includes drift_alert field.

---

## Task 9: Deployment

### Block 24: Dockerization & Deployment

What it does: Dockerizes the backend, deploys to Railway or Render with PostgreSQL, and confirms the hosted demo is live.
*(Note: Must update FastAPI CORS configuration in app/main.py, currently hardcoded to localhost, to allow the production frontend domain.)*

Prompt for Claude Code:
```
Prepare LoanSense for deployment on Railway or Render.

1. Create backend/Dockerfile:
   FROM python:3.11-slim
   WORKDIR /app
   COPY requirements.txt .
   RUN pip install --no-cache-dir -r requirements.txt
   COPY . .
   EXPOSE 8000
   CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]

2. Create backend/.dockerignore:
   .env, mlruns/, __pycache__/, *.pyc, .venv/, data/raw/

3. Create backend/scripts/warmup.py:
   Simple script that POSTs a test applicant to /api/v1/assess and prints response time.
   Used to warm up the container before a demo.

4. Create railway.json or render.yaml with service configuration:
   - Backend service: Python, start command uvicorn app.main:app --host 0.0.0.0 --port $PORT
   - PostgreSQL: managed database add-on
   - Environment variables to set (list them — not values): DATABASE_URL, GEMINI_API_KEY, MLFLOW_TRACKING_URI, ENVIRONMENT, FRONTEND_URL

5. For frontend: create vercel.json or netlify.toml
   Build command: npm run build
   Output: dist/
   Set VITE_API_URL to hosted backend URL

6. Create deployment-checklist.md:
   - [ ] .env not committed
   - [ ] All env vars set in hosting platform
   - [ ] Database migrated (alembic upgrade head runs on deploy)
   - [ ] MLflow models accessible (note: MLflow model files need to be bundled or use remote tracking URI)
   - [ ] CORS configured for production frontend URL
   - [ ] /health endpoint returns 200
   - [ ] Warmup script runs successfully
   - [ ] Full assessment tested on hosted demo

Note on MLflow in production: for a portfolio project, bundling the model files directly and loading from path is simpler than running a full MLflow tracking server. Document this tradeoff explicitly.
```

Exit condition: `docker build` completes without errors. `deployment-checklist.md` created. Backend deployed and GET /health returns 200 on hosted URL.

---

## Task 10: Documentation & Polish

### Block 25: README as System Design Doc

What it does: Produces the README that functions as a system design document — the artifact that a recruiter or engineer reads first.

Prompt for Claude Code:
```
Create README.md in the project root. This is a system design document, not a standard README.

Structure:

# LoanSense
One-line: "Agentic underwriting intelligence for Indian NBFCs — jointly modeling fraud and credit risk with explainable, RBI-aligned decisions."

## The Problem
2 paragraphs: Why siloed fraud + credit models miss synthetic identity fraud. The specific gap LoanSense addresses.

## Architecture
ASCII architecture diagram (from the plan doc).
Brief description of each component and data flow.

## The Contradiction Detector
This gets its own section — it's the core IP.
Explain the 3-layer hybrid approach. Why it beats naive ensembling. Include the 4 contradiction rules.

## Synthetic Attack Generator
Describe the 4 India-specific fraud patterns parameterized. Include detection rates from Block 17 evaluation.
- Also include the per-pattern default_flag breakdown (Patterns 1, 2, 3, 4 separately) to demonstrate the label-feature divergence.

## Tech Stack
Table with Layer | Choice | Rationale

## Design Tradeoffs
Table format (from plan):
| Decision | Tradeoff | Why |

## RBI Compliance Alignment
The two sample verdicts (Approve and Reject) showing RBI mapping. Explain which Fair Practices Code sections are addressed.

## MLOps
Describe MLflow tracking, model registry, and PSI drift detection. Note what's implemented vs. documented-only.

## ROI Playbook
The one-pager with honest assumptions and ranges (from plan).

## Running Locally
Step-by-step: clone, .env setup, pip install, alembic upgrade head, uvicorn, npm run dev.

## Running Tests
Single command: pytest tests/ -v — expected output description.

## Project Structure
Directory tree with one-line description per directory.

## Known Limitations
Honest section: synthetic data, no real CIBIL integration, LLM non-determinism mitigated by temperature=0, Gemini free tier rate limits.

Length target: thorough but scannable. Use tables and headers. No marketing language.
```

Exit condition: README.md exists at project root. Architecture diagram is accurate. Both RBI sample verdicts are present. Tradeoffs table is complete. Local setup instructions work when followed from scratch.

---

### Block 26: Demo Video & Resume Bullets

What it does: Records the demo walkthrough and writes the final resume bullet points.

Prompt for Claude Code:
```
Two deliverables for this final block:

1. Create docs/demo-script.md — a structured script for recording the demo video:

Scene 1 (30 sec): Show the dashboard with recent assessments and explain the problem in one sentence.

Scene 2 (60 sec): Submit a clean legitimate application. Show the APPROVE verdict with confidence score and RBI mapping. Highlight the what_would_change field.

Scene 3 (90 sec): Submit a Pattern 1 attack (stolen PAN + fabricated employment). Walk through:
- The REJECT verdict
- The contradiction signals detected
- The primary_reason in plain language
- The audit trail showing all three model calls

Scene 4 (30 sec): Show the audit log timeline for the fraud case.

Scene 5 (30 sec): Show the drift detection dashboard banner (trigger manually if needed).

Total target: ~4 minutes.

2. Create docs/resume-bullets.md with 4 resume bullet points in Google XYZ format:
(Accomplished X, as measured by Y, by doing Z)

Write bullets covering:
- The contradiction detector (technical depth)
- The agent reasoning layer (agentic AI angle)
- The MLOps layer (production systems angle)
- The full system end-to-end (scope and completion)

Be honest about what was built vs. simulated. Do not overclaim.
```

Exit condition: `demo-script.md` exists with all 5 scenes. `resume-bullets.md` exists with 4 XYZ-format bullets. Bullets are honest, specific, and avoid generic language.
