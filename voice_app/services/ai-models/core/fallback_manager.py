#!/usr/bin/env python3
"""
Model Fallback and Error Recovery System
========================================

Comprehensive fallback management and error recovery for AI model services.
Ensures high availability and reliability through intelligent fallback strategies
and automatic error recovery mechanisms.

Features:
- Multi-tier fallback strategies
- Automatic error detection and recovery
- Circuit breaker patterns
- Health-based model selection
- Graceful degradation
- Recovery monitoring and analytics
"""

import logging
import asyncio
import time
import threading
from typing import Dict, List, Optional, Any, Callable, Union, Tuple
from dataclasses import dataclass, field
from enum import Enum
from datetime import datetime, timedelta
from collections import defaultdict, deque

from .model_manager import BaseModel, ModelState, ModelManager
from ..utils.performance_metrics import PerformanceMetrics, TimingContext


# =============================================================================
# FALLBACK CONFIGURATION
# =============================================================================

class FallbackStrategy(Enum):
    """Fallback strategy types"""
    ROUND_ROBIN = "round_robin"        # Cycle through available models
    PRIORITY_BASED = "priority_based"  # Use highest priority available
    LOAD_BALANCED = "load_balanced"    # Balance load across models
    PERFORMANCE_BASED = "performance_based"  # Use best performing model
    CIRCUIT_BREAKER = "circuit_breaker"  # Circuit breaker pattern


class CircuitState(Enum):
    """Circuit breaker states"""
    CLOSED = "closed"      # Normal operation
    OPEN = "open"          # Failing, rejecting requests
    HALF_OPEN = "half_open"  # Testing recovery


@dataclass
class FallbackConfig:
    """Fallback configuration"""
    strategy: FallbackStrategy = FallbackStrategy.PRIORITY_BASED
    max_retries: int = 3
    retry_delay_ms: int = 100
    circuit_breaker_threshold: int = 5  # failures before opening
    circuit_breaker_timeout_ms: int = 30000  # time before half-open
    health_check_interval_ms: int = 10000
    performance_window_minutes: int = 5
    enable_graceful_degradation: bool = True


@dataclass
class ModelFallbackEntry:
    """Fallback model entry"""
    model_name: str
    priority: int = 1  # Lower number = higher priority
    weight: float = 1.0  # For load balancing
    enabled: bool = True
    max_concurrent_requests: int = 10
    timeout_ms: int = 30000
    
    # Runtime state
    current_requests: int = 0
    circuit_state: CircuitState = CircuitState.CLOSED
    failure_count: int = 0
    last_failure: Optional[datetime] = None
    last_success: Optional[datetime] = None
    average_latency_ms: float = 0.0


@dataclass
class FallbackAttempt:
    """Record of a fallback attempt"""
    timestamp: datetime
    primary_model: str
    fallback_model: str
    reason: str
    success: bool
    latency_ms: float = 0.0
    error_message: Optional[str] = None


# =============================================================================
# FALLBACK MANAGER
# =============================================================================

