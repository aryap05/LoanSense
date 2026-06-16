# LoanSense — Task 3: Comprehensive Model Training & Validation Retrospective

This technical document provides an in-depth retrospective of **Task 3** (Model Training & Validation), covering the iterative design, implementation, debugging, and final optimization of the three core machine learning models in the LoanSense system:
1. **Credit Risk Scorer** (Block 8)
2. **Fraud Signal Detector** (Block 9)
3. **Contradiction Detector — Rule Layer** (Block 10)
4. **Contradiction Detector — Meta-Model Stack** (Block 11)

---

## Block 8: Credit Risk Scorer Model Training & Optimization

### 1. What Was Done
* We developed the initial credit risk scorer training script in [train_credit.py](file:///d:/LoanSense/backend/ml/training/train_credit.py) to train an XGBoost classifier predicting `default_flag` based on 9 key credit features (CIBIL, account age, EMI ratio, employment type, loan amount, etc.).
* Integrated **Optuna** to automatically optimize hyperparameters (maximizing Validation PR-AUC).
* Preprocessed categorical data using an `OrdinalEncoder` wrapped in a `ColumnTransformer` inside a scikit-learn pipeline, and dynamically handled class imbalance via:
  $$\text{scale\_pos\_weight} = \frac{N_{\text{majority}}}{N_{\text{minority}}}$$

### 2. Issues Encountered & Rationale
* **Issue A: Severe Overfitting during Hyperparameter Tuning (Block 8.1)**
  * *Symptoms:* The initial Optuna run trained a model that achieved a `0.90` training ROC-AUC and `0.73` PR-AUC, but collapsed to `0.67` ROC-AUC and `0.32` PR-AUC on the validation set.
  * *Reason:* The search space allowed trees that were too deep (`max_depth=8`). When features lacked correlation, XGBoost simply memorized noise, producing a model with low generalizability.
  * *Resolution:* Constrained the search space to shallow trees (`max_depth` between 3 and 5), enforced high node weight (`min_child_weight` between 10 and 50), and enabled strong L1/L2 regularization (`reg_alpha` and `reg_lambda` up to 10.0).
* **Issue B: Label-Feature Independence Bug (Block 8.2)**
  * *Symptoms:* Even with heavy regularization, validation ROC-AUC remained stuck at `0.67`.
  * *Reason:* An audit of [synthetic_layer.py](file:///d:/LoanSense/backend/ml/data/synthetic_layer.py) revealed that the synthetic features (CIBIL score, account age, etc.) were generated using independent `np.random` calls that had no statistical association with the pre-calculated `default_flag`. They were mathematically pure noise.
  * *Resolution:* We rewrote the synthetic pipeline to inject a causal formula:
    $$logit = -4.0 + 2.5 \times (1 - \text{CIBIL}_{\text{normalized}}) + 1.5 \times (\text{EMI}_{\text{ratio}} > 0.5) + 1.0 \times (\text{acct\_age} < 6) + 0.8 \times \frac{\text{enquiries} > 4}{4} + \epsilon$$
    $$\text{default\_probability} = \frac{1}{1 + e^{-logit}}$$
    The `default_flag` was sampled via `np.random.binomial(1, probs)`. This was also applied to simulated attack files to preserve the **intended divergence** for Pattern 4 (Synthetic Identity), ensuring low default risk (~7.6%) despite fraud.

### 3. Final Retrained Metrics
* **Validation ROC-AUC:** `0.7237` (up from `0.6702`)
* **Validation PR-AUC:** `0.3800` (up from `0.3199`)
* **Validation F1-Score:** `0.2980`
* **Train-Val ROC-AUC Gap:** `0.0367` (from `0.2308` — overfitting eliminated)

---

## Block 9: Fraud Signal Detector Training & Leakage Remediation

### 1. What Was Done
* Created [train_fraud.py](file:///d:/LoanSense/backend/ml/training/train_fraud.py) to train the second model predicting `fraud_flag`.
* Implemented the [FraudPreFilter](file:///d:/LoanSense/backend/ml/training/train_fraud.py#L14-L37) rule engine which checks for local anomalies such as income-transaction ratio mismatch, rapid enquiry rate, and young accounts with high credit scores.

### 2. Issues Encountered & Rationale
* **Issue A: Trivial Separability and Target Leakage (Block 9.1)**
  * *Symptoms:* The initial model achieved an unrealistic **`0.9999` Validation ROC-AUC**.
  * *Reason:* An audit documented in [block9-leakage-diagnostic.md](file:///d:/LoanSense/docs/block9-leakage-diagnostic.md) showed that the synthetic attack generator created fraud patterns with completely disjoint ranges (e.g. Pattern 3 had a UPI velocity percentile spike that never occurred in the legitimate dataset, making them trivially separable). The model learned simple rules instead of generalizable features.
  * *Resolution:* We rewrote the generator in [generate_attacks.py](file:///d:/LoanSense/backend/ml/attack_generator/generate_attacks.py) and base feature mappings in [feature_engineering.py](file:///d:/LoanSense/backend/ml/data/feature_engineering.py) to ensure distributions heavily overlap. For example, fraud transaction velocity was shifted to `poisson(30)`, which overlaps with the legit `poisson(25)`.
  * *Constraints Enforced:* No single feature could have a univariate AUC greater than `0.85`, and they must exhibit substantial dual-population overlap.

### 3. Final Retrained Metrics
* **Validation ROC-AUC:** `0.9923` (Train-Val gap: `0.0037`)
* **Validation FPR:** `2.48%`
* **Pattern 2 (Fragmented Bureau) Detection:** Dropped to **`20.2%`**, proving the model can no longer trivially separate thin bureau profiles.
* **Pattern 4 (Synthetic Identity) Detection:** Remained high at **`94.2%`**. A quick check showed that the multivariate combination of `account_age_months < 6` and `cibil_score_simulated > 750` appears in only **3.61%** of legitimate validation profiles. This confirmed the model learned a genuine domain anomaly rather than a univariate shortcut.

---

## Block 10: Contradiction Detector — Rule Layer

### 1. What Was Done
* Implemented the rule-based component of the Contradiction Detector in [rules.py](file:///d:/LoanSense/backend/ml/training/contradiction/rules.py).
* Defined 5 distinct rules extending a common [BaseContradictionRule](file:///d:/LoanSense/backend/ml/training/contradiction/rules.py#L4-L21) interface:
  1. `HighScoreNewAccountRule` (Synthetic Identity: young account with high CIBIL).
  2. `IncomeTransactionMismatchRule` (Income fabrication: income-to-transaction ratio mismatch).
  3. `CreditFraudDivergenceRule` (Credit-Fraud Signal Divergence: safe credit but high fraud probability).
  4. `EnquiryBurstThinFileRule` (Bust-out risk: enquiry burst with thin bureau file).
  5. `CleanProfileVelocityRule` (Pre-application velocity spike: transaction surge on clean profile).
* Written a unit test suite in [test_contradiction.py](file:///d:/LoanSense/backend/tests/test_contradiction.py). All 6 unit tests passed successfully.

### 2. Rationale
* **Base Architecture:** OOP interface enforcement ensures that adding new regulatory or domain rules requires zero changes to the orchestration pipeline.
* **Explainability:** Each rule returns a custom detail string containing interpolated row values (e.g. *"CIBIL score of 780 with account age of 3 months is inconsistent"*), which is served to the end-user.

---

## Block 11: Contradiction Detector — Meta-Model Stack

### 1. What Was Done
* Created [train_contradiction.py](file:///d:/LoanSense/backend/ml/training/train_contradiction.py) to train a hybrid Meta-Model that stacks base model outputs, anomaly scores, and rule signals.
* Extracted out-of-fold (OOF) predictions using a **5-fold cross-validation loop** on the training set.
* Fitted a **Logistic Regression meta-model** using these OOF inputs.
* Fitted a final **Isolation Forest** pipeline to capture multivariate anomalies in the legitimate population.
* Wrapped the meta-model, Isolation Forest, and rule engine into a custom [ContradictionDetectorPyFunc](file:///d:/LoanSense/backend/ml/training/train_contradiction.py#L29-L105) MLflow model.

### 2. Rationale
* **Out-Of-Fold (OOF) Stacking:** Using raw training predictions would bias the meta-model, as the base models are overconfident on their training data. Stacking prevents data leakage, forcing the meta-model to learn realistic base model relationships on unseen data.
* **Negative Credit Risk Coefficient:** The meta-model learned a negative coefficient (`-5.98`) for `credit_risk_score` and a positive coefficient (`+9.94`) for `fraud_probability`. This represents the mathematical model of a **contradiction**: an applicant with safe credit risk (low score) and high fraud probability is flagged as highly contradictory.
* **FPR Segmentation:** Segmented the false positive rate by credit risk band to check for runway flags on safe demographics. The Low Risk band has a higher FPR (~4.05%) compared to High Risk (<0.85%), resulting in an overall FPR of **2.06%**. This represents an acceptable operational tradeoff to capture elite synthetic identity fraud.

### 3. Performance Results
* **Validation ROC-AUC:** `0.9895`
* **Pattern Detection Rates:**
  * Pattern 1 (Stolen PAN): **`97.8%`**
  * Pattern 2 (Fragmented Bureau): **`95.6%`** (Up from 20.2% fraud-model baseline due to rules + anomaly score stack)
  * Pattern 3 (UPI Velocity Spike): **`92.4%`**
  * Pattern 4 (Synthetic Identity): **`90.8%`**

---

## Technical Interview Q&A for Task 3

* **Q: What is Out-of-Fold (OOF) stacking and why did you use it for the Contradiction Detector?**
  * *A:* "OOF stacking is an ensemble technique where predictions for the training set are generated using cross-validation. We split the data into 5 folds, fit the base models on 4 folds, and predict on the remaining 1 fold. We repeat this until we have predictions for the entire dataset. We use OOF stacking because training base models on the full training set and immediately using their predictions as meta-features leads to data leakage. The base models would be overconfident, and the meta-model would learn to over-trust them, causing it to generalize poorly on unseen test data."
* **Q: Why does a negative coefficient for Credit Risk indicate a successful meta-model?**
  * *A:* "A negative coefficient for `credit_risk_score` (representing default probability) means that as credit risk decreases, the contradiction score increases. In our system, a traditional default profile shows high credit risk and high fraud risk (both models aligned). However, a synthetic identity fraudster carefully builds a clean credit profile (low credit risk) while exhibiting fraud signals. The model successfully learned this tension: the highest contradiction scores are assigned to profiles with very low credit risk but elevated fraud probabilities."
* **Q: What is the F1 vs ROC-AUC tradeoff, and why did you prefer ROC-AUC?**
  * *A:* "F1-score requires a fixed decision threshold (typically 0.5) to convert probabilities into binary classes. Because our dataset has a natural class imbalance, the posterior probability of default rarely crosses 0.5, dragging down the F1 score. ROC-AUC is threshold-independent, measuring the model's ability to rank applicants from high to low risk. For underwriting, a ranking score is much more useful than a static binary flag, as it allows risk segmentation into bands (Low/Medium/High) for routing decisions."
* **Q: Why did you enforce a strict <0.85 univariate AUC limit for the Fraud Detector?**
  * *A:* "If a single feature has a univariate AUC > 0.85, the model can separate fraud from legitimate data using a simple threshold. In synthetic datasets, this happens when feature ranges are hardcoded without overlap. Limping with 0.9999 validation scores looks impressive but fails in production because real-world fraud is noisy and overlaps with legit behavior. Restricting univariate AUCs forced the model to learn complex, multivariate boundaries, resulting in a robust model that generalizes well."
