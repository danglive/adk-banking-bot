# monitoring/logger.py (tiếp theo)
import logging
import os
import pytest
import json
import threading
import traceback
from datetime import datetime
from typing import Dict, Any, Optional
from logging.handlers import RotatingFileHandler
import tempfile

class JSONFormatter(logging.Formatter):
    """Format log records as JSON for better parsing."""
    
    def __init__(self, **kwargs):
        self.kwargs = kwargs
        super().__init__()
    
    def format(self, record):
        log_data = {
            "timestamp": datetime.fromtimestamp(record.created).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno,
            "thread": record.thread,
            "process": record.process
        }
        
        # Add extra context from kwargs
        for key, value in self.kwargs.items():
            if key not in log_data:
                log_data[key] = value
        
        # Add extra context from record
        if hasattr(record, 'request_id'):
            log_data['request_id'] = record.request_id
        
        if hasattr(record, 'user_id'):
            log_data['user_id'] = record.user_id
        
        # Include exception info if present
        if record.exc_info:
            log_data['exception'] = {
                'type': record.exc_info[0].__name__,
                'value': str(record.exc_info[1]),
                'traceback': traceback.format_exception(*record.exc_info)
            }
        
        return json.dumps(log_data)

class StructuredLoggerAdapter(logging.LoggerAdapter):
    """Logger adapter that adds structured context to log records."""
    
    def process(self, msg, kwargs):
        # Add extra context to the record
        if 'extra' not in kwargs:
            kwargs['extra'] = {}
        
        # Add all context items to extra
        for key, value in self.extra.items():
            kwargs['extra'][key] = value
        
        return msg, kwargs

class LogManager:
    """Manages logging configuration and provides structured loggers."""
    
    def __init__(self, log_dir: str = "logs"):
        self.log_dir = log_dir

        # Default context (application-wide)
        self.default_context = {
            "app": "banking_bot",
            "environment": os.getenv("ENVIRONMENT", "development")
        }

        # Create logs directory
        os.makedirs(log_dir, exist_ok=True)

        # Configure root logger
        self.configure_root_logger()

        # Thread-local storage for request context
        self.context = threading.local()

        logger = logging.getLogger(__name__)
        logger.info(f"Log manager initialized, storing logs in {log_dir}")

        
    def configure_root_logger(self) -> None:
        """Configure the root logger with console and file handlers."""
        root_logger = logging.getLogger()
        root_logger.setLevel(logging.INFO)
        
        # Clear existing handlers
        for handler in root_logger.handlers[:]:
            root_logger.removeHandler(handler)
        
        # Console handler (plain text for readability)
        console_handler = logging.StreamHandler()
        console_handler.setLevel(logging.INFO)
        console_formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        console_handler.setFormatter(console_formatter)
        root_logger.addHandler(console_handler)
        
        # File handler (JSON for parsing)
        main_log_file = os.path.join(self.log_dir, "banking_bot.log")
        file_handler = RotatingFileHandler(
            main_log_file, maxBytes=10*1024*1024, backupCount=5
        )
        file_handler.setLevel(logging.INFO)
        file_formatter = JSONFormatter(**self.default_context)
        file_handler.setFormatter(file_formatter)
        root_logger.addHandler(file_handler)
        
        # Error log file (separate file for errors and above)
        error_log_file = os.path.join(self.log_dir, "errors.log")
        error_handler = RotatingFileHandler(
            error_log_file, maxBytes=10*1024*1024, backupCount=5
        )
        error_handler.setLevel(logging.ERROR)
        error_handler.setFormatter(file_formatter)
        root_logger.addHandler(error_handler)
    
    def get_logger(self, name: str, **context) -> logging.Logger:
        """
        Get a logger with context information.
        
        Args:
            name: Logger name
            **context: Additional context to include in logs
            
        Returns:
            logging.Logger: A logger instance
        """
        logger = logging.getLogger(name)
        
        # Combine default context, thread-local context, and provided context
        combined_context = {**self.default_context}
        
        if hasattr(self.context, 'data'):
            combined_context.update(self.context.data)
        
        combined_context.update(context)
        
        return StructuredLoggerAdapter(logger, combined_context)
    
    def set_context(self, **context) -> None:
        """
        Set context for the current thread.
        
        Args:
            **context: Context key-value pairs
        """
        if not hasattr(self.context, 'data'):
            self.context.data = {}
        
        self.context.data.update(context)
    
    def clear_context(self) -> None:
        """Clear the context for the current thread."""
        if hasattr(self.context, 'data'):
            del self.context.data
    
    def log_request(self, request_id: str, user_id: str, method: str, path: str, 
                   params: Dict[str, Any] = None) -> None:
        """
        Log an API request with standardized format.
        
        Args:
            request_id: Request identifier
            user_id: User identifier
            method: HTTP method
            path: Request path
            params: Request parameters (sanitized)
        """
        logger = self.get_logger("api.request", request_id=request_id, user_id=user_id)
        logger.info(f"{method} {path}", extra={
            "http_method": method,
            "path": path,
            "params": params or {}
        })
    
    def log_response(self, request_id: str, status_code: int, 
                    duration_ms: float, error: Optional[str] = None) -> None:
        """
        Log an API response with standardized format.
        
        Args:
            request_id: Request identifier
            status_code: HTTP status code
            duration_ms: Request duration in milliseconds
            error: Error message if applicable
        """
        logger = self.get_logger("api.response", request_id=request_id)
        
        log_data = {
            "status_code": status_code,
            "duration_ms": duration_ms
        }
        
        if error:
            log_data["error"] = error
            logger.error(f"Response {status_code} in {duration_ms:.2f}ms - {error}", 
                       extra=log_data)
        else:
            logger.info(f"Response {status_code} in {duration_ms:.2f}ms", 
                      extra=log_data)

# Singleton instance
log_manager = LogManager()
