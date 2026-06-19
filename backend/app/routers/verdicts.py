from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from uuid import UUID
from typing import List
from ..db import database, crud, models

router = APIRouter(tags=["Verdicts"])

@router.get("/verdicts/recent")
def get_recent_assessments(limit: int = 5, db: Session = Depends(database.get_db)):
    verdicts = crud.get_recent_verdicts(db, limit)
    result = []
    for v in verdicts:
        applicant = crud.get_applicant_by_id(db, v.applicant_id)
        name = applicant.raw_features.get("name", "Unknown") if applicant else "Unknown"
        result.append({
            "applicant_id": v.applicant_id,
            "name": name,
            "decision": v.decision,
            "created_at": v.created_at
        })
    return result

@router.get("/verdicts/{applicant_id}")
def get_verdicts(applicant_id: UUID, db: Session = Depends(database.get_db)):
    applicant = crud.get_applicant_by_id(db, applicant_id)
    if not applicant:
        raise HTTPException(status_code=404, detail="Applicant not found")
        
    verdicts = crud.get_verdicts_by_applicant(db, applicant_id)
    if not verdicts:
        raise HTTPException(status_code=404, detail="No verdicts found for this applicant")
        
    latest_verdict = verdicts[0]
    
    # Format the payload exactly as the frontend expects
    return {
        "decision": latest_verdict.decision,
        "confidence_score": latest_verdict.confidence,
        "reasons": [latest_verdict.reason] if latest_verdict.reason else [],
        "rbi_flags": list(latest_verdict.rbi_compliance.values()) if latest_verdict.rbi_compliance else [],
        "contradiction_detected": latest_verdict.risk_signals.get("contradiction_score", 0) > 0.5 if latest_verdict.risk_signals else False,
        "contradiction_score": latest_verdict.risk_signals.get("contradiction_score", 0) if latest_verdict.risk_signals else 0.0,
        "name": applicant.raw_features.get("name", "Unknown"),
        "pan_hash": applicant.hashed_pan
    }
