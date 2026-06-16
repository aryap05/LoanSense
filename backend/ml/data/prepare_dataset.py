import pandas as pd
import numpy as np
from pathlib import Path
from sklearn.model_selection import train_test_split
from imblearn.over_sampling import SMOTENC
import warnings

warnings.filterwarnings('ignore')

def prepare_dataset():
    print("Assembling final training dataset...")
    base_dir = Path(__file__).parent.parent.parent
    processed_dir = base_dir / "ml" / "data" / "processed"
    attacks_dir = base_dir / "ml" / "data" / "attacks"
    
    # 1. Load datasets
    print("Loading datasets...")
    df_base = pd.read_parquet(processed_dir / "india_synthetic.parquet")
    df_attacks = pd.read_parquet(attacks_dir / "combined_attacks.parquet")
    
    # 2. Concatenate
    # india_synthetic lacks pattern_label, so it will become NaN. Fill with 'none'
    df_combined = pd.concat([df_base, df_attacks], ignore_index=True)
    df_combined['pattern_label'] = df_combined['pattern_label'].fillna('none')
    
    print(f"Combined dataset shape: {df_combined.shape}")
    
    # 3. Stratified split (70/15/15)
    # Stratify on fraud_flag to ensure equal representation across splits
    print("Splitting dataset (70% train, 15% val, 15% test)...")
    df_train, df_temp = train_test_split(
        df_combined, test_size=0.30, stratify=df_combined['fraud_flag'], random_state=42
    )
    df_val, df_test = train_test_split(
        df_temp, test_size=0.50, stratify=df_temp['fraud_flag'], random_state=42
    )
    
    pre_smote_counts = df_train['fraud_flag'].value_counts(normalize=True) * 100
    print(f"\nPre-SMOTE Train Class Distribution (fraud_flag):")
    print(f"0 (Legit): {pre_smote_counts.get(0, 0):.2f}%")
    print(f"1 (Fraud): {pre_smote_counts.get(1, 0):.2f}%")
    
    # 4. Apply SMOTENC on the training split ONLY
    # Target: fraud_flag. We set sampling_strategy=0.25 (minority will be 25% of majority, ~20% of total)
    print("\nApplying SMOTENC to training split...")
    
    # Identify categorical columns for SMOTENC
    cat_cols = ['employment_type', 'loan_purpose', 'employer_description', 'pattern_label', 'new_to_credit', 'default_flag']
    
    X_train = df_train.drop(columns=['fraud_flag'])
    y_train = df_train['fraud_flag']
    
    cat_indices = [X_train.columns.get_loc(c) for c in cat_cols if c in X_train.columns]
    
    # Use sampling_strategy=0.25 -> #fraud = 0.25 * #legit. Since legit is ~95%, fraud becomes ~19% of total.
    smote = SMOTENC(categorical_features=cat_indices, sampling_strategy=0.25, random_state=42)
    X_res, y_res = smote.fit_resample(X_train, y_train)
    
    df_train_res = pd.concat([X_res, y_res], axis=1)
    
    # Post-process: ensure numeric columns didn't get weird floats from interpolation
    int_cols = ['SK_ID_CURR', 'loan_amount', 'income', 'loan_tenure_months', 'existing_obligations', 
                'cibil_score_simulated', 'transaction_velocity_30d', 'account_age_months', 'enquiry_count_30d']
    for col in int_cols:
        if col in df_train_res.columns:
            df_train_res[col] = df_train_res[col].round().astype(int)
            
    post_smote_counts = df_train_res['fraud_flag'].value_counts(normalize=True) * 100
    print(f"Post-SMOTE Train Class Distribution (fraud_flag):")
    print(f"0 (Legit): {post_smote_counts.get(0, 0):.2f}%")
    print(f"1 (Fraud): {post_smote_counts.get(1, 0):.2f}%")
    
    # 5. Save Splits
    print("\nSaving splits...")
    df_train_res.to_parquet(processed_dir / "train.parquet", index=False)
    df_val.to_parquet(processed_dir / "val.parquet", index=False)
    df_test.to_parquet(processed_dir / "test.parquet", index=False)
    
    val_fraud = df_val['fraud_flag'].mean() * 100
    test_fraud = df_test['fraud_flag'].mean() * 100
    print(f"Validation fraud rate: {val_fraud:.2f}%")
    print(f"Test fraud rate: {test_fraud:.2f}%")
    print(f"Train shape: {df_train_res.shape}")
    print(f"Val shape: {df_val.shape}")
    print(f"Test shape: {df_test.shape}")
    
    # 6. Generate dataset_card.md
    dataset_card = f"""# LoanSense Dataset Card

## Overview
This dataset combines India-realistic synthetic legitimate applicants with 4 parameterized synthetic attack patterns.

## Data Splits
- **Train Split:** {df_train_res.shape[0]:,} rows (SMOTE applied)
- **Validation Split:** {df_val.shape[0]:,} rows (Strictly isolated)
- **Test Split:** {df_test.shape[0]:,} rows (Strictly isolated)

## Class Distribution (fraud_flag)
- **Train (Pre-SMOTE):** {pre_smote_counts.get(1, 0):.2f}% fraud
- **Train (Post-SMOTE):** {post_smote_counts.get(1, 0):.2f}% fraud
- **Validation:** {val_fraud:.2f}% fraud (True distribution)
- **Test:** {test_fraud:.2f}% fraud (True distribution)

## Why SMOTE was applied ONLY to the train split
SMOTE (Synthetic Minority Over-sampling Technique) was used to increase the fraud signal density in the training set to ~20%. This provides the model with enough examples of the minority class to learn decision boundaries effectively. 
Critically, SMOTE was **never** applied to the validation or test splits. Evaluating on oversampled data causes massive data leakage and gives falsely optimistic performance metrics. Val and test splits represent the true, imbalanced distribution of the data.

## Features
- **SK_ID_CURR** (int): Applicant ID
- **loan_amount** (int): Loan amount asked
- **income** (int): Declared monthly income
- **emi_to_income_ratio** (float): Monthly installment vs income
- **employment_type** (categorical): Type of employment
- **loan_tenure_months** (int): Estimated tenure
- **existing_obligations** (int): Derived existing debt
- **cibil_score_simulated** (int): Simulated 300-900 credit score
- **transaction_velocity_30d** (int): Num transactions in last 30 days
- **account_age_months** (int): Age of oldest account
- **enquiry_count_30d** (int): Hard enquiries in 30 days
- **income_transaction_ratio** (float): Income vs transaction behavior
- **new_to_credit** (bool): If account age < 6 months
- **upi_velocity_percentile** (float): Percentile rank of transaction velocity
- **loan_purpose** (categorical): Declared purpose of loan
- **employer_description** (text): Unstructured employer description
- **pattern_label** (categorical): Type of fraud attack (or 'none')
- **default_flag** (bool/int): Target for credit risk
- **fraud_flag** (bool/int): Target for fraud signal

## Label-Feature Independence & Causality
- **Causal Generation:** `default_flag` is generated using a logistic probability derived directly from credit features (CIBIL, account age, EMI ratio), ensuring realistic but noisy correlations (e.g., CIBIL vs default correlation is ~ -0.09).
- **Intentional Divergence (Pattern 4):** The 'Synthetic Identity' pattern is carefully constructed to show high fraud signal (fraud_flag=1) but very low default probability (~7.6%). This proves that a credit risk model alone will miss synthetic identities, making the Contradiction Detector necessary.

## Limitations
- **Synthetic Join:** The base data is derived from Home Credit, with fraud flags and signals synthetically modeled from IEEE-CIS distributions. There is no true row-level key joining them.
- **Simulated Features:** Features like `account_age_months` and `upi_velocity_percentile` are statistically simulated based on standard fraud behaviors, not empirically recorded.
"""
    
    with open(processed_dir / "dataset_card.md", "w") as f:
        f.write(dataset_card)
        
    print("dataset_card.md generated successfully.")

if __name__ == "__main__":
    prepare_dataset()
