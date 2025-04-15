# tests/conftest.py
import pytest
import os
import asyncio
from unittest.mock import MagicMock, patch
from fastapi.testclient import TestClient
import tempfile
import sys

# Add project root to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# Định nghĩa SessionService trước khi import
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, List

class SessionService(ABC):
    """Abstract base class for session services."""
    @abstractmethod
    def create_session(self, app_name: str, user_id: str, session_id: str, state: Optional[Dict[str, Any]] = None):
        pass
    
    @abstractmethod
    def get_session(self, app_name: str, user_id: str, session_id: str):
        pass
    
    @abstractmethod
    def update_session(self, session):
        pass
    
    @abstractmethod
    def delete_session(self, app_name: str, user_id: str, session_id: str):
        pass

import config

@pytest.fixture(scope="session", autouse=True)
def mock_dependencies():
    """Patch các dependencies cần thiết cho toàn bộ test suite."""
    mods = {}
    
    # Patch Session và InMemorySessionService
    session_mod = MagicMock()
    session_class = MagicMock()
    inmemory_service_class = MagicMock()
    session_mod.Session = session_class
    session_mod.InMemorySessionService = inmemory_service_class
    mods["google.adk.sessions"] = session_mod
    
    with patch.dict("sys.modules", mods):
        yield

# Patch SessionService

from app import app
from runner import BankingBotRunner, create_default_runner
from agents import create_root_agent, create_greeting_agent, create_farewell_agent, create_balance_agent, create_transfer_agent
from tools import get_balance, transfer_money, get_financial_advice, say_hello, say_goodbye
from sessions.session_service import EnhancedInMemorySessionService


@pytest.fixture
def mock_app():
    return MagicMock()

# Create a test client
@pytest.fixture
def test_client(mock_app):
    return TestClient(mock_app)

# Override environment settings for testing
os.environ["SESSION_TYPE"] = "memory"
os.environ["APP_NAME"] = "banking_bot_test"

# Create a test client for FastAPI
@pytest.fixture
def test_client():
    return TestClient(app)

# Mock LLM for testing
@pytest.fixture
def mock_llm():
    with patch('google.adk.models.lite_llm.LiteLlm') as mock:
        # Configure mock to return predictable responses
        mock_instance = MagicMock()
        mock.return_value = mock_instance
        
        # Set up the mock to simulate LLM responses
        def generate_response(prompt, **kwargs):
            # Simulate different responses based on prompt content
            if "greeting" in prompt.lower():
                return "Hello! How can I help you with your banking needs today?"
            elif "balance" in prompt.lower():
                return "Your account balance is $2,547.83."
            elif "transfer" in prompt.lower():
                return "I've successfully transferred $100 from your checking to your savings account."
            else:
                return "I'm your banking assistant. How can I help you today?"
        
        mock_instance.generate.side_effect = generate_response
        yield mock

# Mock session service
@pytest.fixture
def mock_session_service():
    service = EnhancedInMemorySessionService()
    return service

# Create a temporary SQLite database for testing
@pytest.fixture
def temp_sqlite_db():
    temp_dir = tempfile.mkdtemp()
    db_path = os.path.join(temp_dir, "test_banking.db")
    yield db_path
    # Cleanup
    if os.path.exists(db_path):
        os.remove(db_path)

# Create test runner with mocked components
@pytest.fixture
def test_runner(mock_llm, mock_session_service):
    # Create agents with mocked LLM
    greeting_agent = create_greeting_agent(mock_llm, say_hello)
    farewell_agent = create_farewell_agent(mock_llm, say_goodbye)
    balance_agent = create_balance_agent(mock_llm, get_balance)
    transfer_agent = create_transfer_agent(mock_llm, transfer_money)
    
    # Create root agent with mock callbacks
    mock_before_model = MagicMock(return_value=None)  # Allow all inputs
    mock_before_tool = MagicMock(return_value=None)   # Allow all tool calls
    
    root_agent = create_root_agent(
        model_name=mock_llm,
        sub_agents=[greeting_agent, farewell_agent, balance_agent, transfer_agent],
        tools=[get_financial_advice],
        before_model_callback=mock_before_model,
        before_tool_callback=mock_before_tool
    )
    
    # Create a runner with this setup
    runner = BankingBotRunner(
        root_agent=root_agent,
        session_service=mock_session_service,
        app_name="banking_bot_test"
    )
    
    return runner

# Event loop for async tests
@pytest.fixture
def event_loop():
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()