# Block 9: Leakage Diagnostic Report

## Objective
Investigate the `0.9999` Validation ROC-AUC reported by the Block 9 Fraud Signal Detector to determine if target leakage or trivial separability exists due to hardcoded, non-overlapping feature ranges in the synthetic attack generator.

## 1. Per-Feature Correlation with `fraud_flag` (Pre-SMOTE Training Split)
| Feature | Pearson Correlation | Note |
| :--- | :--- | :--- |
| `transaction_velocity_30d` | +0.6587 | **[INVESTIGATE FOR LEAKAGE]** (> 0.5) |
| `loan_amount` | +0.3644 | |
| `enquiry_count_30d` | +0.3406 | |
| `upi_velocity_percentile` | +0.2575 | |
| `income_transaction_ratio` | -0.1328 | |
| `new_to_credit` | +0.0946 | |
| `account_age_months` | -0.0686 | |

## 2. Single-Feature AUC against `fraud_flag`
| Feature | Single-Feature AUC | Note |
| :--- | :--- | :--- |
| `transaction_velocity_30d` | 0.9301 | **[INVESTIGATE FOR LEAKAGE]** (> 0.85) |
| `income_transaction_ratio` | 0.8559 | **[INVESTIGATE FOR LEAKAGE]** (> 0.85) |
| `loan_amount` | 0.8506 | **[INVESTIGATE FOR LEAKAGE]** (> 0.85) |
| `upi_velocity_percentile` | 0.8322 | |
| `enquiry_count_30d` | 0.7533 | |
| `account_age_months` | 0.6010 | |
| `new_to_credit` | 0.5923 | |

## 3. Distribution Overlap Check for Flagged Features

**`transaction_velocity_30d`**
- **Legit**: min=6.00, p50=25.00, p90=32.00, max=47.00
- **Fraud**: min=15.00, p50=57.00, p90=75.00, max=183.00
- **Overlap**: **30.44%** of fraud samples fall within the legit range [6.00, 47.00].
- **Distinct Range**: Values > 47 are exclusive to fraud.

**`income_transaction_ratio`**
- **Legit**: min=1.28, p50=2.30, p90=6.13, max=11.12
- **Fraud**: min=0.10, p50=0.70, p90=2.42, max=15.00
- **Overlap**: **22.32%** of fraud samples fall within the legit range [1.28, 11.12].
- **Distinct Range**: Values < 1.28 and > 11.12 are almost exclusive to fraud.

**`loan_amount`**
- **Legit**: min=30k, p50=230k, p90=901k, max=14.3M
- **Fraud**: min=76k, p50=1.02M, p90=2.1M, max=49.9M
- **Overlap**: **99.95%** of fraud samples fall within the legit range.

## 4. Source Pattern Analysis & Conclusion

**Strict Criteria Check**: Did any feature meet all three criteria (`|corr| > 0.5` AND `AUC > 0.85` AND `overlap < 10%`)?
**Answer: NO.** The lowest overlap for a flagged feature globally was 22.32%.

**Alternative Explanation for 0.9999 ROC-AUC:**
While no *single* feature is globally <10% overlapping, this is an illusion caused by the 4 distinct attack patterns diluting each other. When an attack pattern does not mutate a feature, it uses the "clean" base distribution, which overlaps 100% with legit data, raising the global overlap metric. 

However, looking at the patterns individually:
1. **Pattern 3 (`upi_velocity_spike`)**: Uses `transaction_velocity_30d = np.random.poisson(150)`. The absolute maximum for legit is `47`. **Overlap = 0%** for this pattern. It is trivially separable.
2. **Pattern 2 (`fragmented_bureau_footprint`)**: Uses `enquiry_count_30d = np.random.randint(6, 13)`. Legit is `poisson(1)`, where values > 5 are extremely rare. **Overlap ≈ 0%** for this pattern.
3. **Pattern 3 (`upi_velocity_spike`)**: Uses `income_transaction_ratio = np.random.uniform(0.1, 0.49)`. Legit minimum is `1.28`. **Overlap = 0%** for this pattern.

Because XGBoost builds a decision tree, it simply creates one branch for `transaction_velocity_30d > 50` (catches all Pattern 3 perfectly), another for `enquiry_count_30d > 5` (catches all Pattern 2 perfectly), and so on. The 0.9999 ROC-AUC is achieved by combining these moderately-to-perfectly separable, disjoint boxes.

**Is 0.9999 realistic to defend?**
**No.** In real life, fraud signals overlap significantly with the tails of legitimate behavior (e.g., a legitimate user buying a house might have 6 enquiries). Hardcoding boundaries that never occur in the legitimate population makes the ML model a trivial lookup table, which defeats the purpose of showcasing ML skills in a portfolio project.

**Recommendation:**
We must revise `generate_attacks.py` to use overlapping distributions (e.g., pulling from the 90th percentile of legit behavior rather than completely disconnected value ranges).
