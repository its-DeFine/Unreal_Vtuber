"""
Structured logging utilities for GraphFlow system.

This module provides structured logging capabilities with consistent
formatting and metadata handling.
"""

import logging
import structlog
from typing import Any, Dict, Optional
import sys
import json
import uuid
from datetime import datetime


# Configure structlog processors
structlog.configure(
    processors=[
        structlog.stdlib.filter_by_level,
        structlog.stdlib.add_logger_name,
        structlog.stdlib.add_log_level,
        structlog.stdlib.PositionalArgumentsFormatter(),
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
        structlog.processors.UnicodeDecoder(),
        structlog.processors.JSONRenderer()
    ],
    context_class=dict,
    logger_factory=structlog.stdlib.LoggerFactory(),
    cache_logger_on_first_use=True,
)


def create_correlation_id() -> str:
    """
    Generate a unique correlation ID for tracking requests.
    
    Returns:
        UUID-based correlation ID as string
    """
    return str(uuid.uuid4())


def get_structured_logger(name: str) -> structlog.BoundLogger:
    """
    Get a structured logger with consistent configuration.
    
    Args:
        name: Logger name (typically module name)
        
    Returns:
        Configured structured logger instance
    """
    # Create stdlib logger
    stdlib_logger = logging.getLogger(name)
    
    # Set level from environment or default
    import os
    log_level = os.getenv("GRAPHFLOW_LOG_LEVEL", "INFO")
    stdlib_logger.setLevel(getattr(logging, log_level.upper()))
    
    # Add handler if not already present
    if not stdlib_logger.handlers:
        handler = logging.StreamHandler(sys.stdout)
        handler.setFormatter(StructuredFormatter())
        stdlib_logger.addHandler(handler)
    
    # Wrap with structlog
    return structlog.get_logger(name).bind(
        service="graphflow-gateway",
        version="1.0.0"
    )


class StructuredFormatter(logging.Formatter):
    """
    Custom formatter for structured logging output.
    
    Formats log records as JSON with consistent structure.
    """
    
    def format(self, record: logging.LogRecord) -> str:
        """
        Format log record as structured JSON.
        
        Args:
            record: Log record to format
            
        Returns:
            JSON formatted log string
        """
        # Base log structure
        log_data = {
            "timestamp": datetime.utcnow().isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "service": "graphflow-gateway",
        }
        
        # Add extra fields
        if hasattr(record, "stimuli_id"):
            log_data["stimuli_id"] = record.stimuli_id
        if hasattr(record, "execution_plan_id"):
            log_data["execution_plan_id"] = record.execution_plan_id
        if hasattr(record, "processing_time"):
            log_data["processing_time"] = record.processing_time
        if hasattr(record, "error"):
            log_data["error"] = record.error
        
        # Add exception info if present
        if record.exc_info:
            log_data["exception"] = self.formatException(record.exc_info)
        
        # Add any additional context
        for key, value in record.__dict__.items():
            if key not in ["name", "msg", "args", "created", "filename", 
                          "funcName", "levelname", "levelno", "lineno", 
                          "module", "msecs", "pathname", "process", "processName",
                          "relativeCreated", "thread", "threadName", "exc_info",
                          "exc_text", "stack_info", "getMessage"]:
                log_data[key] = value
        
        return json.dumps(log_data)


