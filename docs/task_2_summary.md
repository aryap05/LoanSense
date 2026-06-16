# LoanSense — Task 2: Synthetic Dataset & Attack Generator Technical Summary

This document serves as a detailed reference for the implementation of **Task 2**, breaking down each block’s purpose, technical execution, design rationales, and common interview questions with answers.

---

## Block 3: Dataset Acquisition & Audit

### What Was Done
* We downloaded public datasets:
  * **Home Credit Default Risk**: [application_train.csv](file:///d:/LoanSense/backend/ml/data/raw/home_credit/application_train.csv) (~166 MB)
  * **IEEE-CIS Fraud Detection**: [train_transaction.csv](file:///d:/LoanSense/backend/ml/data/raw/ieee_cis/train_transaction.csv) (~683 MB) and [train_identity.csv](file:///d:/LoanSense/backend/ml/data/raw/ieee_cis/train_identity.csv) (~26.5 MB)
* Wrote [audit_data.py](file:///d:/LoanSense/backend/ml/data/audit_data.py) to parse the files and output [audit_report.md](file:///d:/LoanSense/backend/ml/data/audit_report.md), documenting shapes, missing values, datatypes, and class imbalances.

### Technical Design Rationale
* **Chunking (`chunksize=50000`)**: Pandas loads files into memory using a representation that can consume 3–5x more RAM than the raw file size. Loading a ~683 MB CSV directly can crash constrained environments. Streaming chunks limits peak RAM consumption to a few megabytes.
* **Low-Memory Type Handling**: Used `low_memory=False` in `pd.read_csv` for the IEEE-CIS dataset to prevent `DtypeWarning` alerts caused by different data types appearing across different chunks.

### Interview Q&A for Block 3
* **Q: Why did you write custom streaming aggregation loops instead of using standard `describe()`?**
  * *A:* "Commutative operations like sums (for missing value counts) and counts (for categorical values) can be aggregated iteratively. A custom chunking loop allowed us to compile these global metrics without needing the entire dataset loaded in memory at any point."
* **Q: Why not use Polars or Dask for this auditing task?**
  * *A:* "While Polars or Dask are excellent for out-of-core calculations, introducing them adds unnecessary third-party dependencies. Utilizing standard Pandas chunking is highly portable, memory-safe, and integrates natively with our downstream models."

---

## Block 4: Unified Feature Engineering

### What Was Done
* Created [feature_engineering.py](file:///d:/LoanSense/backend/ml/data/feature_engineering.py) to sample 100,000 records from Home Credit and merge features.
* Engineered credit risk columns: `loan_amount`, `income`, `emi_to_income_ratio`, `loan_tenure_months`, `existing_obligations`, and `cibil_score_simulated`.
* Created a **Synthetic Join** to assign fraud probabilities and flags from the IEEE-CIS dataset.
* Generated [feature_definitions.md](file:///d:/LoanSense/backend/ml/data/processed/feature_definitions.md) documenting the output.

### Technical Design Rationale
* **Annuity-Based Tenure**: Derived `loan_tenure_months` using `loan_amount / AMT_ANNUITY` to establish a logical baseline, handling division by zero and infinite values cleanly.
* **Quantile-Based Synthetic Join**: Since we lack a physical join key between the two datasets, we calculated IEEE-CIS fraud rates within `TransactionAmt` quantiles and mapped those probabilities to matching quantiles of the Home Credit `loan_amount` using a binomial distribution `np.random.binomial(n=1, p=prob)`.
* **Gamma and Poisson Fraud Profiling**: Fraudsters typically behave differently than clean applicants. We modeled `account_age_months` using a Gamma distribution (mean 6 months for fraud, 48 months for clean) and transaction counts using a Poisson distribution (mean 60 transactions for fraud, 25 for clean) to introduce realistic features.

### Interview Q&A for Block 4
* **Q: Explain how you engineered the synthetic join between the credit and fraud datasets.**
  * *A:* "Since the datasets don't share a primary key, we used a quantile mapping technique. We quantized credit application amounts (Home Credit) and transaction amounts (IEEE-CIS) into 5 equal-sized bins. We calculated the empirical fraud rate for each bin in IEEE-CIS, mapped those probabilities to corresponding bins in Home Credit, and sampled the binary fraud flags using a binomial trial."
* **Q: Why did you use Gamma and Poisson distributions to simulate transaction velocities and account ages?**
  * *A:* "Real-world transaction counts are discrete counts that can be modeled well with a Poisson distribution. Similarly, account ages are non-negative, right-skewed variables that are best modeled using a Gamma distribution. This ensures that the generated variables contain realistic mathematical properties rather than uniform distributions."

---

## Block 5: India-Realistic Synthetic Layer

### What Was Done
* Wrote [synthetic_layer.py](file:///d:/LoanSense/backend/ml/data/synthetic_layer.py) to convert the base variables into India-realistic credit files.
* Outputted the localized file [india_synthetic.parquet](file:///d:/LoanSense/backend/ml/data/processed/india_synthetic.parquet).

### Technical Design Rationale
* **Income Pareto Tail**: Segmented income into low (40%), middle (35%), upper-middle (20%), and high (5%) brackets. For high income, we applied a **Pareto distribution** to model the realistic wealth-distribution curve.
* **Debt-to-Income Correlation**: Ensured that the `loan_amount` was scaled to `2x-8x` of the monthly income.
* **Bimodal Account Age**: Modeled bank account seasoning using a bimodal distribution: 30% new accounts (1–6 months) and 70% established relationships (12–120 months) to replicate true credit footprints.
* **CIBIL Score Segmentation**: Grouped scores into bands including a `no_file` category (20% share with score `0`) to model credit-naive applicants.

### Interview Q&A for Block 5
* **Q: Why did you use a Pareto distribution for the high-income bracket?**
  * *A:* "Incomes follow power-law behavior rather than normal distributions. Normal or uniform scaling would result in an underrepresented right tail. The Pareto distribution allows us to simulate the extreme upper-income values mathematically, representing the true distribution of high-net-worth borrowers."
* **Q: What is the purpose of enforcing a bimodal distribution for account ages?**
  * *A:* "It represents two distinct customer groups: credit-naive applicants who have recently opened their first bank accounts, and prime/established borrowers with years of history. Splitting them into distinct peaks prevents our models from seeing a flat average age that doesn't occur in reality."

---

## Block 6: Synthetic Attack Generator

### What Was Done
* Created [generate_attacks.py](file:///d:/LoanSense/backend/ml/attack_generator/generate_attacks.py) to construct 500 synthetic fraudulent records for each of the 4 core Indian fraud patterns (2,000 total).
* Created a placeholder script [evaluate_attacks.py](file:///d:/LoanSense/backend/ml/attack_generator/evaluate_attacks.py) to check detection rates on the models.

### Technical Design Rationale
* **Mutating a Clean Base**: The script generates a normal applicant profile using `generate_clean_base` and overrides specific features to inject the fraud patterns.
* **Deterministic Seeding**: Applied `np.random.seed(42)` to ensure identical records are generated on every run.
* **Static `if-elif` Branching**: We used an `if-elif` chain to execute custom vector adjustments depending on the attack type.

### Interview Q&A for Block 6
* **Q: Why did you use an `if-elif` conditional structure inside the generator instead of a polymorphic class structure?**
  * *A:* "OOP polymorphism adds boilerplate code. Since each fraud pattern alters a completely different subset of columns with varying datatypes and statistical formulas, a sequential `if-elif` block keeps the mathematical adjustments explicit, readable, and highly maintainable."
* **Q: Why did you limit the generator to 500 rows per pattern?**
  * *A:* "This keeps the raw base fraud rate at a realistic ~0.65% when combined with the 307,511 clean records. It prevents skewing our validation and test datasets, which must remain unpolluted to measure actual performance in production."

---

## Block 7: Final Training Dataset Assembly

### What Was Done
* Created [prepare_dataset.py](file:///d:/LoanSense/backend/ml/data/prepare_dataset.py) to combine, split, and balance our final datasets.
* Outputted `train.parquet`, `val.parquet`, and `test.parquet`.
* Created [dataset_card.md](file:///d:/LoanSense/backend/ml/data/processed/dataset_card.md) for data transparency.

### Technical Design Rationale
* **Stratification**: Stratified on `fraud_flag` during splitting to ensure the ~0.65% fraud distribution was preserved identically across Train, Val, and Test sets.
* **SMOTENC**: Used SMOTENC (Synthetic Minority Over-sampling Technique for Nominal and Continuous features) because our dataset contains categorical features (e.g. `employment_type`, `new_to_credit`).
* **Training-Only Resampling**: Oversampled the training split to ~20% fraud signal density, while keeping the validation and test sets completely natural.
* **Integer Type Recovery**: Rounded and cast continuous numerical interpolations back to integers (e.g., CIBIL scores and IDs) to prevent float coercion.

### Interview Q&A for Block 7
* **Q: Why did you apply SMOTENC only to the training split and not to the entire dataset?**
  * *A:* "Applying SMOTE before splitting causes severe data leakage. Synthetic samples in the validation/test sets would be generated based on neighbors in the training set, leading to over-optimistic performance metrics. The validation and test splits must remain untouched to evaluate the model under true, imbalanced production conditions."
* **Q: Why did you use SMOTENC instead of standard SMOTE?**
  * *A:* "Standard SMOTE calculates new samples by taking linear distances, which only works for numerical data. If applied to categorical columns, it generates invalid decimals. SMOTENC uses the mode of the categorical features among nearest neighbors, ensuring that values like `employment_type` remain valid categorical strings."
