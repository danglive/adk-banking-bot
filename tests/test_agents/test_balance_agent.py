# tests/test_agents/test_balance_agent.py
import pytest
from unittest.mock import MagicMock, patch
from google.adk.agents import Agent
from google.adk.models.lite_llm import LiteLlm

from agents.balance_agent import create_balance_agent

def test_create_balance_agent():
    """Test that the balance agent is created properly."""
    # Arrange
    mock_model = "openai/gpt-4o"
    mock_get_balance_tool = MagicMock()
    mock_get_balance_tool.__name__ = "get_balance"
    
    # Act
    with patch('google.adk.models.lite_llm.LiteLlm') as mock_lite_llm:
        mock_lite_llm_instance = MagicMock()
        mock_lite_llm.return_value = mock_lite_llm_instance
        agent = create_balance_agent(mock_model, mock_get_balance_tool)
    
    # Assert
    assert agent.name == "balance_agent"
    assert len(agent.tools) == 1
    assert agent.tools[0] == mock_get_balance_tool
    assert "balance" in agent.description.lower()

def test_balance_agent_instruction_content():
    """Test that the balance agent has appropriate instructions."""
    # Arrange
    mock_model = MagicMock(spec=LiteLlm)
    mock_get_balance_tool = MagicMock()
    
    # Act
    agent = create_balance_agent(mock_model, mock_get_balance_tool)
    
    # Assert
    instruction = agent.instruction
    assert "get_balance" in instruction  # Should mention the tool
    assert "account" in instruction.lower()  # Should mention accounts
    assert "professional" in instruction.lower()  # Should have tone guidance
