from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from uuid import UUID
from typing import List
from ..db import database, crud, models

router = APIRouter(tags=["Audit Logs"])

@router.get("/audit/{applicant_id}")
def get_audit_logs(applicant_id: UUID, db: Session = Depends(database.get_db)):
    logs = crud.get_audit_logs_by_applicant(db, applicant_id)
    if not logs:
        raise HTTPException(status_code=404, detail="No audit logs found for this applicant")
    return logs
