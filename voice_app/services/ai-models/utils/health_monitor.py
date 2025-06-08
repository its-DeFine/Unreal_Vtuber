#!/usr/bin/env python3
"""
Health Monitoring for AI Model Services
======================================

Comprehensive health monitoring and diagnostic utilities for AI model services.
Tracks service health, performance metrics, and system resource usage.
"""

import logging
import asyncio
import time
import threading
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Callable, Any
from datetime import datetime, timedelta
from enum import Enum
import psutil
import torch


# =============================================================================
# HEALTH STATUS DEFINITIONS
# =============================================================================

class HealthStatus(Enum):
    """Health status levels"""
    HEALTHY = "healthy"
    WARNING = "warning"
    UNHEALTHY = "unhealthy"
    CRITICAL = "critical"
    UNKNOWN = "unknown"


@dataclass
class HealthCheck:
    """Individual health check result"""
    name: str
    status: HealthStatus
    message: str
    timestamp: datetime = field(default_factory=datetime.now)
    response_time_ms: float = 0.0
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class SystemMetrics:
    """System resource metrics"""
    cpu_percent: float
    memory_percent: float
    disk_percent: float
    gpu_memory_percent: float
    gpu_utilization_percent: float
    network_bytes_sent: int
    network_bytes_recv: int
    timestamp: datetime = field(default_factory=datetime.now)


@dataclass
class ServiceHealth:
    """Overall service health status"""
    service_name: str
    status: HealthStatus
    uptime_seconds: float
    checks: List[HealthCheck] = field(default_factory=list)
    system_metrics: Optional[SystemMetrics] = None
    last_updated: datetime = field(default_factory=datetime.now)


# =============================================================================
# HEALTH MONITOR IMPLEMENTATION
# =============================================================================

