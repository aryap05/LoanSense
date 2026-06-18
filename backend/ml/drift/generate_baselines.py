import json
import numpy as np
import pandas as pd
from pathlib import Path
import sys

# Add backend dir to path for imports
base_dir = Path(__file__).parent.parent.parent
sys.path.append(str(base_dir))

from app.models.loader import model_registry

def generate_baselines():
    print("Loading models...")
    model_registry.load_all()
    
    data_path = base_dir / "ml" / "data" / "processed" / "train.parquet"
    print(f"Loading training data from {data_path}...")
    df = pd.read_parquet(data_path)
    
    # Required features for each model
    credit_features = [
        'income', 'loan_amount', 'emi_to_income_ratio', 'employment_type', 
        'cibil_score_simulated', 'loan_tenure_months', 'existing_obligations', 
        'account_age_months', 'new_to_credit'
    ]
    
    fraud_features = [
        'transaction_velocity_30d', 'account_age_months', 'enquiry_count_30d', 
        'income_transaction_ratio', 'upi_velocity_percentile', 'new_to_credit', 'loan_amount'
    ]
    
    print("Generating predictions...")
    credit_model = model_registry.models.get("credit-risk-scorer")["model"]
    fraud_model = model_registry.models.get("fraud-signal-detector")["model"]
    
    credit_df = df[credit_features]
    fraud_df = df[fraud_features]
    
    # Handle different prediction APIs (xgboost vs sklearn)
    try:
        credit_scores = credit_model.predict_proba(credit_df)[:, 1]
    except AttributeError:
        credit_scores = credit_model.predict(credit_df)
        
    try:
        fraud_scores = fraud_model.predict_proba(fraud_df)[:, 1]
    except AttributeError:
        fraud_scores = fraud_model.predict(fraud_df)
        
    def get_distribution(scores, bins=10):
        # Create histogram with bins from 0.0 to 1.0
        hist, bin_edges = np.histogram(scores, bins=bins, range=(0.0, 1.0))
        # Convert to percentages
        percentages = (hist / len(scores)).tolist()
        return percentages
        
    baselines = {
        "credit-risk-scorer": get_distribution(credit_scores),
        "fraud-signal-detector": get_distribution(fraud_scores),
        # Contradiction detector outputs score based on meta-model, but let's stick to the two main models for now
    }
    
    out_path = Path(__file__).parent / "baselines.json"
    with open(out_path, "w") as f:
        json.dump(baselines, f, indent=2)
        
    print(f"Baselines successfully saved to {out_path}")
    print(json.dumps(baselines, indent=2))

if __name__ == "__main__":
    generate_baselines()
