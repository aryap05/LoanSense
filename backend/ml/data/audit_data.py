import pandas as pd
import numpy as np
from pathlib import Path
import os
import io

def generate_audit_report():
    base_dir = Path(__file__).parent.parent.parent
    raw_dir = base_dir / "ml" / "data" / "raw"
    
    home_credit_path = raw_dir / "home_credit" / "application_train.csv"
    ieee_transaction_path = raw_dir / "ieee_cis" / "train_transaction.csv"
    ieee_identity_path = raw_dir / "ieee_cis" / "train_identity.csv"
    
    report_path = raw_dir.parent / "audit_report.md"
    
    if not home_credit_path.exists() or not ieee_transaction_path.exists():
        print(f"Error: Datasets not found. Please follow the instructions in {raw_dir}/README.md to download them.")
        return False
        
    print("Loading Home Credit dataset (in chunks)...")
    hc_shape_0 = 0
    hc_shape_1 = 0
    hc_missing = None
    hc_target_counts = pd.Series(dtype=int)
    hc_dtypes = None
    
    for chunk in pd.read_csv(home_credit_path, chunksize=50000):
        hc_shape_0 += len(chunk)
        hc_shape_1 = chunk.shape[1]
        
        if hc_dtypes is None:
            hc_dtypes = chunk.dtypes
            hc_missing = chunk.isnull().sum()
        else:
            hc_missing += chunk.isnull().sum()
            
        if 'TARGET' in chunk:
            hc_target_counts = hc_target_counts.add(chunk['TARGET'].value_counts(), fill_value=0)
            
    print("Loading IEEE-CIS dataset (in chunks)...")
    ieee_shape_0 = 0
    ieee_shape_1 = 0
    ieee_missing = None
    ieee_target_counts = pd.Series(dtype=int)
    ieee_dtypes = None
    
    for chunk in pd.read_csv(ieee_transaction_path, chunksize=50000, low_memory=False):
        ieee_shape_0 += len(chunk)
        ieee_shape_1 = chunk.shape[1]
        
        if ieee_dtypes is None:
            ieee_dtypes = chunk.dtypes
            ieee_missing = chunk.isnull().sum()
        else:
            ieee_missing += chunk.isnull().sum()
            
        if 'isFraud' in chunk:
            ieee_target_counts = ieee_target_counts.add(chunk['isFraud'].value_counts(), fill_value=0)
            
    with open(report_path, "w") as f:
        f.write("# Dataset Audit Report\n\n")
        
        # --- Home Credit ---
        f.write("## 1. Home Credit Default Risk\n\n")
        f.write(f"- **Shape:** {hc_shape_0:,} rows, {hc_shape_1:,} columns\n")
        
        target_pct = (hc_target_counts / hc_shape_0) * 100
        f.write(f"- **Target Distribution (TARGET):** 0 (No Default): {target_pct.get(0, 0):.2f}%, 1 (Default): {target_pct.get(1, 0):.2f}%\n")
        f.write(f"  - *Class Imbalance Ratio:* ~1:{int(target_pct.get(0, 0)/target_pct.get(1, 1)) if target_pct.get(1, 0) > 0 else 'N/A'}\n")
        
        f.write("- **Feature Types:**\n")
        dtypes_counts = hc_dtypes.value_counts()
        for dtype, count in dtypes_counts.items():
            f.write(f"  - {dtype}: {count}\n")
            
        f.write("\n- **Top 20 Columns with Missing Values:**\n")
        missing_pct = (hc_missing / hc_shape_0 * 100).sort_values(ascending=False).head(20)
        for col, pct in missing_pct.items():
            f.write(f"  - `{col}`: {pct:.2f}%\n")
            
        f.write("\n- **Candidates for Unified LoanSense Feature Set:**\n")
        f.write("  - `AMT_CREDIT` (Loan amount)\n")
        f.write("  - `AMT_INCOME_TOTAL` (Income)\n")
        f.write("  - `AMT_ANNUITY` (Used for EMI to income ratio)\n")
        f.write("  - `NAME_INCOME_TYPE` (Employment type)\n")
        f.write("  - `AMT_GOODS_PRICE` (Existing obligations proxy)\n")
        f.write("  - `EXT_SOURCE_2` (CIBIL score simulation)\n")
        f.write("  - `TARGET` (default_flag)\n\n")
        
        # --- IEEE-CIS ---
        f.write("## 2. IEEE-CIS Fraud Detection\n\n")
        f.write(f"- **Shape:** {ieee_shape_0:,} rows, {ieee_shape_1:,} columns\n")
        
        target_pct = (ieee_target_counts / ieee_shape_0) * 100
        f.write(f"- **Target Distribution (isFraud):** 0 (Legit): {target_pct.get(0, 0):.2f}%, 1 (Fraud): {target_pct.get(1, 0):.2f}%\n")
        f.write(f"  - *Class Imbalance Ratio:* ~1:{int(target_pct.get(0, 0)/target_pct.get(1, 1)) if target_pct.get(1, 0) > 0 else 'N/A'}\n")
        
        f.write("- **Feature Types:**\n")
        dtypes_counts = ieee_dtypes.value_counts()
        for dtype, count in dtypes_counts.items():
            f.write(f"  - {dtype}: {count}\n")
            
        f.write("\n- **Top 20 Columns with Missing Values:**\n")
        missing_pct = (ieee_missing / ieee_shape_0 * 100).sort_values(ascending=False).head(20)
        for col, pct in missing_pct.items():
            f.write(f"  - `{col}`: {pct:.2f}%\n")
            
        f.write("\n- **Candidates for Unified LoanSense Feature Set:**\n")
        f.write("  - `TransactionAmt` (Used for transaction velocity proxy)\n")
        f.write("  - `TransactionDT` (Used for time-based velocity features)\n")
        f.write("  - `isFraud` (fraud_flag)\n")
        f.write("  - `card1` to `card6` (Proxy for categorical/card details if needed)\n")
        
    print(f"Audit report generated at {report_path}")
    return True

if __name__ == "__main__":
    generate_audit_report()
