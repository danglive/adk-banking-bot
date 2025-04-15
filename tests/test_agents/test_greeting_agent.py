# tests/test_agents/test_greeting_agent.py
import pytest
from unittest.mock import MagicMock, patch
from google.adk.agents import Agent
from google.adk.models.lite_llm import LiteLlm

from agents.greeting_agent import create_greeting_agent

def test_create_greeting_agent():
    """Test that the greeting agent is created properly."""
    # Arrange
    mock_model = "openai/gpt-4o"
    mock_say_hello_tool = MagicMock()
    mock_say_hello_tool.__name__ = "say_hello"
    
    # Act
    with patch('google.adk.models.lite_llm.LiteLlm') as mock_lite_llm:
        mock_lite_llm_instance = MagicMock()
        mock_lite_llm.return_value = mock_lite_llm_instance
        agent = create_greeting_agent(mock_model, mock_say_hello_tool)
    
    # Assert
    assert agent.name == "greeting_agent"
    assert len(agent.tools) == 1
    assert agent.tools[0] == mock_say_hello_tool
    assert "greeting" in agent.description.lower()

def test_greeting_agent_instruction_content():
    """Test that the greeting agent has appropriate instructions."""
    # Arrange
    mock_model = MagicMock(spec=LiteLlm)
    mock_say_hello_tool = MagicMock()
    
    # Act
    agent = create_greeting_agent(mock_model, mock_say_hello_tool)
    
    # Assert
    instruction = agent.instruction
    assert "ONLY task" in instruction  # Should be focused on a single task
    assert "say_hello" in instruction  # Should mention the tool
    assert "friendly" in instruction.lower()  # Should have tone guidance
