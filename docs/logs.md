# LoanSense — Command Logs

This file tracks all terminal commands run during the implementation.

### Task 1: Domain Research & Project Setup

**Block 1: Domain Research**
- No commands run. Research performed via web search.

**Block 2: Project Scaffolding**
```powershell
# Create backend directories
New-Item -ItemType Directory -Force -Path "backend\app\routers", "backend\app\agent", "backend\app\models", "backend\app\db", "backend\app\schemas", "backend\ml\data\raw", "backend\ml\data\processed", "backend\ml\training", "backend\ml\attack_generator", "backend\ml\drift", "backend\tests", "backend\mlruns", "backend\alembic"

# Create __init__.py files
New-Item -ItemType File -Force -Path "backend\app\__init__.py", "backend\app\routers\__init__.py", "backend\app\agent\__init__.py", "backend\app\models\__init__.py", "backend\app\db\__init__.py", "backend\app\schemas\__init__.py", "backend\ml\__init__.py", "backend\ml\data\__init__.py", "backend\ml\training\__init__.py", "backend\ml\attack_generator\__init__.py", "backend\ml\drift\__init__.py", "backend\tests\__init__.py"

# Create requirements.txt, .env.template, .gitignore
# (Files created directly via write_to_file)

# Scaffold frontend with Vite
npm create vite@latest frontend -- --template react

# Downgrade Tailwind for standard init format, then init
cd frontend
npm install -D tailwindcss@^3.4.1 postcss autoprefixer
npx tailwindcss init -p
cd ..

# Setup Python Virtual Environment and Install Dependencies
python -m venv backend\.venv
.\backend\.venv\Scripts\python -m pip install --upgrade pip
.\backend\.venv\Scripts\pip install -r backend\requirements.txt

# Verify PostgreSQL is running on port 5432
Test-NetConnection -ComputerName localhost -Port 5432

# Verify MLflow module was installed successfully
.\backend\.venv\Scripts\python -c "import mlflow; print('MLflow installed:', mlflow.__version__)"

# Fix: MLflow 3.13 deprecated filesystem backend — switch to SQLite
# Updated .env.template: MLFLOW_TRACKING_URI=sqlite:///mlruns/mlflow.db
.\backend\.venv\Scripts\mlflow ui --backend-store-uri "sqlite:///backend/mlruns/mlflow.db" --port 5555

# Fix: tailwind.config.js content array was empty (would purge all classes)
# Updated content: ["./index.html", "./src/**/*.{js,ts,jsx,tsx}"]

# Verify frontend dev server launches
cd frontend; npm run dev
# Output: VITE v8.0.16 ready — http://localhost:5173/

# Clean up stray .venv from project root (created during early failed attempt)
Remove-Item -Recurse -Force .\.venv
```

**Block 3: Dataset Acquisition & Audit**
```powershell
# Attempt to check if Kaggle CLI is available
kaggle competitions list
# Output: CommandNotFoundException

# Check if kaggle.json API token exists
Test-Path ~/.kaggle/kaggle.json
# Output: False

# Created backend/ml/data/raw/README.md with download instructions
# (File created directly)

# Created backend/ml/data/audit_data.py to run the audit once data is downloaded
# (File created directly)

# After manual dataset download, ran the audit script
.\backend\.venv\Scripts\python backend\ml\data\audit_data.py
# Output: Audit report generated at D:\LoanSense\backend\ml\data\audit_report.md
```

**Block 4: Unified Feature Engineering**
```powershell
# Created backend/ml/data/feature_engineering.py
# (File created directly)

# Run feature engineering script
.\backend\.venv\Scripts\python backend\ml\data\feature_engineering.py
# Output: Unified features saved to D:\LoanSense\backend\ml\data\processed\unified_features.parquet with shape (100000, 16)
```

**Block 5: India-Realistic Synthetic Layer**
```powershell
# Created backend/ml/data/synthetic_layer.py
# (File created directly)

# Run synthetic layer script
.\backend\.venv\Scripts\python backend\ml\data\synthetic_layer.py
# Output: Saved india_synthetic.parquet with shape (100000, 18). Printed target and income distributions.
```

**Block 6: Synthetic Attack Generator**
```powershell
# Created backend/ml/attack_generator/generate_attacks.py
# (File created directly)

# Created backend/ml/attack_generator/evaluate_attacks.py
# (File created directly)

# Run attack generator script
.\backend\.venv\Scripts\python backend\ml\attack_generator\generate_attacks.py
# Output: Generated 4 patterns (500 each) and combined_attacks.parquet with shape (2000, 19)
```

**Block 7: Final Training Dataset Assembly**
```powershell
# Created backend/ml/data/prepare_dataset.py
# (File created directly)

# Run prepare dataset script
.\backend\.venv\Scripts\python backend\ml\data\prepare_dataset.py
# Output: Assembled final train/val/test splits. SMOTE applied to train (fraud rate increased to 20%).
# Saved train.parquet, val.parquet, test.parquet, and dataset_card.md
```

