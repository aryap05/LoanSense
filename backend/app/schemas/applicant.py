import re
from typing import Optional, Dict, Any
from pydantic import BaseModel, Field, field_validator

def sanitize_text(text: str) -> str:
    """
    Sanitize input text to prevent prompt injection and clean up basic issues.
    """
    if not text:
        return text
        
    # Check for prompt injection patterns
    injection_patterns = [
        r"(?i)ignore previous instructions",
        r"(?i)system\s*:",
        r"(?i)assistant\s*:",
        r"(?i)you are a",
        r"(?i)bypass",
        r"(?i)override",
    ]
    
    for pattern in injection_patterns:
        if re.search(pattern, text):
            raise ValueError(f"Potential prompt injection detected: matching pattern {pattern}")
            
    # Basic cleanup
    text = text.strip()
    return text

class ApplicantInput(BaseModel):
    # Core identifying
    name: str = Field(default="Unknown", min_length=2, max_length=100, description="Applicant full name")
    pan_number: str = Field(..., description="PAN Card number, will be hashed.")
    
    # Financial features
    income: float = Field(..., ge=0, description="Monthly income in INR")
    loan_amount: float = Field(..., gt=0, description="Requested loan amount in INR")
    loan_term_months: int = Field(..., gt=0, le=360, description="Loan term in months")
    
    # Credit History
    cibil_score: int = Field(ge=0, le=900, description="Applicant's credit score (0 if new to credit)")
    existing_emi: float = Field(default=0.0, ge=0, description="Existing EMI obligations")
    account_age_months: int = Field(default=0, ge=0, description="Account age in months")
    enquiry_count_30d: int = Field(default=0, ge=0, description="Hard credit enquiries in last 30 days")
    
    # Fraud signals / Transaction velocity
    upi_velocity_percentile: float = Field(default=50.0, ge=0.0, le=100.0, description="UPI velocity percentile rank")
    transaction_velocity_30d: float = Field(default=0.0, ge=0.0, description="Transaction velocity in last 30 days")
    
    # Demographics / Metadata
    employment_type: str = Field(..., description="E.g., Salaried, Self-Employed")
    employer_name: Optional[str] = Field(None, description="Name of the employer")
    purpose: str = Field(..., description="Purpose of the loan")
    
    # Justification / NLP features
    applicant_notes: Optional[str] = Field(None, description="Free text notes provided by applicant")
    
    @field_validator('applicant_notes', mode='before')
    @classmethod
    def validate_notes(cls, v):
        if v is not None:
            return sanitize_text(v)
        return v
