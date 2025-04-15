# callbacks/before_tool.py
from google.adk.tools.base_tool import BaseTool
from google.adk.tools.tool_context import ToolContext
from typing import Optional, Dict, Any, List, Set

class ToolGuard:
    """A class containing callback functions to validate tool arguments before execution."""
    
    @staticmethod
    def transfer_limit_guardrail(
        tool: BaseTool, 
        args: Dict[str, Any], 
        tool_context: ToolContext,
        transfer_limit: float = 1000.0
    ) -> Optional[Dict]:
        """
        Enforces transfer limits on money transfers.
        
        Args:
            tool: The tool being called
            args: The arguments provided to the tool
            tool_context: Provides access to session state
            transfer_limit: Maximum allowed transfer amount
            
        Returns:
            Dict with error information if blocked, None to allow the tool to execute
        """
        tool_name = tool.name
        agent_name = tool_context.agent_name
        
        print(f"--- Callback: transfer_limit_guardrail running for tool '{tool_name}' in agent '{agent_name}' ---")
        
        # Only apply to the transfer_money tool
        if tool_name != "transfer_money":
            print(f"--- Callback: Not the transfer tool. Allowing execution. ---")
            return None
        
        # Check arguments
        if "amount" in args:
            transfer_amount = args["amount"]
            print(f"--- Callback: Checking transfer amount: ${transfer_amount} against limit: ${transfer_limit} ---")
            
            # Apply transfer limit check
            if transfer_amount > transfer_limit:
                print(f"--- Callback: Transfer amount ${transfer_amount} exceeds limit ${transfer_limit}. Blocking! ---")
                
                # Log to state
                tool_context.state["transfer_limit_exceeded_count"] = tool_context.state.get("transfer_limit_exceeded_count", 0) + 1
                tool_context.state["last_blocked_transfer_amount"] = transfer_amount
                
                # Return error response in the same format expected from the tool
                return {
                    "status": "error",
                    "error_message": f"Transfer amount ${transfer_amount:.2f} exceeds the maximum allowed limit of ${transfer_limit:.2f} per transaction. Please reduce the amount or contact customer service for assistance with larger transfers."
                }
        
        print(f"--- Callback: Transfer amount within limits. Allowing execution. ---")
        return None  # Allow the tool to execute
    
    @staticmethod
    def account_validation_guardrail(
        tool: BaseTool, 
        args: Dict[str, Any], 
        tool_context: ToolContext,
        restricted_accounts: Set[str] = None
    ) -> Optional[Dict]:
        """
        Validates account access based on restrictions.
        
        Args:
            tool: The tool being called
            args: The arguments provided to the tool
            tool_context: Provides access to session state
            restricted_accounts: Set of account names/IDs with restrictions
            
        Returns:
            Dict with error information if blocked, None to allow the tool to execute
        """
        tool_name = tool.name
        print(f"--- Callback: account_validation_guardrail running for tool '{tool_name}' ---")
        
        # Default restricted accounts
        default_restricted = {"business", "corporate", "trust", "minor", "deceased"}
        accounts_to_check = restricted_accounts if restricted_accounts else default_restricted
        
        # Apply to balance checks and transfers
        if tool_name in ["get_balance", "transfer_money"]:
            # For get_balance, check the account_id
            if tool_name == "get_balance" and "account_id" in args:
                account = args["account_id"].lower()
                if any(restricted in account for restricted in accounts_to_check):
                    print(f"--- Callback: Restricted account '{account}' detected. Blocking access. ---")
                    
                    # Log to state
                    tool_context.state["restricted_account_access_attempt"] = account
                    
                    return {
                        "status": "error",
                        "error_message": f"Access to this account type requires additional verification. Please contact customer service or visit a branch."
                    }
            
            # For transfer_money, check source and destination
            elif tool_name == "transfer_money":
                source = args.get("source_account", "").lower()
                destination = args.get("destination_account", "").lower()
                
                # Check if either account is restricted
                restricted_source = any(restricted in source for restricted in accounts_to_check)
                restricted_dest = any(restricted in destination for restricted in accounts_to_check)
                
                if restricted_source or restricted_dest:
                    print(f"--- Callback: Restricted account detected in transfer. Blocking. ---")
                    
                    # Log to state
                    tool_context.state["restricted_transfer_attempt"] = {
                        "source": source if restricted_source else None,
                        "destination": destination if restricted_dest else None
                    }
                    
                    return {
                        "status": "error",
                        "error_message": f"This transfer involves a restricted account type that requires additional verification. Please contact customer service."
                    }
        
        print(f"--- Callback: No account restrictions found. Allowing tool execution. ---")
        return None  # Allow the tool to execute
    
    @staticmethod
    def authentication_guardrail(
        tool: BaseTool, 
        args: Dict[str, Any], 
        tool_context: ToolContext
    ) -> Optional[Dict]:
        """
        Checks if user is authenticated for sensitive operations.
        
        Args:
            tool: The tool being called
            args: The arguments provided to the tool
            tool_context: Provides access to session state
            
        Returns:
            Dict with error information if blocked, None to allow the tool to execute
        """
        tool_name = tool.name
        print(f"--- Callback: authentication_guardrail for tool '{tool_name}' ---")
        
        # Define which tools require authentication
        sensitive_tools = {"transfer_money", "get_balance"}
        
        if tool_name in sensitive_tools:
            # Check authentication status in session state
            is_authenticated = tool_context.state.get("user_authenticated", False)
            print(f"--- Callback: Authentication check for sensitive tool. Status: {is_authenticated} ---")
            
            if not is_authenticated:
                print(f"--- Callback: User not authenticated for sensitive operation. Blocking. ---")
                
                # Update state to recommend authentication
                tool_context.state["auth_required_count"] = tool_context.state.get("auth_required_count", 0) + 1
                
                return {
                    "status": "error",
                    "error_message": "This operation requires authentication. Please log in to your account or verify your identity before proceeding."
                }
        
        print(f"--- Callback: Authentication check passed or not required. Allowing tool execution. ---")
        return None  # Allow the tool to execute