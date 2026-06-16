import pandas as pd
import numpy as np
from pathlib import Path
import mlflow
import mlflow.sklearn
import mlflow.pyfunc
import warnings
import joblib

warnings.filterwarnings('ignore')

def main():
    base_dir = Path(__file__).parent.parent.parent
    processed_dir = base_dir / "ml" / "data" / "processed"
    
    # MLflow Setup
    mlruns_path = base_dir / "mlruns" / "mlflow.db"
    mlflow.set_tracking_uri(f"sqlite:///{mlruns_path.as_posix()}")
    
    print("Loading Data...")
    df_val = pd.read_parquet(processed_dir / "val.parquet")
    if 'new_to_credit' in df_val.columns and df_val['new_to_credit'].dtype == bool:
        df_val['new_to_credit'] = df_val['new_to_credit'].astype(int)
        
    print("Loading Base Models...")
    credit_model = mlflow.sklearn.load_model("models:/credit-risk-scorer/latest")
    fraud_model = mlflow.sklearn.load_model("models:/fraud-signal-detector/latest")
    
    # Load isolation forest directly from the tmp_artifacts to check the training distribution
    iso_forest = joblib.load(base_dir / "ml" / "training" / "tmp_artifacts" / "isolation_forest.pkl")
    
    credit_features = [
        'income', 'loan_amount', 'emi_to_income_ratio', 'employment_type', 
        'cibil_score_simulated', 'loan_tenure_months', 'existing_obligations', 
        'account_age_months', 'new_to_credit'
    ]
    fraud_features = [
        'transaction_velocity_30d', 'account_age_months', 'enquiry_count_30d', 
        'income_transaction_ratio', 'upi_velocity_percentile', 'new_to_credit', 'loan_amount'
    ]
    combined_features = list(set(credit_features + fraud_features))
    
    df_val['credit_risk_score'] = credit_model.predict_proba(df_val[credit_features])[:, 1]
    df_val['fraud_probability'] = fraud_model.predict_proba(df_val[fraud_features])[:, 1]
    
    # In sklearn IsolationForest.score_samples returns negative anomaly scores 
    # (lower is more anomalous). Our pipeline negates this:
    # anomaly_score = -self.isolation_forest.score_samples(anomaly_features)
    # Let's verify min/max/mean of this negated score on val set.
    raw_scores = iso_forest.score_samples(df_val[combined_features])
    anomaly_scores = -raw_scores
    
    print("\n=== Anomaly Score Distribution (Val Set) ===")
    print(f"Min:  {anomaly_scores.min():.4f}")
    print(f"Max:  {anomaly_scores.max():.4f}")
    print(f"Mean: {anomaly_scores.mean():.4f}")
    
    # Compute full contradiction predictions
    print("\nLoading Contradiction Model...")
    contradiction_model = mlflow.pyfunc.load_model("models:/contradiction-detector/latest")
    
    preds = contradiction_model.predict(df_val)
    df_val['contradiction_score'] = preds['contradiction_score']
    
    # False Positive Rate on Legitimate Applicants
    df_legit = df_val[df_val['fraud_flag'] == 0].copy()
    
    # Segment by credit risk band
    def get_band(score):
        if score < 0.3: return "Low"
        elif score <= 0.6: return "Medium"
        else: return "High"
        
    df_legit['credit_band'] = df_legit['credit_risk_score'].apply(get_band)
    
    print("\n=== False Positive Rate by Credit Risk Band ===")
    print("(Legitimate applicants only, flagged as contradiction > 0.6)")
    
    for band in ["Low", "Medium", "High"]:
        band_df = df_legit[df_legit['credit_band'] == band]
        if len(band_df) == 0:
            print(f"Band {band:6s}: No legitimate applicants in this band.")
            continue
            
        fps = (band_df['contradiction_score'] > 0.6).sum()
        total = len(band_df)
        fpr = fps / total
        print(f"Band {band:6s}: {fps}/{total} ({fpr*100:.2f}%) False Positives")
        
    # Overall FPR
    total_fps = (df_legit['contradiction_score'] > 0.6).sum()
    total_legit = len(df_legit)
    print(f"\nOverall FPR: {total_fps}/{total_legit} ({(total_fps/total_legit)*100:.2f}%)")

if __name__ == "__main__":
    main()
