import os
from typing import Dict, Any
import mlflow
from mlflow.tracking import MlflowClient
from pathlib import Path

class ModelRegistry:
    def __init__(self, tracking_uri: str = None):
        if not tracking_uri:
            tracking_uri = os.getenv("MLFLOW_TRACKING_URI")
        if not tracking_uri:
            # Default to local sqlite if not provided
            base_dir = Path(__file__).parent.parent.parent
            tracking_uri = f"sqlite:///{base_dir.as_posix()}/mlruns/mlflow.db"
        
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
                import traceback
                error_msg = f"{type(e).__name__}: {str(e)}\n{traceback.format_exc()}"
                print(f"Warning: Failed to load {model_name}: {error_msg}")
                self.models[model_name] = {"model": None, "error": error_msg}
                
    def _align_features(self, applicant_data: Dict[str, Any]) -> Dict[str, Any]:
        """Maps and derives features from ApplicantInput format to the format required by the ML models."""
        income = float(applicant_data.get('income', 0.0))
        loan_amount = float(applicant_data.get('loan_amount', 0.0))
        
        # Check loan_term_months or loan_tenure_months
        loan_term_months = int(applicant_data.get('loan_term_months', applicant_data.get('loan_tenure_months', 36)))
        
        # Check existing_emi or existing_obligations
        existing_emi = float(applicant_data.get('existing_emi', applicant_data.get('existing_obligations', 0.0)))
        
        # Check cibil_score or cibil_score_simulated
        cibil_score = int(applicant_data.get('cibil_score', applicant_data.get('cibil_score_simulated', 0)))
        
        account_age_months = int(applicant_data.get('account_age_months', 0))
        transaction_velocity_30d = float(applicant_data.get('transaction_velocity_30d', 0.0))
        
        # Derived features
        emi_to_income_ratio = (existing_emi / income) if income > 0 else 0.0
        
        # Handle new_to_credit (account age less than 6 months)
        new_to_credit = applicant_data.get('new_to_credit')
        if new_to_credit is None:
            new_to_credit = 1 if account_age_months < 6 else 0
        else:
            new_to_credit = int(new_to_credit)
            
        # income_transaction_ratio: declared income vs avg transaction
        # If not present, we can estimate it based on velocity (Legitimate baseline: transactions spend 40% of income)
        income_transaction_ratio = applicant_data.get('income_transaction_ratio')
        if income_transaction_ratio is None:
            tx_volume = transaction_velocity_30d * 1500.0  # Assumes ~1500 INR average UPI txn
            income_transaction_ratio = income / (tx_volume + 1.0)
        else:
            income_transaction_ratio = float(income_transaction_ratio)
            
        aligned = {
            'income': income,
            'loan_amount': loan_amount,
            'emi_to_income_ratio': emi_to_income_ratio,
            'employment_type': applicant_data.get('employment_type', 'Salaried'),
            'cibil_score_simulated': cibil_score,
            'loan_tenure_months': float(loan_term_months),
            'existing_obligations': existing_emi,
            'account_age_months': account_age_months,
            'new_to_credit': new_to_credit,
            'transaction_velocity_30d': transaction_velocity_30d,
            'enquiry_count_30d': int(applicant_data.get('enquiry_count_30d', 0)),
            'income_transaction_ratio': income_transaction_ratio,
            'upi_velocity_percentile': float(applicant_data.get('upi_velocity_percentile', 50.0))
        }
        return aligned

    def get_credit_score(self, applicant_data: Dict[str, Any]) -> Dict[str, Any]:
        model_info = self.models.get("credit-risk-scorer")
        if not model_info or not model_info["model"]:
            raise ValueError("Credit risk model is not loaded")
            
        aligned = self._align_features(applicant_data)
        credit_features = [
            'income', 'loan_amount', 'emi_to_income_ratio', 'employment_type', 
            'cibil_score_simulated', 'loan_tenure_months', 'existing_obligations', 
            'account_age_months', 'new_to_credit'
        ]
        feature_dict = {k: aligned[k] for k in credit_features}
        
        import pandas as pd
        df = pd.DataFrame([feature_dict])
        
        try:
            prediction = model_info["model"].predict_proba(df)[0][1]
        except AttributeError:
            prediction = model_info["model"].predict(df)[0]
            
        score = float(prediction)
        risk_band = "Low"
        if score > 0.6:
            risk_band = "High"
        elif score >= 0.3:
            risk_band = "Medium"
            
        return {
            "score": score,
            "risk_band": risk_band,
            "version": model_info["version"]
        }
        
    def get_fraud_signals(self, applicant_data: Dict[str, Any]) -> Dict[str, Any]:
        model_info = self.models.get("fraud-signal-detector")
        if not model_info or not model_info["model"]:
            raise ValueError("Fraud signal model is not loaded")
            
        aligned = self._align_features(applicant_data)
        fraud_features = [
            'transaction_velocity_30d', 'account_age_months', 'enquiry_count_30d', 
            'income_transaction_ratio', 'upi_velocity_percentile', 'new_to_credit', 'loan_amount'
        ]
        feature_dict = {k: aligned[k] for k in fraud_features}
        
        import pandas as pd
        df = pd.DataFrame([feature_dict])
        
        try:
            fraud_probability = float(model_info["model"].predict_proba(df)[0][1])
        except AttributeError:
            fraud_probability = float(model_info["model"].predict(df)[0])
            
        # Layer 1 — Rule-based pre-filter:
        fraud_signals = []
        if aligned['income_transaction_ratio'] > 6.0:
            fraud_signals.append("income_fabrication_risk")
        if aligned['enquiry_count_30d'] > 5:
            fraud_signals.append("high_enquiry_velocity")
        if aligned['account_age_months'] < 6 and aligned['cibil_score_simulated'] > 700:
            fraud_signals.append("new_account_high_score")
        if aligned['upi_velocity_percentile'] > 90.0:
            fraud_signals.append("transaction_velocity_anomaly")
            
        is_fraud = bool(fraud_probability > 0.5)
        elevated_fraud_risk = bool(len(fraud_signals) > 0 and fraud_probability > 0.3)
        
        return {
            "is_fraud": is_fraud,
            "fraud_probability": fraud_probability,
            "fraud_signals": fraud_signals,
            "elevated_fraud_risk": elevated_fraud_risk,
            "version": model_info["version"]
        }
        
    def get_contradiction_score(self, applicant_data: Dict[str, Any]) -> Dict[str, Any]:
        model_info = self.models.get("contradiction-detector")
        if not model_info or not model_info["model"]:
            raise ValueError("Contradiction model is not loaded")
            
        aligned = self._align_features(applicant_data)
        
        # Get dependency scores
        credit_out = self.get_credit_score(aligned)
        fraud_out = self.get_fraud_signals(aligned)
        
        aligned['credit_risk_score'] = credit_out['score']
        aligned['fraud_probability'] = fraud_out['fraud_probability']
        
        import pandas as pd
        df = pd.DataFrame([aligned])
        prediction_df = model_info["model"].predict(df)
        pred_row = prediction_df.iloc[0]
        
        return {
            "contradiction_score": float(pred_row["contradiction_score"]),
            "anomaly_score": float(pred_row["anomaly_score"]),
            "contradiction_type": str(pred_row["contradiction_type"]),
            "rule_flags": list(pred_row["rule_flags"]),
            "version": model_info["version"]
        }

# Global registry instance
model_registry = ModelRegistry()
