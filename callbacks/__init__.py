# callbacks/__init__.py
from .before_model import InputGuard
from .before_tool import ToolGuard

# For convenience, create direct exports of the main callback functions
blocked_keywords_guardrail = InputGuard.blocked_keywords_guardrail
pii_detection_guardrail = InputGuard.pii_detection_guardrail
transfer_limit_guardrail = ToolGuard.transfer_limit_guardrail
account_validation_guardrail = ToolGuard.account_validation_guardrail
authentication_guardrail = ToolGuard.authentication_guardrail

__all__ = [
    'InputGuard',
    'ToolGuard',
    'blocked_keywords_guardrail',
    'pii_detection_guardrail',
    'transfer_limit_guardrail',
    'account_validation_guardrail',
    'authentication_guardrail'
]