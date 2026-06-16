import pytest
import sys
import os

# Add backend to path so we can import from ml
sys.path.append(os.path.join(os.path.dirname(__file__), ".."))

from ml.training.contradiction.rules import ContradictionRuleEngine

@pytest.fixture
def engine():
    return ContradictionRuleEngine()

def test_clean_applicant(engine):
    features = {
        'cibil_score_simulated': 750,
        'account_age_months': 24,
        'income': 50000,
        'income_transaction_ratio': 2.0,
        'enquiry_count_30d': 1,
        'new_to_credit': False,
        'upi_velocity_percentile': 50
    }
    result = engine.check(features, credit_risk_score=0.1, fraud_probability=0.1)
    assert result['rule_flag_count'] == 0
    assert result['max_severity'] == "NONE"
    assert not result['any_high_severity']

def test_high_score_new_account(engine):
    features = {
        'cibil_score_simulated': 720,
        'account_age_months': 3
    }
    result = engine.check(features, credit_risk_score=0.2, fraud_probability=0.1)
    assert result['rule_flag_count'] == 1
    assert result['max_severity'] == "HIGH"
    assert result['rule_flags'][0]['flag'] == "synthetic_identity_risk"

def test_income_transaction_mismatch(engine):
    features = {
        'income': 100000,
        'income_transaction_ratio': 6.0
    }
    result = engine.check(features, credit_risk_score=0.2, fraud_probability=0.1)
    assert result['rule_flag_count'] == 1
    assert result['max_severity'] == "HIGH"
    assert result['rule_flags'][0]['flag'] == "income_fabrication_risk"

def test_credit_fraud_divergence(engine):
    features = {}
    result = engine.check(features, credit_risk_score=0.1, fraud_probability=0.8)
    assert result['rule_flag_count'] == 1
    assert result['max_severity'] == "MEDIUM"
    assert result['rule_flags'][0]['flag'] == "credit_fraud_signal_divergence"

def test_enquiry_burst_thin_file(engine):
    features = {
        'enquiry_count_30d': 6,
        'new_to_credit': True,
        'cibil_score_simulated': 0
    }
    result = engine.check(features, credit_risk_score=0.4, fraud_probability=0.1)
    assert result['rule_flag_count'] == 1
    assert result['max_severity'] == "HIGH"
    assert result['rule_flags'][0]['flag'] == "bust_out_pattern"

def test_clean_profile_velocity(engine):
    features = {
        'upi_velocity_percentile': 95
    }
    result = engine.check(features, credit_risk_score=0.2, fraud_probability=0.2)
    assert result['rule_flag_count'] == 1
    assert result['max_severity'] == "MEDIUM"
    assert result['rule_flags'][0]['flag'] == "pre_application_velocity_spike"
