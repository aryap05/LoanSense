from abc import ABC, abstractmethod
from typing import Dict, Any

class BaseContradictionRule(ABC):
    @property
    @abstractmethod
    def severity(self) -> str:
        pass

    @property
    @abstractmethod
    def flag_name(self) -> str:
        pass

    @abstractmethod
    def check(self, applicant_features: Dict[str, Any], credit_risk_score: float, fraud_probability: float) -> str | None:
        """
        Returns the detail message if the rule fires, or None if it does not.
        """
        pass


class HighScoreNewAccountRule(BaseContradictionRule):
    @property
    def severity(self) -> str: 
        return "HIGH"
    
    @property
    def flag_name(self) -> str: 
        return "synthetic_identity_risk"
    
    def check(self, applicant_features: Dict[str, Any], credit_risk_score: float, fraud_probability: float) -> str | None:
        cibil = applicant_features.get('cibil_score_simulated', 0)
        age = applicant_features.get('account_age_months', 999)
        if cibil > 700 and age < 6:
            return f"CIBIL score of {cibil} with account age of {age} months is inconsistent — known synthetic identity pattern"
        return None


class IncomeTransactionMismatchRule(BaseContradictionRule):
    @property
    def severity(self) -> str: 
        return "HIGH"
    
    @property
    def flag_name(self) -> str: 
        return "income_fabrication_risk"
    
    def check(self, applicant_features: Dict[str, Any], credit_risk_score: float, fraud_probability: float) -> str | None:
        ratio = applicant_features.get('income_transaction_ratio', 0)
        if ratio > 5:
            income = applicant_features.get('income', 0)
            expected = int(income * 0.5)
            actual = int(income / ratio) if ratio > 0 else 0
            return f"Declared income implies monthly transactions of ~₹{expected} but observed average is ₹{actual}"
        return None
        

class CreditFraudDivergenceRule(BaseContradictionRule):
    @property
    def severity(self) -> str: 
        return "MEDIUM"
    
    @property
    def flag_name(self) -> str: 
        return "credit_fraud_signal_divergence"
    
    def check(self, applicant_features: Dict[str, Any], credit_risk_score: float, fraud_probability: float) -> str | None:
        if credit_risk_score < 0.25 and fraud_probability > 0.45:
            return "Low credit risk score conflicts with elevated fraud probability — signals warrant joint review"
        return None


class EnquiryBurstThinFileRule(BaseContradictionRule):
    @property
    def severity(self) -> str: 
        return "HIGH"
    
    @property
    def flag_name(self) -> str: 
        return "bust_out_pattern"
    
    def check(self, applicant_features: Dict[str, Any], credit_risk_score: float, fraud_probability: float) -> str | None:
        enquiries = applicant_features.get('enquiry_count_30d', 0)
        new_to_credit = applicant_features.get('new_to_credit', False)
        cibil = applicant_features.get('cibil_score_simulated', 0)
        
        if enquiries > 5 and (new_to_credit or cibil < 400):
            return f"{enquiries} bureau enquiries in 30 days on a thin credit file — known bust-out fraud pattern"
        return None


class CleanProfileVelocityRule(BaseContradictionRule):
    @property
    def severity(self) -> str: 
        return "MEDIUM"
    
    @property
    def flag_name(self) -> str: 
        return "pre_application_velocity_spike"
    
    def check(self, applicant_features: Dict[str, Any], credit_risk_score: float, fraud_probability: float) -> str | None:
        upi = applicant_features.get('upi_velocity_percentile', 0)
        if upi > 92 and credit_risk_score < 0.3 and fraud_probability < 0.3:
            return "Transaction velocity spike detected on otherwise clean profile — consistent with account warming"
        return None


class ContradictionRuleEngine:
    def __init__(self):
        self.rules = [
            HighScoreNewAccountRule(),
            IncomeTransactionMismatchRule(),
            CreditFraudDivergenceRule(),
            EnquiryBurstThinFileRule(),
            CleanProfileVelocityRule()
        ]
        
    def check(self, applicant_features: Dict[str, Any], credit_risk_score: float, fraud_probability: float) -> Dict[str, Any]:
        rule_flags = []
        max_severity_val = 0
        severity_map = {"NONE": 0, "MEDIUM": 1, "HIGH": 2}
        reverse_map = {0: "NONE", 1: "MEDIUM", 2: "HIGH"}
        
        for rule in self.rules:
            detail = rule.check(applicant_features, credit_risk_score, fraud_probability)
            if detail is not None:
                rule_flags.append({
                    "flag": rule.flag_name,
                    "severity": rule.severity,
                    "detail": detail
                })
                max_severity_val = max(max_severity_val, severity_map[rule.severity])
                
        return {
            "rule_flags": rule_flags,
            "rule_flag_count": len(rule_flags),
            "max_severity": reverse_map[max_severity_val],
            "any_high_severity": max_severity_val == 2
        }
