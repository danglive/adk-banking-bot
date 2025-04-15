import pytest
from unittest.mock import MagicMock
from agents.root_agent import create_root_agent
from google.adk.models.lite_llm import LiteLlm
from google.adk.agents import Agent


def test_create_root_agent():
    mock_model = MagicMock(spec=LiteLlm)
    mock_sub_agents = [MagicMock(spec=Agent) for _ in range(2)]
    for agent in mock_sub_agents:
        agent.parent_agent = None
    mock_tools = [MagicMock()]
    mock_before_model_callback = MagicMock()
    mock_before_tool_callback = MagicMock()

    agent = create_root_agent(
        model_name=mock_model,
        sub_agents=mock_sub_agents,
        tools=mock_tools,
        before_model_callback=mock_before_model_callback,
        before_tool_callback=mock_before_tool_callback
    )

    assert agent.name == "banking_root_agent"


def test_root_agent_delegation_configuration():
    mock_model = MagicMock(spec=LiteLlm)
    mock_greeting_agent = MagicMock(spec=Agent)
    mock_farewell_agent = MagicMock(spec=Agent)
    mock_balance_agent = MagicMock(spec=Agent)
    mock_transfer_agent = MagicMock(spec=Agent)

    # Add required names and parent_agent attributes
    for agent, name in zip(
        [mock_greeting_agent, mock_farewell_agent, mock_balance_agent, mock_transfer_agent],
        ["greeting_agent", "farewell_agent", "balance_agent", "transfer_agent"]
    ):
        agent.name = name
        agent.parent_agent = None

    agent = create_root_agent(
        model_name=mock_model,
        sub_agents=[mock_greeting_agent, mock_farewell_agent, mock_balance_agent, mock_transfer_agent],
        tools=[MagicMock()],
        before_model_callback=MagicMock(),
        before_tool_callback=MagicMock()
    )

    assert "delegate to the 'greeting_agent'" in agent.instruction
