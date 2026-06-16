import pandas as pd
import numpy as np
from pathlib import Path
from sklearn.model_selection import train_test_split
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import roc_auc_score
import warnings

warnings.filterwarnings('ignore')

def main():
    base_dir = Path(__file__).parent.parent.parent
    processed_dir = base_dir / "ml" / "data" / "processed"
    attacks_dir = base_dir / "ml" / "data" / "attacks"
    
    # 1. Recreate pre-SMOTE train split
    df_base = pd.read_parquet(processed_dir / "india_synthetic.parquet")
    df_attacks = pd.read_parquet(attacks_dir / "combined_attacks.parquet")
    
    df_combined = pd.concat([df_base, df_attacks], ignore_index=True)
    df_combined['pattern_label'] = df_combined['pattern_label'].fillna('none')
    
    df_train, _ = train_test_split(
        df_combined, test_size=0.30, stratify=df_combined['fraud_flag'], random_state=42
    )
    
    features = [
        'transaction_velocity_30d', 'account_age_months', 'enquiry_count_30d', 
        'income_transaction_ratio', 'upi_velocity_percentile', 'new_to_credit', 'loan_amount'
    ]
    
    df_train['new_to_credit'] = df_train['new_to_credit'].astype(int)
    
    print("=== 1. Correlation with fraud_flag ===")
    corrs = []
    for f in features:
        c = df_train[f].corr(df_train['fraud_flag'])
        corrs.append((f, c, abs(c)))
        
    corrs.sort(key=lambda x: x[2], reverse=True)
    
    flagged_features = set()
    for f, c, ac in corrs:
        flag = "[INVESTIGATE FOR LEAKAGE]" if ac > 0.5 else ""
        if ac > 0.5:
            flagged_features.add(f)
        print(f"{f:30s}: {c:+.4f} {flag}")
        
    print("\n=== 2. Single-feature AUC against fraud_flag ===")
    for f in features:
        X = df_train[[f]]
        y = df_train['fraud_flag']
        lr = LogisticRegression()
        lr.fit(X, y)
        preds = lr.predict_proba(X)[:, 1]
        auc = roc_auc_score(y, preds)
        
        flag = "[INVESTIGATE FOR LEAKAGE]" if auc > 0.85 else ""
        if auc > 0.85:
            flagged_features.add(f)
        print(f"{f:30s}: AUC = {auc:.4f} {flag}")
        
    print("\n=== 3. Distribution Check for Flagged Features ===")
    df_legit = df_train[df_train['fraud_flag'] == 0]
    df_fraud = df_train[df_train['fraud_flag'] == 1]
    
    for f in features:
        print(f"\nFeature: {f}")
        legit_vals = df_legit[f]
        fraud_vals = df_fraud[f]
        
        def print_stats(name, vals):
            print(f"  {name:6s}: min={vals.min():.2f}, p25={vals.quantile(0.25):.2f}, "
                  f"p50={vals.quantile(0.5):.2f}, p75={vals.quantile(0.75):.2f}, "
                  f"p90={vals.quantile(0.9):.2f}, max={vals.max():.2f}, mean={vals.mean():.2f}")
                  
        print_stats("Legit", legit_vals)
        print_stats("Fraud", fraud_vals)
        
        l_min, l_max = legit_vals.min(), legit_vals.max()
        f_min, f_max = fraud_vals.min(), fraud_vals.max()
        
        # Calculate overlap: what % of fraud values fall inside the legit [min, max] range?
        overlap_mask_fraud = (fraud_vals >= l_min) & (fraud_vals <= l_max)
        overlap_pct_fraud = overlap_mask_fraud.mean() * 100
        print(f"  Fraud Overlap: {overlap_pct_fraud:.2f}% of fraud samples fall within legit range [{l_min:.2f}, {l_max:.2f}]")
        
        overlap_mask_legit = (legit_vals >= f_min) & (legit_vals <= f_max)
        overlap_pct_legit = overlap_mask_legit.mean() * 100
        print(f"  Legit Overlap: {overlap_pct_legit:.2f}% of legit samples fall within fraud range [{f_min:.2f}, {f_max:.2f}]")
        
        # Check if there is a distinct hardcoded range
        print(f"  Distinct Fraud Range? (Values outside legit range): {fraud_vals[~overlap_mask_fraud].unique()[:5]}")

if __name__ == "__main__":
    main()
