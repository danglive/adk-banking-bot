# monitoring/alerts.py
import logging
import threading
import time
from typing import Dict, Any, List, Optional, Callable, Set
from datetime import datetime, timedelta
from enum import Enum
import json
import os
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

from .metrics_collector import metrics_collector
from .performance_tracker import performance_tracker

# Configure logging
logger = logging.getLogger(__name__)

class AlertSeverity(Enum):
    """Alert severity levels."""
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"

class AlertType(Enum):
    """Types of alerts that can be triggered."""
    PERFORMANCE = "performance"
    ERROR_RATE = "error_rate"
    GUARDRAIL = "guardrail"
    USAGE = "usage"
    SECURITY = "security"
    SYSTEM = "system"

class AlertSystem:
    """System for detecting and handling alert conditions."""
    
    def __init__(self, alerts_dir: str = "alerts"):
        """
        Initialize the alert system.
        
        Args:
            alerts_dir: Directory to store alert records
        """
        self.alerts_dir = alerts_dir
        self.metrics_collector = metrics_collector
        self.performance_tracker = performance_tracker
        
        # Alert handlers by type
        self.alert_handlers: Dict[AlertType, List[Callable]] = {
            alert_type: [] for alert_type in AlertType
        }
        
        # Alert thresholds and configurations
        self.thresholds = {
            AlertType.PERFORMANCE: {
                "api_request_ms": 2000,  # 2 seconds
                "llm_call_ms": 5000,     # 5 seconds
                "tool_execution_ms": 1000,  # 1 second
            },
            AlertType.ERROR_RATE: {
                "max_error_rate": 0.05,  # 5% error rate
                "window_size": 100,      # Over last 100 requests
            },
            AlertType.GUARDRAIL: {
                "max_block_rate": 0.10,  # 10% block rate
            },
            AlertType.USAGE: {
                "max_requests_per_minute": 100,
                "max_tokens_per_minute": 10000,
            }
        }
        
        # Active alerts
        self.active_alerts: Dict[str, Dict[str, Any]] = {}
        self.resolved_alerts: List[Dict[str, Any]] = []
        self.alert_lock = threading.RLock()
        
        # Create alerts directory
        os.makedirs(alerts_dir, exist_ok=True)
        
        # Start monitoring thread
        self._monitor_thread = threading.Thread(target=self._background_monitor, daemon=True)
        self._monitor_thread.start()
        
        # Register default handlers
        self._register_default_handlers()
        
        logger.info(f"Alert system initialized, storing alerts in {alerts_dir}")
    
    def register_handler(self, alert_type: AlertType, handler: Callable) -> None:
        """
        Register a handler for a specific type of alert.
        
        Args:
            alert_type: The type of alert to handle
            handler: Callback function that accepts an alert dict
        """
        self.alert_handlers[alert_type].append(handler)
        logger.info(f"Registered handler for {alert_type.value} alerts")
    
    def set_threshold(self, alert_type: AlertType, key: str, value: Any) -> None:
        """
        Set a threshold for a specific alert type.
        
        Args:
            alert_type: The type of alert
            key: Threshold key
            value: Threshold value
        """
        if alert_type not in self.thresholds:
            self.thresholds[alert_type] = {}
        
        self.thresholds[alert_type][key] = value
        logger.info(f"Set {alert_type.value} threshold: {key}={value}")
    
    def trigger_alert(self, alert_type: AlertType, severity: AlertSeverity, 
                     message: str, details: Optional[Dict[str, Any]] = None) -> str:
        """
        Trigger a new alert.
        
        Args:
            alert_type: Type of the alert
            severity: Severity level
            message: Alert message
            details: Additional alert details
            
        Returns:
            str: Alert ID
        """
        now = datetime.now()
        alert_id = f"{alert_type.value}_{now.strftime('%Y%m%d%H%M%S')}_{hash(message) % 10000}"
        
        alert = {
            "id": alert_id,
            "type": alert_type.value,
            "severity": severity.value,
            "message": message,
            "details": details or {},
            "timestamp": now.isoformat(),
            "status": "active",
            "resolved_at": None,
            "resolution_message": None
        }
        
        with self.alert_lock:
            self.active_alerts[alert_id] = alert
        
        # Write alert to file
        self._save_alert(alert)
        
        # Call handlers
        for handler in self.alert_handlers[alert_type]:
            try:
                handler(alert)
            except Exception as e:
                logger.error(f"Error in alert handler: {e}")
        
        logger.warning(f"ALERT [{severity.value.upper()}]: {message}")
        return alert_id
    
    def resolve_alert(self, alert_id: str, resolution_message: str) -> bool:
        """
        Resolve an active alert.
        
        Args:
            alert_id: The alert identifier
            resolution_message: Message explaining the resolution
            
        Returns:
            bool: True if alert was found and resolved, False otherwise
        """
        with self.alert_lock:
            if alert_id not in self.active_alerts:
                return False
            
            alert = self.active_alerts.pop(alert_id)
            alert["status"] = "resolved"
            alert["resolved_at"] = datetime.now().isoformat()
            alert["resolution_message"] = resolution_message
            
            self.resolved_alerts.append(alert)
            
            # Cap resolved alerts list
            if len(self.resolved_alerts) > 1000:
                self.resolved_alerts.pop(0)
        
        # Update alert file
        self._save_alert(alert)
        
        logger.info(f"Resolved alert {alert_id}: {resolution_message}")
        return True
    
    def get_active_alerts(self, alert_type: Optional[AlertType] = None, 
                         min_severity: Optional[AlertSeverity] = None) -> List[Dict[str, Any]]:
        """
        Get active alerts, optionally filtered.
        
        Args:
            alert_type: Filter by alert type
            min_severity: Filter by minimum severity
            
        Returns:
            List[Dict[str, Any]]: Matching active alerts
        """
        with self.alert_lock:
            alerts = list(self.active_alerts.values())
        
        # Apply filters
        if alert_type:
            alerts = [a for a in alerts if a["type"] == alert_type.value]
        
        if min_severity:
            severity_values = [s.value for s in AlertSeverity]
            min_idx = severity_values.index(min_severity.value)
            alerts = [a for a in alerts if severity_values.index(a["severity"]) >= min_idx]
        
        return alerts
    
    def _save_alert(self, alert: Dict[str, Any]) -> None:
        """Save an alert to disk."""
        try:
            status = alert["status"]
            alert_type = alert["type"]
            filename = f"{status}_{alert_type}_{alert['id']}.json"
            filepath = os.path.join(self.alerts_dir, filename)
            
            with open(filepath, 'w') as f:
                json.dump(alert, f, indent=2)
            
            # If alert was resolved, remove the active alert file
            if status == "resolved":
                active_file = filepath.replace("resolved_", "active_")
                if os.path.exists(active_file):
                    os.remove(active_file)
                    
        except Exception as e:
            logger.error(f"Error saving alert to file: {e}")
    
    def _register_default_handlers(self) -> None:
        """Register default alert handlers."""
        # Log all alerts
        for alert_type in AlertType:
            self.register_handler(alert_type, self._log_alert_handler)
        
        # Email critical alerts
        for alert_type in AlertType:
            self.register_handler(alert_type, self._email_critical_alert_handler)
    
    def _log_alert_handler(self, alert: Dict[str, Any]) -> None:
        """Default handler to log all alerts."""
        severity = alert["severity"].upper()
        logger.warning(f"ALERT [{severity}]: {alert['message']}")
    
    def _email_critical_alert_handler(self, alert: Dict[str, Any]) -> None:
        """Handler to email critical alerts."""
        if alert["severity"] != AlertSeverity.CRITICAL.value:
            return
        
        # In a real system, this would send an email
        # For this demo, we'll just log
        logger.critical(f"Would send email for CRITICAL alert: {alert['message']}")
    
    def _check_performance_alerts(self) -> None:
        """Check for performance-related alert conditions."""
        performance_metrics = self.performance_tracker.get_performance_metrics()
        
        for category, metrics in performance_metrics.items():
            threshold_key = f"{category}_ms"
            if (AlertType.PERFORMANCE in self.thresholds and 
                threshold_key in self.thresholds[AlertType.PERFORMANCE]):
                
                threshold_ms = self.thresholds[AlertType.PERFORMANCE][threshold_key]
                p95_ms = metrics.get("p95_ms")
                
                if p95_ms and p95_ms > threshold_ms:
                    # Generate a unique key for this alert to prevent duplicates
                    alert_key = f"performance_{category}_{datetime.now().strftime('%Y%m%d_%H')}"
                    
                    # Only trigger if we don't already have an active alert for this
                    if alert_key not in self.active_alerts:
                        self.trigger_alert(
                            alert_type=AlertType.PERFORMANCE,
                            severity=AlertSeverity.WARNING,
                            message=f"Performance degradation in {category}: p95 latency {p95_ms:.2f}ms exceeds threshold {threshold_ms}ms",
                            details={
                                "category": category,
                                "p95_ms": p95_ms,
                                "threshold_ms": threshold_ms,
                                "metrics": metrics
                            }
                        )
    
    def _check_error_rate_alerts(self) -> None:
        """Check for error rate alert conditions."""
        current_metrics = self.metrics_collector.get_current_metrics()
        
        if AlertType.ERROR_RATE in self.thresholds:
            max_rate = self.thresholds[AlertType.ERROR_RATE].get("max_error_rate", 0.05)
            
            error_rate = current_metrics["failed_requests"] / max(1, current_metrics["total_requests"])
            
            if error_rate > max_rate and current_metrics["total_requests"] >= 10:
                # Generate a unique key for this alert
                alert_key = f"error_rate_{datetime.now().strftime('%Y%m%d_%H')}"
                
                if alert_key not in self.active_alerts:
                    self.trigger_alert(
                        alert_type=AlertType.ERROR_RATE,
                        severity=AlertSeverity.ERROR,
                        message=f"High error rate: {error_rate:.2%} exceeds threshold {max_rate:.2%}",
                        details={
                            "error_rate": error_rate,
                            "threshold": max_rate,
                            "failed_requests": current_metrics["failed_requests"],
                            "total_requests": current_metrics["total_requests"]
                        }
                    )
    
    def _background_monitor(self) -> None:
        """Background thread to monitor for alert conditions."""
        while True:
            try:
                # Check each type of alert
                self._check_performance_alerts()
                self._check_error_rate_alerts()
                
                # Check for auto-resolution of alerts
                self._auto_resolve_alerts()
                
                # Sleep for 60 seconds
                time.sleep(60)
                
            except Exception as e:
                logger.error(f"Error in alert monitor: {e}")
                time.sleep(60)
    
    def _auto_resolve_alerts(self) -> None:
        """Automatically resolve alerts that are no longer relevant."""
        with self.alert_lock:
            for alert_id, alert in list(self.active_alerts.items()):
                # Check if performance alerts can be auto-resolved
                if alert["type"] == AlertType.PERFORMANCE.value:
                    category = alert["details"].get("category")
                    if category:
                        metrics = self.performance_tracker.get_performance_metrics()
                        if category in metrics:
                            p95_ms = metrics[category].get("p95_ms")
                            threshold_ms = alert["details"].get("threshold_ms")
                            
                            if p95_ms and threshold_ms and p95_ms < threshold_ms:
                                self.resolve_alert(
                                    alert_id=alert_id,
                                    resolution_message=f"Performance recovered: {category} p95 latency now {p95_ms:.2f}ms (below threshold {threshold_ms}ms)"
                                )

# Singleton instance
alert_system = AlertSystem()
