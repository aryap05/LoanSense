import pandas as pd
import numpy as np
from pathlib import Path
import warnings
from sklearn.metrics import roc_auc_score

warnings.filterwarnings('ignore')

def compute_default_probability(features: dict) -> float:
    cibil = features.get('cibil_score_simulated', 0)
    cibil_normalized = cibil / 900.0 if cibil > 0 else 0.5
    emi_ratio = features.get('emi_to_income_ratio', 0)
    acct_age = features.get('account_age_months', 120)
    enquiries = features.get('enquiry_count_30d', 0)
    
    default_logit = (
        -4.0
        + 2.5 * (1 - cibil_normalized)
        + 1.5 * (emi_ratio > 0.5)
        + 1.0 * (acct_age < 6)
        + 0.8 * (enquiries > 4) / 4
        + np.random.normal(0, 0.5)
    )
    
    default_probability = 1.0 / (1.0 + np.exp(-default_logit))
    return default_probability

def apply_synthetic_layer():
    print("Starting India-Realistic Synthetic Layer application...")
    np.random.seed(42)
    
    base_dir = Path(__file__).parent.parent.parent
    processed_dir = base_dir / "ml" / "data" / "processed"
    
    input_path = processed_dir / "unified_features.parquet"
    if not input_path.exists():
        print(f"Error: {input_path} not found.")
        return
        
    df = pd.read_parquet(input_path)
    n = len(df)
    
    # 1. Income (India realistic right-skewed distribution per month)
    print("Applying realistic income distributions...")
    income_bands = np.random.choice(
        ['low', 'middle', 'upper_middle', 'high'], 
        size=n, 
        p=[0.40, 0.35, 0.20, 0.05]
    )
    
    incomes = np.zeros(n)
    incomes[income_bands == 'low'] = np.random.uniform(15000, 35000, size=(income_bands == 'low').sum())
    incomes[income_bands == 'middle'] = np.random.uniform(35000, 100000, size=(income_bands == 'middle').sum())
    incomes[income_bands == 'upper_middle'] = np.random.uniform(100000, 250000, size=(income_bands == 'upper_middle').sum())
    # For high income, use a pareto distribution scaled to 250k+ to give a realistic right tail
    high_n = (income_bands == 'high').sum()
    incomes[income_bands == 'high'] = 250000 + (np.random.pareto(a=2.5, size=high_n) * 100000)
    
    df['income'] = incomes.round()
    
    # 2. Loan Amount (2x-8x monthly income)
    df['loan_amount'] = (df['income'] * np.random.uniform(2, 8, size=n)).round()
    
    # Update EMI based on derived tenure to match new loan amount and income
    # Ensure emi_to_income_ratio stays somewhat realistic by re-deriving
    df['emi_to_income_ratio'] = np.random.uniform(0.1, 0.6, size=n)
    
    # 3. CIBIL Score Simulated
    cibil_bands = np.random.choice(
        ['no_file', 'poor', 'fair_good', 'excellent'],
        size=n,
        p=[0.20, 0.30, 0.35, 0.15]
    )
    cibil_scores = np.zeros(n, dtype=int)
    cibil_scores[cibil_bands == 'no_file'] = 0
    cibil_scores[cibil_bands == 'poor'] = np.random.randint(300, 600, size=(cibil_bands == 'poor').sum())
    cibil_scores[cibil_bands == 'fair_good'] = np.random.randint(600, 750, size=(cibil_bands == 'fair_good').sum())
    cibil_scores[cibil_bands == 'excellent'] = np.random.randint(750, 901, size=(cibil_bands == 'excellent').sum())
    
    df['cibil_score_simulated'] = cibil_scores
    # If no file, enforce new_to_credit
    df['new_to_credit'] = np.where(df['cibil_score_simulated'] == 0, True, df['new_to_credit'])
    
    # 4. Employment Type
    df['employment_type'] = np.random.choice(
        ['salaried_private', 'salaried_govt', 'self_employed', 'gig_worker'],
        size=n,
        p=[0.35, 0.15, 0.30, 0.20]
    )
    
    # 5. Loan Purpose
    df['loan_purpose'] = np.random.choice(
        ['home_renovation', 'education', 'business_capital', 'medical', 'vehicle', 'personal'],
        size=n
    )
    
    # 6. Employer Description
    emp_descs = {
        'salaried_private': ["Software engineer at mid-size IT firm", "Sales executive at FMCG company", "HR Manager at local branch", "Accountant at private firm", "Data entry operator at BPO"],
        'salaried_govt': ["Clerk at state government office", "Teacher at public school", "Railway employee", "Police constable", "Postal worker"],
        'self_employed': ["Runs a local grocery store", "Independent contractor", "Boutique shop owner", "Hardware store proprietor", "Freelance consultant"],
        'gig_worker': ["Freelance delivery partner", "Rideshare driver", "Freelance graphic designer", "UrbanCompany service professional", "Daily wage laborer"]
    }
    
    def get_desc(emp_type):
        return np.random.choice(emp_descs[emp_type])
        
    df['employer_description'] = df['employment_type'].apply(get_desc)
    
    # 7. Account Age Months
    acct_age_bands = np.random.choice(['new', 'established'], size=n, p=[0.30, 0.70])
    acct_ages = np.zeros(n, dtype=int)
    acct_ages[acct_age_bands == 'new'] = np.random.randint(1, 7, size=(acct_age_bands == 'new').sum())
    acct_ages[acct_age_bands == 'established'] = np.random.randint(12, 121, size=(acct_age_bands == 'established').sum())
    df['account_age_months'] = acct_ages
    
    # Consistency update: new_to_credit should align with account_age_months < 6
    df['new_to_credit'] = df['account_age_months'] < 6
    
    # 8. Re-assign default_flag based on new features
    print("Computing causal default_flag...")
    probs = df.apply(lambda row: compute_default_probability(row.to_dict()), axis=1)
    df['default_flag'] = np.random.binomial(1, probs)

    features_to_check = ['cibil_score_simulated', 'account_age_months', 'enquiry_count_30d', 'income', 'loan_amount', 'emi_to_income_ratio']
    print("\nCorrelations with default_flag:")
    for f in features_to_check:
        if f in df.columns:
            corr = df[f].corr(df['default_flag'])
            print(f"  {f}: {corr:.4f}")
            
    print("\nSingle-Feature ROC-AUC vs default_flag:")
    for f in ['cibil_score_simulated', 'account_age_months', 'enquiry_count_30d']:
        if f in df.columns:
            if f in ['cibil_score_simulated', 'account_age_months']:
                auc = roc_auc_score(df['default_flag'], -df[f])
            else:
                auc = roc_auc_score(df['default_flag'], df[f])
            print(f"  {f}: {auc:.4f}")
    
    # Output to parquet
    out_path = processed_dir / "india_synthetic.parquet"
    df.to_parquet(out_path, index=False)
    
    print("\n--- India-Realistic Synthetic Layer Application Complete ---")
    print(f"Final shape: {df.shape}")
    print(f"Saved to: {out_path}")
    print("\nTarget Distributions:")
    print(f"default_flag:\n{df['default_flag'].value_counts(normalize=True) * 100}")
    print(f"\nfraud_flag:\n{df['fraud_flag'].value_counts(normalize=True) * 100}")
    
    print("\nIncome Distribution Summary:")
    print(df['income'].describe().round())

if __name__ == "__main__":
    apply_synthetic_layer()
