import pytest
from unittest.mock import patch, MagicMock
from app.models.loader import ModelRegistry

@patch('app.models.loader.MlflowClient')
@patch('app.models.loader.mlflow')
def test_fallback_hierarchy(mock_mlflow, mock_client_class):
    mock_client = MagicMock()
    mock_client_class.return_value = mock_client
    
    registry = ModelRegistry(tracking_uri="sqlite:///fake.db")
    
    # Create fake model versions
    v1 = MagicMock(version="1", current_stage="None")
    v2 = MagicMock(version="2", current_stage="Staging")
    v3 = MagicMock(version="3", current_stage="Production")
    
    # Test Production fallback
    mock_client.search_model_versions.return_value = [v1, v2, v3]
    uri, version = registry._get_model_uri_with_fallback("test-model")
    assert version == "3"
    assert uri == "models:/test-model/3"
    
    # Test Staging fallback (no Production)
    mock_client.search_model_versions.return_value = [v1, v2]
    uri, version = registry._get_model_uri_with_fallback("test-model")
    assert version == "2"
    assert uri == "models:/test-model/2"
    
    # Test None fallback (Latest)
    mock_client.search_model_versions.return_value = [v1]
    uri, version = registry._get_model_uri_with_fallback("test-model")
    assert version == "1"
    assert uri == "models:/test-model/1"

@patch('app.models.loader.MlflowClient')
@patch('app.models.loader.mlflow')
def test_load_all_handles_missing(mock_mlflow, mock_client_class):
    mock_client = MagicMock()
    mock_client_class.return_value = mock_client
    
    # Simulate no versions found
    mock_client.search_model_versions.return_value = []
    
    registry = ModelRegistry(tracking_uri="sqlite:///fake.db")
    registry.load_all()
    
    # Should not raise, just set to None
    assert registry.models["credit-risk-scorer"] is None
