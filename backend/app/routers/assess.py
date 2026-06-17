import hashlib
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from ..db import database, crud
from ..schemas.applicant import ApplicantInput
from ..models.loader import model_registry

router = APIRouter(tags=["Assess"])

@router.post("/assess")
def assess_applicant(applicant: ApplicantInput, db: Session = Depends(database.get_db)):
    # 1. Hash PAN
    pan_hash = hashlib.sha256(applicant.pan_number.encode()).hexdigest()
    
    # 2. Log assessment started
    # Note: we need applicant UUID. Let's create applicant first.
    app_data = applicant.model_dump(exclude={'pan_number'})
    db_applicant = crud.create_applicant(db, pan_hash, app_data)
    
    crud.create_audit_log(
        db, 
        db_applicant.id, 
        "assessment_started", 
        {"message": "Received application and sanitized inputs."}
    )
    
    # 3. Model Scoring
    # Credit Risk
    try:
        credit_result = model_registry.get_credit_score(app_data)
        crud.create_model_output(
            db, db_applicant.id, "credit-risk-scorer", credit_result["version"], score=credit_result["score"]
        )
    except Exception as e:
        credit_result = {"error": str(e)}

    # Fraud
    try:
        fraud_result = model_registry.get_fraud_signals(app_data)
        crud.create_model_output(
            db, db_applicant.id, "fraud-signal-detector", fraud_result["version"], signals={"is_fraud": fraud_result["is_fraud"]}
        )
    except Exception as e:
        fraud_result = {"error": str(e)}
        
    # Contradiction
    try:
        contra_result = model_registry.get_contradiction_score(app_data)
        crud.create_model_output(
            db, db_applicant.id, "contradiction-detector", contra_result["version"], score=contra_result["contradiction_score"]
        )
    except Exception as e:
        contra_result = {"error": str(e)}

    crud.create_audit_log(
        db, db_applicant.id, "models_executed", 
        {"credit": credit_result, "fraud": fraud_result, "contradiction": contra_result}
    )

    # 4. Agent Verdict (Mock for now since Block 15 Agent is next)
    verdict = crud.create_verdict(
        db, 
        db_applicant.id, 
        decision="MANUAL_REVIEW" if fraud_result.get("is_fraud") else "APPROVED",
        confidence=0.85,
        reason="Agent reasoning not implemented yet. Base scores applied.",
        risk_signals={"fraud": fraud_result.get("is_fraud", False)}
    )

    crud.create_audit_log(db, db_applicant.id, "verdict_issued", {"decision": verdict.decision})

    return {
        "applicant_id": db_applicant.id,
        "status": "success",
        "verdict": {
            "decision": verdict.decision,
            "confidence": verdict.confidence,
            "reason": verdict.reason
        }
    }
