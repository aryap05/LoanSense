import pytest
import json
from unittest.mock import patch, MagicMock, AsyncMock
from uuid import uuid4
import os
from app.agent.orchestrator import AgentOrchestrator
from app.db import crud
from tests.test_db import db_session, setup_database
from app.models.loader import model_registry
import asyncio

@pytest.fixture(autouse=True)
def set_env_vars():
    os.environ["GROQ_API_KEY"] = "fake-key"
    yield
    os.environ.pop("GROQ_API_KEY", None)

@pytest.fixture
def mock_httpx_post():
    with patch("app.agent.orchestrator.httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post:
        yield mock_post

def make_mock_tool_response(tool_name, args):
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = {
        "choices": [{
            "message": {
                "role": "assistant",
                "content": None,
                "tool_calls": [{
                    "id": f"call_{uuid4().hex[:6]}",
                    "type": "function",
                    "function": {
                        "name": tool_name,
                        "arguments": json.dumps(args)
                    }
                }]
            }
        }]
    }
    return mock_resp

def make_mock_final_response(decision, confidence, primary_reason):
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = {
        "choices": [{
            "message": {
                "role": "assistant",
                "content": json.dumps({
                    "decision": decision,
                    "confidence": confidence,
                    "primary_reason": primary_reason,
                    "risk_signals": {"fraud": False, "other_flags": []},
                    "rbi_mapping": {"section": "None"},
                    "what_would_change": "Nothing"
                })
            }
        }]
    }
    return mock_resp

# Test 1: Stolen PAN (Fabricated Employment)
def test_agent_stolen_pan_fabricated_employment(db_session, mock_httpx_post, monkeypatch):
    monkeypatch.setattr(model_registry, "get_credit_score", lambda x: {"score": 0.2, "version": "1.0"})
    monkeypatch.setattr(model_registry, "get_fraud_signals", lambda x: {"is_fraud": True, "fraud_probability": 0.9, "signals": ["income_fabrication_risk"], "version": "1.0"})
    monkeypatch.setattr(model_registry, "get_contradiction_score", lambda x: {"contradiction_score": 0.2, "version": "1.0"})

    app = crud.create_applicant(db_session, "hash_stolen", {"income": 80000})
    app_id = str(app.id)

    mock_httpx_post.side_effect = [
        make_mock_tool_response("get_fraud_signals", {"applicant_id": app_id}),
        make_mock_final_response("REJECT", 0.95, "Fabricated employment detected")
    ]

    orchestrator = AgentOrchestrator(db_session)
    result = asyncio.run(orchestrator.assess(app_id, "applicant context"))

    assert result["decision"] == "REJECT"

# Test 2: Fragmented Bureau Footprint
def test_agent_fragmented_bureau_footprint(db_session, mock_httpx_post, monkeypatch):
    monkeypatch.setattr(model_registry, "get_credit_score", lambda x: {"score": 0.8, "version": "1.0"})
    monkeypatch.setattr(model_registry, "get_fraud_signals", lambda x: {"is_fraud": False, "version": "1.0"})
    monkeypatch.setattr(model_registry, "get_contradiction_score", lambda x: {"contradiction_score": 0.3, "version": "1.0"})

    app = crud.create_applicant(db_session, "hash_frag", {"income": 40000})
    app_id = str(app.id)

    mock_httpx_post.side_effect = [
        make_mock_tool_response("get_credit_risk_score", {"applicant_id": app_id}),
        make_mock_final_response("REJECT", 0.9, "High credit risk due to fragmented footprint")
    ]

    orchestrator = AgentOrchestrator(db_session)
    result = asyncio.run(orchestrator.assess(app_id, "applicant context"))

    assert result["decision"] == "REJECT"

# Test 3: UPI Velocity Spike
def test_agent_upi_velocity_spike(db_session, mock_httpx_post, monkeypatch):
    monkeypatch.setattr(model_registry, "get_credit_score", lambda x: {"score": 0.4, "version": "1.0"})
    monkeypatch.setattr(model_registry, "get_fraud_signals", lambda x: {"is_fraud": True, "signals": ["upi_velocity_spike"], "version": "1.0"})
    monkeypatch.setattr(model_registry, "get_contradiction_score", lambda x: {"contradiction_score": 0.4, "version": "1.0"})

    app = crud.create_applicant(db_session, "hash_upi", {"income": 50000})
    app_id = str(app.id)

    mock_httpx_post.side_effect = [
        make_mock_tool_response("get_fraud_signals", {"applicant_id": app_id}),
        make_mock_final_response("FLAG_FOR_REVIEW", 0.85, "UPI velocity spike detected")
    ]

    orchestrator = AgentOrchestrator(db_session)
    result = asyncio.run(orchestrator.assess(app_id, "applicant context"))

    assert result["decision"] == "FLAG_FOR_REVIEW"

# Test 4: Synthetic Identity Clean (Triggers Contradiction Safety Override)
def test_agent_synthetic_identity_contradiction_override(db_session, mock_httpx_post, monkeypatch):
    monkeypatch.setattr(model_registry, "get_credit_score", lambda x: {"score": 0.1, "version": "1.0"})
    monkeypatch.setattr(model_registry, "get_fraud_signals", lambda x: {"is_fraud": False, "version": "1.0"})
    
    # Explicitly feed contradiction_score=0.7 to test safety override
    monkeypatch.setattr(model_registry, "get_contradiction_score", lambda x: {"contradiction_score": 0.7, "version": "1.0"})
    
    app = crud.create_applicant(db_session, "hash_syn", {"income": 90000})
    app_id = str(app.id)

    # LLM incorrectly tries to APPROVE the applicant despite the 0.7 contradiction score
    mock_httpx_post.side_effect = [
        make_mock_tool_response("get_contradiction_score", {"applicant_id": app_id}),
        make_mock_final_response("APPROVE", 0.95, "Applicant looks perfect, approving.")
    ]

    orchestrator = AgentOrchestrator(db_session)
    result = asyncio.run(orchestrator.assess(app_id, "applicant context"))

    # Assert the hard rule kicks in: decision != "APPROVE"
    assert result["decision"] != "APPROVE"
    assert result["decision"] == "FLAG_FOR_REVIEW"
    assert "OVERRIDE" in result["primary_reason"]
    
    logs = crud.get_audit_logs_by_applicant(db_session, app.id)
    override_logs = [log for log in logs if log.event_type == "verdict_override"]
    assert len(override_logs) == 1
    assert override_logs[0].event_data["contradiction_score"] == 0.7

# Test 5: Clean Applicant
def test_agent_clean_applicant(db_session, mock_httpx_post, monkeypatch):
    monkeypatch.setattr(model_registry, "get_credit_score", lambda x: {"score": 0.1, "version": "1.0"})
    monkeypatch.setattr(model_registry, "get_fraud_signals", lambda x: {"is_fraud": False, "version": "1.0"})
    monkeypatch.setattr(model_registry, "get_contradiction_score", lambda x: {"contradiction_score": 0.1, "version": "1.0"})
    
    app = crud.create_applicant(db_session, "hash_clean", {"income": 60000})
    app_id = str(app.id)

    mock_httpx_post.side_effect = [
        make_mock_tool_response("get_credit_risk_score", {"applicant_id": app_id}),
        make_mock_final_response("APPROVE", 0.95, "Clean applicant")
    ]

    orchestrator = AgentOrchestrator(db_session)
    result = asyncio.run(orchestrator.assess(app_id, "applicant context"))

    assert result["decision"] == "APPROVE"
    
def test_agent_orchestrator_fallback_on_error(db_session, mock_httpx_post):
    app = crud.create_applicant(db_session, "hash_err", {"income": 50000})
    app_id = str(app.id)

    mock_resp_1 = MagicMock()
    mock_resp_1.status_code = 500
    mock_resp_1.text = "Internal Server Error"
    
    mock_httpx_post.return_value = mock_resp_1

    orchestrator = AgentOrchestrator(db_session)
    result = asyncio.run(orchestrator.assess(app_id, "applicant context"))

    assert result["decision"] == "FLAG_FOR_REVIEW"
    assert result["confidence"] == 0.0
    assert "SYSTEM FALLBACK" in result["primary_reason"]

