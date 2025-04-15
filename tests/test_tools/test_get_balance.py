# tests/test_tools/test_get_balance.py
import pytest
from tools import get_balance
from google.adk.tools.tool_context import ToolContext
from unittest.mock import MagicMock

def test_get_balance_success():
    """Test get_balance tool with valid account."""
    # Arrange
    account_id = "checking"
    
    # Act
    result = get_balance(account_id)
    
    # Assert
    assert result["status"] == "success"
    assert "balance" in result
    assert result["account_type"] == "Checking"
    assert result["currency"] == "USD"

def test_get_balance_invalid_account():
    """Test get_balance tool with invalid account."""
    # Arrange
    account_id = "nonexistent"
    
    # Act
    result = get_balance(account_id)
    
    # Assert
    assert result["status"] == "error"
    assert "error_message" in result
    assert "Unable to find account" in result["error_message"]

def test_get_balance_with_tool_context():
    """Test get_balance tool with ToolContext for state management."""
    # Arrange
    account_id = "savings"
    mock_context = MagicMock(spec=ToolContext)
    mock_context.state = {}
    
    # Act
    result = get_balance(account_id, mock_context)
    
    # Assert
    assert result["status"] == "success"
    assert mock_context.state.get("last_account_checked") == account_id
