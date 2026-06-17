import os
from typing import Dict, Any
import mlflow
from mlflow.tracking import MlflowClient
from pathlib import Path

class ModelRegistry:
    def __init__(self, tracking_uri: str = None):
        if not tracking_uri:
            # Default to local sqlite if not provided
            base_dir = Path(__file__).parent.parent.parent.parent
            tracking_uri = f"sqlite:///{base_dir}/mlruns/mlflow.db"
        
        mlflow.set_tracking_uri(tracking_uri)
        self.client = MlflowClient(tracking_uri=tracking_uri)
        self.models = {}
        
    def _get_model_uri_with_fallback(self, model_name: str) -> str:
        """
        Implements fallback hierarchy:
        1. Production
        2. Staging
        3. None (Latest registered version)
        """
        try:
            versions = self.client.search_model_versions(f"name='{model_name}'")
            if not versions:
                raise ValueError(f"No registered versions found for model '{model_name}'")
            
            # Sort versions descending by version number
            versions = sorted(versions, key=lambda v: int(v.version), reverse=True)
            
            # 1. Check Production
            prod_versions = [v for v in versions if v.current_stage == "Production"]
            if prod_versions:
                return f"models:/{model_name}/{prod_versions[0].version}", prod_versions[0].version
                
            # 2. Check Staging
            staging_versions = [v for v in versions if v.current_stage == "Staging"]
            if staging_versions:
                return f"models:/{model_name}/{staging_versions[0].version}", staging_versions[0].version
                
            # 3. Check None (Latest)
            none_versions = [v for v in versions if v.current_stage == "None"]
            if none_versions:
                return f"models:/{model_name}/{none_versions[0].version}", none_versions[0].version
                
            # Fallback to the absolute latest version if stages are weird
            return f"models:/{model_name}/{versions[0].version}", versions[0].version
            
        except Exception as e:
            raise RuntimeError(f"Error resolving version for {model_name}: {str(e)}")

    def load_all(self):
        """Load all required models into memory."""
        models_to_load = ["credit-risk-scorer", "fraud-signal-detector", "contradiction-detector"]
        
        for model_name in models_to_load:
            try:
                uri, version = self._get_model_uri_with_fallback(model_name)
                print(f"Loading {model_name} (version {version}) from {uri}")
                # We use pyfunc to load models generically
                self.models[model_name] = {
                    "model": mlflow.pyfunc.load_model(uri),
                    "version": version
                }
            except Exception as e:
                print(f"Warning: Failed to load {model_name}: {e}")
                self.models[model_name] = None
                
    def get_credit_score(self, applicant_data: Dict[str, Any]) -> Dict[str, Any]:
        model_info = self.models.get("credit-risk-scorer")
        if not model_info or not model_info["model"]:
            raise ValueError("Credit risk model is not loaded")
            
        import pandas as pd
        df = pd.DataFrame([applicant_data])
        # Assuming the pyfunc model handles preprocessing internally or expects raw dict
        prediction = model_info["model"].predict(df)[0]
        # In scikit-learn/xgboost wrapped in pyfunc, predict might return class or proba.
        # Ideally, we should use predict_proba if available, but pyfunc standardizes to predict.
        # We will assume predict gives the score or we just return it.
        return {
            "score": float(prediction),
            "version": model_info["version"]
        }
        
    def get_fraud_signals(self, applicant_data: Dict[str, Any]) -> Dict[str, Any]:
        model_info = self.models.get("fraud-signal-detector")
        if not model_info or not model_info["model"]:
            raise ValueError("Fraud signal model is not loaded")
            
        import pandas as pd
        df = pd.DataFrame([applicant_data])
        prediction = model_info["model"].predict(df)[0]
        return {
            "is_fraud": bool(prediction),
            "version": model_info["version"]
        }
        
    def get_contradiction_score(self, applicant_data: Dict[str, Any]) -> Dict[str, Any]:
        model_info = self.models.get("contradiction-detector")
        if not model_info or not model_info["model"]:
            raise ValueError("Contradiction model is not loaded")
            
        import pandas as pd
        df = pd.DataFrame([applicant_data])
        prediction = model_info["model"].predict(df)[0]
        return {
            "contradiction_score": float(prediction),
            "version": model_info["version"]
        }

# Global registry instance
model_registry = ModelRegistry()
