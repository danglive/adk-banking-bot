import os
import tempfile
import pytest
from monitoring.analytics_service import AnalyticsService

@pytest.fixture
def analytics_service_instance():
    with tempfile.TemporaryDirectory() as tmpdir:
        service = AnalyticsService(analytics_dir=tmpdir)
        yield service

def test_generate_hourly_report_structure(analytics_service_instance):
    report = analytics_service_instance.generate_hourly_report()
    assert report["report_type"] == "hourly"
    assert "current_metrics" in report
    assert "hourly_statistics" in report
    assert "performance_trends" in report

def test_generate_daily_report_structure(analytics_service_instance):
    report = analytics_service_instance.generate_daily_report()
    assert report["report_type"] == "daily"
    assert "current_metrics" in report
    assert "daily_statistics" in report
    assert "user_analytics" in report
    assert "performance_analytics" in report
    assert "content_analytics" in report

