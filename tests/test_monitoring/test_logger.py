import logging
import os
import pytest
import json
import threading
import traceback
from datetime import datetime
from monitoring.logger import LogManager, StructuredLoggerAdapter

import tempfile

logger = logging.getLogger(__name__) 


@pytest.fixture
def log_manager_instance():
    with tempfile.TemporaryDirectory() as tmpdir:
        manager = LogManager(log_dir=tmpdir)
        yield manager

def test_get_logger_with_context(log_manager_instance):
    logger = log_manager_instance.get_logger("test.logger", custom_key="value")
    assert isinstance(logger, StructuredLoggerAdapter)
    logger.info("Test log with context")

def test_set_and_clear_context(log_manager_instance):
    log_manager_instance.set_context(user_id="user123")
    logger = log_manager_instance.get_logger("context.logger")
    logger.info("With thread-local context")

    log_manager_instance.clear_context()
    logger = log_manager_instance.get_logger("context.logger")
    logger.info("After clearing context")

def test_log_request_and_response(log_manager_instance):
    log_manager_instance.log_request(
        request_id="req-1",
        user_id="user-1",
        method="GET",
        path="/api/test",
        params={"q": "search"}
    )
    log_manager_instance.log_response(
        request_id="req-1",
        status_code=200,
        duration_ms=123.45
    )

def test_log_response_with_error(log_manager_instance):
    log_manager_instance.log_response(
        request_id="req-2",
        status_code=500,
        duration_ms=321.0,
        error="Internal Server Error"
    )
