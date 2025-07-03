"""
Utils package for the GraphFlow External Stimuli System.

This package provides core utilities for:
- Structured logging with correlation ID support
- Prometheus-based metrics collection
- Input validation and sanitization
"""

from .logging import (
    get_structured_logger,
    create_correlation_id,
    log_stimuli_processed,
    log_processing_error,
    log_system_health,
    log_integration_event
)

from .metrics import MetricsCollector

from .validation import (
    InputValidator,
    ValidationResult
)

from .llm_client import (
    LLMClient,
    OllamaLLMClient,
    OpenAILLMClient,
    MockLLMClient,
    create_llm_client,
    LLMError,
    LLMTimeoutError,
    LLMConnectionError
)

__all__ = [
    # Logging utilities
    "get_structured_logger",
    "create_correlation_id",
    "log_stimuli_processed",
    "log_processing_error",
    "log_system_health",
    "log_integration_event",
    
    # Metrics utilities
    "MetricsCollector",
    
    # Validation utilities
    "InputValidator",
    "ValidationResult",
    
    # LLM Client utilities
    "LLMClient",
    "OllamaLLMClient",
    "OpenAILLMClient",
    "MockLLMClient",
    "create_llm_client",
    "LLMError",
    "LLMTimeoutError",
    "LLMConnectionError"
]