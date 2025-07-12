"""
Comprehensive Error Handling System
==================================

Standardized error handling, logging, and recovery across the CORE system.
"""

import asyncio
import logging
import traceback
import time
from contextlib import asynccontextmanager
from dataclasses import dataclass
from datetime import datetime, timedelta
from enum import Enum
from typing import Dict, Any, Optional, Callable, Type, Union
import sys

from ..config import get_config
from ..di import ServiceLifecycle, singleton


logger = logging.getLogger(__name__)


class ErrorSeverity(str, Enum):
    """Error severity levels"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class ErrorCategory(str, Enum):
    """Error categories for better classification"""
    SYSTEM = "system"
    NETWORK = "network"
    DATABASE = "database"
    VALIDATION = "validation"
    BUSINESS_LOGIC = "business_logic"
    EXTERNAL_SERVICE = "external_service"
    CONFIGURATION = "configuration"
    SECURITY = "security"


@dataclass
class ErrorContext:
    """Error context information"""
    operation: str
    component: str
    user_id: Optional[str] = None
    session_id: Optional[str] = None
    request_id: Optional[str] = None
    metadata: Dict[str, Any] = None
    
    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}


@dataclass
class ErrorRecord:
    """Comprehensive error record"""
    id: str
    timestamp: datetime
    severity: ErrorSeverity
    category: ErrorCategory
    error_type: str
    message: str
    traceback: str
    context: ErrorContext
    resolved: bool = False
    resolution_time: Optional[datetime] = None
    resolution_notes: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for logging/storage"""
        return {
            'id': self.id,
            'timestamp': self.timestamp.isoformat(),
            'severity': self.severity.value,
            'category': self.category.value,
            'error_type': self.error_type,
            'message': self.message,
            'traceback': self.traceback,
            'context': {
                'operation': self.context.operation,
                'component': self.context.component,
                'user_id': self.context.user_id,
                'session_id': self.context.session_id,
                'request_id': self.context.request_id,
                'metadata': self.context.metadata
            },
            'resolved': self.resolved,
            'resolution_time': self.resolution_time.isoformat() if self.resolution_time else None,
            'resolution_notes': self.resolution_notes
        }


class CoreException(Exception):
    """Base exception for CORE system with enhanced context"""
    
    def __init__(
        self,
        message: str,
        severity: ErrorSeverity = ErrorSeverity.MEDIUM,
        category: ErrorCategory = ErrorCategory.SYSTEM,
        context: Optional[ErrorContext] = None,
        cause: Optional[Exception] = None
    ):
        super().__init__(message)
        self.message = message
        self.severity = severity
        self.category = category
        self.context = context
        self.cause = cause
        self.timestamp = datetime.now()


class ValidationError(CoreException):
    """Data validation errors"""
    
    def __init__(self, message: str, field: str = None, value: Any = None, **kwargs):
        context = kwargs.get('context') or ErrorContext(
            operation="validation",
            component="validator",
            metadata={'field': field, 'value': str(value) if value is not None else None}
        )
        super().__init__(
            message,
            severity=ErrorSeverity.LOW,
            category=ErrorCategory.VALIDATION,
            context=context,
            **kwargs
        )


class NetworkError(CoreException):
    """Network-related errors"""
    
    def __init__(self, message: str, endpoint: str = None, **kwargs):
        context = kwargs.get('context') or ErrorContext(
            operation="network_request",
            component="network",
            metadata={'endpoint': endpoint}
        )
        super().__init__(
            message,
            severity=ErrorSeverity.HIGH,
            category=ErrorCategory.NETWORK,
            context=context,
            **kwargs
        )


class DatabaseError(CoreException):
    """Database-related errors"""
    
    def __init__(self, message: str, query: str = None, **kwargs):
        context = kwargs.get('context') or ErrorContext(
            operation="database_operation",
            component="database",
            metadata={'query': query}
        )
        super().__init__(
            message,
            severity=ErrorSeverity.HIGH,
            category=ErrorCategory.DATABASE,
            context=context,
            **kwargs
        )


