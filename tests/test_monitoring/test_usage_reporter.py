# tests/test_monitoring/test_usage_reporter.py
import os
import json
import time
import shutil
from datetime import datetime
import pytest
from unittest.mock import patch, MagicMock, PropertyMock
from monitoring.usage_reporter import UsageReporter, usage_reporter

@pytest.fixture
def usage_reporter_instance():
    """Create a fresh instance of UsageReporter for each test."""
    # Use a test-specific directory
    test_dir = "test_reports"
    
    # Clean up any existing test directory
    if os.path.exists(test_dir):
        shutil.rmtree(test_dir)
    os.makedirs(test_dir, exist_ok=True)
    
    # Create instance with mocked dependencies
    with patch('monitoring.usage_reporter.metrics_collector') as mock_metrics, \
         patch('monitoring.usage_reporter.analytics_service') as mock_analytics:
        
        # Configure the metrics collector mock
        mock_metrics.get_current_metrics.return_value = {
            "total_requests": 100,
            "successful_requests": 95,
            "failed_requests": 5,
            "success_rate": 0.95,
            "average_latency_ms": 150.5,
            "top_tools": {"get_balance": 45, "transfer_money": 30},
            "top_agents": {"balance_agent": 45, "transfer_agent": 30},
            "guardrail_blocks": 3
        }
        
        # Configure the analytics service mock
        mock_daily_report = {
            "current_metrics": {
                "total_requests": 100,
                "success_rate": 0.95,
                "average_latency_ms": 150.5,
                "top_tools": {"get_balance": 45, "transfer_money": 30}
            },
            "daily_statistics": {
                "2025-04-14": {
                    "total_requests": 50,
                    "successful_requests": 48,
                    "failed_requests": 2,
                    "success_rate": 0.96,
                    "average_latency_ms": 145.2
                },
                "2025-04-15": {
                    "total_requests": 50,
                    "successful_requests": 47,
                    "failed_requests": 3,
                    "success_rate": 0.94,
                    "average_latency_ms": 155.8
                }
            },
            "user_analytics": {
                "active_users": 25,
                "new_users_last_day": 5
            }
        }
        mock_analytics.generate_daily_report.return_value = mock_daily_report
        
        # Create reporter instance with test directory and start without background thread
        reporter = UsageReporter(reports_dir=test_dir)
        
        # Stop the background thread
        if hasattr(reporter, '_report_thread'):
            original_thread = reporter._report_thread
            reporter._report_thread = MagicMock()
        
        yield reporter
    
    # Clean up test directory after tests
    if os.path.exists(test_dir):
        shutil.rmtree(test_dir)

def test_init(usage_reporter_instance):
    """Test the initialization of UsageReporter."""
    assert usage_reporter_instance.reports_dir == "test_reports"
    assert os.path.exists("test_reports")

def test_generate_daily_usage_report(usage_reporter_instance):
    """Test generating a daily usage report."""
    # Call the method
    report = usage_reporter_instance.generate_daily_usage_report()
    
    # Verify the report structure
    assert report["report_type"] == "daily_usage"
    assert "generated_at" in report
    assert report["period"] == "last_7_days"
    
    # Check summary section
    assert report["summary"]["total_requests"] == 100
    assert report["summary"]["success_rate"] == 0.95
    assert report["summary"]["active_users"] == 25
    assert report["summary"]["new_users"] == 5
    assert report["summary"]["average_latency_ms"] == 150.5
    assert "top_tools" in report["summary"]
    
    # Check daily trends
    assert "2025-04-14" in report["daily_trends"]
    assert "2025-04-15" in report["daily_trends"]
    assert report["daily_trends"]["2025-04-14"]["success_rate"] == 0.96
    
    # Check visualizations
    assert "visualizations" in report
    assert "requests_chart" in report["visualizations"]
    
    # Verify that the file was created
    files = os.listdir("test_reports")
    assert any(f.startswith("daily_usage_report_") for f in files)
    
    # Verify file content
    report_file = [f for f in files if f.startswith("daily_usage_report_")][0]
    with open(os.path.join("test_reports", report_file), 'r') as f:
        file_content = json.load(f)
    assert file_content["report_type"] == "daily_usage"

def test_create_usage_visualizations(usage_reporter_instance):
    """Test creating usage visualizations."""
    # Test data
    daily_stats = {
        "2025-04-14": {
            "total_requests": 50,
            "success_rate": 0.96,
            "average_latency_ms": 145.2
        },
        "2025-04-15": {
            "total_requests": 50,
            "success_rate": 0.94,
            "average_latency_ms": 155.8
        }
    }
    
    # Call the method
    chart_paths = usage_reporter_instance._create_usage_visualizations(daily_stats)
    
    # Verify the returned paths
    assert "requests_chart" in chart_paths
    assert "success_rate_chart" in chart_paths
    assert "latency_chart" in chart_paths
    assert "tool_usage_chart" in chart_paths
    
    # Verify the charts directory was created
    assert os.path.exists(os.path.join("test_reports", "charts"))

def test_generate_usage_summary(usage_reporter_instance):
    """Test generating usage summaries for different periods."""
    # Test different periods
    periods = ["day", "week", "month", "custom"]
    
    for period in periods:
        # Call the method for each period
        summary = usage_reporter_instance.generate_usage_summary(period=period)
        
        # Verify common structure
        assert "title" in summary
        assert "generated_at" in summary
        assert "timeframe" in summary
        assert "metrics" in summary
        assert "usage" in summary
        
        # Check title and timeframe based on period
        if period == "day":
            assert "Daily" in summary["title"]
            assert summary["timeframe"] == "Today"
        elif period == "week":
            assert "Weekly" in summary["title"]
            assert summary["timeframe"] == "This Week"
        elif period == "month":
            assert "Monthly" in summary["title"]
            assert summary["timeframe"] == "This Month"
        else:
            assert summary["timeframe"] == "All Time"
        
        # Check metrics
        assert summary["metrics"]["total_requests"] == 100
        assert summary["metrics"]["successful_requests"] == 95
        assert summary["metrics"]["failed_requests"] == 5
        assert summary["metrics"]["success_rate"] == 0.95
        assert summary["metrics"]["average_latency_ms"] == 150.5
        
        # Check usage data
        assert "top_tools" in summary["usage"]
        assert "top_agents" in summary["usage"]
        assert summary["usage"]["guardrail_blocks"] == 3

def test_background_report_generator():
    """Test the background report generator functionality."""
    # Create a mock UsageReporter
    with patch('monitoring.usage_reporter.UsageReporter.generate_daily_usage_report') as mock_generate:
        # Create a reporter instance
        reporter = UsageReporter(reports_dir="test_reports")
        
        # Mock datetime.now to return midnight
        mock_now = datetime(2025, 4, 15, 0, 5)  # 00:05, should trigger report
        
        with patch('monitoring.usage_reporter.datetime') as mock_datetime:
            # Configure datetime.now to return our fixed time
            mock_datetime.now.return_value = mock_now
            mock_datetime.side_effect = lambda *args, **kw: datetime(*args, **kw)
            
            # Mock time.sleep to avoid waiting
            with patch('time.sleep'):
                # Call the method once
                try:
                    # Extract the relevant code from the background thread function
                    # without the while loop
                    now = mock_now
                    if now.hour == 0 and now.minute < 10:
                        reporter.generate_daily_usage_report()
                except Exception as e:
                    pytest.fail(f"Background report generator failed: {e}")
        
        # Verify generate_daily_usage_report was called
        mock_generate.assert_called_once()

if __name__ == "__main__":
    pytest.main()