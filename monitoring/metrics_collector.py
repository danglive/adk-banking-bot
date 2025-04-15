# monitoring/metrics_collector.py
import time
import threading
import logging
from typing import Dict, Any, List, Optional, Set, Counter
import json
import os
from datetime import datetime, timedelta
from dataclasses import dataclass, field



# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@dataclass
class MetricsContext:
    """Context for storing metrics during a request lifecycle."""
    request_id: str
    user_id: str
    session_id: str
    start_time: float = field(default_factory=time.time)
    end_time: Optional[float] = None
    llm_call_count: int = 0
    llm_tokens_in: int = 0
    llm_tokens_out: int = 0
    tool_calls: Counter = field(default_factory=Counter)
    agent_calls: Counter = field(default_factory=Counter)
    guardrail_blocks: int = 0
    errors: List[str] = field(default_factory=list)
    latency_ms: Optional[float] = None
    
    def complete(self):
        """Mark the context as complete and calculate latency."""
        self.end_time = time.time()
        self.latency_ms = (self.end_time - self.start_time) * 1000
        return self

class MetricsCollector:
    """Collects and manages metrics from the banking bot."""
    
    def __init__(self, metrics_dir: str = "metrics"):
        """
        Initialize the metrics collector.
        
        Args:
            metrics_dir: Directory to store metrics data files
        """
        self.metrics_dir = metrics_dir
        self.active_contexts: Dict[str, MetricsContext] = {}
        self.historical_metrics: List[Dict[str, Any]] = []
        self.max_historical = 1000  # Max records to keep in memory
        
        # Create metrics directory if it doesn't exist
        os.makedirs(metrics_dir, exist_ok=True)
        
        # Performance metrics
        self.total_requests = 0
        self.successful_requests = 0
        self.failed_requests = 0
        self.total_latency_ms = 0
        self.tool_usage: Counter = Counter()
        self.agent_usage: Counter = Counter()
        self.guardrail_blocks = 0
        
        # Start background metrics writer
        self._writer_thread = threading.Thread(target=self._background_metrics_writer, daemon=True)
        self._writer_thread.start()
        
        logger.info(f"Metrics collector initialized, storing data in {metrics_dir}")
    
    def start_request(self, request_id: str, user_id: str, session_id: str) -> str:
        """
        Start tracking metrics for a new request.
        
        Args:
            request_id: Unique identifier for the request
            user_id: User identifier
            session_id: Session identifier
            
        Returns:
            str: The request ID for reference
        """
        context = MetricsContext(request_id=request_id, user_id=user_id, session_id=session_id)
        self.active_contexts[request_id] = context
        self.total_requests += 1
        return request_id
    
    def record_llm_call(self, request_id: str, tokens_in: int, tokens_out: int) -> None:
        """Record an LLM API call."""
        if request_id in self.active_contexts:
            context = self.active_contexts[request_id]
            context.llm_call_count += 1
            context.llm_tokens_in += tokens_in
            context.llm_tokens_out += tokens_out
    
    def record_tool_call(self, request_id: str, tool_name: str) -> None:
        """Record a tool invocation."""
        if request_id in self.active_contexts:
            context = self.active_contexts[request_id]
            context.tool_calls[tool_name] += 1
            self.tool_usage[tool_name] += 1
    
    def record_agent_call(self, request_id: str, agent_name: str) -> None:
        """Record an agent invocation."""
        if request_id in self.active_contexts:
            context = self.active_contexts[request_id]
            context.agent_calls[agent_name] += 1
            self.agent_usage[agent_name] += 1
    
    def record_guardrail_block(self, request_id: str, reason: str) -> None:
        """Record a request blocked by a guardrail."""
        if request_id in self.active_contexts:
            context = self.active_contexts[request_id]
            context.guardrail_blocks += 1
            self.guardrail_blocks += 1
    
    def record_error(self, request_id: str, error_message: str) -> None:
        """Record an error that occurred during processing."""
        if request_id in self.active_contexts:
            context = self.active_contexts[request_id]
            context.errors.append(error_message)
    
    def complete_request(self, request_id: str, success: bool = True) -> Optional[MetricsContext]:
        """
        Complete a request context and record final metrics.
        
        Args:
            request_id: The request identifier
            success: Whether the request was successful
            
        Returns:
            Optional[MetricsContext]: The completed context, or None if not found
        """
        if request_id not in self.active_contexts:
            return None
        
        # Get the context and mark it complete
        context = self.active_contexts.pop(request_id)
        context.complete()
        
        # Update aggregate metrics
        if success:
            self.successful_requests += 1
        else:
            self.failed_requests += 1
        
        self.total_latency_ms += context.latency_ms
        
        # Convert to dict for storage
        context_dict = {
            "request_id": context.request_id,
            "user_id": context.user_id,
            "session_id": context.session_id,
            "timestamp": datetime.fromtimestamp(context.start_time).isoformat(),
            "latency_ms": context.latency_ms,
            "llm_call_count": context.llm_call_count,
            "llm_tokens_in": context.llm_tokens_in,
            "llm_tokens_out": context.llm_tokens_out,
            "tool_calls": dict(context.tool_calls),
            "agent_calls": dict(context.agent_calls),
            "guardrail_blocks": context.guardrail_blocks,
            "errors": context.errors,
            "success": success
        }
        
        # Add to historical metrics with capped size
        self.historical_metrics.append(context_dict)
        if len(self.historical_metrics) > self.max_historical:
            self.historical_metrics.pop(0)
        
        return context
    
    def get_current_metrics(self) -> Dict[str, Any]:
        """
        Get current aggregate metrics.
        
        Returns:
            Dict[str, Any]: Current metrics
        """
        avg_latency = 0
        if self.total_requests > 0:
            avg_latency = self.total_latency_ms / self.total_requests
        
        return {
            "total_requests": self.total_requests,
            "successful_requests": self.successful_requests,
            "failed_requests": self.failed_requests,
            "success_rate": self.successful_requests / max(1, self.total_requests),
            "average_latency_ms": avg_latency,
            "top_tools": dict(self.tool_usage.most_common(5)),
            "top_agents": dict(self.agent_usage.most_common(5)),
            "guardrail_blocks": self.guardrail_blocks,
            "active_requests": len(self.active_contexts)
        }
    
    def _background_metrics_writer(self) -> None:
        """Background thread to periodically write metrics to disk."""
        while True:
            try:
                # Create a timestamp for the metrics file
                now = datetime.now()
                filename = f"metrics_{now.strftime('%Y%m%d_%H%M%S')}.json"
                filepath = os.path.join(self.metrics_dir, filename)
                
                # Get a snapshot of the current metrics
                metrics = self.get_current_metrics()
                metrics["timestamp"] = now.isoformat()
                metrics["recent_requests"] = self.historical_metrics[-100:] if self.historical_metrics else []
                
                # Write to file
                with open(filepath, 'w') as f:
                    json.dump(metrics, f, indent=2)
                
                logger.debug(f"Wrote metrics to {filepath}")
                
                # Sleep for 5 minutes
                time.sleep(300)
                
            except Exception as e:
                logger.error(f"Error in metrics writer: {e}")
                time.sleep(60)  # Shorter sleep on error

# Singleton instance
metrics_collector = MetricsCollector()
