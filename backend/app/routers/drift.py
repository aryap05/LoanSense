from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.db import database
from ml.drift import monitor

# Global variable to cache the last drift alert status for the health endpoint
last_drift_alert = False

router = APIRouter(tags=["MLOps"])

@router.get("/drift")
def get_drift_status(db: Session = Depends(database.get_db)):
    global last_drift_alert
    try:
        result = monitor.run_drift_check(db)
        
        # Update the global health state
        last_drift_alert = result.get("drift_detected", False)
        
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