class ExternalServiceError(CoreException):
    """External service errors"""
    
    def __init__(self, message: str, service: str = None, **kwargs):
        context = kwargs.get('context') or ErrorContext(
            operation="external_service_call",
            component="external_service",
            metadata={'service': service}
        )
        super().__init__(
            message,
            severity=ErrorSeverity.MEDIUM,
            category=ErrorCategory.EXTERNAL_SERVICE,
            context=context,
            **kwargs
        )


class CircuitBreakerError(CoreException):
    """Circuit breaker triggered"""
    
    def __init__(self, service: str, **kwargs):
        super().__init__(
            f"Circuit breaker open for service: {service}",
            severity=ErrorSeverity.HIGH,
            category=ErrorCategory.EXTERNAL_SERVICE,
            **kwargs
        )


class CircuitBreaker:
    """Circuit breaker pattern implementation"""
    
    def __init__(
        self,
        failure_threshold: int = 5,
        recovery_timeout: float = 60.0,
        expected_exceptions: tuple = (Exception,)
    ):
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.expected_exceptions = expected_exceptions
        
        self.failure_count = 0
        self.last_failure_time = None
        self.state = "closed"  # closed, open, half_open
    
    async def call(self, func: Callable, *args, **kwargs):
        """Execute function with circuit breaker protection"""
        if self.state == "open":
            if self._should_attempt_reset():
                self.state = "half_open"
            else:
                raise CircuitBreakerError("circuit_breaker")
        
        try:
            result = await func(*args, **kwargs) if asyncio.iscoroutinefunction(func) else func(*args, **kwargs)
            self._on_success()
            return result
            
        except self.expected_exceptions as e:
            self._on_failure()
            raise e
    
    def _should_attempt_reset(self) -> bool:
        """Check if enough time has passed to attempt reset"""
        return (
            self.last_failure_time and
            time.time() - self.last_failure_time >= self.recovery_timeout
        )
    
    def _on_success(self):
        """Handle successful call"""
        self.failure_count = 0
        self.state = "closed"
    
    def _on_failure(self):
        """Handle failed call"""
        self.failure_count += 1
        self.last_failure_time = time.time()
        
        if self.failure_count >= self.failure_threshold:
            self.state = "open"


