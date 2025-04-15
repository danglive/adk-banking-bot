# agents/farewell_agent.py
from google.adk.agents import Agent
from google.adk.models.lite_llm import LiteLlm
from typing import Union, Callable


def resolve_model(model_name: Union[str, LiteLlm]) -> Union[str, LiteLlm]:
    if isinstance(model_name, str) and model_name.startswith(("openai/", "anthropic/")):
        return LiteLlm(model=model_name)
    return model_name


def create_farewell_agent(model_name: Union[str, LiteLlm], say_goodbye_tool: Callable) -> Agent:
    """
    Create an agent that handles farewells.
    """
    return Agent(
        name="farewell_agent",
        model=resolve_model(model_name),
        description="Sends polite and professional farewells to users.",
        instruction="""
You are the Farewell Agent in a banking assistant system.

Your ONLY task is to:
- Say goodbye politely.
- Thank the user for using the service.
- Offer assistance if needed before closing.
- Maintain a professional and respectful tone.
Use the 'say_goodbye' tool to execute your task.
        """,
        tools=[say_goodbye_tool],
    )