class LogContext:
    """
    Context manager for adding temporary log context.
    
    Usage:
        with LogContext(logger, stimuli_id="123", category="USER"):
            logger.info("Processing stimuli")
    """
    
    def __init__(self, logger: structlog.BoundLogger, **kwargs):
        """
        Initialize log context.
        
        Args:
            logger: Structured logger instance
            **kwargs: Context key-value pairs to bind
        """
        self.logger = logger
        self.context = kwargs
        self.original_logger = None
    
    def __enter__(self):
        """Enter context and bind values."""
        self.original_logger = self.logger
        self.logger = self.logger.bind(**self.context)
        return self.logger
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Exit context and restore original logger."""
        self.logger = self.original_logger


# Logging utilities for specific use cases

def log_stimuli_processing(
    logger: structlog.BoundLogger,
    stimuli_id: str,
    stage: str,
    **kwargs
) -> None:
    """
    Log stimuli processing events with consistent structure.
    
    Args:
        logger: Logger instance
        stimuli_id: Stimuli identifier
        stage: Processing stage name
        **kwargs: Additional log data
    """
    logger.info(
        "Stimuli processing",
        stimuli_id=stimuli_id,
        processing_stage=stage,
        **kwargs
    )


def log_execution_result(
    logger: structlog.BoundLogger,
    execution_plan_id: str,
    success: bool,
    execution_time: float,
    **kwargs
) -> None:
    """
    Log execution results with consistent structure.
    
    Args:
        logger: Logger instance
        execution_plan_id: Execution plan identifier
        success: Whether execution was successful
        execution_time: Time taken for execution
        **kwargs: Additional log data
    """
    if success:
        logger.info(
            "Execution completed",
            execution_plan_id=execution_plan_id,
            success=success,
            execution_time=execution_time,
            **kwargs
        )
    else:
        logger.error(
            "Execution failed",
            execution_plan_id=execution_plan_id,
            success=success,
            execution_time=execution_time,
            **kwargs
        )


def log_decision(
    logger: structlog.BoundLogger,
    stimuli_id: str,
    decision: str,
    confidence: float,
    reasoning: str,
    **kwargs
) -> None:
    """
    Log routing decisions with consistent structure.
    
    Args:
        logger: Logger instance
        stimuli_id: Stimuli identifier
        decision: Decision made
        confidence: Confidence score
        reasoning: Decision reasoning
        **kwargs: Additional log data
    """
    logger.info(
        "Routing decision",
        stimuli_id=stimuli_id,
        decision=decision,
        confidence=confidence,
        reasoning=reasoning,
        **kwargs
    )


def log_performance_metric(
    logger: structlog.BoundLogger,
    metric_name: str,
    value: float,
    unit: str,
    **kwargs
) -> None:
    """
    Log performance metrics with consistent structure.
    
    Args:
        logger: Logger instance
        metric_name: Name of the metric
        value: Metric value
        unit: Unit of measurement
        **kwargs: Additional log data
    """
    logger.info(
        "Performance metric",
        metric_name=metric_name,
        metric_value=value,
        metric_unit=unit,
        **kwargs
    )


# Configure root logger for the package
def configure_logging(
    log_level: str = "INFO",
    log_file: Optional[str] = None,
    enable_json: bool = True
) -> None:
    """
    Configure logging for the entire GraphFlow system.
    
    Args:
        log_level: Logging level (DEBUG, INFO, WARNING, ERROR)
        log_file: Optional log file path
        enable_json: Whether to use JSON formatting
    """
    # Set root logger level
    logging.root.setLevel(getattr(logging, log_level.upper()))
    
    # Clear existing handlers
    logging.root.handlers.clear()
    
    # Console handler
    console_handler = logging.StreamHandler(sys.stdout)
    if enable_json:
        console_handler.setFormatter(StructuredFormatter())
    else:
        console_handler.setFormatter(
            logging.Formatter(
                "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
            )
        )
    logging.root.addHandler(console_handler)
    
    # File handler if specified
    if log_file:
        file_handler = logging.FileHandler(log_file)
        if enable_json:
            file_handler.setFormatter(StructuredFormatter())
        else:
            file_handler.setFormatter(
                logging.Formatter(
                    "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
                )
            )
        logging.root.addHandler(file_handler)


def log_stimuli_processed(
    logger: structlog.BoundLogger,
    stimuli_id: str,
    processing_time: float,
    **kwargs
) -> None:
    """
    Log stimuli processing completion.
    
    Args:
        logger: Logger instance
        stimuli_id: Stimuli identifier
        processing_time: Time taken to process
        **kwargs: Additional log data
    """
    logger.info(
        "Stimuli processed",
        stimuli_id=stimuli_id,
        processing_time=processing_time,
        **kwargs
    )


def log_processing_error(
    logger: structlog.BoundLogger,
    stimuli_id: str,
    error: str,
    **kwargs
) -> None:
    """
    Log processing error.
    
    Args:
        logger: Logger instance
        stimuli_id: Stimuli identifier
        error: Error description
        **kwargs: Additional log data
    """
    logger.error(
        "Processing error",
        stimuli_id=stimuli_id,
        error=error,
        **kwargs
    )


def log_system_health(
    logger: structlog.BoundLogger,
    component: str,
    status: str,
    **kwargs
) -> None:
    """
    Log system health status.
    
    Args:
        logger: Logger instance
        component: Component name
        status: Health status
        **kwargs: Additional log data
    """
    logger.info(
        "System health",
        component=component,
        status=status,
        **kwargs
    )


def log_integration_event(
    logger: structlog.BoundLogger,
    integration: str,
    event: str,
    **kwargs
) -> None:
    """
    Log integration event.
    
    Args:
        logger: Logger instance
        integration: Integration name
        event: Event description
        **kwargs: Additional log data
    """
    logger.info(
        "Integration event",
        integration=integration,
        event=event,
        **kwargs
    )