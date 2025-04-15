# tests/test_api/test_chat_endpoints.py
import pytest
from fastapi.testclient import TestClient
import json

def test_chat_endpoint_success(test_client):
    """Test successful chat interaction with the API."""
    # Arrange
    payload = {
        "message": "What's my checking account balance?",
        "user_id": "test_user",
        "session_id": "test_session"
    }
    
    # Act
    response = test_client.post("/api/chat", json=payload)
    
    # Assert
    assert response.status_code == 200
    data = response.json()
    assert "response_text" in data
    assert data["user_id"] == "test_user"
    assert data["session_id"] == "test_session"
    assert data["input_message"] == payload["message"]

def test_chat_endpoint_invalid_request(test_client):
    """Test chat endpoint with invalid request format."""
    # Arrange
    payload = {
        # Missing required "message" field
        "user_id": "test_user"
    }
    
    # Act
    response = test_client.post("/api/chat", json=payload)
    
    # Assert
    assert response.status_code == 422  # Validation error
