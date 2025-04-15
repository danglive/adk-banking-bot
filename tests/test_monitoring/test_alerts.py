# tests/test_monitoring/test_alerts.py

import tempfile
import pytest
from monitoring.alerts import AlertSystem, AlertSeverity, AlertType


@pytest.fixture
def alert_system():
    with tempfile.TemporaryDirectory() as tmpdir:
        system = AlertSystem(alerts_dir=tmpdir)
        yield system


def test_trigger_and_resolve_alert(alert_system):
    alert_id = alert_system.trigger_alert(
        alert_type=AlertType.SYSTEM,
        severity=AlertSeverity.CRITICAL,
        message="Test critical system alert",
        details={"test_key": "test_value"},
    )

    active_alerts = alert_system.get_active_alerts()
    assert any(alert["id"] == alert_id for alert in active_alerts)

    resolved = alert_system.resolve_alert(alert_id, "Manual resolution for test")
    assert resolved

    active_alerts_after = alert_system.get_active_alerts()
    assert all(alert["id"] != alert_id for alert in active_alerts_after)


def test_get_active_alerts_filtered(alert_system):
    alert_system.trigger_alert(AlertType.SECURITY, AlertSeverity.INFO, "Info alert")
    alert_system.trigger_alert(AlertType.SECURITY, AlertSeverity.ERROR, "Error alert")

    filtered_type = alert_system.get_active_alerts(alert_type=AlertType.SECURITY)
    assert all(alert["type"] == "security" for alert in filtered_type)

    filtered_severity = alert_system.get_active_alerts(min_severity=AlertSeverity.ERROR)
    assert all(alert["severity"] in ["error", "critical"] for alert in filtered_severity)

