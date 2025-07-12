"""
Comprehensive Error Handling System
==================================

Standardized error handling, logging, and recovery across the CORE system.
"""

from .error_handler import (
    ErrorHandler,
    ErrorSeverity,
    ErrorCategory,
    ErrorContext,
    ErrorRecord,
    CoreException,
    ValidationError,
    NetworkError,
    DatabaseError,
    ExternalServiceError,
    CircuitBreakerError,
    CircuitBreaker,
    error_context,
    handle_errors,
    safe_call
)

__all__ = [
    "ErrorHandler",
    "ErrorSeverity",
    "ErrorCategory", 
    "ErrorContext",
    "ErrorRecord",
    "CoreException",
    "ValidationError",
    "NetworkError",
    "DatabaseError",
    "ExternalServiceError",
    "CircuitBreakerError",
    "CircuitBreaker",
    "error_context",
    "handle_errors",
    "safe_call"
]