class FallbackManager:
    """Comprehensive fallback and error recovery manager"""
    
    def __init__(
        self,
        model_manager: ModelManager,
        performance_metrics: PerformanceMetrics,
        config: Optional[FallbackConfig] = None
    ):
        self.model_manager = model_manager
        self.performance_metrics = performance_metrics
        self.config = config or FallbackConfig()
        self.logger = logging.getLogger("fallback_manager")
        
        # Fallback configurations by service type
        self.fallback_configs: Dict[str, List[ModelFallbackEntry]] = defaultdict(list)
        self.fallback_history: deque = deque(maxlen=1000)
        
        # Circuit breaker state
        self.circuit_timers: Dict[str, asyncio.Task] = {}
        
        # Performance tracking
        self.performance_tracker: Dict[str, deque] = defaultdict(lambda: deque(maxlen=100))
        
        # Health monitoring
        self._health_task: Optional[asyncio.Task] = None
        self._shutdown_event = asyncio.Event()
        
        # Locks for thread safety
        self._fallback_lock = threading.RLock()
        self._circuit_lock = threading.RLock()
        
        self.logger.info("Fallback Manager initialized")
    
    def register_fallback_chain(
        self,
        service_type: str,
        models: List[Tuple[str, int, Dict[str, Any]]]
    ) -> None:
        """
        Register a fallback chain for a service type
        
        Args:
            service_type: Type of service (e.g., "llm", "tts", "stt")
            models: List of (model_name, priority, config) tuples
        """
        with self._fallback_lock:
            self.fallback_configs[service_type] = []
            
            for model_name, priority, config in models:
                entry = ModelFallbackEntry(
                    model_name=model_name,
                    priority=priority,
                    **config
                )
                self.fallback_configs[service_type].append(entry)
            
            # Sort by priority (lower number = higher priority)
            self.fallback_configs[service_type].sort(key=lambda x: x.priority)
            
            self.logger.info(f"Registered fallback chain for {service_type}: {[m.model_name for m in self.fallback_configs[service_type]]}")
    
    async def execute_with_fallback(
        self,
        service_type: str,
        operation: Callable,
        *args,
        operation_name: str = "unknown",
        **kwargs
    ) -> Any:
        """
        Execute an operation with fallback support
        
        Args:
            service_type: Type of service
            operation: Async function to execute
            operation_name: Name for logging/metrics
            *args, **kwargs: Arguments for operation
            
        Returns:
            Operation result
            
        Raises:
            Exception: If all fallback options fail
        """
        if service_type not in self.fallback_configs:
            self.logger.warning(f"No fallback chain configured for {service_type}")
            return await operation(*args, **kwargs)
        
        fallback_chain = self._get_available_models(service_type)
        
        if not fallback_chain:
            raise RuntimeError(f"No available models for {service_type}")
        
        last_exception = None
        
        for i, model_entry in enumerate(fallback_chain):
            model_name = model_entry.model_name
            
            # Check if model is available and healthy
            if not self._is_model_available(model_entry):
                continue
            
            try:
                # Track concurrent requests
                model_entry.current_requests += 1
                
                start_time = time.time()
                
                # Execute operation with timeout
                with TimingContext(self.performance_metrics, f"{service_type}_{operation_name}", {"model": model_name}):
                    result = await asyncio.wait_for(
                        operation(*args, model_name=model_name, **kwargs),
                        timeout=model_entry.timeout_ms / 1000.0
                    )
                
                # Success - update metrics
                latency_ms = (time.time() - start_time) * 1000
                self._record_success(model_entry, latency_ms)
                
                # Record fallback attempt if not primary model
                if i > 0:
                    self._record_fallback_attempt(
                        service_type, fallback_chain[0].model_name, model_name,
                        "primary_failed", True, latency_ms
                    )
                
                return result
                
            except Exception as e:
                last_exception = e
                latency_ms = (time.time() - start_time) * 1000
                
                # Record failure
                self._record_failure(model_entry, str(e))
                
                # Record fallback attempt
                if i > 0:
                    self._record_fallback_attempt(
                        service_type, fallback_chain[0].model_name, model_name,
                        f"fallback_failed: {str(e)}", False, latency_ms, str(e)
                    )
                
                self.logger.warning(f"Operation failed on {model_name}: {str(e)}")
                
            finally:
                model_entry.current_requests = max(0, model_entry.current_requests - 1)
        
        # All models failed
        self.performance_metrics.record_metric("fallback_exhausted", 1.0, tags={"service_type": service_type})
        raise RuntimeError(f"All fallback models failed for {service_type}. Last error: {last_exception}")
    
    def _get_available_models(self, service_type: str) -> List[ModelFallbackEntry]:
        """Get available models based on fallback strategy"""
        with self._fallback_lock:
            all_models = self.fallback_configs[service_type].copy()
        
        # Filter enabled and not overloaded models
        available = [
            model for model in all_models
            if model.enabled and self._is_model_available(model)
        ]
        
        if not available:
            return []
        
        # Apply fallback strategy
        if self.config.strategy == FallbackStrategy.PRIORITY_BASED:
            return sorted(available, key=lambda x: x.priority)
        
        elif self.config.strategy == FallbackStrategy.PERFORMANCE_BASED:
            return sorted(available, key=lambda x: x.average_latency_ms)
        
        elif self.config.strategy == FallbackStrategy.LOAD_BALANCED:
            return sorted(available, key=lambda x: x.current_requests / x.max_concurrent_requests)
        
        elif self.config.strategy == FallbackStrategy.ROUND_ROBIN:
            # Simple round-robin based on current time
            index = int(time.time()) % len(available)
            return available[index:] + available[:index]
        
        else:
            return available
    
    def _is_model_available(self, model_entry: ModelFallbackEntry) -> bool:
        """Check if a model is available for requests"""
        # Check if model is loaded
        if not self.model_manager.is_model_loaded(model_entry.model_name):
            return False
        
        # Check circuit breaker state
        if model_entry.circuit_state == CircuitState.OPEN:
            return False
        
        # Check concurrent request limit
        if model_entry.current_requests >= model_entry.max_concurrent_requests:
            return False
        
        # Check if model is healthy
        model = self.model_manager.get_model(model_entry.model_name)
        if model and model.state != ModelState.LOADED:
            return False
        
        return True
    
    def _record_success(self, model_entry: ModelFallbackEntry, latency_ms: float) -> None:
        """Record successful operation"""
        model_entry.last_success = datetime.now()
        model_entry.failure_count = 0  # Reset failure count on success
        
        # Update average latency
        if model_entry.average_latency_ms == 0:
            model_entry.average_latency_ms = latency_ms
        else:
            # Exponential moving average
            model_entry.average_latency_ms = (
                model_entry.average_latency_ms * 0.8 + latency_ms * 0.2
            )
        
        # Close circuit if it was half-open
        if model_entry.circuit_state == CircuitState.HALF_OPEN:
            self._close_circuit(model_entry)
        
        # Track performance
        self.performance_tracker[model_entry.model_name].append({
            "timestamp": datetime.now(),
            "latency_ms": latency_ms,
            "success": True
        })
    
    def _record_failure(self, model_entry: ModelFallbackEntry, error_message: str) -> None:
        """Record failed operation"""
        model_entry.last_failure = datetime.now()
        model_entry.failure_count += 1
        
        # Check if circuit breaker should open
        if (model_entry.circuit_state == CircuitState.CLOSED and 
            model_entry.failure_count >= self.config.circuit_breaker_threshold):
            self._open_circuit(model_entry)
        
        # Track performance
        self.performance_tracker[model_entry.model_name].append({
            "timestamp": datetime.now(),
            "error": error_message,
            "success": False
        })
        
        self.logger.warning(f"Recorded failure for {model_entry.model_name}: {error_message}")
    
    def _open_circuit(self, model_entry: ModelFallbackEntry) -> None:
        """Open circuit breaker for a model"""
        with self._circuit_lock:
            model_entry.circuit_state = CircuitState.OPEN
            
            # Schedule circuit recovery
            if model_entry.model_name in self.circuit_timers:
                self.circuit_timers[model_entry.model_name].cancel()
            
            self.circuit_timers[model_entry.model_name] = asyncio.create_task(
                self._schedule_circuit_recovery(model_entry)
            )
        
        self.logger.warning(f"Opened circuit breaker for {model_entry.model_name}")
        self.performance_metrics.record_metric("circuit_breaker_opened", 1.0, tags={"model": model_entry.model_name})
    
    def _close_circuit(self, model_entry: ModelFallbackEntry) -> None:
        """Close circuit breaker for a model"""
        with self._circuit_lock:
            model_entry.circuit_state = CircuitState.CLOSED
            model_entry.failure_count = 0
            
            # Cancel recovery timer
            if model_entry.model_name in self.circuit_timers:
                self.circuit_timers[model_entry.model_name].cancel()
                del self.circuit_timers[model_entry.model_name]
        
        self.logger.info(f"Closed circuit breaker for {model_entry.model_name}")
        self.performance_metrics.record_metric("circuit_breaker_closed", 1.0, tags={"model": model_entry.model_name})
    
    async def _schedule_circuit_recovery(self, model_entry: ModelFallbackEntry) -> None:
        """Schedule circuit breaker recovery"""
        try:
            await asyncio.sleep(self.config.circuit_breaker_timeout_ms / 1000.0)
            
            with self._circuit_lock:
                if model_entry.circuit_state == CircuitState.OPEN:
                    model_entry.circuit_state = CircuitState.HALF_OPEN
                    self.logger.info(f"Circuit breaker half-open for {model_entry.model_name}")
                    
        except asyncio.CancelledError:
            pass
    
    def _record_fallback_attempt(
        self,
        service_type: str,
        primary_model: str,
        fallback_model: str,
        reason: str,
        success: bool,
        latency_ms: float,
        error_message: Optional[str] = None
    ) -> None:
        """Record a fallback attempt"""
        attempt = FallbackAttempt(
            timestamp=datetime.now(),
            primary_model=primary_model,
            fallback_model=fallback_model,
            reason=reason,
            success=success,
            latency_ms=latency_ms,
            error_message=error_message
        )
        
        self.fallback_history.append(attempt)
        
        # Record metrics
        tags = {
            "service_type": service_type,
            "primary_model": primary_model,
            "fallback_model": fallback_model,
            "success": str(success)
        }
        self.performance_metrics.record_metric("fallback_attempt", 1.0, tags=tags)
    
    async def health_check_model(self, model_name: str) -> bool:
        """Perform health check on a specific model"""
        try:
            model = self.model_manager.get_model(model_name)
            if not model:
                return False
            
            # Basic health check - ensure model is loaded and responsive
            if model.state != ModelState.LOADED:
                return False
            
            # Could add more sophisticated health checks here
            return True
            
        except Exception as e:
            self.logger.error(f"Health check failed for {model_name}: {e}")
            return False
    
    async def start_health_monitoring(self) -> None:
        """Start background health monitoring"""
        async def health_loop():
            while not self._shutdown_event.is_set():
                try:
                    await self._perform_health_checks()
                    await asyncio.sleep(self.config.health_check_interval_ms / 1000.0)
                except Exception as e:
                    self.logger.error(f"Health monitoring error: {e}")
                    await asyncio.sleep(self.config.health_check_interval_ms / 1000.0)
        
        self._health_task = asyncio.create_task(health_loop())
        self.logger.info("Started health monitoring")
    
    async def stop_health_monitoring(self) -> None:
        """Stop health monitoring"""
        self._shutdown_event.set()
        
        if self._health_task:
            try:
                await asyncio.wait_for(self._health_task, timeout=5.0)
            except asyncio.TimeoutError:
                self._health_task.cancel()
            self._health_task = None
        
        # Cancel all circuit timers
        for timer in self.circuit_timers.values():
            timer.cancel()
        self.circuit_timers.clear()
        
        self.logger.info("Stopped health monitoring")
    
    async def _perform_health_checks(self) -> None:
        """Perform health checks on all models"""
        for service_type, models in self.fallback_configs.items():
            for model_entry in models:
                if model_entry.enabled:
                    healthy = await self.health_check_model(model_entry.model_name)
                    
                    if not healthy and model_entry.circuit_state == CircuitState.CLOSED:
                        self.logger.warning(f"Health check failed for {model_entry.model_name}")
                        self._record_failure(model_entry, "health_check_failed")
    
    def get_fallback_stats(self, service_type: Optional[str] = None) -> Dict[str, Any]:
        """Get fallback statistics"""
        stats = {
            "total_fallback_attempts": len(self.fallback_history),
            "successful_fallbacks": len([a for a in self.fallback_history if a.success]),
            "circuit_breakers_open": 0,
            "service_stats": {}
        }
        
        # Count circuit breakers
        for models in self.fallback_configs.values():
            for model in models:
                if model.circuit_state == CircuitState.OPEN:
                    stats["circuit_breakers_open"] += 1
        
        # Service-specific stats
        for svc_type, models in self.fallback_configs.items():
            if service_type and svc_type != service_type:
                continue
            
            service_stats = {
                "models": [],
                "fallback_attempts": len([a for a in self.fallback_history if a.primary_model in [m.model_name for m in models]]),
                "total_models": len(models),
                "healthy_models": len([m for m in models if m.circuit_state == CircuitState.CLOSED and m.enabled])
            }
            
            for model in models:
                model_stats = {
                    "name": model.model_name,
                    "priority": model.priority,
                    "enabled": model.enabled,
                    "circuit_state": model.circuit_state.value,
                    "current_requests": model.current_requests,
                    "failure_count": model.failure_count,
                    "average_latency_ms": model.average_latency_ms,
                    "last_success": model.last_success.isoformat() if model.last_success else None,
                    "last_failure": model.last_failure.isoformat() if model.last_failure else None
                }
                service_stats["models"].append(model_stats)
            
            stats["service_stats"][svc_type] = service_stats
        
        return stats
    
    def get_recent_fallback_attempts(self, limit: int = 50) -> List[Dict[str, Any]]:
        """Get recent fallback attempts"""
        recent = list(self.fallback_history)[-limit:]
        
        return [{
            "timestamp": attempt.timestamp.isoformat(),
            "primary_model": attempt.primary_model,
            "fallback_model": attempt.fallback_model,
            "reason": attempt.reason,
            "success": attempt.success,
            "latency_ms": attempt.latency_ms,
            "error_message": attempt.error_message
        } for attempt in recent]
    
    def enable_model(self, service_type: str, model_name: str) -> bool:
        """Enable a model in fallback chain"""
        with self._fallback_lock:
            for model in self.fallback_configs.get(service_type, []):
                if model.model_name == model_name:
                    model.enabled = True
                    self.logger.info(f"Enabled model {model_name} for {service_type}")
                    return True
        return False
    
    def disable_model(self, service_type: str, model_name: str) -> bool:
        """Disable a model in fallback chain"""
        with self._fallback_lock:
            for model in self.fallback_configs.get(service_type, []):
                if model.model_name == model_name:
                    model.enabled = False
                    self.logger.info(f"Disabled model {model_name} for {service_type}")
                    return True
        return False
    
    def reset_circuit_breaker(self, model_name: str) -> bool:
        """Manually reset a circuit breaker"""
        with self._circuit_lock:
            for models in self.fallback_configs.values():
                for model in models:
                    if model.model_name == model_name:
                        self._close_circuit(model)
                        self.logger.info(f"Manually reset circuit breaker for {model_name}")
                        return True
        return False 