#!/usr/bin/env python3
"""
Performance Metrics Collection System
=====================================

Comprehensive performance monitoring and analytics for AI model services.
Tracks latency, throughput, resource usage, and service quality metrics.

Features:
- Real-time performance monitoring
- Statistical analysis and trending
- Resource usage tracking
- Service quality metrics
- Performance alerts and thresholds
- Historical data retention and analysis
"""

import logging
import asyncio
import time
import threading
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any, Callable, Union, Tuple
from datetime import datetime, timedelta
from enum import Enum
from collections import deque, defaultdict
import statistics
import psutil
import torch
import json
from pathlib import Path


# =============================================================================
# METRIC DEFINITIONS
# =============================================================================

class MetricType(Enum):
    """Types of performance metrics"""
    LATENCY = "latency"              # Response time metrics
    THROUGHPUT = "throughput"        # Requests per second
    RESOURCE = "resource"            # CPU, memory, GPU usage
    QUALITY = "quality"              # Accuracy, success rate
    CUSTOM = "custom"                # User-defined metrics


class MetricUnit(Enum):
    """Units for metrics"""
    MILLISECONDS = "ms"
    SECONDS = "s"
    REQUESTS_PER_SECOND = "rps"
    PERCENT = "%"
    BYTES = "bytes"
    MEGABYTES = "MB"
    GIGABYTES = "GB"
    COUNT = "count"
    RATIO = "ratio"


@dataclass
class MetricPoint:
    """Individual metric data point"""
    timestamp: datetime
    value: float
    tags: Dict[str, str] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class MetricDefinition:
    """Definition of a metric"""
    name: str
    type: MetricType
    unit: MetricUnit
    description: str
    aggregation_window: int = 60  # seconds
    retention_days: int = 7
    thresholds: Optional[Dict[str, float]] = None  # warning, critical levels


@dataclass
class MetricStats:
    """Statistical summary of metric data"""
    count: int
    min_value: float
    max_value: float
    mean: float
    median: float
    std_dev: float
    p95: float
    p99: float
    rate_per_second: float = 0.0


@dataclass
class PerformanceAlert:
    """Performance alert definition"""
    metric_name: str
    threshold_type: str  # warning, critical
    threshold_value: float
    current_value: float
    timestamp: datetime
    severity: str
    message: str
    resolved: bool = False


# =============================================================================
# PERFORMANCE METRICS COLLECTOR
# =============================================================================

