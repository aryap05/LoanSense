import pytest
from uuid import uuid4
from app.agent.tools import execute_tool_call
from app.db import crud
from tests.test_db import db_session, setup_database
from app.models.loader import model_registry

@pytest.fixture(autouse=True)
def mock_registry(monkeypatch):
    monkeypatch.setattr(model_registry, "get_credit_score", lambda x: {"score": 0.25, "version": "1.0"})
    monkeypatch.setattr(model_registry, "get_fraud_signals", lambda x: {"is_fraud": False, "version": "1.0"})
    monkeypatch.setattr(model_registry, "get_contradiction_score", lambda x: {"contradiction_score": 0.1, "version": "1.0"})

def test_execute_tool_call_not_found(db_session):
    # Test applicant not found logic
    random_id = str(uuid4())
    result = execute_tool_call("get_credit_risk_score", random_id, db_session)
    assert "error" in result
    assert "not found" in result["error"]

def test_execute_tool_call_invalid_tool(db_session):
    # Create valid applicant
    app = crud.create_applicant(db_session, "hash", {"income": 50000})
    result = execute_tool_call("invalid_tool_name", str(app.id), db_session)
    assert "error" in result
    assert "Unknown tool name" in result["error"]

def test_execute_tool_call_invalid_uuid(db_session):
    # Test invalid UUID format handling
    result = execute_tool_call("get_credit_risk_score", "not-a-uuid", db_session)
    assert "error" in result
    assert "badly formed hexadecimal UUID string" in result["error"]

def test_execute_tool_call_success(db_session):
    # This requires models to be loaded and DB session
    
    # Use valid raw features that match model schema roughly
    raw_features = {
        'income': 50000, 
        'purpose': 'Personal', 
        'cibil_score_simulated': 750, 
        'loan_amount': 200000, 
        'existing_emi': 5000, 
        'employment_type': 'Salaried', 
        'loan_term_months': 24,
        'emi_to_income_ratio': 0.1,
        'existing_obligations': 0,
        'transaction_velocity_30d': 10,
        'account_age_months': 36,
        'enquiry_count_30d': 1,
        'income_transaction_ratio': 5.0,
        'new_to_credit': False,
        'upi_velocity_percentile': 0.5
    }
    app = crud.create_applicant(db_session, "hash123", raw_features)
    app_id = str(app.id)

    # 1. Test get_credit_risk_score
    res1 = execute_tool_call("get_credit_risk_score", app_id, db_session)
    assert "score" in res1
    assert "version" in res1

    # 2. Test get_fraud_signals
    res2 = execute_tool_call("get_fraud_signals", app_id, db_session)
    assert "is_fraud" in res2
    assert "version" in res2

    # 3. Test get_contradiction_score
    res3 = execute_tool_call("get_contradiction_score", app_id, db_session)
    assert "contradiction_score" in res3
    assert "version" in res3

    # Verify audit logs
    logs = crud.get_audit_logs_by_applicant(db_session, app.id)
    # They are ordered by created_at desc
    assert len(logs) == 3
    for log in logs:
        assert log.event_type == "model_called"
        assert "tool_name" in log.event_data
        assert "model_version" in log.event_data
