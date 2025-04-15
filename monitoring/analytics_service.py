# monitoring/analytics_service.py
import os
import json
import logging
import threading
import time
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime, timedelta
import pandas as pd
import numpy as np
from collections import Counter, defaultdict

from .metrics_collector import metrics_collector

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class AnalyticsService:
    """Service for analyzing and reporting on collected metrics."""
    
    def __init__(self, analytics_dir: str = "analytics"):
        """
        Initialize the analytics service.
        
        Args:
            analytics_dir: Directory to store analytics reports
        """
        self.analytics_dir = analytics_dir
        self.metrics_collector = metrics_collector
        
        # Create analytics directory if it doesn't exist
        os.makedirs(analytics_dir, exist_ok=True)
        
        # Start background analytics generator
        self._analytics_thread = threading.Thread(target=self._background_analytics_generator, daemon=True)
        self._analytics_thread.start()
        
        logger.info(f"Analytics service initialized, storing reports in {analytics_dir}")
    
    def generate_daily_report(self) -> Dict[str, Any]:
        """
        Generate a daily analytics report.
        
        Returns:
            Dict[str, Any]: The daily report data
        """
        # Get current metrics
        current_metrics = self.metrics_collector.get_current_metrics()
        
        # Get historical data
        historical_metrics = self.metrics_collector.historical_metrics
        
        # Calculate daily statistics
        daily_stats = self._calculate_daily_stats(historical_metrics)
        
        # Create the report
        report = {
            "report_type": "daily",
            "generated_at": datetime.now().isoformat(),
            "current_metrics": current_metrics,
            "daily_statistics": daily_stats,
            "user_analytics": self._analyze_users(historical_metrics),
            "performance_analytics": self._analyze_performance(historical_metrics),
            "content_analytics": self._analyze_content(historical_metrics)
        }
        
        return report
    
    def generate_hourly_report(self) -> Dict[str, Any]:
        """
        Generate an hourly analytics report.
        
        Returns:
            Dict[str, Any]: The hourly report data
        """
        # Get current metrics
        current_metrics = self.metrics_collector.get_current_metrics()
        
        # Get historical data from the last 24 hours
        now = datetime.now()
        last_day = now - timedelta(days=1)
        
        historical_metrics = [
            m for m in self.metrics_collector.historical_metrics
            if datetime.fromisoformat(m["timestamp"]) >= last_day
        ]
        
        # Calculate hourly statistics
        hourly_stats = self._calculate_hourly_stats(historical_metrics)
        
        # Create the report
        report = {
            "report_type": "hourly",
            "generated_at": now.isoformat(),
            "current_metrics": current_metrics,
            "hourly_statistics": hourly_stats,
            "performance_trends": self._analyze_hourly_performance(historical_metrics)
        }
        
        return report
    
    def _calculate_daily_stats(self, metrics: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Calculate daily statistics from historical metrics."""
        if not metrics:
            return {"message": "No metrics available"}
        
        # Group by day
        metrics_by_day = defaultdict(list)
        for m in metrics:
            day = datetime.fromisoformat(m["timestamp"]).strftime("%Y-%m-%d")
            metrics_by_day[day].append(m)
        
        # Calculate stats for each day
        daily_stats = {}
        for day, day_metrics in metrics_by_day.items():
            successful = sum(1 for m in day_metrics if m["success"])
            failed = len(day_metrics) - successful
            
            latencies = [m["latency_ms"] for m in day_metrics]
            avg_latency = sum(latencies) / len(latencies) if latencies else 0
            
            tool_calls = Counter()
            agent_calls = Counter()
            for m in day_metrics:
                for tool, count in m["tool_calls"].items():
                    tool_calls[tool] += count
                for agent, count in m["agent_calls"].items():
                    agent_calls[agent] += count
            
            daily_stats[day] = {
                "total_requests": len(day_metrics),
                "successful_requests": successful,
                "failed_requests": failed,
                "success_rate": successful / len(day_metrics) if day_metrics else 0,
                "average_latency_ms": avg_latency,
                "top_tools": dict(tool_calls.most_common(5)),
                "top_agents": dict(agent_calls.most_common(5))
            }
        
        return daily_stats
    
    def _calculate_hourly_stats(self, metrics: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Calculate hourly statistics from historical metrics."""
        if not metrics:
            return {"message": "No metrics available"}
        
        # Group by hour
        metrics_by_hour = defaultdict(list)
        for m in metrics:
            hour = datetime.fromisoformat(m["timestamp"]).strftime("%Y-%m-%d %H:00")
            metrics_by_hour[hour].append(m)
        
        # Calculate stats for each hour
        hourly_stats = {}
        for hour, hour_metrics in metrics_by_hour.items():
            successful = sum(1 for m in hour_metrics if m["success"])
            failed = len(hour_metrics) - successful
            
            latencies = [m["latency_ms"] for m in hour_metrics]
            avg_latency = sum(latencies) / len(latencies) if latencies else 0
            
            hourly_stats[hour] = {
                "total_requests": len(hour_metrics),
                "successful_requests": successful,
                "failed_requests": failed,
                "success_rate": successful / len(hour_metrics) if hour_metrics else 0,
                "average_latency_ms": avg_latency
            }
        
        return hourly_stats
    
    def _analyze_users(self, metrics: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Analyze user behavior from metrics."""
        if not metrics:
            return {"message": "No metrics available"}
        
        # Group by user
        metrics_by_user = defaultdict(list)
        for m in metrics:
            metrics_by_user[m["user_id"]].append(m)
        
        # Calculate user statistics
        user_stats = {}
        for user_id, user_metrics in metrics_by_user.items():
            # Calculate basic stats
            request_count = len(user_metrics)
            session_count = len(set(m["session_id"] for m in user_metrics))
            
            # Tool usage
            tool_usage = Counter()
            for m in user_metrics:
                for tool, count in m["tool_calls"].items():
                    tool_usage[tool] += count
            
            # Calculate retention
            timestamps = sorted([datetime.fromisoformat(m["timestamp"]) for m in user_metrics])
            first_seen = timestamps[0] if timestamps else None
            last_seen = timestamps[-1] if timestamps else None
            days_active = len(set(ts.date() for ts in timestamps))
            
            user_stats[user_id] = {
                "request_count": request_count,
                "session_count": session_count,
                "first_seen": first_seen.isoformat() if first_seen else None,
                "last_seen": last_seen.isoformat() if last_seen else None,
                "days_active": days_active,
                "preferred_tools": dict(tool_usage.most_common(3))
            }
        
        # Overall user analytics
        active_users = len(user_stats)
        new_users_last_day = sum(
            1 for user, stats in user_stats.items() 
            if datetime.fromisoformat(stats["first_seen"]) >= datetime.now() - timedelta(days=1)
        )
        
        return {
            "active_users": active_users,
            "new_users_last_day": new_users_last_day,
            "user_details": user_stats
        }
    
    def _analyze_performance(self, metrics: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Analyze performance metrics."""
        if not metrics:
            return {"message": "No metrics available"}
        
        # Extract latencies
        latencies = [m["latency_ms"] for m in metrics]
        
        # Calculate performance metrics
        performance = {
            "average_latency_ms": sum(latencies) / len(latencies) if latencies else 0,
            "median_latency_ms": sorted(latencies)[len(latencies)//2] if latencies else 0,
            "p95_latency_ms": sorted(latencies)[int(len(latencies)*0.95)] if latencies else 0,
            "min_latency_ms": min(latencies) if latencies else 0,
            "max_latency_ms": max(latencies) if latencies else 0,
            "total_llm_tokens_in": sum(m["llm_tokens_in"] for m in metrics),
            "total_llm_tokens_out": sum(m["llm_tokens_out"] for m in metrics),
            "average_tokens_per_request": {
                "in": sum(m["llm_tokens_in"] for m in metrics) / len(metrics) if metrics else 0,
                "out": sum(m["llm_tokens_out"] for m in metrics) / len(metrics) if metrics else 0
            }
        }
        
        # Analyze performance by tool
        tool_latencies = defaultdict(list)
        for m in metrics:
            for tool in m["tool_calls"]:
                tool_latencies[tool].append(m["latency_ms"])
        
        tool_performance = {}
        for tool, latencies in tool_latencies.items():
            tool_performance[tool] = {
                "count": len(latencies),
                "average_latency_ms": sum(latencies) / len(latencies) if latencies else 0,
                "p95_latency_ms": sorted(latencies)[int(len(latencies)*0.95)] if len(latencies) >= 20 else None
            }
        
        performance["tool_performance"] = tool_performance
        return performance
    
    def _analyze_content(self, metrics: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Analyze content usage patterns."""
        # This would normally analyze the actual content of messages
        # For this demo, we'll focus on tool and agent usage patterns
        if not metrics:
            return {"message": "No metrics available"}
        
        # Analyze tool usage patterns
        all_tool_calls = Counter()
        for m in metrics:
            for tool, count in m["tool_calls"].items():
                all_tool_calls[tool] += count
        
        # Analyze agent delegation patterns
        all_agent_calls = Counter()
        for m in metrics:
            for agent, count in m["agent_calls"].items():
                all_agent_calls[agent] += count
        
        # Calculate common tool sequences (simplified)
        # In a real system, this would analyze the actual sequence of tool calls
        
        return {
            "most_used_tools": dict(all_tool_calls.most_common(10)),
            "most_delegated_agents": dict(all_agent_calls.most_common(5)),
            "guardrail_block_rate": sum(m["guardrail_blocks"] for m in metrics) / len(metrics) if metrics else 0
        }
    
    def _analyze_hourly_performance(self, metrics: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Analyze performance trends by hour."""
        if not metrics:
            return {"message": "No metrics available"}
        
        # Group by hour
        metrics_by_hour = defaultdict(list)
        for m in metrics:
            hour = datetime.fromisoformat(m["timestamp"]).strftime("%Y-%m-%d %H:00")
            metrics_by_hour[hour].append(m)
        
        # Calculate performance trends
        hourly_performance = {}
        for hour, hour_metrics in metrics_by_hour.items():
            latencies = [m["latency_ms"] for m in hour_metrics]
            
            hourly_performance[hour] = {
                "request_count": len(hour_metrics),
                "average_latency_ms": sum(latencies) / len(latencies) if latencies else 0,
                "p95_latency_ms": sorted(latencies)[int(len(latencies)*0.95)] if len(latencies) >= 20 else None,
                "error_rate": sum(1 for m in hour_metrics if not m["success"]) / len(hour_metrics) if hour_metrics else 0,
                "token_usage": {
                    "in": sum(m["llm_tokens_in"] for m in hour_metrics),
                    "out": sum(m["llm_tokens_out"] for m in hour_metrics)
                }
            }
        
        return hourly_performance
    
    def _background_analytics_generator(self) -> None:
        """Background thread to periodically generate and save analytics reports."""
        while True:
            try:
                # Generate and save hourly report
                hourly_report = self.generate_hourly_report()
                hourly_filename = f"hourly_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
                hourly_filepath = os.path.join(self.analytics_dir, hourly_filename)
                
                with open(hourly_filepath, 'w') as f:
                    json.dump(hourly_report, f, indent=2)
                
                logger.info(f"Generated hourly analytics report: {hourly_filepath}")
                
                # Generate daily report once per day (at midnight)
                now = datetime.now()
                if now.hour == 0 and now.minute < 10:  # Between midnight and 12:10 AM
                    daily_report = self.generate_daily_report()
                    daily_filename = f"daily_report_{now.strftime('%Y%m%d')}.json"
                    daily_filepath = os.path.join(self.analytics_dir, daily_filename)
                    
                    with open(daily_filepath, 'w') as f:
                        json.dump(daily_report, f, indent=2)
                    
                    logger.info(f"Generated daily analytics report: {daily_filepath}")
                
                # Sleep for 1 hour
                time.sleep(3600)
                
            except Exception as e:
                logger.error(f"Error in analytics generator: {e}")
                time.sleep(300)  # 5 minutes on error

# Singleton instance
analytics_service = AnalyticsService()