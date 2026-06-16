# LoanSense Data Lineage & Synthetic Engineering

This document outlines the complete data lineage for the LoanSense project, tracing how raw public datasets were transformed, synthesized, and merged to create the final India-specific credit and fraud dataset.

## 1. Base Datasets & Raw Columns

Since we did not have access to proprietary Indian banking data, we started with two distinct public Kaggle datasets to capture base credit and fraud signals.

### A. Home Credit Default Risk (Kaggle)
*Purpose: Provides baseline personal loan application signals and default behavior.*
* **`AMT_INCOME_TOTAL`** $\rightarrow$ Base for `income`
* **`AMT_CREDIT`** $\rightarrow$ Base for `loan_amount`
* **`AMT_ANNUITY`** $\rightarrow$ Used to calculate EMI burden
* **`AMT_GOODS_PRICE`** $\rightarrow$ Used to estimate existing obligations
* **`NAME_INCOME_TYPE`** $\rightarrow$ Base for `employment_type`
* **`TARGET`** $\rightarrow$ Base for `default_flag`

### B. IEEE-CIS Fraud Detection (Kaggle)
*Purpose: Provides baseline transaction behavior and fraud signals.*
* **`TransactionAmt`** $\rightarrow$ Used to calculate velocity and percentile signals
* **`isFraud`** $\rightarrow$ Base for `fraud_flag`

---

## 2. The Synthetic Join (Creating the Unified Dataset)

Because Home Credit (credit signals) and IEEE-CIS (transaction signals) have no shared keys, they could not be joined normally. 

**The Strategy:** We performed a **"Synthetic Join"**. 
1. We sampled applicants from the Home Credit dataset.
2. We matched them to transactions from the IEEE-CIS dataset based on **Income/Transaction Amount bands**.
3. If an applicant fell into a specific financial band, they were assigned a `fraud_flag` and transaction behavior sampled from that same band in the IEEE-CIS data.

> [!WARNING]
> This join inherently destroys some real-world covariance. To fix this, we layered causal relationships and explicit attack patterns on top of this base.

---

## 3. The India-Realistic Synthetic Layer

To localize the data to the Indian NBFC (Non-Banking Financial Company) context, we mathematically over-wrote several columns with realistic distributions and specific formulas.

### Synthetically Generated Columns

* **`income`**: Re-sampled from a right-skewed distribution.
  * 40% Low: ₹15k–₹35k/month
  * 35% Middle: ₹35k–₹1L/month
  * 20% Upper-Middle: ₹1L–₹2.5L/month
  * 5% High: ₹2.5L+
* **`loan_amount`**: Correlated to income (randomly assigned between 2x and 8x monthly income).
* **`emi_to_income_ratio`**: Derived as (Simulated EMI / `income`).
* **`cibil_score_simulated`**: 
  * 20% New to credit (Score = 0)
  * 30% Poor (300–599)
  * 35% Fair/Good (600–749)
  * 15% Excellent (750–900)
* **`account_age_months`**: 30% new accounts (1–6 months), 70% established (12–120 months).
* **`employment_type`**: Mapped to India-specific categories (`salaried_private`, `salaried_govt`, `self_employed`, `gig_worker`).

### The Causal Target Formula (`default_flag`)

As discovered during Block 8, if we didn't force a mathematical relationship between our synthetic features and the default flag, the model would overfit on noise. We implemented the following logistic formula to generate the `default_probability`:

$$logit = -4.0 + 2.5 \times (1 - \text{CIBIL}_{\text{normalized}}) + 1.5 \times (\text{EMI}_{\text{ratio}} > 0.5) + 1.0 \times (\text{acct\_age} < 6) + 0.8 \times \frac{\text{enquiries} > 4}{4} + \epsilon$$

*(Where $\text{CIBIL}_{\text{normalized}} = \frac{\text{cibil}}{900}$ and $\epsilon$ is random normal noise).*

The `default_flag` was then determined via a binomial trial using this probability, yielding a realistic ~9.9% baseline default rate.

---

## 4. The Attack Generator (Explicit Fraud Patterns)

To ensure the model learned actual fraud typologies rather than random noise, we appended explicitly generated fraudulent rows representing 4 known attack vectors:

1. **Stolen PAN / Fabricated Employment:**
   * High CIBIL (680-800) + High Income + Low Account Age (2-5 months)
   * `income_transaction_ratio` > 8 (Income heavily outweighs actual transaction history).
2. **Fragmented Bureau Footprint:**
   * CIBIL = 0 or very thin + `enquiry_count_30d` = 6-12 (Massive sudden credit hunger).
3. **UPI Velocity Spike:**
   * Clean credit profile + `upi_velocity_percentile` > 95th percentile (Sudden account warming/bust-out).
4. **Synthetic Identity (Clean):**
   * Perfectly crafted fake profile. Good CIBIL (720-780), reasonable income.
   * **The anomaly:** `account_age_months` across all bureaus is identically short (2-4 months).

---

## 5. Final Assembly & SMOTE

1. **Concatenation:** The base India-realistic legitimate applicants and the explicitly generated Attack Patterns were concatenated into one master dataset.
2. **Train/Val/Test Split:** Stratified 70/15/15 split on the `fraud_flag`.
3. **SMOTE:** Applied **only to the training split** to bring the fraud representation up to ~15-20% to give the XGBoost models enough density to learn decision boundaries, without leaking synthetic data into the validation/test sets.
