# tests/test_callbacks/test_before_model.py
import pytest
from callbacks.before_model import InputGuard
from google.adk.agents.callback_context import CallbackContext
from google.adk.models.llm_request import LlmRequest
from google.genai.types import Content, Part
from unittest.mock import MagicMock

def test_blocked_keywords_guardrail_valid_input():
    callback_context = MagicMock(spec=CallbackContext)
    callback_context.agent_name = "test_agent"
    callback_context.state = {}

    content = Content(role="user", parts=[Part(text="Show me my balance")])
    llm_request = MagicMock(spec=LlmRequest)
    llm_request.contents = [content]

    result = InputGuard.blocked_keywords_guardrail(callback_context, llm_request)
    assert result is None

def test_blocked_keywords_guardrail_blocked_input():
    callback_context = MagicMock(spec=CallbackContext)
    callback_context.agent_name = "test_agent"
    callback_context.state = {}

    content = Content(role="user", parts=[Part(text="My PASSWORD is 12345")])
    llm_request = MagicMock(spec=LlmRequest)
    llm_request.contents = [content]

    result = InputGuard.blocked_keywords_guardrail(callback_context, llm_request)
    assert result is not None
    assert "PASSWORD" in callback_context.state["guardrail_blocked_keywords"]

def test_pii_detection_guardrail_blocks_pii():
    callback_context = MagicMock(spec=CallbackContext)
    callback_context.agent_name = "test_agent"
    callback_context.state = {}

    llm_request = LlmRequest(contents=[
        Content(role="user", parts=[Part(text="My SSN is 123-45-6789")])
    ])

    result = InputGuard.pii_detection_guardrail(callback_context, llm_request)
    assert result is not None
    assert "ssn" in callback_context.state["guardrail_pii_detected_types"]

def test_pii_detection_guardrail_allows_safe_input():
    callback_context = MagicMock(spec=CallbackContext)
    callback_context.agent_name = "test_agent"
    callback_context.state = {}

    llm_request = LlmRequest(contents=[
        Content(role="user", parts=[Part(text="How much money do I have?")])
    ])

    result = InputGuard.pii_detection_guardrail(callback_context, llm_request)
    assert result is None
    assert "guardrail_pii_detected_types" not in callback_context.state
