# LoanSense — Task 8: MLOps & Drift Detection Technical Summary

This document details the design, implementation, and optimization of the MLOps layer (**Task 8**), specifically focusing on real-time statistical drift monitoring using the Population Stability Index (PSI). It outlines the mathematical logic, monitor architectures, and debugging resolutions applied during integration.

---

## 1. Population Stability Index (PSI) Theory & Mathematics

In machine learning production systems, **data drift** (changes in the distribution of input features) and **concept drift** (changes in the relationship between features and target labels) degrade model performance over time. To detect this, we implemented a **Population Stability Index (PSI)** monitor.

### The Mathematical Formula
PSI measures the degree of shift between a baseline distribution $Q$ (training dataset predictions) and a target distribution $P$ (live production predictions):

$$\text{PSI} = \sum_{i=1}^{k} \left( P_i - Q_i \right) \times \ln\left(\frac{P_i}{Q_i}\right)$$

where:
* $k$ is the number of bins (set to 10 equal-width bins spanning $[0.0, 1.0]$).
* $P_i$ is the percentage of live production predictions falling in bin $i$.
* $Q_i$ is the baseline percentage of training predictions falling in bin $i$.

### Interpretation Thresholds
* **$\text{PSI} < 0.1$:** No significant change. The model's inputs/outputs remain stable.
* **$0.1 \le \text{PSI} < 0.2$:** Moderate change. Indicates a slight shift; the team should monitor the features closely.
* **$\text{PSI} \ge 0.2$:** Significant shift. Triggers an alert requiring model performance review and potential retraining.

---

## 2. Component Implementation & Code Walkthrough

We structured the drift detection pipeline inside the [backend/ml/drift/](file:///d:/LoanSense/backend/ml/drift/) directory.

### 1. The Core Calculator: `psi.py` ([psi.py](file:///d:/LoanSense/backend/ml/drift/psi.py))
Defines the `calculate_psi` function. It takes training baseline percentages and current raw scores, bins them using `np.histogram` over the range $[0.0, 1.0]$, and computes the sum of the log-ratios.

### 2. Baseline Profiler: `generate_baselines.py` ([generate_baselines.py](file:///d:/LoanSense/backend/ml/drift/generate_baselines.py))
Before launching the server, this script is executed to run the registered credit risk and fraud models against the entire training dataset (`train.parquet`).
* It computes prediction scores for all training rows.
* Bins the scores into 10 buckets.
* Serializes these distributions into [baselines.json](file:///d:/LoanSense/backend/ml/drift/baselines.json) to serve as the system reference.

### 3. Monitoring Daemon: `monitor.py` ([monitor.py](file:///d:/LoanSense/backend/ml/drift/monitor.py))
Implements `run_drift_check(db)`.
* Queries the PostgreSQL `model_outputs` table for predictions written in the last 7 days.
* Filters out empty scores, runs the PSI calculator for each model, and returns status details.
* **Alert Generation:** If any model registers a $\text{PSI} \ge 0.2$, the system triggers `drift_detected = True` and writes a `drift_alert` event containing recommendations into the `audit_logs` table.

### 4. API & Health Integration
* **`GET /api/v1/drift` ([drift.py](file:///d:/LoanSense/backend/app/routers/drift.py)):** Calls the monitoring check on-demand and caches the alert status in a global variable.
* **`GET /api/v1/health` ([health.py](file:///d:/LoanSense/backend/app/routers/health.py)):** References this cached state, returning `distribution_drift_detected: true` if drift is present, raising visibility on frontend dashboard banners.

---

## 3. Errors Faced & Resolutions

During development and testing of the MLOps pipeline, three major issues were diagnosed and resolved.

### Error 1: Division by Zero and Log-Zero Crashes
* **The Bug:** In early tests, when the production query had no predictions falling into specific score bins (e.g. $[0.9, 1.0]$ for clean borrowers), $P_i$ fell to `0.0`. This caused `np.log(current_pct / baseline_pct)` to evaluate as $\ln(0)$ or division by zero, yielding `-inf` or `NaN` values that crashed the summation.
* **The Resolution:** Implemented an **epsilon padding** scheme inside `psi.py`. Any zero percentage is clamped to a tiny positive float ($\epsilon = 10^{-4}$) using `np.where` before computing the ratio or logarithm:
  ```python
  epsilon = 1e-4
  current_pct = np.where(current_pct == 0, epsilon, current_pct)
  baseline_pct = np.where(baseline_pct == 0, epsilon, baseline_pct)
  ```

### Error 2: Small Sample Size Instability (Spurious Alerts)
* **The Bug:** When testing the API with low traffic volumes (e.g. less than 20 new loan submissions in a week), a small cluster of borderline applicants shifted binned percentages drastically, driving PSI over `0.2` and triggering false alarms.
* **The Resolution:** Enforced a **sample volume check** inside `monitor.py`. If fewer than 50 predictions are recorded in the 7-day window, the check skips evaluation and returns a `skipped` status:
  ```python
  if len(outputs) < 50:
      details[model_name] = {"status": "skipped", "reason": f"Insufficient data ({len(outputs)} < 50)"}
      continue
  ```

### Error 3: Missing Baseline Configuration Crash
* **The Bug:** If the backend started up in a clean environment where `generate_baselines.py` had not yet run, the monitoring API crashed because it could not find `baselines.json`.
* **The Resolution:** Added a fail-safe check to verify the file's existence. If missing, it returns a clean status report indicating that baseline generation is pending:
  ```python
  if not baselines_path.exists():
      return {
          "drift_detected": False,
          "details": {"error": "Baselines file not found. Run generate_baselines.py first."}
      }
  ```

---

## Technical Interview Q&A for Task 8

* **Q: What is Population Stability Index (PSI) and why did you select it for drift monitoring?**
  * *A:* "PSI is a metric that quantifies the difference between two probability distributions. It is widely used in credit risk monitoring because it is scale-invariant and lets us easily track if our production score distributions are shifting away from our validation baseline. It provides clear industry-standard alert thresholds: values below 0.1 indicate stability, while values above 0.2 indicate a significant population shift."
* **Q: Explain how you prevented mathematical errors when a score bucket had zero occurrences in your production data.**
  * *A:* "Dividing by zero or taking the logarithm of zero results in undefined mathematical values (NaN or inf). To prevent this, we implemented epsilon padding. Before running the log-ratio calculation, we checked for any zero values in the binned percentages and clamped them to a tiny float epsilon ($\epsilon = 10^{-4}$). This minor adjustment keeps the calculation stable without impacting the overall index value."
* **Q: Why is it important to set a minimum sample size limit before running drift detection?**
  * *A:* "Statistical calculations are highly unstable on small datasets. If a bank receives only 10 applications in a week, a single high-risk applicant represents 10% of the sample, which artificially spikes the PSI and triggers false alarms. By enforcing a minimum sample size constraint (e.g., 50 predictions), we ensure that we only measure shifts when we have sufficient data to draw statistically meaningful conclusions."
* **Q: Where is the baseline distribution calculated and how is it used during live monitoring?**
  * *A:* "The baseline distribution is calculated using `generate_baselines.py` immediately after training. It runs predictions on the full validation training dataset, bins the scores into 10 deciles, and saves the percentages to `baselines.json`. During live monitoring, the `run_drift_check` function loads these fixed reference percentages and compares them against the binned percentages of the last 7 days of production data queried from PostgreSQL."
