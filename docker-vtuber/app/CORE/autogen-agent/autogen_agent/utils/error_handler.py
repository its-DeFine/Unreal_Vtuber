"""
Centralized Error Handling Utilities
====================================

Provides consistent error handling, logging, and recovery mechanisms
across all components of the system.
"""

import logging
import traceback
import time
from typing import Dict, Any, Optional, Callable
from datetime import datetime, timedelta
from functools import wraps

from ..config.processing_config import LoggingConfig


class ErrorHandler:
    """Centralized error handling with consistent logging and recovery."""
    
    def __init__(self):
        self.error_counts: Dict[str, int] = {}
        self.last_error_times: Dict[str, datetime] = {}
        
    def log_with_traceback(
        self, 
        component: str, 
        operation: str, 
        error: Exception,
        include_traceback: bool = True,
        context: Optional[Dict[str, Any]] = None
    ) -> None:
        """
        Log error with optional traceback and context information.
        
        Args:
            component: Component name (e.g., "queue", "team", "character")
            operation: Operation that failed (e.g., "process_item", "initialize")
            error: The exception that occurred
            include_traceback: Whether to include full traceback
            context: Additional context information
        """
        emoji = LoggingConfig.MESSAGE_PREFIX_EMOJI.get("error", "❌")
        component_padded = component.upper().ljust(LoggingConfig.COMPONENT_WIDTH)
        
        # Basic error message
        error_msg = f"{emoji} [{component_padded}] {operation} failed: {error}"
        
        # Add context if provided
        if context:
            context_str = ", ".join(f"{k}={v}" for k, v in context.items())
            error_msg += f" (Context: {context_str})"
        
        # Log the error
        logging.error(error_msg)
        
        # Add traceback if requested and not rate limited
        if include_traceback and self._should_log_traceback(component, operation):
            logging.debug(f"Traceback for {operation}: {traceback.format_exc()}")
    
    def _should_log_traceback(self, component: str, operation: str) -> bool:
        """Rate limit traceback logging to avoid spam."""
        key = f"{component}:{operation}"
        now = datetime.now()
        
        # Check if we've logged this error recently
        last_time = self.last_error_times.get(key)
        if last_time and now - last_time < timedelta(minutes=1):
            self.error_counts[key] = self.error_counts.get(key, 0) + 1
            return self.error_counts[key] <= LoggingConfig.MAX_ERROR_LOGS_PER_MINUTE
        
        # Reset counters for new minute
        self.error_counts[key] = 1
        self.last_error_times[key] = now
        return True
    
    def log_success(
        self, 
        component: str, 
        operation: str, 
        duration: Optional[float] = None,
        context: Optional[Dict[str, Any]] = None
    ) -> None:
        """Log successful operation with timing and context."""
        emoji = LoggingConfig.MESSAGE_PREFIX_EMOJI.get("success", "✅")
        component_padded = component.upper().ljust(LoggingConfig.COMPONENT_WIDTH)
        
        msg = f"{emoji} [{component_padded}] {operation} completed"
        
        if duration is not None:
            msg += f" in {duration:.2f}s"
            # Log slow operations as warnings
            if duration > LoggingConfig.SLOW_OPERATION_THRESHOLD:
                emoji = LoggingConfig.MESSAGE_PREFIX_EMOJI.get("warning", "⚠️")
                msg = f"{emoji} [{component_padded}] {operation} completed slowly in {duration:.2f}s"
                logging.warning(msg)
                return
        
        if context:
            context_str = ", ".join(f"{k}={v}" for k, v in context.items())
            msg += f" (Details: {context_str})"
        
        logging.info(msg)
    
    def log_warning(
        self, 
        component: str, 
        message: str, 
        context: Optional[Dict[str, Any]] = None
    ) -> None:
        """Log warning with consistent formatting."""
        emoji = LoggingConfig.MESSAGE_PREFIX_EMOJI.get("warning", "⚠️")
        component_padded = component.upper().ljust(LoggingConfig.COMPONENT_WIDTH)
        
        msg = f"{emoji} [{component_padded}] {message}"
        
        if context:
            context_str = ", ".join(f"{k}={v}" for k, v in context.items())
            msg += f" (Context: {context_str})"
        
        logging.warning(msg)


def with_error_handling(
    component: str, 
    operation: str = None,
    raise_on_error: bool = True,
    default_return = None
):
    """
    Decorator for consistent error handling across methods.
    
    Args:
        component: Component name for logging
        operation: Operation name (defaults to function name)
        raise_on_error: Whether to re-raise exceptions
        default_return: Value to return on error if not re-raising
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def async_wrapper(*args, **kwargs):
            error_handler = ErrorHandler()
            op_name = operation or func.__name__
            start_time = time.time()
            
            try:
                result = await func(*args, **kwargs)
                duration = time.time() - start_time
                error_handler.log_success(component, op_name, duration)
                return result
                
            except Exception as e:
                duration = time.time() - start_time
                context = {
                    "duration": f"{duration:.2f}s",
                    "args_count": len(args),
                    "kwargs_keys": list(kwargs.keys())
                }
                error_handler.log_with_traceback(component, op_name, e, context=context)
                
                if raise_on_error:
                    raise
                return default_return
        
        @wraps(func)
        def sync_wrapper(*args, **kwargs):
            error_handler = ErrorHandler()
            op_name = operation or func.__name__
            start_time = time.time()
            
            try:
                result = func(*args, **kwargs)
                duration = time.time() - start_time
                error_handler.log_success(component, op_name, duration)
                return result
                
            except Exception as e:
                duration = time.time() - start_time
                context = {
                    "duration": f"{duration:.2f}s",
                    "args_count": len(args),
                    "kwargs_keys": list(kwargs.keys())
                }
                error_handler.log_with_traceback(component, op_name, e, context=context)
                
                if raise_on_error:
                    raise
                return default_return
        
        # Return appropriate wrapper based on function type
        import inspect
        if inspect.iscoroutinefunction(func):
            return async_wrapper
        else:
            return sync_wrapper
    
    return decorator


# Global instance for easy access
error_handler = ErrorHandler()