**Block 8: Credit Risk Model Training**
```powershell
# Created backend/ml/training/train_credit.py
# (File created directly)

# Run credit risk model training
.\backend\.venv\Scripts\python backend\ml\training\train_credit.py
# Output: Model registered as 'credit-risk-scorer' v1. Final Validation ROC-AUC: 0.6700
```

**Block 8.1: Hyperparameter Tuning & Overfitting Diagnosis**
- Upgraded the training script to include Optuna hyperparameter optimization maximizing PR-AUC.
- **Issue Discovered**: The tuner produced a severely overfit model (Train PR-AUC 0.73 vs. Val PR-AUC 0.32; Train ROC-AUC 0.90 vs. Val ROC-AUC 0.67). XGBoost with a `max_depth` of 8 simply memorised the noise in the synthetic dataset.
- **Resolution Plan**: Constrain the Optuna search space heavily (shallow trees, high child weights, and strong L1/L2 regularisation) to extract genuine signal and reduce the training gap.

**Block 8.2: Label-Feature Independence Bug Fix (Pipeline Rewrite)**
- **Issue Discovered**: The model plateaued at 0.67 ROC-AUC even after heavy regularisation because `default_flag` was entirely independent of the credit-related features (CIBIL score, account age, EMI ratio). The synthetic data generated those features via np.random independently, making them pure noise relative to the default label. Furthermore, attack rows had hardcoded `default_flag` values that didn't align with their actual synthetic credit profiles.
- **Pipeline Rewrite**:
  1. Modified `backend/ml/data/synthetic_layer.py` to add `compute_default_probability()`, generating `default_flag` via a logistic regression formula derived from `cibil_score_simulated`, `account_age_months`, `emi_to_income_ratio`, and `enquiry_count_30d`. The intercept was tuned to `-4.0` to maintain a realistic ~10% base default rate.
  2. Modified `backend/ml/attack_generator/generate_attacks.py` to remove hardcoded default labels and use the same causal probability function. Confirmed the intended "Synthetic Identity" divergence (Pattern 4): `fraud_flag` rate = 100%, `default_flag` rate = 7.6%.
  3. Re-ran `prepare_dataset.py` to generate new splits with SMOTE and documented the causal correlations in `dataset_card.md`.
- **Final Model Retraining**:
  - Re-ran the Optuna-tuned `train_credit.py` on the corrected dataset. 
  - The model successfully learned the newly injected causal signal. The massive overfitting gap vanished (Train ROC-AUC 0.76 vs Val 0.72) and the final Validation ROC-AUC jumped from **0.6702 to 0.7237**.

**Block 8.3: Post-Fix Validation Pass**
- **Objective**: Validate the newly implemented causal link between credit features and `default_flag` to ensure no target leakage and verify intended pattern behavior.
- **Actions Taken**:
  - Ran a custom script `backend/ml/data/run_validation.py` to evaluate the training dataset (`train.parquet`).
  - Added the validation findings and F1 vs ROC-AUC explanation to `backend/ml/data/processed/dataset_card.md`.
- **Key Findings**:
  - **No Target Leakage**: The highest correlation with `default_flag` was `emi_to_income_ratio` at +0.1356. No feature exceeded `|correlation| > 0.5`. Single-feature AUCs similarly remained well below 0.85 (max 0.6352).
  - **Domain Alignment**: `cibil_score_simulated` ranked as the 3rd strongest predictor overall (-0.0944), correctly aligning with domain expectations without overshadowing other features.
  - **Pattern Divergence Verified**: The intentional contradiction in Pattern 4 (Synthetic Identity) was confirmed. Pattern 4's `default_flag` rate was 7.60%, closely mirroring the legitimate population base rate of 9.91%, while explicitly forcing `fraud_flag=1`.
  - **Hyperparameter Tuning**: Verified that a *fresh* Optuna search successfully executed on the new dataset during `train_credit.py`, shifting validation ROC-AUC from 0.6702 to 0.7237.
  - **F1 vs ROC-AUC Tradeoff**: Documented that the model's significant ROC-AUC improvement (~0.05) over F1-score (~0.01) stems from ROC-AUC being threshold-independent, whereas F1 at a 0.5 cutoff struggles due to heavy class imbalance dragging down absolute probabilities.

**Block 9: Fraud Signal Detector Training (Initial)**
```powershell
# Created backend/ml/training/train_fraud.py
# (File created directly)

# Run initial fraud model training
.\backend\.venv\Scripts\python backend\ml\training\train_fraud.py
# Output: Train ROC-AUC: 1.0000, Val ROC-AUC: 0.9999. Suspicion of target leakage.
```

