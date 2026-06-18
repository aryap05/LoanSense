import hashlib
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from ..db import database, crud
from ..schemas.applicant import ApplicantInput
from ..agent.orchestrator import AgentOrchestrator

router = APIRouter(tags=["Assess"])

@router.post("/assess")
async def assess_applicant(applicant: ApplicantInput, db: Session = Depends(database.get_db)):
    # 1. Hash PAN
    pan_hash = hashlib.sha256(applicant.pan_number.encode()).hexdigest()
    
    # 2. Log assessment started and create applicant
    app_data = applicant.model_dump(exclude={'pan_number'})
    db_applicant = crud.create_applicant(db, pan_hash, app_data)
    app_id_str = str(db_applicant.id)
    
    crud.create_audit_log(
        db, 
        db_applicant.id, 
        "assessment_started", 
        {"message": "Received application and sanitized inputs."}
    )
    
    # 3. Format applicant context for the Agent
    applicant_context = f"""
    New loan application:
    Applicant ID: {app_id_str}
    Income: {applicant.income}
    Loan Amount: {applicant.loan_amount}
    Loan Term (Months): {applicant.loan_term_months}
    Purpose: {applicant.purpose}
    Employment Type: {applicant.employment_type}
    CIBIL Score (declared): {applicant.cibil_score}
    Existing EMI: {applicant.existing_emi}
    Notes: {applicant.applicant_notes}
    """

    # 4. Invoke Agent Orchestrator
    orchestrator = AgentOrchestrator(db)
    verdict_json = await orchestrator.assess(app_id_str, applicant_context)

    # 5. Save the Agent's Verdict to the DB
    verdict = crud.create_verdict(
        db, 
        db_applicant.id, 
        decision=verdict_json.get("decision", "FLAG_FOR_REVIEW"),
        confidence=verdict_json.get("confidence", 0.0),
        reason=verdict_json.get("primary_reason", "No reason provided."),
        risk_signals=verdict_json.get("risk_signals", {}),
        rbi_compliance=verdict_json.get("rbi_mapping", {})
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