class PerformanceMetrics:
    """Comprehensive performance metrics collection system"""
    
    def __init__(
        self,
        service_name: str,
        storage_path: Optional[str] = None,
        max_memory_points: int = 10000
    ):
        self.service_name = service_name
        self.storage_path = Path(storage_path) if storage_path else None
        self.max_memory_points = max_memory_points
        self.logger = logging.getLogger(f"performance_metrics.{service_name}")
        
        # Metric definitions and data
        self.metric_definitions: Dict[str, MetricDefinition] = {}
        self.metric_data: Dict[str, deque] = defaultdict(lambda: deque(maxlen=max_memory_points))
        self.metric_locks: Dict[str, threading.RLock] = defaultdict(threading.RLock)
        
        # Aggregated statistics
        self.aggregated_stats: Dict[str, Dict[int, MetricStats]] = defaultdict(dict)
        self.last_aggregation: Dict[str, datetime] = {}
        
        # Alerts and thresholds
        self.active_alerts: List[PerformanceAlert] = []
        self.alert_callbacks: List[Callable[[PerformanceAlert], None]] = []
        
        # Background processing
        self._aggregation_task: Optional[asyncio.Task] = None
        self._cleanup_task: Optional[asyncio.Task] = None
        self._shutdown_event = asyncio.Event()
        
        # Built-in metrics
        self._register_builtin_metrics()
        
        self.logger.info(f"Performance Metrics initialized for {service_name}")
    
    def _register_builtin_metrics(self) -> None:
        """Register standard performance metrics"""
        builtin_metrics = [
            MetricDefinition(
                name="request_latency",
                type=MetricType.LATENCY,
                unit=MetricUnit.MILLISECONDS,
                description="Request processing latency",
                thresholds={"warning": 1000.0, "critical": 5000.0}
            ),
            MetricDefinition(
                name="requests_per_second",
                type=MetricType.THROUGHPUT,
                unit=MetricUnit.REQUESTS_PER_SECOND,
                description="Request throughput"
            ),
            MetricDefinition(
                name="success_rate",
                type=MetricType.QUALITY,
                unit=MetricUnit.PERCENT,
                description="Request success rate",
                thresholds={"warning": 95.0, "critical": 90.0}
            ),
            MetricDefinition(
                name="cpu_usage",
                type=MetricType.RESOURCE,
                unit=MetricUnit.PERCENT,
                description="CPU usage percentage",
                thresholds={"warning": 80.0, "critical": 95.0}
            ),
            MetricDefinition(
                name="memory_usage",
                type=MetricType.RESOURCE,
                unit=MetricUnit.PERCENT,
                description="Memory usage percentage",
                thresholds={"warning": 85.0, "critical": 95.0}
            ),
            MetricDefinition(
                name="gpu_memory_usage",
                type=MetricType.RESOURCE,
                unit=MetricUnit.PERCENT,
                description="GPU memory usage percentage",
                thresholds={"warning": 90.0, "critical": 98.0}
            ),
            MetricDefinition(
                name="model_load_time",
                type=MetricType.LATENCY,
                unit=MetricUnit.MILLISECONDS,
                description="Model loading time"
            ),
            MetricDefinition(
                name="inference_time",
                type=MetricType.LATENCY,
                unit=MetricUnit.MILLISECONDS,
                description="Model inference time"
            ),
            MetricDefinition(
                name="queue_size",
                type=MetricType.RESOURCE,
                unit=MetricUnit.COUNT,
                description="Request queue size",
                thresholds={"warning": 100.0, "critical": 500.0}
            ),
            MetricDefinition(
                name="error_rate",
                type=MetricType.QUALITY,
                unit=MetricUnit.PERCENT,
                description="Error rate percentage",
                thresholds={"warning": 5.0, "critical": 10.0}
            )
        ]
        
        for metric in builtin_metrics:
            self.register_metric(metric)
    
    def register_metric(self, metric: MetricDefinition) -> None:
        """Register a new metric definition"""
        self.metric_definitions[metric.name] = metric
        self.logger.info(f"Registered metric: {metric.name} ({metric.type.value})")
    
    def record_metric(
        self,
        metric_name: str,
        value: float,
        tags: Optional[Dict[str, str]] = None,
        metadata: Optional[Dict[str, Any]] = None,
        timestamp: Optional[datetime] = None
    ) -> None:
        """
        Record a metric data point
        
        Args:
            metric_name: Name of the metric
            value: Metric value
            tags: Optional tags for grouping
            metadata: Optional additional data
            timestamp: Optional timestamp (defaults to now)
        """
        if metric_name not in self.metric_definitions:
            self.logger.warning(f"Unknown metric: {metric_name}")
            return
        
        point = MetricPoint(
            timestamp=timestamp or datetime.now(),
            value=value,
            tags=tags or {},
            metadata=metadata or {}
        )
        
        with self.metric_locks[metric_name]:
            self.metric_data[metric_name].append(point)
        
        # Check thresholds for alerts
        self._check_thresholds(metric_name, value)
    
    def record_latency(
        self,
        operation: str,
        latency_ms: float,
        tags: Optional[Dict[str, str]] = None
    ) -> None:
        """Record latency metric"""
        metric_tags = {"operation": operation}
        if tags:
            metric_tags.update(tags)
        
        self.record_metric("request_latency", latency_ms, tags=metric_tags)
    
    def record_throughput(
        self,
        operation: str,
        count: int,
        window_seconds: float = 1.0,
        tags: Optional[Dict[str, str]] = None
    ) -> None:
        """Record throughput metric"""
        rps = count / window_seconds
        metric_tags = {"operation": operation}
        if tags:
            metric_tags.update(tags)
        
        self.record_metric("requests_per_second", rps, tags=metric_tags)
    
    def record_success_rate(
        self,
        operation: str,
        success_count: int,
        total_count: int,
        tags: Optional[Dict[str, str]] = None
    ) -> None:
        """Record success rate metric"""
        if total_count > 0:
            rate = (success_count / total_count) * 100
            metric_tags = {"operation": operation}
            if tags:
                metric_tags.update(tags)
            
            self.record_metric("success_rate", rate, tags=metric_tags)
    
    def record_resource_usage(self) -> None:
        """Record current system resource usage"""
        try:
            # CPU usage
            cpu_percent = psutil.cpu_percent(interval=0.1)
            self.record_metric("cpu_usage", cpu_percent)
            
            # Memory usage
            memory = psutil.virtual_memory()
            self.record_metric("memory_usage", memory.percent)
            
            # GPU memory usage
            if torch.cuda.is_available():
                try:
                    allocated = torch.cuda.memory_allocated()
                    total = torch.cuda.get_device_properties(0).total_memory
                    gpu_percent = (allocated / total) * 100
                    self.record_metric("gpu_memory_usage", gpu_percent)
                except Exception:
                    pass  # GPU metrics are optional
                    
        except Exception as e:
            self.logger.error(f"Failed to record resource usage: {e}")
    
    def get_metric_stats(
        self,
        metric_name: str,
        window_minutes: int = 5,
        tags_filter: Optional[Dict[str, str]] = None
    ) -> Optional[MetricStats]:
        """
        Get statistical summary of metric data
        
        Args:
            metric_name: Metric to analyze
            window_minutes: Time window in minutes
            tags_filter: Optional tag filters
            
        Returns:
            Statistical summary or None if no data
        """
        if metric_name not in self.metric_data:
            return None
        
        cutoff_time = datetime.now() - timedelta(minutes=window_minutes)
        
        with self.metric_locks[metric_name]:
            # Filter data by time window and tags
            filtered_points = []
            for point in self.metric_data[metric_name]:
                if point.timestamp >= cutoff_time:
                    if tags_filter:
                        if all(point.tags.get(k) == v for k, v in tags_filter.items()):
                            filtered_points.append(point)
                    else:
                        filtered_points.append(point)
        
        if not filtered_points:
            return None
        
        values = [p.value for p in filtered_points]
        
        # Calculate statistics
        count = len(values)
        min_val = min(values)
        max_val = max(values)
        mean_val = statistics.mean(values)
        median_val = statistics.median(values)
        
        # Standard deviation
        std_dev = statistics.stdev(values) if count > 1 else 0.0
        
        # Percentiles
        sorted_values = sorted(values)
        p95 = sorted_values[int(0.95 * len(sorted_values))] if count > 0 else 0.0
        p99 = sorted_values[int(0.99 * len(sorted_values))] if count > 0 else 0.0
        
        # Rate calculation
        if filtered_points:
            time_span = (filtered_points[-1].timestamp - filtered_points[0].timestamp).total_seconds()
            rate_per_second = count / time_span if time_span > 0 else 0.0
        else:
            rate_per_second = 0.0
        
        return MetricStats(
            count=count,
            min_value=min_val,
            max_value=max_val,
            mean=mean_val,
            median=median_val,
            std_dev=std_dev,
            p95=p95,
            p99=p99,
            rate_per_second=rate_per_second
        )
    
    def get_metric_history(
        self,
        metric_name: str,
        hours: int = 1,
        tags_filter: Optional[Dict[str, str]] = None
    ) -> List[MetricPoint]:
        """Get historical metric data"""
        if metric_name not in self.metric_data:
            return []
        
        cutoff_time = datetime.now() - timedelta(hours=hours)
        
        with self.metric_locks[metric_name]:
            filtered_points = []
            for point in self.metric_data[metric_name]:
                if point.timestamp >= cutoff_time:
                    if tags_filter:
                        if all(point.tags.get(k) == v for k, v in tags_filter.items()):
                            filtered_points.append(point)
                    else:
                        filtered_points.append(point)
        
        return sorted(filtered_points, key=lambda p: p.timestamp)
    
    def _check_thresholds(self, metric_name: str, value: float) -> None:
        """Check metric value against thresholds and generate alerts"""
        metric_def = self.metric_definitions.get(metric_name)
        if not metric_def or not metric_def.thresholds:
            return
        
        thresholds = metric_def.thresholds
        current_time = datetime.now()
        
        # Check critical threshold
        if "critical" in thresholds and value >= thresholds["critical"]:
            alert = PerformanceAlert(
                metric_name=metric_name,
                threshold_type="critical",
                threshold_value=thresholds["critical"],
                current_value=value,
                timestamp=current_time,
                severity="critical",
                message=f"{metric_name} exceeded critical threshold: {value} >= {thresholds['critical']}"
            )
            self._trigger_alert(alert)
            
        # Check warning threshold
        elif "warning" in thresholds and value >= thresholds["warning"]:
            alert = PerformanceAlert(
                metric_name=metric_name,
                threshold_type="warning",
                threshold_value=thresholds["warning"],
                current_value=value,
                timestamp=current_time,
                severity="warning",
                message=f"{metric_name} exceeded warning threshold: {value} >= {thresholds['warning']}"
            )
            self._trigger_alert(alert)
    
    def _trigger_alert(self, alert: PerformanceAlert) -> None:
        """Trigger a performance alert"""
        # Check if similar alert is already active
        for active_alert in self.active_alerts:
            if (active_alert.metric_name == alert.metric_name and 
                active_alert.threshold_type == alert.threshold_type and
                not active_alert.resolved):
                return  # Don't spam similar alerts
        
        self.active_alerts.append(alert)
        self.logger.warning(f"Performance alert: {alert.message}")
        
        # Notify alert callbacks
        for callback in self.alert_callbacks:
            try:
                callback(alert)
            except Exception as e:
                self.logger.error(f"Alert callback failed: {e}")
    
    def add_alert_callback(self, callback: Callable[[PerformanceAlert], None]) -> None:
        """Add a callback for performance alerts"""
        self.alert_callbacks.append(callback)
    
    def resolve_alerts(self, metric_name: str, threshold_type: str) -> None:
        """Resolve active alerts for a metric"""
        for alert in self.active_alerts:
            if (alert.metric_name == metric_name and 
                alert.threshold_type == threshold_type and
                not alert.resolved):
                alert.resolved = True
                self.logger.info(f"Resolved alert: {alert.message}")
    
    def get_active_alerts(self) -> List[PerformanceAlert]:
        """Get list of active (unresolved) alerts"""
        return [alert for alert in self.active_alerts if not alert.resolved]
    
    async def start_background_collection(self, interval_seconds: int = 30) -> None:
        """Start background resource collection"""
        async def collection_loop():
            while not self._shutdown_event.is_set():
                try:
                    self.record_resource_usage()
                    await asyncio.sleep(interval_seconds)
                except Exception as e:
                    self.logger.error(f"Background collection error: {e}")
                    await asyncio.sleep(interval_seconds)
        
        self._aggregation_task = asyncio.create_task(collection_loop())
        self.logger.info("Started background metrics collection")
    
    async def stop_background_collection(self) -> None:
        """Stop background collection"""
        self._shutdown_event.set()
        
        if self._aggregation_task:
            try:
                await asyncio.wait_for(self._aggregation_task, timeout=5.0)
            except asyncio.TimeoutError:
                self._aggregation_task.cancel()
            self._aggregation_task = None
        
        self.logger.info("Stopped background metrics collection")
    
    def export_metrics(
        self,
        format: str = "json",
        window_hours: int = 1
    ) -> Union[str, Dict[str, Any]]:
        """
        Export metrics data
        
        Args:
            format: Export format ('json', 'dict')
            window_hours: Time window for export
            
        Returns:
            Exported data in requested format
        """
        export_data = {
            "service_name": self.service_name,
            "export_timestamp": datetime.now().isoformat(),
            "window_hours": window_hours,
            "metrics": {}
        }
        
        for metric_name in self.metric_definitions.keys():
            history = self.get_metric_history(metric_name, hours=window_hours)
            stats = self.get_metric_stats(metric_name, window_minutes=window_hours * 60)
            
            metric_data = {
                "definition": {
                    "type": self.metric_definitions[metric_name].type.value,
                    "unit": self.metric_definitions[metric_name].unit.value,
                    "description": self.metric_definitions[metric_name].description
                },
                "stats": {
                    "count": stats.count if stats else 0,
                    "mean": stats.mean if stats else 0,
                    "min": stats.min_value if stats else 0,
                    "max": stats.max_value if stats else 0,
                    "p95": stats.p95 if stats else 0,
                    "p99": stats.p99 if stats else 0
                },
                "data_points": len(history)
            }
            
            export_data["metrics"][metric_name] = metric_data
        
        # Add active alerts
        export_data["active_alerts"] = [
            {
                "metric_name": alert.metric_name,
                "severity": alert.severity,
                "message": alert.message,
                "timestamp": alert.timestamp.isoformat()
            }
            for alert in self.get_active_alerts()
        ]
        
        if format == "json":
            return json.dumps(export_data, indent=2)
        else:
            return export_data
    
    def get_performance_summary(self) -> Dict[str, Any]:
        """Get overall performance summary"""
        summary = {
            "service_name": self.service_name,
            "timestamp": datetime.now().isoformat(),
            "metrics_count": len(self.metric_definitions),
            "active_alerts": len(self.get_active_alerts()),
            "key_metrics": {}
        }
        
        # Key performance indicators
        key_metrics = [
            "request_latency", "requests_per_second", "success_rate",
            "cpu_usage", "memory_usage", "gpu_memory_usage", "error_rate"
        ]
        
        for metric_name in key_metrics:
            if metric_name in self.metric_definitions:
                stats = self.get_metric_stats(metric_name, window_minutes=5)
                if stats:
                    summary["key_metrics"][metric_name] = {
                        "current": stats.mean,
                        "p95": stats.p95,
                        "unit": self.metric_definitions[metric_name].unit.value,
                        "trend": "stable"  # Could add trend analysis
                    }
        
        return summary


