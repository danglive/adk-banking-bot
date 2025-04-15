import pytest
from tools.finance_advisor import get_financial_advice
from types import SimpleNamespace

class MockToolContext:
    def __init__(self):
        self.state = {}

def test_get_financial_advice_success():
    tool_context = MockToolContext()
    result = get_financial_advice("savings", "moderate", tool_context)
    assert result["status"] == "success"
    assert "advice" in result
    assert "resources" in result
    assert tool_context.state["user_risk_profile"] == "moderate"
    assert "savings" in tool_context.state["financial_advice_topics"]

def test_get_financial_advice_invalid_risk():
    result = get_financial_advice("investment", "risky")
    assert result["status"] == "error"
    assert "Invalid risk profile" in result["error_message"]

def test_get_financial_advice_unknown_topic():
    result = get_financial_advice("taxes")
    assert result["status"] == "error"
    assert "don't have advice on" in result["error_message"]