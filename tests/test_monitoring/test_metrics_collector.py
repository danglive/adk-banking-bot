import time
import os
import pytest
from monitoring.metrics_collector import MetricsCollector, MetricsContext
from unittest.mock import patch



def test_start_request(metrics_collector_instance):
    request_id = "req-1"
    user_id = "user-1"
    session_id = "sess-1"
    
    # Start tracking a request
    metrics_collector_instance.start_request(request_id, user_id, session_id)
    
    # Assert that the context is being tracked
    assert request_id in metrics_collector_instance.active_contexts
    context = metrics_collector_instance.active_contexts[request_id]
    assert isinstance(context, MetricsContext)
    assert context.request_id == request_id
    assert context.user_id == user_id
    assert context.session_id == session_id

def test_record_llm_call(metrics_collector_instance):
    request_id = "req-2"
    metrics_collector_instance.start_request(request_id, "user-2", "sess-2")
    
    # Record an LLM call
    metrics_collector_instance.record_llm_call(request_id, tokens_in=100, tokens_out=200)
    
    # Check the updated LLM stats
    context = metrics_collector_instance.active_contexts[request_id]
    assert context.llm_call_count == 1
    assert context.llm_tokens_in == 100
    assert context.llm_tokens_out == 200

def test_record_tool_call(metrics_collector_instance):
    request_id = "req-3"
    metrics_collector_instance.start_request(request_id, "user-3", "sess-3")
    
    # Record a tool call
    metrics_collector_instance.record_tool_call(request_id, tool_name="tool1")
    
    # Check the updated tool usage stats
    context = metrics_collector_instance.active_contexts[request_id]
    assert context.tool_calls["tool1"] == 1
    assert metrics_collector_instance.tool_usage["tool1"] == 1

def test_complete_request(metrics_collector_instance):
    request_id = "req-4"
    metrics_collector_instance.start_request(request_id, "user-4", "sess-4")
    
    # Complete the request with success
    context = metrics_collector_instance.complete_request(request_id, success=True)
    
    # Check that the request is completed and metrics are updated
    assert context is not None
    assert context.latency_ms is not None
    assert metrics_collector_instance.successful_requests == 1

def test_get_current_metrics(metrics_collector_instance):
    # Start two requests
    metrics_collector_instance.start_request("req-1", "user-1", "sess-1")
    metrics_collector_instance.start_request("req-2", "user-2", "sess-2")
    
    # Complete the requests
    metrics_collector_instance.complete_request("req-1", success=True)
    metrics_collector_instance.complete_request("req-2", success=False)
    
    # Get current metrics
    current_metrics = metrics_collector_instance.get_current_metrics()
    
    # Assert the total requests, success rate, etc.
    assert current_metrics["total_requests"] == 2
    assert current_metrics["successful_requests"] == 1
    assert current_metrics["failed_requests"] == 1
    assert "top_tools" in current_metrics
    assert "top_agents" in current_metrics

@pytest.fixture
def metrics_collector_instance():
    collector = MetricsCollector()
    yield collector
    collector.historical_metrics.clear()

def test_background_metrics_writer(metrics_collector_instance):
    # Start a request and complete it
    metrics_collector_instance.start_request("req-5", "user-5", "sess-5")
    metrics_collector_instance.complete_request("req-5", success=True)

    # Mock time.sleep to prevent waiting during test
    with patch("time.sleep", return_value=None):
        # Let the background writer run for a short time
        time.sleep(1)

        # Check that a metrics file was written
        files = os.listdir(metrics_collector_instance.metrics_dir)
        assert len(files) > 0  # Assert that at least one file was written
        assert files[0].startswith("metrics_")  # Check the filename pattern


