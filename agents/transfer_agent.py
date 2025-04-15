# agents/transfer_agent.py
from google.adk.agents import Agent
from google.adk.models.lite_llm import LiteLlm
from typing import Union, Callable


def resolve_model(model_name: Union[str, LiteLlm]) -> Union[str, LiteLlm]:
    if isinstance(model_name, str) and model_name.startswith(("openai/", "anthropic/")):
        return LiteLlm(model=model_name)
    return model_name


def create_transfer_agent(model_name: Union[str, LiteLlm], transfer_money_tool: Callable) -> Agent:
    """
    Creates an agent specialized for handling money transfers.
    """
    return Agent(
        name="transfer_agent",
        model=resolve_model(model_name),
        description="Handles money transfers between accounts using the transfer_money tool.",
        instruction="""
You are the Transfer Agent for a banking system.

Your ONLY task is to:
1. Help users transfer money between accounts using the 'transfer_money' tool.
2. Ensure you collect all necessary information: source account, destination account, and amount.
3. Confirm the details before executing the transfer.
4. Interpret the tool's response and present it clearly to the user.

Important security guidelines:
- Always verify that the user has provided all required information.
- Confirm the transfer amount and destination before executing.
- If the tool returns an error (insufficient funds, invalid account), explain it clearly.
- Never proceed with transfers if any information is missing or unclear.
- Be vigilant about potential fraud indicators and escalate if needed.

Maintain a professional, security-focused tone at all times.
        """,
        tools=[transfer_money_tool]
    )