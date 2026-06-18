from sqlalchemy.orm import Session
from uuid import UUID
from typing import Dict, Any, List, Optional
from . import models

def create_applicant(db: Session, hashed_pan: str, raw_features: Dict[str, Any]) -> models.Applicant:
    db_applicant = models.Applicant(hashed_pan=hashed_pan, raw_features=raw_features)
    db.add(db_applicant)
    db.commit()
    db.refresh(db_applicant)
    return db_applicant

def get_applicant_by_id(db: Session, applicant_id: UUID) -> Optional[models.Applicant]:
    return db.query(models.Applicant).filter(models.Applicant.id == applicant_id).first()

def create_model_output(
    db: Session, 
    applicant_id: UUID, 
    model_name: str, 
    model_version: str, 
    score: Optional[float] = None, 
    signals: Optional[Dict[str, Any]] = None
) -> models.ModelOutput:
    db_model_output = models.ModelOutput(
        applicant_id=applicant_id,
        model_name=model_name,
        model_version=model_version,
        score=score,
        signals=signals
    )
    db.add(db_model_output)
    db.commit()
    db.refresh(db_model_output)
    return db_model_output

def create_verdict(
    db: Session, 
    applicant_id: UUID, 
    decision: str, 
    confidence: float, 
    reason: str, 
    risk_signals: Optional[Dict[str, Any]] = None, 
    rbi_compliance: Optional[Dict[str, Any]] = None
) -> models.AgentVerdict:
    db_verdict = models.AgentVerdict(
        applicant_id=applicant_id,
        decision=decision,
        confidence=confidence,
        reason=reason,
        risk_signals=risk_signals,
        rbi_compliance=rbi_compliance
    )
    db.add(db_verdict)
    db.commit()
    db.refresh(db_verdict)
    return db_verdict

def create_audit_log(
    db: Session, 
    applicant_id: UUID, 
    event_type: str, 
    event_data: Optional[Dict[str, Any]] = None
) -> models.AuditLog:
    db_audit_log = models.AuditLog(
        applicant_id=applicant_id,
        event_type=event_type,
        event_data=event_data
    )
    db.add(db_audit_log)
    db.commit()
    db.refresh(db_audit_log)
    return db_audit_log

def get_verdicts_by_applicant(db: Session, applicant_id: UUID) -> List[models.AgentVerdict]:
    return db.query(models.AgentVerdict).filter(models.AgentVerdict.applicant_id == applicant_id).order_by(models.AgentVerdict.created_at.desc()).all()

def get_audit_logs_by_applicant(db: Session, applicant_id: UUID) -> List[models.AuditLog]:
    return db.query(models.AuditLog).filter(models.AuditLog.applicant_id == applicant_id).order_by(models.AuditLog.created_at.desc()).all()

def get_recent_verdicts(db: Session, limit: int = 20) -> List[models.AgentVerdict]:
    return db.query(models.AgentVerdict).order_by(models.AgentVerdict.created_at.desc()).limit(limit).all()
