# runner.py
import asyncio
import logging
from typing import Dict, Any, Optional, List, Callable, Awaitable, Union, Set
from google.adk.runners import Runner
from google.adk.agents import Agent
from google.adk.sessions import Session, InMemorySessionService 
from google.genai import types
from google.adk.tools.tool_context import ToolContext

# Định nghĩa abstract class SessionService của riêng chúng ta
from abc import ABC, abstractmethod

class SessionService(ABC):
    """Abstract base class for session services."""
    
    @abstractmethod
    def create_session(self, app_name: str, user_id: str, session_id: str, state: Optional[Dict[str, Any]] = None) -> Session:
        """Create a new session."""
        pass
    
    @abstractmethod
    def get_session(self, app_name: str, user_id: str, session_id: str) -> Optional[Session]:
        """Get an existing session."""
        pass
    
    @abstractmethod
    def update_session(self, session: Session) -> None:
        """Update an existing session."""
        pass
    
    @abstractmethod
    def delete_session(self, app_name: str, user_id: str, session_id: str) -> None:
        """Delete a session."""
        pass

from callbacks.before_model import InputGuard
from callbacks.before_tool import ToolGuard
import config
from sessions.session_service import SessionFactory

# Configure logging
logger = logging.getLogger(__name__)

class BankingBotRunner:
    """
    Main runner class for the Banking Bot that orchestrates the agent, 
    session management, and interaction flow.
    """
    
    def __init__(
        self, 
        root_agent: Agent,
        session_service: Optional[SessionService] = None,
        app_name: str = config.APP_NAME,
        before_processing_hooks: Optional[List[Callable]] = None,
        after_response_hooks: Optional[List[Callable]] = None
    ):
        """
        Initialize the Banking Bot Runner.
        
        Args:
            root_agent: The main agent that will handle delegation
            session_service: Service for session management (created if None)
            app_name: Application identifier
            before_processing_hooks: Functions to call before processing input
            after_response_hooks: Functions to call after generating response
        """
        self.root_agent = root_agent
        self.app_name = app_name
        
        # Create session service if not provided
        if session_service is None:
            session_args = {
                "session_ttl": config.SESSION_TTL
            }
            if config.SESSION_TYPE == "sqlite":
                session_args["db_path"] = config.SESSION_DB_PATH
                
            self.session_service = SessionFactory.create_session_service(
                service_type=config.SESSION_TYPE,
                **session_args
            )
            logger.info(f"Created {config.SESSION_TYPE} session service")
        else:
            self.session_service = session_service
            logger.info("Using provided session service")
        
        # Create the ADK Runner
        self.runner = Runner(
            agent=root_agent,
            app_name=app_name,
            session_service=self.session_service
        )
        
        # Hooks for custom pre/post processing
        self.before_processing_hooks = before_processing_hooks or []
        self.after_response_hooks = after_response_hooks or []
        
        logger.info(f"BankingBotRunner initialized with agent: {root_agent.name}")
    
    async def process_message(
        self, 
        user_id: str, 
        session_id: str, 
        message: str,
        context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Process a user message and return the response.
        
        Args:
            user_id: User identifier
            session_id: Session identifier
            message: The user's message text
            context: Additional context information
            
        Returns:
            Dict[str, Any]: Response containing the agent's reply and metadata
        """
        # Ensure session exists
        session = self.session_service.get_session(
            app_name=self.app_name,
            user_id=user_id,
            session_id=session_id
        )
        
        if not session:
            # Create new session
            session = self.session_service.create_session(
                app_name=self.app_name,
                user_id=user_id,
                session_id=session_id,
                state={
                    "user_authenticated": False,
                    "conversation_start_time": asyncio.get_event_loop().time(),
                    "message_count": 0,
                    "context": context or {}
                }
            )
            logger.info(f"Created new session for user {user_id}, session {session_id}")
        
        # Update session with context if provided
        if context:
            session.state["context"] = {**session.state.get("context", {}), **context}
            self.session_service.update_session(session)
        
        # Track message count
        session.state["message_count"] = session.state.get("message_count", 0) + 1
        self.session_service.update_session(session)
        
        # Execute before processing hooks
        for hook in self.before_processing_hooks:
            try:
                await hook(user_id, session_id, message, session.state)
            except Exception as e:
                logger.error(f"Error in before_processing_hook: {e}")
        
        # Prepare user message in ADK format
        content = types.Content(role='user', parts=[types.Part(text=message)])
        
        # Create a response object to collect data
        response_data = {
            "user_id": user_id,
            "session_id": session_id,
            "input_message": message,
            "response_text": None,
            "events": [],
            "state_updates": {},
            "tool_calls": [],
            "delegated_to": None,
            "error": None
        }
        
        try:
            # Process the message through the ADK runner
            async for event in self.runner.run_async(
                user_id=user_id, 
                session_id=session_id, 
                new_message=content
            ):
                # Track all events for monitoring/debugging
                event_info = {
                    "type": type(event).__name__,
                    "is_final": event.is_final_response(),
                    "author": event.author
                }
                response_data["events"].append(event_info)
                
                # Track tool usage
                if hasattr(event, 'tool_name') and event.tool_name:
                    response_data["tool_calls"].append({
                        "tool": event.tool_name,
                        "success": not hasattr(event, 'error') or not event.error
                    })
                
                # Track delegation
                if hasattr(event, 'delegated_agent') and event.delegated_agent:
                    response_data["delegated_to"] = event.delegated_agent
                
                # Extract final response
                if event.is_final_response():
                    if event.content and event.content.parts:
                        response_data["response_text"] = event.content.parts[0].text
                    elif event.actions and event.actions.escalate:
                        response_data["error"] = event.error_message or "Request escalated without specific message."
        
        except Exception as e:
            logger.error(f"Error processing message: {e}")
            response_data["error"] = str(e)
            response_data["response_text"] = "I'm sorry, I encountered an error processing your request. Please try again."
        
        # Get updated session to check state changes
        updated_session = self.session_service.get_session(
            app_name=self.app_name,
            user_id=user_id,
            session_id=session_id
        )
        
        # Track state changes for analytics
        if updated_session:
            response_data["state_updates"] = self._get_state_changes(
                session.state, 
                updated_session.state
            )
        
        # Execute after response hooks
        for hook in self.after_response_hooks:
            try:
                await hook(user_id, session_id, response_data)
            except Exception as e:
                logger.error(f"Error in after_response_hook: {e}")
        
        return response_data
    
    def _get_state_changes(self, old_state: Dict[str, Any], new_state: Dict[str, Any]) -> Dict[str, Any]:
        """
        Identify changes between old and new session state.
        
        Args:
            old_state: The previous session state
            new_state: The current session state
            
        Returns:
            Dict[str, Any]: Dict of changed keys and new values
        """
        changes = {}
        
        # Find keys that were added or modified
        for key, value in new_state.items():
            if key not in old_state or old_state[key] != value:
                changes[key] = value
        
        return changes
    
    async def create_session(
        self, 
        user_id: str, 
        session_id: Optional[str] = None,
        initial_state: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Create a new session for a user.
        
        Args:
            user_id: User identifier
            session_id: Optional session identifier (generated if None)
            initial_state: Initial session state
            
        Returns:
            Dict[str, Any]: Session information
        """
        if session_id is None:
            import uuid
            session_id = str(uuid.uuid4())
        
        default_state = {
            "user_authenticated": False,
            "conversation_start_time": asyncio.get_event_loop().time(),
            "message_count": 0
        }
        
        full_state = {**default_state, **(initial_state or {})}
        
        session = self.session_service.create_session(
            app_name=self.app_name,
            user_id=user_id,
            session_id=session_id,
            state=full_state
        )
        
        logger.info(f"Created session: {self.app_name}/{user_id}/{session_id}")
        
        return {
            "user_id": user_id,
            "session_id": session_id,
            "state": session.state
        }
    
    async def get_session_info(self, user_id: str, session_id: str) -> Optional[Dict[str, Any]]:
        """
        Get information about a session.
        
        Args:
            user_id: User identifier
            session_id: Session identifier
            
        Returns:
            Optional[Dict[str, Any]]: Session information or None if not found
        """
        session = self.session_service.get_session(
            app_name=self.app_name,
            user_id=user_id,
            session_id=session_id
        )
        
        if not session:
            return None
        
        return {
            "user_id": user_id,
            "session_id": session_id,
            "state": session.state,
            "last_update_time": session.last_update_time,
            "message_count": session.state.get("message_count", 0)
        }
    
    async def update_session_state(
        self, 
        user_id: str, 
        session_id: str, 
        state_updates: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        """
        Update session state.
        
        Args:
            user_id: User identifier
            session_id: Session identifier
            state_updates: State key-value pairs to update
            
        Returns:
            Optional[Dict[str, Any]]: Updated session information or None if not found
        """
        session = self.session_service.get_session(
            app_name=self.app_name,
            user_id=user_id,
            session_id=session_id
        )
        
        if not session:
            return None
        
        # Update state
        session.state.update(state_updates)
        self.session_service.update_session(session)
        
        logger.info(f"Updated session state for {user_id}/{session_id}: {state_updates.keys()}")
        
        return {
            "user_id": user_id,
            "session_id": session_id,
            "state": session.state
        }
    
    async def list_user_sessions(self, user_id: str) -> List[Dict[str, Any]]:
        """
        List all sessions for a user.
        
        Args:
            user_id: User identifier
            
        Returns:
            List[Dict[str, Any]]: List of session information
        """
        sessions = self.session_service.list_sessions(
            app_name=self.app_name,
            user_id=user_id
        )
        
        return [
            {
                "user_id": user_id,
                "session_id": session.session_id,
                "state": session.state,
                "last_update_time": session.last_update_time
            }
            for session in sessions
        ]
    
    async def delete_session(self, user_id: str, session_id: str) -> bool:
        """
        Delete a session.
        
        Args:
            user_id: User identifier
            session_id: Session identifier
            
        Returns:
            bool: True if deleted, False if not found
        """
        session = self.session_service.get_session(
            app_name=self.app_name,
            user_id=user_id,
            session_id=session_id
        )
        
        if not session:
            return False
        
        self.session_service.delete_session(
            app_name=self.app_name,
            user_id=user_id,
            session_id=session_id
        )
        
        logger.info(f"Deleted session: {self.app_name}/{user_id}/{session_id}")
        return True


def create_default_runner() -> BankingBotRunner:
    """
    Create the default Banking Bot Runner with all components configured.
    
    Returns:
        BankingBotRunner: Fully configured runner
    """
    from agents import (
        create_root_agent, 
        create_greeting_agent, 
        create_farewell_agent,
        create_balance_agent,
        create_transfer_agent
    )
    from tools import (
        say_hello, 
        say_goodbye, 
        get_balance, 
        transfer_money,
        get_financial_advice
    )
    
    # Create sub-agents
    greeting_agent = create_greeting_agent(config.MODELS["greeting_agent"], say_hello)
    farewell_agent = create_farewell_agent(config.MODELS["farewell_agent"], say_goodbye)
    balance_agent = create_balance_agent(config.MODELS["balance_agent"], get_balance)
    transfer_agent = create_transfer_agent(config.MODELS["transfer_agent"], transfer_money)
    
    # Create callbacks for security
    before_model_callback = lambda ctx, req: InputGuard.blocked_keywords_guardrail(
        ctx, req, set(config.BANKING_CONFIG["blocked_keywords"])
    )
    
    before_tool_callback = lambda tool, args, ctx: ToolGuard.transfer_limit_guardrail(
        tool, args, ctx, config.BANKING_CONFIG["max_transfer_amount"]
    )
    
    # Create root agent with sub-agents and callbacks
    root_agent = create_root_agent(
        model_name=config.MODELS["root_agent"],
        sub_agents=[greeting_agent, farewell_agent, balance_agent, transfer_agent],
        tools=[get_financial_advice],
        before_model_callback=before_model_callback,
        before_tool_callback=before_tool_callback
    )
    
    # Create and return the runner
    return BankingBotRunner(root_agent=root_agent)