class HealthMonitor:
    """Comprehensive health monitoring for AI services"""
    
    def __init__(self, service_name: str, check_interval_seconds: int = 30):
        self.service_name = service_name
        self.check_interval_seconds = check_interval_seconds
        self.logger = logging.getLogger(f"health_monitor.{service_name}")
        
        # Health state
        self.start_time = datetime.now()
        self.health_checks: Dict[str, Callable] = {}
        self.last_check_results: Dict[str, HealthCheck] = {}
        self.system_metrics_history: List[SystemMetrics] = []
        self.max_history_size = 100
        
        # Monitoring control
        self._monitoring_task: Optional[asyncio.Task] = None
        self._shutdown_event = asyncio.Event()
        
        # Health thresholds
        self.cpu_threshold = 80.0  # CPU usage percentage
        self.memory_threshold = 85.0  # Memory usage percentage
        self.disk_threshold = 90.0  # Disk usage percentage
        self.gpu_memory_threshold = 90.0  # GPU memory percentage
        self.response_time_threshold = 5000.0  # Response time in ms
        
        # Network monitoring
        self._last_network_stats = psutil.net_io_counters()
        
        self.logger.info(f"Health Monitor initialized for {service_name}")
    
    def register_health_check(self, name: str, check_func: Callable) -> None:
        """
        Register a health check function
        
        Args:
            name: Name of the health check
            check_func: Async function that returns (status, message, metadata)
        """
        self.health_checks[name] = check_func
        self.logger.info(f"Registered health check: {name}")
    
    def unregister_health_check(self, name: str) -> None:
        """Unregister a health check"""
        if name in self.health_checks:
            del self.health_checks[name]
            self.last_check_results.pop(name, None)
            self.logger.info(f"Unregistered health check: {name}")
    
    async def run_health_check(self, name: str) -> HealthCheck:
        """
        Run a specific health check
        
        Args:
            name: Name of the health check to run
            
        Returns:
            HealthCheck result
        """
        if name not in self.health_checks:
            return HealthCheck(
                name=name,
                status=HealthStatus.UNKNOWN,
                message=f"Health check '{name}' not found"
            )
        
        start_time = time.time()
        
        try:
            check_func = self.health_checks[name]
            
            # Run the check with timeout
            result = await asyncio.wait_for(check_func(), timeout=10.0)
            
            # Parse result
            if isinstance(result, tuple):
                if len(result) == 2:
                    status, message = result
                    metadata = {}
                elif len(result) == 3:
                    status, message, metadata = result
                else:
                    raise ValueError("Invalid health check result format")
            else:
                # Assume boolean result
                status = HealthStatus.HEALTHY if result else HealthStatus.UNHEALTHY
                message = "Health check passed" if result else "Health check failed"
                metadata = {}
            
            response_time = (time.time() - start_time) * 1000
            
            # Check response time threshold
            if response_time > self.response_time_threshold:
                if status == HealthStatus.HEALTHY:
                    status = HealthStatus.WARNING
                    message += f" (slow response: {response_time:.1f}ms)"
            
            health_check = HealthCheck(
                name=name,
                status=status,
                message=message,
                response_time_ms=response_time,
                metadata=metadata
            )
            
            self.last_check_results[name] = health_check
            return health_check
            
        except asyncio.TimeoutError:
            health_check = HealthCheck(
                name=name,
                status=HealthStatus.CRITICAL,
                message="Health check timed out",
                response_time_ms=(time.time() - start_time) * 1000
            )
            self.last_check_results[name] = health_check
            return health_check
            
        except Exception as e:
            health_check = HealthCheck(
                name=name,
                status=HealthStatus.UNHEALTHY,
                message=f"Health check failed: {str(e)}",
                response_time_ms=(time.time() - start_time) * 1000
            )
            self.last_check_results[name] = health_check
            return health_check
    
    async def run_all_health_checks(self) -> List[HealthCheck]:
        """Run all registered health checks"""
        if not self.health_checks:
            return []
        
        # Run all checks concurrently
        tasks = [
            self.run_health_check(name) 
            for name in self.health_checks.keys()
        ]
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Handle any exceptions
        health_checks = []
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                check_name = list(self.health_checks.keys())[i]
                health_check = HealthCheck(
                    name=check_name,
                    status=HealthStatus.CRITICAL,
                    message=f"Health check exception: {str(result)}"
                )
                health_checks.append(health_check)
            else:
                health_checks.append(result)
        
        return health_checks
    
    def collect_system_metrics(self) -> SystemMetrics:
        """Collect current system metrics"""
        try:
            # CPU and Memory
            cpu_percent = psutil.cpu_percent(interval=0.1)
            memory = psutil.virtual_memory()
            
            # Disk usage
            disk = psutil.disk_usage('/')
            disk_percent = disk.percent
            
            # GPU metrics
            gpu_memory_percent = 0.0
            gpu_utilization_percent = 0.0
            
            if torch.cuda.is_available():
                try:
                    gpu_memory_allocated = torch.cuda.memory_allocated()
                    gpu_memory_total = torch.cuda.get_device_properties(0).total_memory
                    gpu_memory_percent = (gpu_memory_allocated / gpu_memory_total) * 100
                    
                    # GPU utilization (basic estimation)
                    import subprocess
                    result = subprocess.run(['nvidia-smi', '--query-gpu=utilization.gpu', '--format=csv,noheader,nounits'], 
                                          capture_output=True, text=True, timeout=5)
                    if result.returncode == 0:
                        gpu_utilization_percent = float(result.stdout.strip())
                except Exception:
                    pass  # GPU metrics optional
            
            # Network stats
            current_network = psutil.net_io_counters()
            network_bytes_sent = current_network.bytes_sent - self._last_network_stats.bytes_sent
            network_bytes_recv = current_network.bytes_recv - self._last_network_stats.bytes_recv
            self._last_network_stats = current_network
            
            return SystemMetrics(
                cpu_percent=cpu_percent,
                memory_percent=memory.percent,
                disk_percent=disk_percent,
                gpu_memory_percent=gpu_memory_percent,
                gpu_utilization_percent=gpu_utilization_percent,
                network_bytes_sent=network_bytes_sent,
                network_bytes_recv=network_bytes_recv
            )
            
        except Exception as e:
            self.logger.error(f"Failed to collect system metrics: {e}")
            return SystemMetrics(
                cpu_percent=0.0,
                memory_percent=0.0,
                disk_percent=0.0,
                gpu_memory_percent=0.0,
                gpu_utilization_percent=0.0,
                network_bytes_sent=0,
                network_bytes_recv=0
            )
    
    def analyze_system_health(self, metrics: SystemMetrics) -> List[HealthCheck]:
        """Analyze system metrics and generate health checks"""
        checks = []
        
        # CPU usage check
        if metrics.cpu_percent > self.cpu_threshold:
            status = HealthStatus.WARNING if metrics.cpu_percent < 95 else HealthStatus.CRITICAL
            checks.append(HealthCheck(
                name="cpu_usage",
                status=status,
                message=f"High CPU usage: {metrics.cpu_percent:.1f}%",
                metadata={"cpu_percent": metrics.cpu_percent}
            ))
        else:
            checks.append(HealthCheck(
                name="cpu_usage",
                status=HealthStatus.HEALTHY,
                message=f"CPU usage normal: {metrics.cpu_percent:.1f}%",
                metadata={"cpu_percent": metrics.cpu_percent}
            ))
        
        # Memory usage check
        if metrics.memory_percent > self.memory_threshold:
            status = HealthStatus.WARNING if metrics.memory_percent < 95 else HealthStatus.CRITICAL
            checks.append(HealthCheck(
                name="memory_usage",
                status=status,
                message=f"High memory usage: {metrics.memory_percent:.1f}%",
                metadata={"memory_percent": metrics.memory_percent}
            ))
        else:
            checks.append(HealthCheck(
                name="memory_usage",
                status=HealthStatus.HEALTHY,
                message=f"Memory usage normal: {metrics.memory_percent:.1f}%",
                metadata={"memory_percent": metrics.memory_percent}
            ))
        
        # Disk usage check
        if metrics.disk_percent > self.disk_threshold:
            status = HealthStatus.WARNING if metrics.disk_percent < 98 else HealthStatus.CRITICAL
            checks.append(HealthCheck(
                name="disk_usage",
                status=status,
                message=f"High disk usage: {metrics.disk_percent:.1f}%",
                metadata={"disk_percent": metrics.disk_percent}
            ))
        else:
            checks.append(HealthCheck(
                name="disk_usage",
                status=HealthStatus.HEALTHY,
                message=f"Disk usage normal: {metrics.disk_percent:.1f}%",
                metadata={"disk_percent": metrics.disk_percent}
            ))
        
        # GPU memory check
        if torch.cuda.is_available() and metrics.gpu_memory_percent > 0:
            if metrics.gpu_memory_percent > self.gpu_memory_threshold:
                status = HealthStatus.WARNING if metrics.gpu_memory_percent < 98 else HealthStatus.CRITICAL
                checks.append(HealthCheck(
                    name="gpu_memory_usage",
                    status=status,
                    message=f"High GPU memory usage: {metrics.gpu_memory_percent:.1f}%",
                    metadata={"gpu_memory_percent": metrics.gpu_memory_percent}
                ))
            else:
                checks.append(HealthCheck(
                    name="gpu_memory_usage",
                    status=HealthStatus.HEALTHY,
                    message=f"GPU memory usage normal: {metrics.gpu_memory_percent:.1f}%",
                    metadata={"gpu_memory_percent": metrics.gpu_memory_percent}
                ))
        
        return checks
    
    def determine_overall_status(self, health_checks: List[HealthCheck]) -> HealthStatus:
        """Determine overall health status from individual checks"""
        if not health_checks:
            return HealthStatus.UNKNOWN
        
        statuses = [check.status for check in health_checks]
        
        # Priority: CRITICAL > UNHEALTHY > WARNING > HEALTHY > UNKNOWN
        if HealthStatus.CRITICAL in statuses:
            return HealthStatus.CRITICAL
        elif HealthStatus.UNHEALTHY in statuses:
            return HealthStatus.UNHEALTHY
        elif HealthStatus.WARNING in statuses:
            return HealthStatus.WARNING
        elif HealthStatus.HEALTHY in statuses:
            return HealthStatus.HEALTHY
        else:
            return HealthStatus.UNKNOWN
    
    async def get_current_health(self) -> ServiceHealth:
        """Get current health status"""
        # Run all health checks
        health_checks = await self.run_all_health_checks()
        
        # Collect system metrics
        system_metrics = self.collect_system_metrics()
        
        # Add system health checks
        system_health_checks = self.analyze_system_health(system_metrics)
        health_checks.extend(system_health_checks)
        
        # Determine overall status
        overall_status = self.determine_overall_status(health_checks)
        
        # Calculate uptime
        uptime = (datetime.now() - self.start_time).total_seconds()
        
        return ServiceHealth(
            service_name=self.service_name,
            status=overall_status,
            uptime_seconds=uptime,
            checks=health_checks,
            system_metrics=system_metrics
        )
    
    async def start_monitoring(self) -> None:
        """Start continuous health monitoring"""
        if self._monitoring_task is not None:
            self.logger.warning("Health monitoring already started")
            return
        
        self._monitoring_task = asyncio.create_task(self._monitoring_loop())
        self.logger.info("Started health monitoring")
    
    async def stop_monitoring(self) -> None:
        """Stop health monitoring"""
        if self._monitoring_task is None:
            return
        
        self._shutdown_event.set()
        
        try:
            await asyncio.wait_for(self._monitoring_task, timeout=5.0)
        except asyncio.TimeoutError:
            self._monitoring_task.cancel()
            try:
                await self._monitoring_task
            except asyncio.CancelledError:
                pass
        
        self._monitoring_task = None
        self.logger.info("Stopped health monitoring")
    
    async def _monitoring_loop(self) -> None:
        """Main monitoring loop"""
        while not self._shutdown_event.is_set():
            try:
                # Collect system metrics
                metrics = self.collect_system_metrics()
                
                # Store metrics history
                self.system_metrics_history.append(metrics)
                if len(self.system_metrics_history) > self.max_history_size:
                    self.system_metrics_history = self.system_metrics_history[-self.max_history_size:]
                
                # Log warnings for system metrics
                if metrics.cpu_percent > self.cpu_threshold:
                    self.logger.warning(f"High CPU usage: {metrics.cpu_percent:.1f}%")
                
                if metrics.memory_percent > self.memory_threshold:
                    self.logger.warning(f"High memory usage: {metrics.memory_percent:.1f}%")
                
                if metrics.gpu_memory_percent > self.gpu_memory_threshold:
                    self.logger.warning(f"High GPU memory usage: {metrics.gpu_memory_percent:.1f}%")
                
                # Wait for next check
                await asyncio.sleep(self.check_interval_seconds)
                
            except Exception as e:
                self.logger.error(f"Error in monitoring loop: {e}")
                await asyncio.sleep(self.check_interval_seconds)
    
    def get_metrics_history(self, minutes: int = 60) -> List[SystemMetrics]:
        """Get system metrics history for the last N minutes"""
        cutoff_time = datetime.now() - timedelta(minutes=minutes)
        return [
            metrics for metrics in self.system_metrics_history
            if metrics.timestamp >= cutoff_time
        ]
    
    def get_health_summary(self) -> Dict[str, Any]:
        """Get a summary of health status"""
        uptime = (datetime.now() - self.start_time).total_seconds()
        
        # Get latest results
        recent_checks = list(self.last_check_results.values())
        overall_status = self.determine_overall_status(recent_checks)
        
        # Get latest system metrics
        latest_metrics = None
        if self.system_metrics_history:
            latest_metrics = self.system_metrics_history[-1]
        
        return {
            "service_name": self.service_name,
            "status": overall_status.value,
            "uptime_seconds": uptime,
            "uptime_formatted": str(timedelta(seconds=int(uptime))),
            "start_time": self.start_time.isoformat(),
            "total_checks": len(self.health_checks),
            "healthy_checks": len([c for c in recent_checks if c.status == HealthStatus.HEALTHY]),
            "warning_checks": len([c for c in recent_checks if c.status == HealthStatus.WARNING]),
            "unhealthy_checks": len([c for c in recent_checks if c.status == HealthStatus.UNHEALTHY]),
            "critical_checks": len([c for c in recent_checks if c.status == HealthStatus.CRITICAL]),
            "latest_system_metrics": {
                "cpu_percent": latest_metrics.cpu_percent if latest_metrics else 0,
                "memory_percent": latest_metrics.memory_percent if latest_metrics else 0,
                "gpu_memory_percent": latest_metrics.gpu_memory_percent if latest_metrics else 0,
                "timestamp": latest_metrics.timestamp.isoformat() if latest_metrics else None
            } if latest_metrics else None,
            "monitoring_active": self._monitoring_task is not None and not self._monitoring_task.done()
        }


# =============================================================================
# UTILITY FUNCTIONS
# =============================================================================

async def create_basic_health_checks() -> Dict[str, Callable]:
    """Create basic health checks for common services"""
    
    async def ping_check():
        """Simple ping/alive check"""
        return HealthStatus.HEALTHY, "Service is responding"
    
    async def memory_leak_check():
        """Check for potential memory leaks"""
        import gc
        gc.collect()
        
        memory = psutil.virtual_memory()
        if memory.percent > 90:
            return HealthStatus.WARNING, f"Very high memory usage: {memory.percent:.1f}%"
        return HealthStatus.HEALTHY, f"Memory usage normal: {memory.percent:.1f}%"
    
    async def disk_space_check():
        """Check available disk space"""
        disk = psutil.disk_usage('/')
        if disk.percent > 95:
            return HealthStatus.CRITICAL, f"Critical disk usage: {disk.percent:.1f}%"
        elif disk.percent > 85:
            return HealthStatus.WARNING, f"High disk usage: {disk.percent:.1f}%"
        return HealthStatus.HEALTHY, f"Disk usage normal: {disk.percent:.1f}%"
    
    return {
        "ping": ping_check,
        "memory_leak": memory_leak_check,
        "disk_space": disk_space_check
    } 