**Block 9.1: Target Leakage Diagnostic & Remediation**
- **Issue Discovered**: The synthetic attack generator (`generate_attacks.py`) created fraud patterns using completely disjoint, hardcoded feature ranges (e.g., Pattern 3 had `transaction_velocity_30d = poisson(150)` while the legitimate maximum was `47`). The model achieved a `0.9999` ROC-AUC simply by drawing trivial threshold boundaries that never appeared in the legitimate dataset.
- **Initial Fix Plan**: Modify `generate_attacks.py` to use shifted but heavily overlapping distributions (e.g., `poisson(55)` instead of `150`, or `uniform(5, 10)` instead of `8.1, 15.0`) to force the model to learn overlapping multivariate signals.
- **Additional Constraints Applied**: 
  - Required reporting dual-population overlap percentages (how much of the fraud population falls into the legit range, and vice versa).
  - Enforced a strict rule: No single feature could have a univariate AUC > `0.85`.
  - Required explicit re-examination of Pattern 4's detection rate to ensure it didn't suffer from independent leakage.
- **Deeper Leakage Found**: Running the diagnostic revealed that the base feature generator (`feature_engineering.py`) *also* baked target leakage into the base fraud cases by using `poisson(60)` for fraud vs `poisson(25)` for legit `transaction_velocity_30d`, making the entire base fraud population trivially separable.
- **Final Remediation Steps**:
  1. Updated `feature_engineering.py` to shift base fraud `transaction_velocity_30d` down to `poisson(30)`, ensuring massive overlap with legit `poisson(25)`.
  2. Updated `feature_engineering.py` to reduce the `income_transaction_ratio` gap.
  3. Updated `generate_attacks.py` to compress Pattern 1, 2, and 3 outliers (e.g. Pattern 3 velocity reduced to `poisson(35)`).
  4. Ran the full pipeline (`feature_engineering.py`, `synthetic_layer.py`, `generate_attacks.py`, `prepare_dataset.py`, `run_fraud_leakage_diagnostic.py`) sequentially.
- **Diagnostic Verification (Post-Fix)**:
  - **No Feature > 0.85 AUC**: The highest single-feature AUC is now `loan_amount` at `0.8450`. The heavily-leaking `transaction_velocity_30d` dropped to `0.7642`.
  - **Meaningful Overlap**: `transaction_velocity_30d` achieved 99.47% Fraud Overlap and 99.85% Legit Overlap.
- **Retraining Fraud Signal Detector**:
  - Re-ran `train_fraud.py`.
  - Val ROC-AUC dropped to a defensible **0.9923** (Train-Val gap of 0.0037).
  - Pattern 2 (Fragmented Bureau) detection plummeted to **20.2%**, proving the model can no longer trivially cheat on `enquiry_count_30d` and correctly struggles when features heavily overlap.
  - Pattern 4 (Synthetic Identity) remained strongly detected at **94.2%**. Verified this is *not* independent leakage: it is successfully detected because the model (and the `FraudPreFilter`) learned the multivariate contradiction of an applicant having a very young account (`< 6 months`) combined with an excellent simulated CIBIL score (`> 750`), a combination almost entirely absent in the legitimate population.

**Block 9.2: Quick Checks & Explanation Chain Verification**
- **Pattern 4 Rarity**: Investigated the rarity of Pattern 4's feature combination (`account_age_months < 6` AND `cibil_score_simulated > 750`) in the legitimate validation population. It occurs in exactly **3.61%** of legit cases. This proves the 94.2% detection rate is a legitimate domain insight—the model is identifying a rare, high-risk multivariate contradiction, not a simple univariate shortcut.
- **Pattern 2 Decomposition**: Decomposed the 20.2% detection rate for Pattern 2 (Fragmented Bureau) to find the bottleneck. Found that the `high_enquiry_velocity` rule (`enquiry_count_30d > 5`) fired exactly 101 times out of 500 (**20.20%**). The bottleneck is purely the rule threshold, not the XGBoost probability cutoff. This highlights a structural weakness to be addressed in Block 11 (Contradiction Detector).
- **False Positive Rate**: Verified the final model maintains an excellent FPR of **2.48%**, confirming it hasn't defaulted to aggressive over-flagging to maintain recall in the newly overlapping dataset.

**Portfolio / README Presentation Note:**
> When writing the final README, do not report the `0.9923` Val ROC-AUC in isolation. It must be reported alongside the explanation chain: (1) All single-feature AUCs < 0.85, (2) Meaningful dual-population overlap proven, (3) FPR is stable at 2.48%, (4) Pattern 4's 3.6% legitimate rarity, and (5) Pattern 2's known rule-threshold limitation. The number alone invites suspicion; the explanation chain turns it into a massive strength showcasing deep model evaluation.

