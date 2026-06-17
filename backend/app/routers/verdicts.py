from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from uuid import UUID
from typing import List
from ..db import database, crud, models

router = APIRouter(tags=["Verdicts"])

@router.get("/verdicts/{applicant_id}")
def get_verdicts(applicant_id: UUID, db: Session = Depends(database.get_db)):
    verdicts = crud.get_verdicts_by_applicant(db, applicant_id)
    if not verdicts:
        raise HTTPException(status_code=404, detail="No verdicts found for this applicant")
    return verdicts
