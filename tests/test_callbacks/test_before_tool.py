# tests/test_callbacks/test_before_tool.py
import pytest
from callbacks.before_tool import ToolGuard
from google.adk.tools.base_tool import BaseTool
from google.adk.tools.tool_context import ToolContext
from unittest.mock import MagicMock

class DummyTool(BaseTool):
    def __init__(self, name):
        self.name = name

@pytest.fixture
def tool_context():
    context = MagicMock(spec=ToolContext)
    context.agent_name = "test_agent"
    context.state = {}
    return context

def test_transfer_limit_guardrail_blocks_large_amount(tool_context):
    tool = DummyTool("transfer_money")
    args = {"amount": 2000}
    response = ToolGuard.transfer_limit_guardrail(tool, args, tool_context)
    assert response is not None
    assert "exceeds the maximum allowed limit" in response["error_message"]

def test_transfer_limit_guardrail_allows_valid_amount(tool_context):
    tool = DummyTool("transfer_money")
    args = {"amount": 500}
    response = ToolGuard.transfer_limit_guardrail(tool, args, tool_context)
    assert response is None

def test_account_validation_guardrail_blocks_restricted_account(tool_context):
    tool = DummyTool("get_balance")
    args = {"account_id": "corporate_savings"}
    response = ToolGuard.account_validation_guardrail(tool, args, tool_context)
    assert response is not None
    assert "requires additional verification" in response["error_message"]

def test_account_validation_guardrail_allows_valid_account(tool_context):
    tool = DummyTool("get_balance")
    args = {"account_id": "personal_checking"}
    response = ToolGuard.account_validation_guardrail(tool, args, tool_context)
    assert response is None

def test_authentication_guardrail_blocks_unauthenticated(tool_context):
    tool = DummyTool("transfer_money")
    args = {"amount": 100}
    tool_context.state["user_authenticated"] = False
    response = ToolGuard.authentication_guardrail(tool, args, tool_context)
    assert response is not None
    assert "requires authentication" in response["error_message"]

def test_authentication_guardrail_allows_authenticated(tool_context):
    tool = DummyTool("transfer_money")
    args = {"amount": 100}
    tool_context.state["user_authenticated"] = True
    response = ToolGuard.authentication_guardrail(tool, args, tool_context)
    assert response is None