# =============================================================================
# TIMING DECORATORS
# =============================================================================

class TimingContext:
    """Context manager for timing operations"""
    
    def __init__(self, metrics: PerformanceMetrics, operation: str, tags: Optional[Dict[str, str]] = None):
        self.metrics = metrics
        self.operation = operation
        self.tags = tags or {}
        self.start_time = None
        self.success = True
    
    def __enter__(self):
        self.start_time = time.time()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.start_time:
            duration_ms = (time.time() - self.start_time) * 1000
            self.metrics.record_latency(self.operation, duration_ms, self.tags)
            
            # Record success/failure
            if exc_type is not None:
                self.success = False
                error_tags = self.tags.copy()
                error_tags["error_type"] = exc_type.__name__
                self.metrics.record_metric("error_rate", 1.0, tags=error_tags)
    
    def mark_error(self, error_type: str = "unknown"):
        """Manually mark operation as error"""
        self.success = False
        error_tags = self.tags.copy()
        error_tags["error_type"] = error_type
        self.metrics.record_metric("error_rate", 1.0, tags=error_tags)


def timed_operation(
    metrics: PerformanceMetrics,
    operation: str,
    tags: Optional[Dict[str, str]] = None
):
    """Decorator for timing function calls"""
    def decorator(func):
        def wrapper(*args, **kwargs):
            with TimingContext(metrics, operation, tags):
                return func(*args, **kwargs)
        return wrapper
    return decorator


def async_timed_operation(
    metrics: PerformanceMetrics,
    operation: str,
    tags: Optional[Dict[str, str]] = None
):
    """Decorator for timing async function calls"""
    def decorator(func):
        async def wrapper(*args, **kwargs):
            with TimingContext(metrics, operation, tags):
                return await func(*args, **kwargs)
        return wrapper
    return decorator 