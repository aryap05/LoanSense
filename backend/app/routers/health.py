from fastapi import APIRouter
from ..models.loader import model_registry

router = APIRouter(tags=["Health"])

@router.get("/health")
def health_check():
    # Check DB could be added here, but for now just app & models
    models_status = {
        model_name: "loaded" if info and info.get("model") else "not_loaded"
        for model_name, info in model_registry.models.items()
    }
    
    return {
        "status": "healthy",
        "models": models_status
    }
