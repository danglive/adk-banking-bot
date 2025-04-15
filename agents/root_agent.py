# agents/root_agent.py
from google.adk.agents import Agent
from google.adk.models.lite_llm import LiteLlm
from typing import Union, List, Callable


def create_root_agent(
    model_name: Union[str, LiteLlm],
    sub_agents: List[Agent],
    tools: List[Callable],
    before_model_callback: Callable,
    before_tool_callback: Callable
) -> Agent:
    """
    Creates the main Banking Root Agent that analyzes intent and delegates to sub-agents.
    """
    model = LiteLlm(model=model_name) if isinstance(model_name, str) and model_name.startswith(("openai/", "anthropic/")) else model_name

    return Agent(
        name="banking_root_agent",
        model=model,
        description="Main banking agent that handles financial requests and delegates to specialists.",
        instruction="""
You are a helpful banking assistant. Your role is to:

1. Analyze the user's request and determine the appropriate action.
2. For simple greetings (hello, hi), delegate to the 'greeting_agent'.
3. For farewells (goodbye, bye), delegate to the 'farewell_agent'.
4. For balance inquiries (check balance, how much money, account balance), delegate to the 'balance_agent'.
5. For transfers (send money, transfer funds), delegate to the 'transfer_agent'.
6. For financial advice questions, use your knowledge to provide general guidance.

Always be professional, courteous, and security-conscious. Never share account details 
with unauthorized users. For sensitive operations, ensure proper verification.
        """,
        tools=tools,
        sub_agents=sub_agents,
        output_key="last_response",
        before_model_callback=before_model_callback,
        before_tool_callback=before_tool_callback
    )