# monitoring/usage_reporter.py
import time
import logging
import threading
import json
import os
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional, Set, Counter
import pandas as pd
import matplotlib.pyplot as plt
from collections import defaultdict

from .metrics_collector import metrics_collector
from .analytics_service import analytics_service

# Configure logging
logger = logging.getLogger(__name__)

class UsageReporter:
    """Generates usage reports and visualizations."""
    
    def __init__(self, reports_dir: str = "reports"):
        """
        Initialize the usage reporter.
        
        Args:
            reports_dir: Directory to store reports
        """
        self.reports_dir = reports_dir
        self.metrics_collector = metrics_collector
        self.analytics_service = analytics_service
        
        # Create reports directory
        os.makedirs(reports_dir, exist_ok=True)
        
        # Start background report generator
        self._report_thread = threading.Thread(target=self._background_report_generator, daemon=True)
        self._report_thread.start()
        
        logger.info(f"Usage reporter initialized, storing reports in {reports_dir}")
    
    def generate_daily_usage_report(self) -> Dict[str, Any]:
        """
        Generate a daily usage report.
        
        Returns:
            Dict[str, Any]: The report data
        """
        # Get daily analytics
        daily_report = self.analytics_service.generate_daily_report()
        
        # Extract key metrics
        current_metrics = daily_report["current_metrics"]
        daily_stats = daily_report["daily_statistics"]
        
        # Create visualizations
        charts_data = self._create_usage_visualizations(daily_stats)
        
        # Compile report
        report = {
            "report_type": "daily_usage",
            "generated_at": datetime.now().isoformat(),
            "period": "last_7_days",
            "summary": {
                "total_requests": current_metrics["total_requests"],
                "success_rate": current_metrics["success_rate"],
                "active_users": daily_report["user_analytics"]["active_users"],
                "new_users": daily_report["user_analytics"]["new_users_last_day"],
                "average_latency_ms": current_metrics["average_latency_ms"],
                "top_tools": current_metrics["top_tools"],
            },
            "daily_trends": {
                day: {
                    "requests": stats["total_requests"],
                    "success_rate": stats["success_rate"],
                    "average_latency": stats["average_latency_ms"]
                }
                for day, stats in daily_stats.items()
            },
            "visualizations": charts_data
        }
        
        # Save report to disk
        report_date = datetime.now().strftime("%Y%m%d")
        filename = f"daily_usage_report_{report_date}.json"
        filepath = os.path.join(self.reports_dir, filename)
        
        with open(filepath, 'w') as f:
            json.dump(report, f, indent=2)
        
        logger.info(f"Generated daily usage report: {filepath}")
        
        return report
    
    def _create_usage_visualizations(self, daily_stats: Dict[str, Any]) -> Dict[str, str]:
        """
        Create visualizations for the usage report.
        
        Args:
            daily_stats: Daily statistics data
            
        Returns:
            Dict[str, str]: Paths to generated chart files
        """
        # This would normally create actual visualizations
        # For this demo, we'll return placeholder paths
        
        # In a real implementation, this would use matplotlib to create:
        # - Daily request volume chart
        # - Success rate trend chart 
        # - Latency trend chart
        # - Tool usage breakdown chart
        
        # Create a reports/charts directory
        charts_dir = os.path.join(self.reports_dir, "charts")
        os.makedirs(charts_dir, exist_ok=True)
        
        date_str = datetime.now().strftime("%Y%m%d")
        
        # Return paths to chart files (that would be created in a real system)
        return {
            "requests_chart": f"charts/requests_trend_{date_str}.png",
            "success_rate_chart": f"charts/success_rate_{date_str}.png",
            "latency_chart": f"charts/latency_trend_{date_str}.png",
            "tool_usage_chart": f"charts/tool_usage_{date_str}.png"
        }
    
    def generate_usage_summary(self, period: str = "day") -> Dict[str, Any]:
        """
        Generate a usage summary for a specific time period.
        
        Args:
            period: Time period ("day", "week", "month")
            
        Returns:
            Dict[str, Any]: Usage summary
        """
        # Get current metrics
        current_metrics = self.metrics_collector.get_current_metrics()
        
        # Calculate period-appropriate metrics
        if period == "day":
            title = "Daily Usage Summary"
            timeframe = "Today"
        elif period == "week":
            title = "Weekly Usage Summary"
            timeframe = "This Week"
        elif period == "month":
            title = "Monthly Usage Summary"
            timeframe = "This Month"
        else:
            title = "Usage Summary"
            timeframe = "All Time"
        
        # Create summary
        summary = {
            "title": title,
            "generated_at": datetime.now().isoformat(),
            "timeframe": timeframe,
            "metrics": {
                "total_requests": current_metrics["total_requests"],
                "successful_requests": current_metrics["successful_requests"],
                "failed_requests": current_metrics["failed_requests"],
                "success_rate": current_metrics["success_rate"],
                "average_latency_ms": current_metrics["average_latency_ms"],
            },
            "usage": {
                "top_tools": current_metrics["top_tools"],
                "top_agents": current_metrics["top_agents"],
                "guardrail_blocks": current_metrics["guardrail_blocks"]
            }
        }
        
        return summary
    
    def _background_report_generator(self) -> None:
        """Background thread to periodically generate reports."""
        while True:
            try:
                # Get current time
                now = datetime.now()
                
                # Generate daily report at midnight
                if now.hour == 0 and now.minute < 10:  # Just after midnight
                    self.generate_daily_usage_report()
                
                # Sleep for 1 hour
                time.sleep(3600)
                
            except Exception as e:
                logger.error(f"Error in report generator: {e}")
                time.sleep(300)  # 5 minutes on error

# Singleton instance
usage_reporter = UsageReporter()