**Block 10: Contradiction Detector — Rule Layer**
- Created `backend/ml/training/contradiction/rules.py` implementing the `BaseContradictionRule` architecture and 5 specific contradiction rules.
- Created `backend/tests/test_contradiction.py` to cover all rules against expected patterns.
```powershell
# Executed tests in the virtual environment
backend\.venv\Scripts\pytest backend\tests\test_contradiction.py -v
# Output: All 6 tests passed (100% coverage on expected rule firing vs clean ignoring).
```

**Block 11: Contradiction Detector — OOF Stacking & Meta-Model**
```powershell
# Created backend/ml/training/train_contradiction.py
# (File created directly)

# Run contradiction detector training
.\backend\.venv\Scripts\python backend\ml\training\train_contradiction.py
# Output: Validation ROC-AUC: 0.9895. All four attack patterns detected at 90%+. Registered as 'contradiction-detector' v1.

# Investigatory script for anomaly score and FPR analysis
.\backend\.venv\Scripts\python backend\ml\training\scratch_investigate.py
```

- **True OOF Stacking Implementation**:
  - The script extracts hyperparameters from the registered base models (`credit-risk-scorer` and `fraud-signal-detector`).
  - It generates out-of-fold (OOF) predictions (`credit_risk_score`, `fraud_probability`) using a 5-fold cross-validation loop on the training set.
  - *Why this matters*: **OOF stacking explicitly prevents data leakage** between the base models and the meta-model. If we simply predicted on the training set, the base models would be overconfident (as they've seen the data), and the meta-model would learn to over-trust them, failing spectacularly on unseen data.

- **Meta-Model Contradiction Tension**:
  - The Logistic Regression meta-model independently learned the exact tension we designed the system to catch, purely from the data (not by manual coefficient assignment).
  - **The Negative Credit Risk Coefficient**: The model learned a strong *negative* weight (`-5.98`) for `credit_risk_score`, while applying a strong positive weight (`+9.94`) for `fraud_probability`.
  - *Domain Interpretation*: A highly negative weight means that an applicant who looks *bad* on paper (high credit risk) actually *decreases* the contradiction score. Legitimate bad borrowers look like bad borrowers. Fraudsters (e.g. Synthetic Identities) often construct profiles that look *too good* (low credit risk). Therefore, high `fraud_probability` combined with *low* `credit_risk_score` mathematically creates the highest possible `contradiction_score`.

- **Anomaly Score Verification**:
  - Validated that the custom Pipeline applying `OrdinalEncoder` to `IsolationForest` worked correctly for mixed-type data.
  - Verified the scaling: The min/max/mean of the `anomaly_score` on the validation set are strictly positive (0.39 to 0.66). The design explicitly inverted the scikit-learn decision function (`-score_samples`) so that higher numbers correctly represent more anomalous behavior.

- **False Positive Rate (FPR) Segmentation**:
  - Segmented the FPR (on legitimate validation applicants, Contradiction > 0.6) by credit risk band to ensure the negative credit score coefficient wasn't causing runaway spurious flags on perfectly clean profiles.
  - Found that the Low Risk band has the highest FPR (~4.05%), while High Risk is <0.85%. Overall FPR is 2.06%.
  - *Conclusion*: This confirms the bounded, acceptable effect of the negative coefficient. A ~4% FPR on the safest demographic is a necessary and very solid operational tradeoff for catching >90% of elite synthetic identities that evade standard models. The human underwriting team would simply focus their manual review capacity on this 4% overlap group.

- **Performance Results**:
  - The system drastically exceeded the 3-out-of-4 target. It successfully detected all four attack patterns at >90% accuracy: `stolen_pan_fabricated_employment` (97.8%), `fragmented_bureau_footprint` (95.6%), `upi_velocity_spike` (92.4%), and `synthetic_identity_clean` (90.8%).

**Block 12, 13, 14: FastAPI Backend, Database Setup, and Model Serving**
```powershell
# Initialize Alembic
.\backend\.venv\Scripts\alembic init alembic

# Recreated schemas due to PSQL 15 default schema security rule on public schema
$env:PGPASSWORD="loansense123"; psql -U loansense_user -d loansense -c "CREATE SCHEMA IF NOT EXISTS loansense_user AUTHORIZATION loansense_user;"

# Run autogenerate migration
.\backend\.venv\Scripts\alembic revision --autogenerate -m "initial schema"

# Upgrade database to head
.\backend\.venv\Scripts\alembic upgrade head

# Run the complete test suite including new DB, endpoints, and MLflow loader tests
.\backend\.venv\Scripts\pytest backend\tests\ -v
# Output: 15 passed, 3 warnings in 4.60s

# Added and ran the missing integration test for full assessment flow (POST /assess -> GET /verdicts -> GET /audit)
.\backend\.venv\Scripts\pytest backend\tests\test_endpoints.py -v
# Output: 3 passed, 3 warnings in 3.27s
```
