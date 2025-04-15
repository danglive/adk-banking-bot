# tools/get_balance.py
from google.adk.tools.tool_context import ToolContext
from typing import Dict, Any

def get_balance(account_id: str, tool_context: ToolContext = None) -> Dict[str, Any]:
    """Retrieves the current balance for a specified account.
    
    This tool checks and returns the balance of a user's bank account.
    
    Args:
        account_id (str): The account identifier (e.g., "checking", "savings", or account number)
        tool_context (ToolContext, optional): Provides access to session state and context information
    
    Returns:
        Dict[str, Any]: A dictionary containing the balance information with keys:
            - status: 'success' or 'error'
            - balance: The current balance amount (if successful)
            - currency: The currency code (if successful)
            - account_type: The type of account (if successful)
            - error_message: Description of the error (if status is 'error')
    """
    print(f"--- Tool: get_balance called for account: {account_id} ---")
    
    # Normalize account identifier (lowercase, remove spaces)
    account_id_normalized = account_id.lower().replace(" ", "")
    
    # Mock database of account balances
    mock_accounts_db = {
        "checking": {
            "status": "success",
            "balance": 2547.83,
            "currency": "USD",
            "account_type": "Checking"
        },
        "savings": {
            "status": "success",
            "balance": 15720.50,
            "currency": "USD",
            "account_type": "Savings"
        },
        "retirement": {
            "status": "success",
            "balance": 87341.25,
            "currency": "USD",
            "account_type": "401K"
        }
    }
    
    # If tool_context is provided, we can store the last checked account
    if tool_context:
        # Save the last account the user checked
        tool_context.state["last_account_checked"] = account_id
        print(f"--- Tool: Updated state 'last_account_checked': {account_id} ---")
        
        # Use any user preferences from state (example: currency format)
        currency_format = tool_context.state.get("preferred_currency_format", "symbol")
        print(f"--- Tool: Using currency format preference: {currency_format} ---")
    
    # Check if the account exists in our mock database
    if account_id_normalized in mock_accounts_db:
        result = mock_accounts_db[account_id_normalized]
        print(f"--- Tool: Found account. Result: {result} ---")
        return result
    else:
        # Account not found
        error_result = {
            "status": "error",
            "error_message": f"Unable to find account '{account_id}'. Please verify the account name or number and try again."
        }
        print(f"--- Tool: Account '{account_id}' not found. ---")
        return error_result