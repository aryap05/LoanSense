import sqlite3
import os
from pathlib import Path

def patch_mlflow_db():
    db_path = Path("/app/mlruns/mlflow.db")
    
    if not db_path.exists():
        print(f"Warning: MLflow database not found at {db_path}. Skipping patch.")
        return
        
    print(f"Patching MLflow database at {db_path} to remove absolute Windows paths...")
    
    try:
        conn = sqlite3.connect(db_path)
        cur = conn.cursor()
        
        # We need to replace any string that looks like 'file:D:/LoanSense/backend/mlruns' 
        # or 'file:D:/LoanSense/mlruns' with 'file:///app/mlruns'
        
        replacements = [
            ("file:D:/LoanSense/backend/mlruns", "file:///app/mlruns"),
            ("file:D:/LoanSense/mlruns", "file:///app/mlruns"),
            ("file:d:/LoanSense/backend/mlruns", "file:///app/mlruns"),
            ("file:d:/LoanSense/mlruns", "file:///app/mlruns")
        ]
        
        for old_path, new_path in replacements:
            # Update runs
            cur.execute("UPDATE runs SET artifact_uri = REPLACE(artifact_uri, ?, ?)", (old_path, new_path))
            
            # Update experiments
            cur.execute("UPDATE experiments SET artifact_location = REPLACE(artifact_location, ?, ?)", (old_path, new_path))
            
        conn.commit()
        
        # Verify it worked
        cur.execute("SELECT artifact_uri FROM runs LIMIT 1")
        sample = cur.fetchone()
        if sample:
            print(f"Sample artifact URI after patch: {sample[0]}")
            
        conn.close()
        print("MLflow database successfully patched for Docker environment.")
        
    except Exception as e:
        print(f"Error patching MLflow DB: {e}")
        
if __name__ == "__main__":
    patch_mlflow_db()
