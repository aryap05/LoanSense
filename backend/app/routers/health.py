from fastapi import APIRouter
from ..models.loader import model_registry

router = APIRouter(tags=["Health"])

@router.get("/health")
def health_check():
    # Check DB could be added here, but for now just app & models
    models_status = {
        model_name: "loaded" if info and info.get("model") else (info.get("error") if info and info.get("error") else "not_loaded")
        for model_name, info in model_registry.models.items()
    }
    
    from . import drift
    
    return {
        "status": "healthy",
        "models": {
            "loaded_models": sum(1 for status in models_status.values() if status == "loaded"),
            "distribution_drift_detected": drift.last_drift_alert,
            "details": models_status
        }
    }
