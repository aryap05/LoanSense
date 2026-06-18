from sqlalchemy.orm import Session
from uuid import UUID
from app.db import crud
from app.models.loader import model_registry


def execute_tool_call(tool_name: str, applicant_id: str, db: Session) -> dict:
    """
    Dispatcher called when Gemini returns a function_call response.
    Returns the result dict.
    """
    try:
        # Validate UUID
        app_uuid = UUID(applicant_id)
        
        # 1. Fetch applicant
        applicant = crud.get_applicant_by_id(db, app_uuid)
        
        # Explicit None Check
        if applicant is None:
            return {"error": f"Applicant with ID {applicant_id} not found."}
            
        # 2. Extract features
        raw_features = applicant.raw_features
        
        # 3. Route to model
        result = None
        model_name = ""
        score = None
        signals = None
        
        if tool_name == "get_credit_risk_score":
            result = model_registry.get_credit_score(raw_features)
            model_name = "credit-risk-scorer"
            score = result.get("score")
            signals = {"risk_band": result.get("risk_band")}
        elif tool_name == "get_fraud_signals":
            result = model_registry.get_fraud_signals(raw_features)
            model_name = "fraud-signal-detector"
            score = result.get("fraud_probability")
            signals = {"fraud_signals": result.get("fraud_signals"), "is_fraud": result.get("is_fraud")}
        elif tool_name == "get_contradiction_score":
            result = model_registry.get_contradiction_score(raw_features)
            model_name = "contradiction-detector"
            score = result.get("contradiction_score")
            signals = {"anomaly_score": result.get("anomaly_score"), "rule_flags": result.get("rule_flags")}
        else:
            return {"error": f"Unknown tool name: {tool_name}"}
            
        # 3.5 Save Model Output for Drift Detection
        if model_name:
            crud.create_model_output(
                db=db,
                applicant_id=app_uuid,
                model_name=model_name,
                model_version=result.get("version", "unknown"),
                score=score,
                signals=signals
            )
            
        # 4. Audit Log (Success)
        crud.create_audit_log(
            db=db, 
            applicant_id=app_uuid, 
            event_type="model_called", 
            event_data={
                "tool_name": tool_name, 
                "result": result, 
                "model_version": result.get("version")
            }
        )
        return result
        
    except Exception as e:
        # 5. Audit Log (Error)
        try:
            crud.create_audit_log(
                db=db, 
                applicant_id=UUID(applicant_id) if applicant_id else None, 
                event_type="model_called_error", 
                event_data={
                    "tool_name": tool_name, 
                    "error": str(e)
                }
            )
        except Exception:
            # If even the audit log fails (e.g. invalid UUID format breaking the logger), 
            # we just swallow the inner exception to ensure we don't crash the orchestrator
            pass
            
        return {"error": str(e)}
