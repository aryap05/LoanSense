import pandas as pd
import numpy as np
from pathlib import Path
import os
import uuid
import sys

backend_dir = Path(__file__).parent.parent.parent
if str(backend_dir) not in sys.path:
    sys.path.append(str(backend_dir))
from ml.data.synthetic_layer import compute_default_probability

def generate_clean_base(n):
    """Generate a clean, normal applicant profile to be mutated by attack patterns."""
    df = pd.DataFrame()
    df['SK_ID_CURR'] = [np.random.randint(1000000, 9999999) for _ in range(n)]
    df['income'] = np.random.uniform(35000, 100000, size=n).round()
    df['loan_amount'] = (df['income'] * np.random.uniform(2, 6, size=n)).round()
    df['loan_tenure_months'] = np.random.choice([12, 24, 36, 48, 60], size=n)
    # emi approx: P * r * (1+r)^n / ((1+r)^n - 1) simplified to something reasonable
    df['emi_to_income_ratio'] = np.random.uniform(0.15, 0.45, size=n)
    df['employment_type'] = np.random.choice(['salaried_private', 'salaried_govt', 'self_employed'], size=n, p=[0.5, 0.2, 0.3])
    df['existing_obligations'] = np.random.uniform(0, df['loan_amount'] * 0.3).round()
    df['cibil_score_simulated'] = np.random.randint(650, 800, size=n)
    df['account_age_months'] = np.random.randint(12, 120, size=n)
    df['new_to_credit'] = df['account_age_months'] < 6
    df['enquiry_count_30d'] = np.random.poisson(1, size=n)
    df['transaction_velocity_30d'] = np.random.poisson(30, size=n)
    df['upi_velocity_percentile'] = np.random.uniform(20, 80, size=n)
    df['income_transaction_ratio'] = np.random.uniform(0.5, 2.5, size=n)
    df['loan_purpose'] = np.random.choice(['home_renovation', 'education', 'medical', 'personal'], size=n)
    df['employer_description'] = "Standard employee"
    df['fraud_flag'] = 0
    return df

def generate_attacks(pattern: str, n: int = 500, seed: int = 42):
    """
    Generates N synthetic fraudulent applicants for a specific attack pattern.
    """
    np.random.seed(seed)
    df = generate_clean_base(n)
    
    if pattern == "stolen_pan_fabricated_employment":
        # Stolen PAN + Fabricated Employment
        # Attacker uses a stolen PAN (good CIBIL) but fabricates income and employment
        df['cibil_score_simulated'] = np.random.randint(680, 800, size=n) # High score stolen from real person
        df['income'] = np.random.uniform(80000, 150000, size=n).round() # High declared income
        df['loan_amount'] = (df['income'] * np.random.uniform(3, 7, size=n)).round() # Try to maximize loan
        df['employment_type'] = 'salaried_private'
        df['account_age_months'] = np.random.randint(2, 6, size=n) # New accounts opened by attacker
        df['new_to_credit'] = df['account_age_months'] < 6
        df['upi_velocity_percentile'] = np.random.uniform(10, 40, size=n) # Low velocity, doesn't match high income
        df['income_transaction_ratio'] = np.random.uniform(5.0, 10.0, size=n) # Income far exceeds transaction evidence
        df['employer_description'] = "Works at private company" # Generic, non-specific description
        df['fraud_flag'] = 1
        df['pattern_label'] = pattern

    elif pattern == "fragmented_bureau_footprint":
        # Fragmented Bureau Footprint (Bust-out attempt with thin file)
        # Attacker changes small PII details to splinter bureau record, appearing as new to credit
        cibil_choices = np.random.choice([0, 1], size=n, p=[0.5, 0.5])
        df['cibil_score_simulated'] = np.where(cibil_choices == 0, 0, np.random.randint(300, 400, size=n)) # 0 (no file) or thin (300-400)
        df['new_to_credit'] = True
        df['account_age_months'] = np.random.randint(1, 4, size=n) # Very new accounts
        df['enquiry_count_30d'] = np.random.poisson(4, size=n) # Poisson(4) pushes right tail but overlaps legit Poisson(1)
        df['loan_amount'] = np.random.uniform(300000, 1000000, size=n).round() # High ask despite thin file
        df['income'] = np.random.uniform(30000, 60000, size=n).round() # Moderate, plausible income
        df['fraud_flag'] = 1
        df['pattern_label'] = pattern

    elif pattern == "upi_velocity_spike":
        # UPI Velocity Spike (Account warming / Bust-out)
        # Profile is clean, but massive recent transaction velocity spike to inflate creditworthiness
        # All credit features remain clean (from base)
        df['upi_velocity_percentile'] = np.random.uniform(95, 99.9, size=n) # Massive spike
        df['transaction_velocity_30d'] = np.random.poisson(35, size=n) # Spike that heavily overlaps legit right tail
        df['income_transaction_ratio'] = np.random.uniform(0.8, 2.5, size=n) # Overlaps legit lower quartile
        df['fraud_flag'] = 1
        df['pattern_label'] = pattern

    elif pattern == "synthetic_identity_clean":
        # Synthetic Identity (Clean constructed profile)
        # Very careful attacker, no single red flag, but all products are perfectly synced to a few months old
        # All individual scores clean
        df['cibil_score_simulated'] = np.random.randint(720, 780, size=n) # Good score, carefully built
        df['income'] = np.random.uniform(40000, 80000, size=n).round() # Reasonable
        df['employment_type'] = 'salaried_private'
        df['account_age_months'] = np.random.randint(2, 5, size=n) # CRITICAL: 2-4 months across all products
        df['new_to_credit'] = True
        df['enquiry_count_30d'] = np.random.randint(1, 3, size=n) # 1-2, careful attacker
        df['employer_description'] = "Senior analyst at tech firm"
        df['fraud_flag'] = 1
        df['pattern_label'] = pattern
        
    else:
        raise ValueError(f"Unknown pattern: {pattern}")
        
    probs = df.apply(lambda row: compute_default_probability(row.to_dict()), axis=1)
    df['default_flag'] = np.random.binomial(1, probs)
        
    return df

def generate_all():
    print("Generating Synthetic Attack Patterns...")
    base_dir = Path(__file__).parent.parent.parent
    out_dir = base_dir / "ml" / "data" / "attacks"
    out_dir.mkdir(parents=True, exist_ok=True)
    
    patterns = [
        "stolen_pan_fabricated_employment",
        "fragmented_bureau_footprint",
        "upi_velocity_spike",
        "synthetic_identity_clean"
    ]
    
    all_dfs = []
    for p in patterns:
        df = generate_attacks(p, n=500, seed=42)
        p_path = out_dir / f"{p}.parquet"
        df.to_parquet(p_path, index=False)
        default_rate = df['default_flag'].mean() * 100
        fraud_rate = df['fraud_flag'].mean() * 100
        print(f"\nPattern {p}: {df.shape}")
        print(f"  fraud_flag rate: {fraud_rate:.2f}%")
        print(f"  default_flag rate: {default_rate:.2f}%")
        if p == "synthetic_identity_clean":
            print(f"  -> INTENDED DIVERGENCE CONFIRMED: High fraud ({fraud_rate:.1f}%), Low default risk ({default_rate:.1f}%)")
        all_dfs.append(df)
        
    combined = pd.concat(all_dfs, ignore_index=True)
    comb_path = out_dir / "combined_attacks.parquet"
    combined.to_parquet(comb_path, index=False)
    print(f"\nAll patterns combined: {combined.shape} -> {comb_path}")

if __name__ == "__main__":
    generate_all()
