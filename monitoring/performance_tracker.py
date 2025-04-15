import time
import logging
from typing import Dict, Any, List, Optional
import threading
import json
import os
from datetime import datetime
from dataclasses import dataclass
import statistics

from .metrics_collector import metrics_collector  

# Set up logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

@dataclass
class PerformanceData:
    """Data structure for tracking detailed performance metrics."""
    name: str
    category: str
    start_time: float
    end_time: Optional[float] = None
    duration_ms: Optional[float] = None
    metadata: Dict[str, Any] = None
    parent: Optional[str] = None
    
    def complete(self) -> 'PerformanceData':
        """Mark as complete and calculate duration."""
        self.end_time = time.time()
        self.duration_ms = (self.end_time - self.start_time) * 1000
        return self

class PerformanceTracker:
    """Tracks detailed performance metrics for various components of the system."""
    
    def __init__(self, storage_dir: str = "performance"):
        """
        Initialize the performance tracker.
        
        Args:
            storage_dir: Directory to store performance data
        """
        self.storage_dir = storage_dir
        self.metrics_collector = metrics_collector
        self.traces: Dict[str, PerformanceData] = {}
        self.historical_data: Dict[str, List[PerformanceData]] = {}
        self.thresholds: Dict[str, float] = {}
        self.trace_lock = threading.RLock()
        
        # Create storage directory
        os.makedirs(storage_dir, exist_ok=True)
        
        # Start background data writer
        self._writer_thread = threading.Thread(target=self._background_data_writer, daemon=True)
        self._writer_thread.start()
        
        # Default performance thresholds (in ms)
        self.set_threshold("api_request", 1000)  # 1 second
        self.set_threshold("llm_call", 2000)  # 2 seconds
        self.set_threshold("tool_execution", 500)  # 500 ms
        self.set_threshold("database_query", 100)  # 100 ms
        
        logger.info(f"Performance tracker initialized, storing data in {storage_dir}")
    
    def start_trace(self, name: str, category: str, request_id: Optional[str] = None, 
                   parent: Optional[str] = None, metadata: Optional[Dict[str, Any]] = None) -> str:
        """
        Start a performance trace.
        
        Args:
            name: Name of the operation being traced
            category: Category of operation (e.g., api, llm, tool, db)
            request_id: Associated request ID (for correlation)
            parent: Parent trace ID (for nested operations)
            metadata: Additional context data
            
        Returns:
            str: Trace ID for reference
        """
        trace_id = f"{name}_{int(time.time() * 1000)}_{hash(name) % 10000}"
        
        with self.trace_lock:
            self.traces[trace_id] = PerformanceData(
                name=name,
                category=category,
                start_time=time.time(),
                metadata={
                    "request_id": request_id,
                    **(metadata or {})
                },
                parent=parent
            )
        
        return trace_id
    
    def end_trace(self, trace_id: str, success: bool = True) -> Optional[PerformanceData]:
        """
        End a performance trace and record results.
        
        Args:
            trace_id: The trace identifier
            success: Whether the operation succeeded
            
        Returns:
            Optional[PerformanceData]: The completed trace data, or None if not found
        """
        with self.trace_lock:
            if trace_id not in self.traces:
                return None
            
            trace = self.traces.pop(trace_id)
            trace.complete()
            
            # Add success status to metadata
            if trace.metadata is None:
                trace.metadata = {}
            trace.metadata["success"] = success
            
            # Store in historical data
            category = trace.category
            if category not in self.historical_data:
                self.historical_data[category] = []
            
            self.historical_data[category].append(trace)
            
            # Cap the size of historical data
            if len(self.historical_data[category]) > 1000:
                self.historical_data[category].pop(0)
            
            # Check against thresholds
            self._check_threshold(trace)
            
            return trace
    
    def set_threshold(self, category: str, threshold_ms: float) -> None:
        """Set performance threshold for a category."""
        self.thresholds[category] = threshold_ms
        logger.info(f"Set performance threshold for {category}: {threshold_ms}ms")
    
    def _check_threshold(self, trace: PerformanceData) -> None:
        """Check if a trace exceeds its threshold and log accordingly."""
        category = trace.category
        if category in self.thresholds and trace.duration_ms > self.thresholds[category]:
            logger.warning(
                f"Performance threshold exceeded: {trace.name} ({category}) "
                f"took {trace.duration_ms:.2f}ms, threshold is {self.thresholds[category]}ms"
            )
    
    def get_performance_metrics(self) -> Dict[str, Any]:
        """
        Get current performance metrics.
        
        Returns:
            Dict[str, Any]: Current performance metrics by category
        """
        metrics = {}
        
        for category, traces in self.historical_data.items():
            if not traces:
                continue
            
            durations = [t.duration_ms for t in traces if t.duration_ms is not None]
            if not durations:
                continue
            
            metrics[category] = {
                "count": len(durations),
                "average_ms": statistics.mean(durations),
                "median_ms": statistics.median(durations),
                "p95_ms": sorted(durations)[int(len(durations) * 0.95)] if len(durations) >= 20 else None,
                "min_ms": min(durations),
                "max_ms": max(durations),
                "threshold_ms": self.thresholds.get(category),
                "threshold_exceeded_count": sum(1 for d in durations if d > self.thresholds.get(category, float('inf')))
            }
        
        return metrics
    
    def _background_data_writer(self) -> None:
        """Background thread to periodically write performance data to disk."""
        while True:
            try:
                # Only write if we have data
                if not self.historical_data:
                    time.sleep(300)
                    continue
                
                # Create a timestamp for the file
                now = datetime.now()
                filename = f"performance_{now.strftime('%Y%m%d_%H%M%S')}.json"
                filepath = os.path.join(self.storage_dir, filename)
                
                # Prepare data for serialization
                serializable_data = {}
                for category, traces in self.historical_data.items():
                    serializable_data[category] = [
                        {
                            "name": t.name,
                            "start_time": t.start_time,
                            "end_time": t.end_time,
                            "duration_ms": t.duration_ms,
                            "metadata": t.metadata,
                            "parent": t.parent
                        }
                        for t in traces
                    ]
                
                # Get aggregated metrics
                metrics = self.get_performance_metrics()
                
                # Combine data and metrics
                output = {
                    "timestamp": now.isoformat(),
                    "metrics": metrics,
                    "traces": serializable_data
                }
                
                # Write to file
                with open(filepath, 'w') as f:
                    json.dump(output, f, indent=2)
                
                logger.debug(f"Wrote performance data to {filepath}")
                
                # Sleep for 15 minutes
                time.sleep(900)
                
            except Exception as e:
                logger.error(f"Error in performance data writer: {e}")
                time.sleep(60)  # 1 minute on error

# Singleton instance
performance_tracker = PerformanceTracker()