@singleton()
class ErrorHandler(ServiceLifecycle):
    """
    Centralized error handling service.
    
    Features:
    - Structured error logging
    - Error categorization and severity
    - Circuit breaker pattern
    - Error recovery strategies
    - Metrics and monitoring
    """
    
    def __init__(self):
        self.error_records: Dict[str, ErrorRecord] = {}
        self.circuit_breakers: Dict[str, CircuitBreaker] = {}
        self.error_handlers: Dict[Type[Exception], Callable] = {}
        self.recovery_strategies: Dict[str, Callable] = {}
        self._running = False
    
    async def start(self):
        """Start error handler service"""
        self._running = True
        
        # Register default error handlers
        self.register_error_handler(NetworkError, self._handle_network_error)
        self.register_error_handler(DatabaseError, self._handle_database_error)
        self.register_error_handler(ExternalServiceError, self._handle_external_service_error)
        
        logger.info("Error handler service started")
    
    async def stop(self):
        """Stop error handler service"""
        self._running = False
        logger.info("Error handler service stopped")
    
    async def health_check(self) -> bool:
        """Check if error handler is healthy"""
        return self._running
    
    def register_error_handler(
        self,
        exception_type: Type[Exception],
        handler: Callable[[Exception, ErrorContext], Any]
    ):
        """Register custom error handler for specific exception type"""
        self.error_handlers[exception_type] = handler
    
    def register_recovery_strategy(
        self,
        strategy_name: str,
        strategy: Callable[[ErrorRecord], bool]
    ):
        """Register error recovery strategy"""
        self.recovery_strategies[strategy_name] = strategy
    
    def get_circuit_breaker(
        self,
        service_name: str,
        failure_threshold: int = 5,
        recovery_timeout: float = 60.0
    ) -> CircuitBreaker:
        """Get or create circuit breaker for service"""
        if service_name not in self.circuit_breakers:
            self.circuit_breakers[service_name] = CircuitBreaker(
                failure_threshold=failure_threshold,
                recovery_timeout=recovery_timeout
            )
        return self.circuit_breakers[service_name]
    
    async def handle_error(
        self,
        error: Exception,
        context: Optional[ErrorContext] = None,
        auto_recover: bool = True
    ) -> ErrorRecord:
        """
        Handle an error with full context and recovery.
        
        Args:
            error: The exception that occurred
            context: Error context information
            auto_recover: Whether to attempt automatic recovery
        
        Returns:
            ErrorRecord with details
        """
        # Create error record
        error_record = self._create_error_record(error, context)
        
        # Store error record
        self.error_records[error_record.id] = error_record
        
        # Log error
        self._log_error(error_record)
        
        # Try custom error handler
        await self._try_custom_handler(error, context)
        
        # Attempt recovery if enabled
        if auto_recover:
            await self._attempt_recovery(error_record)
        
        return error_record
    
    def _create_error_record(
        self,
        error: Exception,
        context: Optional[ErrorContext]
    ) -> ErrorRecord:
        """Create comprehensive error record"""
        import uuid
        
        # Extract info from CoreException or create defaults
        if isinstance(error, CoreException):
            severity = error.severity
            category = error.category
            context = context or error.context
        else:
            severity = ErrorSeverity.MEDIUM
            category = ErrorCategory.SYSTEM
        
        # Default context if none provided
        if context is None:
            context = ErrorContext(
                operation="unknown",
                component="unknown"
            )
        
        return ErrorRecord(
            id=str(uuid.uuid4()),
            timestamp=datetime.now(),
            severity=severity,
            category=category,
            error_type=type(error).__name__,
            message=str(error),
            traceback=traceback.format_exc(),
            context=context
        )
    
    def _log_error(self, error_record: ErrorRecord):
        """Log error with appropriate level"""
        log_data = error_record.to_dict()
        
        if error_record.severity == ErrorSeverity.CRITICAL:
            logger.critical(f"CRITICAL ERROR: {error_record.message}", extra=log_data)
        elif error_record.severity == ErrorSeverity.HIGH:
            logger.error(f"HIGH SEVERITY: {error_record.message}", extra=log_data)
        elif error_record.severity == ErrorSeverity.MEDIUM:
            logger.warning(f"MEDIUM SEVERITY: {error_record.message}", extra=log_data)
        else:
            logger.info(f"LOW SEVERITY: {error_record.message}", extra=log_data)
    
    async def _try_custom_handler(
        self,
        error: Exception,
        context: Optional[ErrorContext]
    ):
        """Try to run custom error handler"""
        error_type = type(error)
        
        if error_type in self.error_handlers:
            try:
                handler = self.error_handlers[error_type]
                await handler(error, context)
            except Exception as e:
                logger.error(f"Error in custom error handler: {e}")
    
    async def _attempt_recovery(self, error_record: ErrorRecord):
        """Attempt error recovery based on category"""
        recovery_strategy = f"recover_{error_record.category.value}"
        
        if recovery_strategy in self.recovery_strategies:
            try:
                strategy = self.recovery_strategies[recovery_strategy]
                success = await strategy(error_record)
                
                if success:
                    error_record.resolved = True
                    error_record.resolution_time = datetime.now()
                    error_record.resolution_notes = f"Auto-recovered using {recovery_strategy}"
                    logger.info(f"Auto-recovered error {error_record.id}")
                
            except Exception as e:
                logger.error(f"Error in recovery strategy {recovery_strategy}: {e}")
    
    async def _handle_network_error(self, error: NetworkError, context: ErrorContext):
        """Handle network errors"""
        # Could implement retry logic, circuit breaking, etc.
        logger.info(f"Handling network error for {context.metadata.get('endpoint')}")
    
    async def _handle_database_error(self, error: DatabaseError, context: ErrorContext):
        """Handle database errors"""
        # Could implement connection retry, query optimization, etc.
        logger.info(f"Handling database error for operation {context.operation}")
    
    async def _handle_external_service_error(
        self,
        error: ExternalServiceError,
        context: ErrorContext
    ):
        """Handle external service errors"""
        service = context.metadata.get('service')
        if service:
            # Trigger circuit breaker
            circuit_breaker = self.get_circuit_breaker(service)
            logger.info(f"External service error for {service}, circuit breaker state: {circuit_breaker.state}")
    
    def get_error_stats(self) -> Dict[str, Any]:
        """Get error statistics"""
        if not self.error_records:
            return {}
        
        total_errors = len(self.error_records)
        resolved_errors = sum(1 for record in self.error_records.values() if record.resolved)
        
        # Group by severity
        severity_counts = {}
        for severity in ErrorSeverity:
            severity_counts[severity.value] = sum(
                1 for record in self.error_records.values()
                if record.severity == severity
            )
        
        # Group by category
        category_counts = {}
        for category in ErrorCategory:
            category_counts[category.value] = sum(
                1 for record in self.error_records.values()
                if record.category == category
            )
        
        return {
            'total_errors': total_errors,
            'resolved_errors': resolved_errors,
            'resolution_rate': resolved_errors / total_errors if total_errors > 0 else 0,
            'severity_breakdown': severity_counts,
            'category_breakdown': category_counts,
            'circuit_breaker_states': {
                name: cb.state for name, cb in self.circuit_breakers.items()
            }
        }


