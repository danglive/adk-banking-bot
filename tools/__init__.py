# tools/__init__.py
from .get_balance import get_balance
from .transfer_money import transfer_money
from .finance_advisor import get_financial_advice

# Simple greeting and farewell tools
def say_hello(name: str = "there") -> str:
    """Provides a simple greeting, optionally addressing the user by name.
    
    Args:
        name (str, optional): The name of the person to greet. Defaults to "there".
    
    Returns:
        str: A friendly greeting message.
    """
    print(f"--- Tool: say_hello called with name: {name} ---")
    return f"Hello, {name}! Welcome to your banking assistant. How can I help you today?"

def say_goodbye() -> str:
    """Provides a simple farewell message to conclude the conversation.
    
    Returns:
        str: A friendly farewell message.
    """
    print(f"--- Tool: say_goodbye called ---")
    return "Thank you for using our banking services. Have a great day!"

__all__ = [
    'get_balance',
    'transfer_money',
    'get_financial_advice',
    'say_hello',
    'say_goodbye'
]