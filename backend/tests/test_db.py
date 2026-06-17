import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
import os
from dotenv import load_dotenv
from pathlib import Path

# Need to load the env or use a separate test db. 
# We'll use the local DB but wrapped in a transaction that rolls back.
env_path = Path(__file__).parent.parent / ".env"
load_dotenv(env_path)

DATABASE_URL = os.getenv("DATABASE_URL")
if not DATABASE_URL:
    raise ValueError("DATABASE_URL environment variable is not set")

from app.db.database import Base
from app.db import crud, models

# Setup engine
engine = create_engine(DATABASE_URL)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

@pytest.fixture(scope="session")
def setup_database():
    Base.metadata.create_all(bind=engine)
    yield
    # We won't drop all tables so that the dev db stays intact. 
    # The tests will rollback their transactions instead.

@pytest.fixture
def db_session(setup_database):
    connection = engine.connect()
    transaction = connection.begin()
    session = TestingSessionLocal(bind=connection)
    
    yield session
    
    session.close()
    transaction.rollback()
    connection.close()

def test_create_applicant(db_session):
    applicant = crud.create_applicant(db_session, hashed_pan="hash123", raw_features={"income": 50000})
    assert applicant.id is not None
    assert applicant.hashed_pan == "hash123"
    assert applicant.raw_features["income"] == 50000

def test_create_model_output(db_session):
    applicant = crud.create_applicant(db_session, hashed_pan="hash123", raw_features={})
    output = crud.create_model_output(
        db_session, 
        applicant_id=applicant.id, 
        model_name="credit-risk", 
        model_version="1", 
        score=0.85
    )
    assert output.id is not None
    assert output.applicant_id == applicant.id
    assert output.model_name == "credit-risk"
    assert output.score == 0.85

def test_create_verdict_and_get_recent(db_session):
    applicant = crud.create_applicant(db_session, hashed_pan="hash123", raw_features={})
    verdict = crud.create_verdict(
        db_session, 
        applicant_id=applicant.id, 
        decision="APPROVED", 
        confidence=0.9, 
        reason="Good credit"
    )
    
    assert verdict.id is not None
    
    verdicts = crud.get_recent_verdicts(db_session)
    assert len(verdicts) >= 1
    assert any(v.id == verdict.id for v in verdicts)

def test_create_audit_log(db_session):
    applicant = crud.create_applicant(db_session, hashed_pan="hash123", raw_features={})
    log = crud.create_audit_log(
        db_session, 
        applicant_id=applicant.id, 
        event_type="assessment_started"
    )
    assert log.id is not None
    
    logs = crud.get_audit_logs_by_applicant(db_session, applicant.id)
    assert len(logs) == 1
    assert logs[0].event_type == "assessment_started"
