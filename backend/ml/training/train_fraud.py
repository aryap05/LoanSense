import pandas as pd
import numpy as np
from pathlib import Path
import xgboost as xgb
from sklearn.metrics import roc_auc_score, f1_score, precision_score, recall_score, confusion_matrix
import mlflow
import mlflow.sklearn
import shap
import matplotlib.pyplot as plt
import warnings

warnings.filterwarnings('ignore')

class FraudPreFilter:
    def __init__(self):
        pass
        
    def check_rules(self, row):
        signals = []
        if row.get('income_transaction_ratio', 0) > 6:
            signals.append('income_fabrication_risk')
        if row.get('enquiry_count_30d', 0) > 5:
            signals.append('high_enquiry_velocity')
            
        # DECISION: Deduplication of `new_account_high_score`.
        # We KEEP this rule here in the fraud layer despite it also existing in Block 11's Contradiction rules.
        # Reason: The fraud pre-filter acts as a standalone defense mechanism. Catching a high-score thin-file
        # is a critical primary fraud signal (Synthetic Identity). Block 11 will later use this as a structural
        # contradiction between the overall credit score and fraud probability, but the fraud model needs 
        # to trigger `elevated_fraud_risk` independently based on this local feature pattern.
        if row.get('account_age_months', 120) < 6 and row.get('cibil_score_simulated', 0) > 700:
            signals.append('new_account_high_score')
            
        if row.get('upi_velocity_percentile', 0) > 90:
            signals.append('transaction_velocity_anomaly')
            
        return signals

def evaluate_attacks(model, pre_filter, features, base_dir):
    attacks_path = base_dir / "ml" / "data" / "attacks" / "combined_attacks.parquet"
    if not attacks_path.exists():
        print(f"Skipping attack evaluation, file not found: {attacks_path}")
        return
        
    df_attacks = pd.read_parquet(attacks_path)
    print("\n=== Attack Pattern Detection Rate ===")
    
    # We must ensure 'new_to_credit' is mapped to int if it's bool
    if df_attacks['new_to_credit'].dtype == bool:
        df_attacks['new_to_credit'] = df_attacks['new_to_credit'].astype(int)
        
    for pattern in df_attacks['pattern_label'].unique():
        df_pat = df_attacks[df_attacks['pattern_label'] == pattern]
        X_pat = df_pat[features]
        
        preds_proba = model.predict_proba(X_pat)[:, 1]
        
        caught_count = 0
        for i in range(len(df_pat)):
            row = df_pat.iloc[i].to_dict()
            prob = preds_proba[i]
            signals = pre_filter.check_rules(row)
            
            elevated_risk = (len(signals) > 0) and (prob > 0.3)
            if elevated_risk:
                caught_count += 1
                
        print(f"Pattern {pattern:35s}: {caught_count}/{len(df_pat)} ({(caught_count/len(df_pat))*100:.1f}%) caught")


def main():
    base_dir = Path(__file__).parent.parent.parent
    processed_dir = base_dir / "ml" / "data" / "processed"
    
    df_train = pd.read_parquet(processed_dir / "train.parquet")
    df_val = pd.read_parquet(processed_dir / "val.parquet")
    
    features = [
        'transaction_velocity_30d', 'account_age_months', 'enquiry_count_30d', 
        'income_transaction_ratio', 'upi_velocity_percentile', 'new_to_credit', 'loan_amount'
    ]
    target = 'fraud_flag'
    
    # Handle boolean new_to_credit
    for df in [df_train, df_val]:
        if df['new_to_credit'].dtype == bool:
            df['new_to_credit'] = df['new_to_credit'].astype(int)
        
    X_train = df_train[features]
    y_train = df_train[target]
    
    X_val = df_val[features]
    y_val = df_val[target]
    
    neg = (y_train == 0).sum()
    pos = (y_train == 1).sum()
    scale_pos = neg / pos if pos > 0 else 1.0
    
    mlflow.set_tracking_uri(f"sqlite:///{base_dir}/mlruns/mlflow.db")
    mlflow.set_experiment("loansense-fraud-signal")
    
    with mlflow.start_run():
        params = {
            'n_estimators': 300,
            'max_depth': 5,
            'learning_rate': 0.03,
            'scale_pos_weight': scale_pos,
            'random_state': 42
        }
        mlflow.log_params(params)
        
        print("Training Fraud Signal Detector (Baseline)...")
        model = xgb.XGBClassifier(**params)
        model.fit(X_train, y_train)
        
        train_preds = model.predict_proba(X_train)[:, 1]
        train_auc = roc_auc_score(y_train, train_preds)
        
        val_preds_proba = model.predict_proba(X_val)[:, 1]
        val_preds_class = (val_preds_proba > 0.5).astype(int)
        
        val_auc = roc_auc_score(y_val, val_preds_proba)
        val_f1 = f1_score(y_val, val_preds_class)
        val_prec = precision_score(y_val, val_preds_class)
        val_rec = recall_score(y_val, val_preds_class)
        
        tn, fp, fn, tp = confusion_matrix(y_val, val_preds_class).ravel()
        fpr = fp / (fp + tn)
        
        gap = train_auc - val_auc
        
        print("\n=== Model Metrics ===")
        print(f"Train ROC-AUC: {train_auc:.4f}")
        print(f"Val ROC-AUC:   {val_auc:.4f}")
        print(f"Train-Val Gap: {gap:.4f}")
        print(f"Val F1-Score:  {val_f1:.4f}")
        print(f"Val Precision: {val_prec:.4f}")
        print(f"Val Recall:    {val_rec:.4f}")
        print(f"Val FPR:       {fpr:.4f}")
        
        if gap > 0.1:
            print("\n[WARNING] Train-Val gap exceeds 0.1 ROC-AUC! Model is overfitting.")
            print("Optuna search and/or regularization is highly recommended.")
        
        mlflow.log_metrics({
            'train_roc_auc': train_auc,
            'val_roc_auc': val_auc,
            'val_f1': val_f1,
            'val_precision': val_prec,
            'val_recall': val_rec,
            'val_fpr': fpr
        })
        
        pre_filter = FraudPreFilter()
        evaluate_attacks(model, pre_filter, features, base_dir)
        
        explainer = shap.TreeExplainer(model)
        shap_sample = X_val.sample(n=min(1000, len(X_val)), random_state=42)
        shap_values = explainer.shap_values(shap_sample)
        
        plt.figure()
        shap.summary_plot(shap_values, shap_sample, show=False)
        shap_plot_path = base_dir / "ml" / "training" / "shap_summary_fraud.png"
        shap_plot_path.parent.mkdir(parents=True, exist_ok=True)
        plt.savefig(shap_plot_path, bbox_inches='tight')
        mlflow.log_artifact(str(shap_plot_path))
        
        print("\nLogging and Registering Model...")
        mlflow.sklearn.log_model(
            sk_model=model,
            artifact_path="model",
            registered_model_name="fraud-signal-detector"
        )
        print("Done!")

if __name__ == "__main__":
    main()
