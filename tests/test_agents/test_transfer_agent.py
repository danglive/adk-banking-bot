# tests/test_agents/test_transfer_agent.py
import pytest
from unittest.mock import MagicMock, patch
from google.adk.agents import Agent
from google.adk.models.lite_llm import LiteLlm

from agents.transfer_agent import create_transfer_agent

def test_create_transfer_agent():
    """Test that the transfer agent is created properly."""
    # Arrange
    mock_model = "openai/gpt-4o"
    mock_transfer_money_tool = MagicMock()
    mock_transfer_money_tool.__name__ = "transfer_money"
    
    # Act
    with patch('google.adk.models.lite_llm.LiteLlm') as mock_lite_llm:
        mock_lite_llm_instance = MagicMock()
        mock_lite_llm.return_value = mock_lite_llm_instance
        agent = create_transfer_agent(mock_model, mock_transfer_money_tool)
    
    # Assert
    assert agent.name == "transfer_agent"
    assert len(agent.tools) == 1
    assert agent.tools[0] == mock_transfer_money_tool
    assert "transfer" in agent.description.lower()

def test_transfer_agent_instruction_content():
    """Test that the transfer agent has appropriate instructions."""
    # Arrange
    mock_model = MagicMock(spec=LiteLlm)
    mock_transfer_money_tool = MagicMock()
    
    # Act
    agent = create_transfer_agent(mock_model, mock_transfer_money_tool)
    
    # Assert
    instruction = agent.instruction
    assert "transfer_money" in instruction  # Should mention the tool
    assert "security" in instruction.lower()  # Should emphasize security
    assert "source account" in instruction.lower()  # Should mention required information
    assert "destination account" in instruction.lower()  # Should mention required information
    assert "amount" in instruction.lower()  # Should mention required information
