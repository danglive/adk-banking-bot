# callbacks/before_model.py
from google.adk.agents.callback_context import CallbackContext
from google.adk.models.llm_request import LlmRequest
from google.adk.models.llm_response import LlmResponse
from google.genai import types
from typing import Optional, List, Set
import re

class InputGuard:
    """A class containing callback functions to validate user input before it reaches the LLM."""
    
    @staticmethod
    def blocked_keywords_guardrail(
        callback_context: CallbackContext, 
        llm_request: LlmRequest,
        blocked_keywords: Set[str] = None
    ) -> Optional[LlmResponse]:
        """
        Inspects user input for blocked keywords. Blocks LLM call if found.
        
        Args:
            callback_context: Provides access to agent info, session state
            llm_request: Contains the request payload for the LLM
            blocked_keywords: Set of keywords to block. If None, uses default set.
            
        Returns:
            LlmResponse if blocked, None if allowed to proceed
        """
        agent_name = callback_context.agent_name
        print(f"--- Callback: blocked_keywords_guardrail running for agent: {agent_name} ---")
        
        # Default blocked keywords for a banking bot (expand as needed)
        default_blocked_keywords = {
            "PASSWORD", "SSN", "SOCIAL SECURITY", "CREDIT CARD NUMBER", "PIN", 
            "HACK", "EXPLOIT", "BYPASS", "FRAUD", "STEAL", "ILLEGAL"
        }
        
        # Use provided keywords or defaults
        keywords_to_check = blocked_keywords if blocked_keywords else default_blocked_keywords
        
        # Extract the text from the latest user message
        last_user_message_text = ""
        if llm_request.contents:
            # Find the most recent message with role 'user'
            for content in reversed(llm_request.contents):
                if content.role == 'user' and content.parts:
                    if content.parts[0].text:
                        last_user_message_text = content.parts[0].text
                        break
        
        print(f"--- Callback: Inspecting user message for blocked keywords ---")
        
        # Check for any blocked keywords (case insensitive)
        user_message_upper = last_user_message_text.upper()
        found_keywords = [kw for kw in keywords_to_check if kw in user_message_upper]
        
        if found_keywords:
            print(f"--- Callback: Found blocked keywords: {found_keywords}. Blocking LLM call! ---")
            
            # Set a flag in state to record the block event
            callback_context.state["guardrail_blocked_keywords"] = found_keywords
            callback_context.state["blocked_input_count"] = callback_context.state.get("blocked_input_count", 0) + 1
            
            # Create a safe response that doesn't repeat the blocked content
            return LlmResponse(
                content=types.Content(
                    role="model",
                    parts=[types.Part(text=f"I cannot process this request because it contains sensitive information or prohibited terms. For security reasons, please avoid sharing personal identifiable information such as passwords, account numbers, or social security numbers. How can I help you with your banking needs in a secure way?")],
                )
            )
        else:
            print(f"--- Callback: No blocked keywords found. Allowing LLM call for {agent_name}. ---")
            return None  # Allow the request to proceed
    
    @staticmethod
    def pii_detection_guardrail(
        callback_context: CallbackContext, 
        llm_request: LlmRequest
    ) -> Optional[LlmResponse]:
        """
        Inspects user input for patterns that look like PII. Blocks LLM call if found.
        
        Args:
            callback_context: Provides access to agent info, session state
            llm_request: Contains the request payload for the LLM
            
        Returns:
            LlmResponse if blocked, None if allowed to proceed
        """
        agent_name = callback_context.agent_name
        print(f"--- Callback: pii_detection_guardrail running for agent: {agent_name} ---")
        
        # Extract the text from the latest user message
        last_user_message_text = ""
        if llm_request.contents:
            for content in reversed(llm_request.contents):
                if content.role == 'user' and content.parts:
                    if content.parts[0].text:
                        last_user_message_text = content.parts[0].text
                        break
        
        print(f"--- Callback: Checking for PII patterns ---")
        
        # Define regex patterns for common PII
        pii_patterns = {
            "credit_card": r'\b(?:\d{4}[-\s]?){3}\d{4}\b',  # Credit card format: xxxx-xxxx-xxxx-xxxx
            "ssn": r'\b\d{3}[-\s]?\d{2}[-\s]?\d{4}\b',  # SSN format: xxx-xx-xxxx
            "email": r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b',  # Email pattern
            "phone": r'\b(?:\+\d{1,2}\s)?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}\b',  # Phone number patterns
            "account_number": r'\b\d{8,17}\b'  # Generic account number (8-17 digits)
        }
        
        # Check for PII matches
        pii_found = {}
        for pii_type, pattern in pii_patterns.items():
            matches = re.findall(pattern, last_user_message_text)
            if matches:
                pii_found[pii_type] = True
        
        if pii_found:
            print(f"--- Callback: Detected potential PII: {list(pii_found.keys())}. Blocking LLM call! ---")
            
            # Update state to record PII detection
            callback_context.state["guardrail_pii_detected_types"] = list(pii_found.keys())
            callback_context.state["pii_detection_count"] = callback_context.state.get("pii_detection_count", 0) + 1
            
            # Return a warning response without including any detected PII
            return LlmResponse(
                content=types.Content(
                    role="model",
                    parts=[types.Part(text="I noticed what appears to be sensitive personal information in your message. For your security, please don't share personal identifiable information like account numbers, credit card details, social security numbers, or complete contact information. How can I assist you without using this sensitive data?")],
                )
            )
        else:
            print(f"--- Callback: No PII patterns detected. Allowing LLM call. ---")
            return None  # Allow the request to proceed