# Context managers and decorators
@asynccontextmanager
async def error_context(
    operation: str,
    component: str,
    **context_kwargs
):
    """Context manager for automatic error handling"""
    from ..di import get_container
    
    context = ErrorContext(
        operation=operation,
        component=component,
        **context_kwargs
    )
    
    try:
        yield context
    except Exception as e:
        error_handler = get_container().get(ErrorHandler)
        await error_handler.handle_error(e, context)
        raise


def handle_errors(
    operation: str = None,
    component: str = None,
    auto_recover: bool = True
):
    """Decorator for automatic error handling"""
    def decorator(func):
        async def async_wrapper(*args, **kwargs):
            context = ErrorContext(
                operation=operation or func.__name__,
                component=component or func.__module__
            )
            
            try:
                return await func(*args, **kwargs)
            except Exception as e:
                from ..di import get_container
                error_handler = get_container().get(ErrorHandler)
                await error_handler.handle_error(e, context, auto_recover)
                raise
        
        def sync_wrapper(*args, **kwargs):
            context = ErrorContext(
                operation=operation or func.__name__,
                component=component or func.__module__
            )
            
            try:
                return func(*args, **kwargs)
            except Exception as e:
                # For sync functions, we can't use async error handling
                # So just log and re-raise
                logger.error(f"Error in {context.component}.{context.operation}: {e}")
                raise
        
        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        else:
            return sync_wrapper
    
    return decorator


# Convenience functions
async def safe_call(
    func: Callable,
    *args,
    operation: str = None,
    component: str = None,
    default_return: Any = None,
    **kwargs
):
    """
    Safely call a function with error handling.
    
    Returns default_return if an error occurs.
    """
    try:
        async with error_context(
            operation=operation or func.__name__,
            component=component or "safe_call"
        ):
            if asyncio.iscoroutinefunction(func):
                return await func(*args, **kwargs)
            else:
                return func(*args, **kwargs)
    except Exception:
        return default_return