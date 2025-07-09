"""
Performance metrics collection for GraphFlow system.

This module provides metrics collection and exposure for monitoring
system performance and health.
"""

import asyncio
import time
from typing import Dict, Any, Optional, List
from datetime import datetime
from collections import defaultdict, deque
import threading

try:
    from prometheus_client import (
        Counter, Histogram, Gauge, Summary,
        start_http_server, REGISTRY
    )
    PROMETHEUS_AVAILABLE = True
except ImportError:
    PROMETHEUS_AVAILABLE = False
    # Dummy implementations for when prometheus is not available
    class Counter:
        def __init__(self, *args, **kwargs): pass
        def inc(self, amount=1): pass
        def labels(self, **kwargs): return self
    
    class Histogram:
        def __init__(self, *args, **kwargs): pass
        def observe(self, value): pass
        def labels(self, **kwargs): return self
    
    class Gauge:
        def __init__(self, *args, **kwargs): pass
        def set(self, value): pass
        def inc(self, amount=1): pass
        def dec(self, amount=1): pass
        def labels(self, **kwargs): return self
    
    class Summary:
        def __init__(self, *args, **kwargs): pass
        def observe(self, value): pass
        def labels(self, **kwargs): return self

from ..utils.logging import get_structured_logger


class MetricsCollector:
    """
    Collects and exposes performance metrics for the GraphFlow system.
    
    Provides both Prometheus metrics (if available) and internal metrics
    storage for analysis and debugging.
    """
    
    _instance = None
    _initialized = False
    
    def __new__(cls, enabled: bool = True, port: int = 9090):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(self, enabled: bool = True, port: int = 9090):
        """
        Initialize metrics collector.
        
        Args:
            enabled: Whether metrics collection is enabled
            port: Port for Prometheus metrics server
        """
        if self._initialized:
            return
            
        self.enabled = enabled
        self.port = port
        self.logger = get_structured_logger("metrics_collector")
        
        # Internal metrics storage
        self._metrics_lock = threading.Lock()
        self._processing_times: deque = deque(maxlen=1000)
        self._decision_counts: Dict[str, int] = defaultdict(int)
        self._error_counts: Dict[str, int] = defaultdict(int)
        self._category_counts: Dict[str, int] = defaultdict(int)
        
        if self.enabled and PROMETHEUS_AVAILABLE:
            # Prometheus metrics
            self.stimuli_received = Counter(
                'graphflow_stimuli_received_total',
                'Total number of stimuli received',
                ['source', 'priority']
            )
            
            self.stimuli_processed = Counter(
                'graphflow_stimuli_processed_total',
                'Total number of stimuli processed',
                ['category', 'decision', 'success']
            )
            
            self.processing_time = Histogram(
                'graphflow_processing_time_seconds',
                'Time taken to process stimuli',
                buckets=[0.1, 0.5, 1.0, 2.0, 5.0, 10.0, 30.0]
            )
            
            self.categorization_accuracy = Gauge(
                'graphflow_categorization_accuracy_ratio',
                'Accuracy of stimuli categorization'
            )
            
            self.active_requests = Gauge(
                'graphflow_active_requests_current',
                'Number of currently active requests'
            )
            
            self.queue_size = Gauge(
                'graphflow_processing_queue_size',
                'Current size of the processing queue'
            )
            
            self.system_health = Gauge(
                'graphflow_system_health_status',
                'Overall system health status (1=healthy, 0=unhealthy)'
            )
            
            self.decision_distribution = Counter(
                'graphflow_decisions_made_total',
                'Distribution of routing decisions',
                ['decision_type']
            )
            
            self.execution_success_rate = Gauge(
                'graphflow_execution_success_rate',
                'Success rate of executions'
            )
            
            self.processing_errors = Counter(
                'graphflow_processing_errors_total',
                'Total number of processing errors',
                ['error_type']
            )
            
            self.node_processing_time = Histogram(
                'graphflow_node_processing_time_seconds',
                'Time taken by each processing node',
                ['node_name'],
                buckets=[0.01, 0.05, 0.1, 0.5, 1.0, 5.0]
            )
            
            self.resource_utilization = Gauge(
                'graphflow_resource_utilization_ratio',
                'Resource utilization metrics',
                ['resource_type']
            )
        else:
            # Create dummy metrics when Prometheus is not available
            class DummyMetric:
                def inc(self, amount=1, **kwargs): pass
                def dec(self, amount=1, **kwargs): pass
                def set(self, value, **kwargs): pass
                def observe(self, amount, **kwargs): pass
                def time(self): return DummyTimer()
                def labels(self, **kwargs): return self
            
            class DummyTimer:
                def __enter__(self): return self
                def __exit__(self, *args): pass
            
            self.stimuli_received = DummyMetric()
            self.stimuli_processed = DummyMetric()
            self.processing_time = DummyMetric()
            self.categorization_accuracy = DummyMetric()
            self.active_requests = DummyMetric()
            self.queue_size = DummyMetric()
            self.system_health = DummyMetric()
            self.decision_distribution = DummyMetric()
            self.execution_success_rate = DummyMetric()
            self.processing_errors = DummyMetric()
            self.node_processing_time = DummyMetric()
            self.resource_utilization = DummyMetric()
        
        self._server_started = False
        self._initialized = True
    
    async def start(self) -> None:
        """Start the metrics collection server."""
        if self.enabled and PROMETHEUS_AVAILABLE and not self._server_started:
            try:
                # Start Prometheus HTTP server in a separate thread
                start_http_server(self.port)
                self._server_started = True
                self.logger.info(
                    f"Prometheus metrics server started on port {self.port}"
                )
            except Exception as e:
                self.logger.error(f"Failed to start metrics server: {e}")
    
    async def stop(self) -> None:
        """Stop the metrics collection."""
        # Prometheus server runs in a thread and will stop with the process
        self.logger.info("Metrics collector stopping")
    
    def increment_stimuli_received(self, source: str, priority: str) -> None:
        """Increment counter for received stimuli."""
        if self.enabled:
            self.stimuli_received.labels(source=source, priority=priority).inc()
    
    def increment_stimuli_processed(
        self, 
        category: str, 
        decision: str, 
        success: bool
    ) -> None:
        """Increment counter for processed stimuli."""
        if self.enabled:
            self.stimuli_processed.labels(
                category=category,
                decision=decision,
                success=str(success)
            ).inc()
            
            # Update internal counters
            with self._metrics_lock:
                self._category_counts[category] += 1
                self._decision_counts[decision] += 1
    
    def record_processing_time(self, duration: float) -> None:
        """Record stimuli processing time."""
        if self.enabled:
            self.processing_time.observe(duration)
            
            # Store internally for analysis
            with self._metrics_lock:
                self._processing_times.append({
                    'duration': duration,
                    'timestamp': datetime.now()
                })
    
    def set_categorization_accuracy(self, accuracy: float) -> None:
        """Set categorization accuracy metric."""
        if self.enabled:
            self.categorization_accuracy.set(accuracy)
    
    def set_active_requests(self, count: int) -> None:
        """Set number of active requests."""
        if self.enabled:
            self.active_requests.set(count)
    
    def increment_active_requests(self) -> None:
        """Increment active requests counter."""
        if self.enabled:
            self.active_requests.inc()
    
    def decrement_active_requests(self) -> None:
        """Decrement active requests counter."""
        if self.enabled:
            self.active_requests.dec()
    
    def set_queue_size(self, size: int) -> None:
        """Set processing queue size."""
        if self.enabled:
            self.queue_size.set(size)
    
    def set_system_health(self, is_healthy: bool) -> None:
        """Set system health status."""
        if self.enabled:
            self.system_health.set(1 if is_healthy else 0)
    
    def increment_decision(self, decision_type: str) -> None:
        """Increment decision counter."""
        if self.enabled:
            self.decision_distribution.labels(decision_type=decision_type).inc()
    
    def set_execution_success_rate(self, rate: float) -> None:
        """Set execution success rate."""
        if self.enabled:
            self.execution_success_rate.set(rate)
    
    def increment_processing_errors(self, error_type: str) -> None:
        """Increment processing error counter."""
        if self.enabled:
            self.processing_errors.labels(error_type=error_type).inc()
            
            # Update internal counter
            with self._metrics_lock:
                self._error_counts[error_type] += 1
    
    def record_node_processing_time(self, node_name: str, duration: float) -> None:
        """Record processing time for a specific node."""
        if self.enabled:
            self.node_processing_time.labels(node_name=node_name).observe(duration)
    
    def set_resource_utilization(self, resource_type: str, utilization: float) -> None:
        """Set resource utilization metric."""
        if self.enabled:
            self.resource_utilization.labels(resource_type=resource_type).set(utilization)
    
    async def get_metrics(self) -> Dict[str, Any]:
        """
        Get current metrics as a dictionary.
        
        Returns:
            Dictionary containing current metric values
        """
        with self._metrics_lock:
            # Calculate average processing time
            if self._processing_times:
                avg_processing_time = sum(
                    pt['duration'] for pt in self._processing_times
                ) / len(self._processing_times)
            else:
                avg_processing_time = 0.0
            
            # Calculate percentiles
            if self._processing_times:
                sorted_times = sorted(pt['duration'] for pt in self._processing_times)
                p50_idx = int(len(sorted_times) * 0.5)
                p95_idx = int(len(sorted_times) * 0.95)
                p99_idx = int(len(sorted_times) * 0.99)
                
                p50 = sorted_times[p50_idx] if p50_idx < len(sorted_times) else 0
                p95 = sorted_times[p95_idx] if p95_idx < len(sorted_times) else 0
                p99 = sorted_times[p99_idx] if p99_idx < len(sorted_times) else 0
            else:
                p50 = p95 = p99 = 0
            
            return {
                "processing_metrics": {
                    "average_time": avg_processing_time,
                    "p50_time": p50,
                    "p95_time": p95,
                    "p99_time": p99,
                    "total_processed": sum(self._category_counts.values())
                },
                "category_distribution": dict(self._category_counts),
                "decision_distribution": dict(self._decision_counts),
                "error_counts": dict(self._error_counts),
                "collection_enabled": self.enabled,
                "prometheus_available": PROMETHEUS_AVAILABLE
            }
    
    def get_processing_stats(self) -> Dict[str, float]:
        """
        Get processing time statistics.
        
        Returns:
            Dictionary with processing time stats
        """
        with self._metrics_lock:
            if not self._processing_times:
                return {
                    "min": 0.0,
                    "max": 0.0,
                    "avg": 0.0,
                    "count": 0
                }
            
            durations = [pt['duration'] for pt in self._processing_times]
            return {
                "min": min(durations),
                "max": max(durations),
                "avg": sum(durations) / len(durations),
                "count": len(durations)
            }
    
    def reset_metrics(self) -> None:
        """Reset internal metrics (useful for testing)."""
        with self._metrics_lock:
            self._processing_times.clear()
            self._decision_counts.clear()
            self._error_counts.clear()
            self._category_counts.clear()
    
    def record_rule_hit(self, rule_id: str) -> None:
        """Record a rule hit for decision tracking."""
        if self.enabled:
            # Track internally for statistics
            with self._metrics_lock:
                if not hasattr(self, '_rule_hits'):
                    self._rule_hits = defaultdict(int)
                self._rule_hits[rule_id] += 1
    
    def record_decision_rule_hit(self, rule_category: str, decision: str) -> None:
        """Record a decision rule hit for category and decision type."""
        if self.enabled:
            # Track rule category hits
            with self._metrics_lock:
                if not hasattr(self, '_rule_category_hits'):
                    self._rule_category_hits = defaultdict(lambda: defaultdict(int))
                self._rule_category_hits[rule_category][decision] += 1
    
    def record_resource_availability(self, cpu: float, memory: float, capacity: int) -> None:
        """Record resource availability metrics."""
        if self.enabled:
            self.set_resource_utilization("cpu", 1.0 - cpu)  # Convert availability to utilization
            self.set_resource_utilization("memory", 1.0 - memory)
            self.set_resource_utilization("processing_capacity", capacity / 100.0)  # Normalize to ratio
    
    def record_http_request(self, endpoint: str, method: str, status_code: int, duration: float) -> None:
        """Record HTTP request metrics."""
        if self.enabled and PROMETHEUS_AVAILABLE:
            # Create HTTP request specific metrics if not already present
            if not hasattr(self, 'http_requests'):
                self.http_requests = Counter(
                    'graphflow_http_requests_total',
                    'Total HTTP requests made',
                    ['endpoint', 'method', 'status_code']
                )
            
            if not hasattr(self, 'http_request_duration'):
                self.http_request_duration = Histogram(
                    'graphflow_http_request_duration_seconds',
                    'HTTP request duration',
                    ['endpoint', 'method'],
                    buckets=[0.1, 0.5, 1.0, 2.0, 5.0, 10.0, 30.0]
                )
            
            # Record the metrics
            self.http_requests.labels(
                endpoint=endpoint,
                method=method,
                status_code=str(status_code)
            ).inc()
            
            self.http_request_duration.labels(
                endpoint=endpoint,
                method=method
            ).observe(duration)
        
        # Store internally for analysis when Prometheus is not available
        with self._metrics_lock:
            if not hasattr(self, '_http_requests'):
                self._http_requests = defaultdict(int)
            
            request_key = f"{method}_{endpoint}_{status_code}"
            self._http_requests[request_key] += 1
    
    def get_all_metrics(self) -> Dict[str, Any]:
        """
        Get all metrics as a dictionary.
        
        Returns:
            Dictionary containing all metric values
        """
        with self._metrics_lock:
            # Calculate average processing time
            if self._processing_times:
                avg_processing_time = sum(
                    pt['duration'] for pt in self._processing_times
                ) / len(self._processing_times)
            else:
                avg_processing_time = 0.0
            
            return {
                "processing_metrics": {
                    "avg_processing_time": avg_processing_time,
                    "total_processed": len(self._processing_times),
                    "decision_counts": dict(self._decision_counts),
                    "error_counts": dict(self._error_counts),
                    "category_counts": dict(self._category_counts)
                },
                "rule_metrics": {
                    "rule_hits": dict(getattr(self, '_rule_hits', {})),
                    "rule_category_hits": dict(getattr(self, '_rule_category_hits', {}))
                },
                "http_metrics": {
                    "http_requests": dict(getattr(self, '_http_requests', {}))
                }
            }


# Context manager for timing operations
class MetricTimer:
    """
    Context manager for timing operations and recording metrics.
    
    Usage:
        with MetricTimer(metrics_collector, "operation_name") as timer:
            # Do something
            pass
    """
    
    def __init__(
        self, 
        metrics_collector: MetricsCollector,
        operation_name: str,
        record_as_node: bool = False
    ):
        """
        Initialize metric timer.
        
        Args:
            metrics_collector: Metrics collector instance
            operation_name: Name of the operation being timed
            record_as_node: Whether to record as node processing time
        """
        self.metrics_collector = metrics_collector
        self.operation_name = operation_name
        self.record_as_node = record_as_node
        self.start_time = None
        self.duration = None
    
    def __enter__(self):
        """Start timing."""
        self.start_time = time.time()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Stop timing and record metric."""
        if self.start_time:
            self.duration = time.time() - self.start_time
            
            if self.record_as_node:
                self.metrics_collector.record_node_processing_time(
                    self.operation_name,
                    self.duration
                )
            else:
                self.metrics_collector.record_processing_time(self.duration)