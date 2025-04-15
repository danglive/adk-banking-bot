# tools/transfer_money.py
from google.adk.tools.tool_context import ToolContext
from typing import Dict, Any
import time

def transfer_money(
    source_account: str,
    destination_account: str, 
    amount: float,
    tool_context: ToolContext = None
) -> Dict[str, Any]:
    """Transfers money between two accounts.
    
    This tool transfers funds from a source account to a destination account.
    
    Args:
        source_account (str): The account to transfer money from
        destination_account (str): The account to transfer money to
        amount (float): The amount of money to transfer
        tool_context (ToolContext, optional): Provides access to session state and context information
    
    Returns:
        Dict[str, Any]: A dictionary containing the transfer result with keys:
            - status: 'success' or 'error'
            - transaction_id: Unique ID for the transaction (if successful)
            - source_account: The source account (if successful)
            - destination_account: The destination account (if successful)
            - amount: The transferred amount (if successful)
            - new_balance: The new balance in the source account (if successful)
            - timestamp: The time of the transfer (if successful)
            - error_message: Description of the error (if status is 'error')
    """
    print(f"--- Tool: transfer_money called from {source_account} to {destination_account} for ${amount} ---")
    
    # Normalize account identifiers
    source_account_normalized = source_account.lower().replace(" ", "")
    destination_account_normalized = destination_account.lower().replace(" ", "")
    
    # Mock database of account balances (reused from get_balance)
    mock_accounts_db = {
        "checking": {
            "balance": 2547.83,
            "currency": "USD",
            "account_type": "Checking"
        },
        "savings": {
            "balance": 15720.50,
            "currency": "USD",
            "account_type": "Savings"
        },
        "retirement": {
            "balance": 87341.25,
            "currency": "USD",
            "account_type": "401K"
        },
        "external": {
            "balance": 0,  # External account for demo purposes
            "currency": "USD",
            "account_type": "External"
        }
    }
    
    # Check if accounts exist
    if source_account_normalized not in mock_accounts_db:
        return {
            "status": "error",
            "error_message": f"Source account '{source_account}' not found."
        }
    
    if destination_account_normalized not in mock_accounts_db:
        return {
            "status": "error",
            "error_message": f"Destination account '{destination_account}' not found."
        }
    
    # Check if amount is valid
    if amount <= 0:
        return {
            "status": "error",
            "error_message": "Transfer amount must be greater than zero."
        }
    
    # Check if source account has sufficient funds
    source_balance = mock_accounts_db[source_account_normalized]["balance"]
    if source_balance < amount:
        return {
            "status": "error",
            "error_message": f"Insufficient funds in {source_account}. Current balance: ${source_balance:.2f}"
        }
    
    # If we reach here, the transfer can proceed
    new_balance = source_balance - amount
    timestamp = time.time()
    transaction_id = f"TX-{int(timestamp)}"
    
    # Update mock balances (in a real system, this would be a database transaction)
    mock_accounts_db[source_account_normalized]["balance"] = new_balance
    mock_accounts_db[destination_account_normalized]["balance"] += amount
    
    # If tool_context is provided, update transfer history in state
    if tool_context:
        # Get or initialize transfer history
        transfer_history = tool_context.state.get("transfer_history", [])
        
        # Add this transaction to history
        transfer_history.append({
            "transaction_id": transaction_id,
            "source_account": source_account,
            "destination_account": destination_account,
            "amount": amount,
            "timestamp": timestamp
        })
        
        # Update state
        tool_context.state["transfer_history"] = transfer_history
        tool_context.state["last_transaction_id"] = transaction_id
        print(f"--- Tool: Updated transfer history in state. Total transactions: {len(transfer_history)} ---")
    
    # Create success response
    result = {
        "status": "success",
        "transaction_id": transaction_id,
        "source_account": source_account,
        "destination_account": destination_account,
        "amount": amount,
        "new_balance": new_balance,
        "currency": mock_accounts_db[source_account_normalized]["currency"],
        "timestamp": timestamp
    }
    
    print(f"--- Tool: Transfer successful. Transaction ID: {transaction_id} ---")
    return result