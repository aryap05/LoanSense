# Dataset Audit Report

## 1. Home Credit Default Risk

- **Shape:** 307,511 rows, 122 columns
- **Target Distribution (TARGET):** 0 (No Default): 91.93%, 1 (Default): 8.07%
  - *Class Imbalance Ratio:* ~1:11
- **Feature Types:**
  - float64: 65
  - int64: 41
  - object: 16

- **Top 20 Columns with Missing Values:**
  - `COMMONAREA_AVG`: 69.87%
  - `COMMONAREA_MODE`: 69.87%
  - `COMMONAREA_MEDI`: 69.87%
  - `NONLIVINGAPARTMENTS_MEDI`: 69.43%
  - `NONLIVINGAPARTMENTS_MODE`: 69.43%
  - `NONLIVINGAPARTMENTS_AVG`: 69.43%
  - `FONDKAPREMONT_MODE`: 68.39%
  - `LIVINGAPARTMENTS_AVG`: 68.35%
  - `LIVINGAPARTMENTS_MEDI`: 68.35%
  - `LIVINGAPARTMENTS_MODE`: 68.35%
  - `FLOORSMIN_MODE`: 67.85%
  - `FLOORSMIN_AVG`: 67.85%
  - `FLOORSMIN_MEDI`: 67.85%
  - `YEARS_BUILD_AVG`: 66.50%
  - `YEARS_BUILD_MODE`: 66.50%
  - `YEARS_BUILD_MEDI`: 66.50%
  - `OWN_CAR_AGE`: 65.99%
  - `LANDAREA_MEDI`: 59.38%
  - `LANDAREA_AVG`: 59.38%
  - `LANDAREA_MODE`: 59.38%

- **Candidates for Unified LoanSense Feature Set:**
  - `AMT_CREDIT` (Loan amount)
  - `AMT_INCOME_TOTAL` (Income)
  - `AMT_ANNUITY` (Used for EMI to income ratio)
  - `NAME_INCOME_TYPE` (Employment type)
  - `AMT_GOODS_PRICE` (Existing obligations proxy)
  - `EXT_SOURCE_2` (CIBIL score simulation)
  - `TARGET` (default_flag)

## 2. IEEE-CIS Fraud Detection

- **Shape:** 590,540 rows, 394 columns
- **Target Distribution (isFraud):** 0 (Legit): 96.50%, 1 (Fraud): 3.50%
  - *Class Imbalance Ratio:* ~1:27
- **Feature Types:**
  - float64: 376
  - object: 14
  - int64: 4

- **Top 20 Columns with Missing Values:**
  - `dist2`: 93.63%
  - `D7`: 93.41%
  - `D13`: 89.51%
  - `D14`: 89.47%
  - `D12`: 89.04%
  - `D6`: 87.61%
  - `D9`: 87.31%
  - `D8`: 87.31%
  - `V153`: 86.12%
  - `V149`: 86.12%
  - `V141`: 86.12%
  - `V146`: 86.12%
  - `V154`: 86.12%
  - `V162`: 86.12%
  - `V142`: 86.12%
  - `V158`: 86.12%
  - `V161`: 86.12%
  - `V157`: 86.12%
  - `V138`: 86.12%
  - `V139`: 86.12%

- **Candidates for Unified LoanSense Feature Set:**
  - `TransactionAmt` (Used for transaction velocity proxy)
  - `TransactionDT` (Used for time-based velocity features)
  - `isFraud` (fraud_flag)
  - `card1` to `card6` (Proxy for categorical/card details if needed)
