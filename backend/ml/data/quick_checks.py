import pandas as pd
import numpy as np
from pathlib import Path
from sklearn.metrics import confusion_matrix
import joblib

def main():
    base_dir = Path(__file__).parent.parent.parent
    processed_dir = base_dir / "ml" / "data" / "processed"
    attacks_dir = base_dir / "ml" / "data" / "attacks"
    models_dir = base_dir / "ml" / "training"
    
    # Check 1: Rarity of Pattern 4 combination in legit population
    df_train = pd.read_parquet(processed_dir / "train.parquet")
    # Actually, we should check pre-SMOTE, let's load val.parquet
    df_val = pd.read_parquet(processed_dir / "val.parquet")
    df_legit_val = df_val[df_val['fraud_flag'] == 0]
    
    pat4_cond = (df_legit_val['account_age_months'] < 6) & (df_legit_val['cibil_score_simulated'] > 750)
    legit_pct = pat4_cond.mean() * 100
    print(f"Check 1: Pattern 4 rarity")
    print(f"  % of legit rows with age < 6 AND cibil > 750: {legit_pct:.4f}% ({pat4_cond.sum()} / {len(df_legit_val)})")
    
    # Check 2: Decompose Pattern 2's 20.2% detection
    # Load combined_attacks to get exact rows for Pattern 2
    df_attacks = pd.read_parquet(attacks_dir / "combined_attacks.parquet")
    pat2 = df_attacks[df_attacks['pattern_label'] == 'fragmented_bureau_footprint']
    
    # Load the rule and model from train_fraud.py
    import sys
    sys.path.append(str(base_dir / "ml" / "training"))
    from train_fraud import FraudPreFilter
    
    # Re-train XGBoost on df_train
    print("Training XGBoost on train split...")
    cat_cols = ['employment_type', 'loan_purpose', 'employer_description', 'new_to_credit', 'default_flag']
    X_train = df_train.drop(columns=['fraud_flag', 'pattern_label'], errors='ignore')
    if 'SK_ID_CURR' in X_train.columns:
        X_train = X_train.drop(columns=['SK_ID_CURR'])
    y_train = df_train['fraud_flag']
    
    X_pat2 = pat2.drop(columns=['fraud_flag', 'pattern_label'], errors='ignore')
    if 'SK_ID_CURR' in X_pat2.columns:
        X_pat2 = X_pat2.drop(columns=['SK_ID_CURR'])
        
    filter = FraudPreFilter()
    rule_fired = 0
    for _, row in X_pat2.iterrows():
        fired_rules = filter.check_rules(row)
        if len(fired_rules) > 0:
            rule_fired += 1
            
    print(f"\nCheck 2: Pattern 2 Decomposition")
    print(f"  Rule Fired alone rate: {rule_fired / len(X_pat2) * 100:.2f}% ({rule_fired} / {len(X_pat2)})")
    
    for c in cat_cols:
        if c in X_train.columns:
            X_train[c] = X_train[c].astype('category')
            
    import xgboost as xgb
    xgb_model = xgb.XGBClassifier(
        n_estimators=100, max_depth=4, learning_rate=0.1, 
        subsample=0.8, colsample_bytree=0.8, enable_categorical=True, 
        random_state=42, use_label_encoder=False, eval_metric='logloss'
    )
    xgb_model.fit(X_train, y_train)
    
    for c in cat_cols:
        if c in X_pat2.columns:
            X_pat2[c] = X_pat2[c].astype('category')
            
    xgb_preds = xgb_model.predict_proba(X_pat2)[:, 1]
    
    above_thresh = (xgb_preds > 0.30).sum()
    print(f"  XGB Probability > 0.3 alone rate: {above_thresh / len(X_pat2) * 100:.2f}% ({above_thresh} / {len(X_pat2)})")
    
    # Combined rate
    combined = 0
    for i, (_, row) in enumerate(X_pat2.iterrows()):
        fired = len(filter.check_rules(row)) > 0
        if fired and xgb_preds[i] > 0.3:
            combined += 1
            
    print(f"  Combined (Rule + XGB > 0.3): {combined / len(X_pat2) * 100:.2f}% ({combined} / {len(X_pat2)})")
    
    # Note: the 20.2% is specifically from val set evaluation which had the combined rule
    
if __name__ == "__main__":
    main()
