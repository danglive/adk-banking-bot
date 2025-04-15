# agents/balance_agent.py
from google.adk.agents import Agent
from google.adk.models.lite_llm import LiteLlm
from typing import Union, Callable


def resolve_model(model_name: Union[str, LiteLlm]) -> Union[str, LiteLlm]:
    if isinstance(model_name, str) and model_name.startswith(("openai/", "anthropic/")):
        return LiteLlm(model=model_name)
    return model_name


def create_balance_agent(model_name: Union[str, LiteLlm], get_balance_tool: Callable) -> Agent:
    """
    Creates an agent specialized for handling balance inquiries.
    """
    return Agent(
        name="balance_agent",
        model=resolve_model(model_name),
        description="Handles account balance inquiries using the get_balance tool.",
        instruction="""
You are the Balance Agent for a banking system.

Your ONLY task is to:
1. Help users check their account balance using the 'get_balance' tool.
2. Interpret the tool's response and present it in a clear, professional manner.
3. If the tool returns an error, explain it politely to the user.

You should collect the account ID if the user hasn't specified it.
If no account is specified, you should first ask which account they want to check.

Always maintain a professional tone as you represent a financial institution.
Never make up account details or balances - only use information returned by the tool.
Remind users to keep their financial information secure.
        """,
        tools=[get_balance_tool]
    )