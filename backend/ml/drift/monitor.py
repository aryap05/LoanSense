import json
from pathlib import Path
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
import numpy as np

from app.db import models
from app.db import crud
from .psi import calculate_psi

def run_drift_check(db: Session) -> dict:
    """
    Runs drift detection against the last 7 days of model predictions.
    
    Returns:
        dict: containing 'drift_detected' and 'details'
    """
    base_dir = Path(__file__).parent
    baselines_path = base_dir / "baselines.json"
    
    if not baselines_path.exists():
        return {
            "drift_detected": False,
            "details": {"error": "Baselines file not found. Run generate_baselines.py first."}
        }
        
    with open(baselines_path, "r") as f:
        baselines = json.load(f)
        
    seven_days_ago = datetime.utcnow() - timedelta(days=7)
    
    drift_detected = False
    details = {}
    
    for model_name, baseline_pct in baselines.items():
        # Query model outputs
        outputs = db.query(models.ModelOutput).filter(
            models.ModelOutput.model_name == model_name,
            models.ModelOutput.created_at >= seven_days_ago
        ).order_by(models.ModelOutput.created_at.desc()).all()
        
        if len(outputs) < 50:
            details[model_name] = {"status": "skipped", "reason": f"Insufficient data ({len(outputs)} < 50)"}
            continue
            
        scores = np.array([out.score for out in outputs if out.score is not None])
        if len(scores) < 50:
            details[model_name] = {"status": "skipped", "reason": "Insufficient non-null scores"}
            continue
            
        psi_value = calculate_psi(baseline_pct, scores)
        
        details[model_name] = {
            "status": "monitored",
            "psi": psi_value
        }
        
        if psi_value >= 0.2:
            drift_detected = True
            details[model_name]["alert"] = True
            
            # Log to audit_logs (attach to the most recent applicant in this batch)
            latest_applicant_id = outputs[0].applicant_id
            crud.create_audit_log(
                db=db,
                applicant_id=latest_applicant_id,
                event_type="drift_alert",
                event_data={
                    "model_name": model_name,
                    "psi_value": psi_value,
                    "threshold": 0.2,
                    "recommendation": "Review model performance"
                }
            )
            
    return {
        "drift_detected": drift_detected,
        "details": details
    }
