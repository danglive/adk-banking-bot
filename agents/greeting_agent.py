# agents/greeting_agent.py
from google.adk.agents import Agent
from google.adk.models.lite_llm import LiteLlm
from typing import Union, Callable


def resolve_model(model_name: Union[str, LiteLlm]) -> Union[str, LiteLlm]:
    if isinstance(model_name, str) and model_name.startswith(("openai/", "anthropic/")):
        return LiteLlm(model=model_name)
    return model_name


def create_greeting_agent(model_name: Union[str, LiteLlm], say_hello_tool: Callable) -> Agent:
    """
    Creates an agent specialized for handling greetings.
    """
    return Agent(
        name="greeting_agent",
        model=resolve_model(model_name),
        description="Handles simple greetings and welcomes using the say_hello tool.",
        instruction="""
You are the Greeting Agent for a banking system.

Your ONLY task is to provide a friendly greeting to the user.
Use the 'say_hello' tool to generate the greeting.
If the user provides their name, make sure to pass it to the tool.
Do not engage in any other banking conversation or tasks.
Keep your responses friendly but professional, as you represent a bank.
        """,
        tools=[say_hello_tool]
    )