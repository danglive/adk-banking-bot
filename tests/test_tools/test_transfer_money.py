import pytest
import time

from tools.transfer_money import transfer_money
from google.adk.tools.tool_context import ToolContext
from google.adk.agents.invocation_context import InvocationContext
from google.adk.sessions import BaseSessionService, Session
from google.adk.agents import BaseAgent
from pydantic import Field


class DummySessionService(BaseSessionService):
    def append_event(self, *args, **kwargs): pass
    def close_session(self, *args, **kwargs): pass
    def create_session(self, *args, **kwargs): pass
    def delete_session(self, *args, **kwargs): pass
    def get_session(self, *args, **kwargs): return {}
    def list_events(self, *args, **kwargs): return []
    def list_sessions(self, *args, **kwargs): return []


class DummyAgent(BaseAgent):
    name: str = Field(default="test-agent")


def test_transfer_success():
    session = Session(
        id="test-session-id",
        app_name="test-app",
        user_id="test-user"
    )

    invocation_context = InvocationContext(
        session_service=DummySessionService(),
        invocation_id="test-invocation-id",
        agent=DummyAgent(),
        session=session
    )

    ctx = ToolContext(invocation_context=invocation_context)

    result = transfer_money("checking", "savings", 100.0, tool_context=ctx)

    assert result["status"] == "success"
    assert result["source_account"] == "checking"
    assert result["destination_account"] == "savings"
    assert result["amount"] == 100.0
    assert "transaction_id" in result
    assert "timestamp" in result
    assert "new_balance" in result
    assert ctx.state["last_transaction_id"] == result["transaction_id"]
    assert len(ctx.state["transfer_history"]) == 1
