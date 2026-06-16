import pandas as pd
import numpy as np
from pathlib import Path
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import roc_auc_score
from sklearn.preprocessing import StandardScaler

def main():
    base_dir = Path(__file__).parent.parent.parent
    processed_dir = base_dir / "ml" / "data" / "processed"
    attacks_dir = base_dir / "ml" / "data" / "attacks"
    
    # 1. Full Correlation Table on train.parquet
    print("=== 1. Full Correlation Table (train.parquet) ===")
    train_df = pd.read_parquet(processed_dir / "train.parquet")
    
    # Encode categorical features for correlation
    df_corr = train_df.copy()
    cat_cols = df_corr.select_dtypes(include=['object', 'category', 'bool']).columns
    for col in cat_cols:
        df_corr[col] = pd.factorize(df_corr[col])[0]
        
    correlations = df_corr.corr()['default_flag'].drop('default_flag').sort_values(key=abs, ascending=False)
    
    for feat, corr in correlations.items():
        abs_corr = abs(corr)
        flag = ""
        if abs_corr < 0.05:
            flag = " [weak/near-noise]"
        elif abs_corr > 0.5:
            flag = " [investigate for leakage]"
        print(f"{feat:30s}: {corr:+.4f}{flag}")
        
    # Check cibil vs emi
    cibil_corr = abs(correlations.get('cibil_score_simulated', 0))
    emi_corr = abs(correlations.get('emi_to_income_ratio', 0))
    print(f"\nCIBIL correlation: {cibil_corr:.4f} vs EMI correlation: {emi_corr:.4f}")
    if cibil_corr < emi_corr:
        print("Note: CIBIL is weaker than EMI! Logit coefficients used in synthetic_layer.py:")
        print("  CIBIL logit impact: + 2.5 * (1 - cibil_normalized)")
        print("  EMI logit impact: + 1.5 * (emi_ratio > 0.5)")
        
    # 2. Single-Feature AUC (train.parquet)
    print("\n=== 2. Single-Feature AUC (Logistic Regression on train.parquet) ===")
    features_to_test = ['cibil_score_simulated', 'account_age_months', 'enquiry_count_30d', 'emi_to_income_ratio']
    
    for f in features_to_test:
        if f not in train_df.columns:
            continue
        X = train_df[[f]].values
        y = train_df['default_flag'].values
        
        scaler = StandardScaler()
        X_scaled = scaler.fit_transform(X)
        
        lr = LogisticRegression()
        lr.fit(X_scaled, y)
        preds = lr.predict_proba(X_scaled)[:, 1]
        auc = roc_auc_score(y, preds)
        
        flag = " [potential leakage concern]" if auc > 0.85 else ""
        print(f"{f:30s}: AUC = {auc:.4f}{flag}")

    # 3. Pattern 4 vs Legitimate Population
    print("\n=== 3. Pattern 4 vs Legitimate Population ===")
    india_df = pd.read_parquet(processed_dir / "india_synthetic.parquet")
    p4_df = pd.read_parquet(attacks_dir / "synthetic_identity_clean.parquet")
    
    legit_rate = india_df['default_flag'].mean() * 100
    p4_rate = p4_df['default_flag'].mean() * 100
    train_rate = train_df['default_flag'].mean() * 100
    
    print(f"Legitimate Population (india_synthetic): {legit_rate:.2f}%")
    print(f"Pattern 4 (synthetic_identity_clean)   : {p4_rate:.2f}%")
    print(f"Overall Training Set (train.parquet)   : {train_rate:.2f}% (Note: post-SMOTE fraud oversampled)")
    
    diff = abs(legit_rate - p4_rate)
    if diff <= 3.0:
        print(f"-> Pattern 4 default_flag rate is statistically close to legitimate population (diff: {diff:.2f}%).")
    else:
        print(f"-> Pattern 4 default_flag rate deviates from legitimate population by {diff:.2f}%.")

if __name__ == "__main__":
    main()
