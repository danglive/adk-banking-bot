# tests/test_agents/test_farewell_agent.py
import pytest
from unittest.mock import MagicMock, patch
from google.adk.agents import Agent
from google.adk.models.lite_llm import LiteLlm

from agents.farewell_agent import create_farewell_agent

def test_create_farewell_agent():
    """Test that the farewell agent is created properly."""
    # Arrange
    mock_model = "openai/gpt-4o"
    mock_say_goodbye_tool = MagicMock()
    mock_say_goodbye_tool.__name__ = "say_goodbye"
    
    # Act
    with patch('google.adk.models.lite_llm.LiteLlm') as mock_lite_llm:
        mock_lite_llm_instance = MagicMock()
        mock_lite_llm.return_value = mock_lite_llm_instance
        agent = create_farewell_agent(mock_model, mock_say_goodbye_tool)
    
    # Assert
    assert agent.name == "farewell_agent"
    assert len(agent.tools) == 1
    assert agent.tools[0] == mock_say_goodbye_tool
    assert "farewell" in agent.description.lower() or "goodbye" in agent.description.lower()

def test_farewell_agent_instruction_content():
    """Test that the farewell agent has appropriate instructions."""
    # Arrange
    mock_model = MagicMock(spec=LiteLlm)
    mock_say_goodbye_tool = MagicMock()
    
    # Act
    agent = create_farewell_agent(mock_model, mock_say_goodbye_tool)
    
    # Assert
    instruction = agent.instruction
    assert "ONLY task" in instruction  # Should be focused on a single task
    assert "say_goodbye" in instruction  # Should mention the tool
    assert "polite" in instruction.lower()  # Should have tone guidance
