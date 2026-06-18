import asyncio
import pandas as pd
from pathlib import Path
import httpx
from collections import Counter
import sys
import argparse

backend_dir = Path(__file__).parent.parent.parent
if str(backend_dir) not in sys.path:
    sys.path.append(str(backend_dir))

from dotenv import load_dotenv
load_dotenv(backend_dir / ".env")

from app.main import app
from ml.attack_generator.generate_attacks import generate_clean_base

from app.models.loader import model_registry
from app.db import crud
from app.db.database import SessionLocal
from uuid import uuid4

# NOTE: Live Groq API calls (via AgentOrchestrator) are reserved for manual 
# spot checks and single applicant reviews only. For bulk evaluation of 
# attack patterns, we evaluate the underlying ML models and Contradiction Engine 
# directly to avoid hitting strict Token-Per-Day (TPD) limits on free-tier LLMs.

def evaluate_applicant_models(raw_features):
    """Hits the local ML models directly instead of the full Agent loop"""
    try:
        # Get signals
        credit = model_registry.get_credit_score(raw_features)
        fraud = model_registry.get_fraud_signals(raw_features)
        contradiction = model_registry.get_contradiction_score(raw_features)
        
        # Simple programmatic decision logic (mimicking agent baseline)
        if contradiction.get("contradiction_score", 0.0) > 0.6:
            return {"decision": "FLAG_FOR_REVIEW", "reason": "Contradiction override"}
            
        if fraud.get("is_fraud", False) or fraud.get("fraud_probability", 0.0) > 0.7:
            return {"decision": "REJECT", "reason": "Fraud detected"}
            
        if credit.get("score", 0.0) > 0.7:
            return {"decision": "REJECT", "reason": "High credit risk"}
            
        return {"decision": "APPROVE", "reason": "Clean"}
        
    except Exception as e:
        return {"decision": "ERROR", "reason": str(e)}

async def run_evaluation(num_per_pattern=20, clean_samples=20):
    print(f"Loading data... ({num_per_pattern} per pattern, {clean_samples} clean)")
    attacks_path = backend_dir / "ml" / "data" / "attacks" / "combined_attacks.parquet"
    
    if not attacks_path.exists():
        print(f"Error: {attacks_path} not found.")
        return
        
    df_attacks = pd.read_parquet(attacks_path)
    
    # Sample from each pattern
    patterns = df_attacks['pattern_label'].unique()
    sampled_attacks = pd.DataFrame()
    for p in patterns:
        sampled_attacks = pd.concat([sampled_attacks, df_attacks[df_attacks['pattern_label'] == p].sample(n=num_per_pattern, random_state=42)])
        
    # Generate clean samples
    df_clean = generate_clean_base(clean_samples)
    df_clean['pattern_label'] = 'legitimate'
    
    # Combine
    df_eval = pd.concat([sampled_attacks, df_clean], ignore_index=True)
    
    records = []
    for idx, row in df_eval.iterrows():
        # Build features directly for the model
        features = {
            "income": float(row['income']),
            "loan_amount": float(row['loan_amount']),
            "cibil_score": int(row['cibil_score_simulated']),
            "account_age_months": int(row['account_age_months']),
            "enquiry_count_30d": int(row['enquiry_count_30d']),
            "upi_velocity_percentile": float(row.get('upi_velocity_percentile', 50.0)),
            "transaction_velocity_30d": float(row.get('transaction_velocity_30d', 10.0)),
            "loan_term_months": int(row.get('loan_tenure_months', 24)),
            "existing_emi": float(row.get('existing_obligations', 0.0))
        }
        records.append({
            "pattern": row['pattern_label'],
            "features": features
        })
        
    print(f"Prepared {len(records)} applicants. Starting local ML evaluation...")
    
    # Ensure models are loaded
    model_registry.load_all()
    
    results = []
    total = len(records)
    for i, record in enumerate(records):
        res = evaluate_applicant_models(record['features'])
        
        results.append({
            "pattern": record["pattern"],
            "decision": res["decision"],
            "reason": res["reason"]
        })
                
    # Aggregate metrics
    print("\n" + "="*50)
    print("EVALUATION REPORT (LOCAL ML ONLY)")
    print("="*50)
    
    df_results = pd.DataFrame(results)
    
    all_patterns = df_results['pattern'].unique()
    for p in all_patterns:
        sub_df = df_results[df_results['pattern'] == p]
        count = len(sub_df)
        approves = len(sub_df[sub_df['decision'] == 'APPROVE'])
        flags = len(sub_df[sub_df['decision'] == 'FLAG_FOR_REVIEW'])
        rejects = len(sub_df[sub_df['decision'] == 'REJECT'])
        errors = len(sub_df[sub_df['decision'] == 'ERROR'])
        
        detection_rate = ((flags + rejects) / count) * 100 if count > 0 else 0
        approve_rate = (approves / count) * 100 if count > 0 else 0
        
        print(f"\nPattern: {p.upper()} (N={count})")
        
        if p == 'legitimate':
            print(f"  False Flag Rate (Should be < 15%): {detection_rate:.1f}%")
            print(f"  True Approval Rate: {approve_rate:.1f}%")
        else:
            print(f"  Detection Rate (FLAG/REJECT): {detection_rate:.1f}%")
            print(f"  False Approval Rate (APPROVE): {approve_rate:.1f}%")
            
        if errors > 0:
            print(f"  Errors: {errors}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--iter", type=int, default=20, help="Number of samples per pattern for iteration")
    parser.add_argument("--clean", type=int, default=20, help="Number of clean samples")
    args = parser.parse_args()
    
    # Windows asyncio fix
    if sys.platform == 'win32':
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
        
    asyncio.run(run_evaluation(num_per_pattern=args.iter, clean_samples=args.clean))
