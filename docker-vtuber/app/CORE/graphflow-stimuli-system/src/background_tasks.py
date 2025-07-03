"""
Background tasks for the GraphFlow External Stimuli System.

This module provides background tasks that run periodically to maintain
system health, collect metrics, and perform cleanup operations.
"""

import asyncio
import json
import os
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, List

try:
    import aiofiles
except ImportError:
    # Fallback for missing aiofiles
    class aiofiles:
        @staticmethod
        def open(filename, mode):
            class AsyncFileContext:
                def __init__(self, filename, mode):
                    self.filename = filename
                    self.mode = mode
                    self.file = None
                
                async def __aenter__(self):
                    self.file = open(self.filename, self.mode)
                    return self
                
                async def __aexit__(self, *args):
                    if self.file:
                        self.file.close()
                
                async def write(self, data):
                    return self.file.write(data)
                
                async def read(self):
                    return self.file.read()
            
            return AsyncFileContext(filename, mode)

try:
    import psutil
except ImportError:
    # Fallback for missing psutil
    class psutil:
        @staticmethod
        def cpu_percent(interval=None):
            return 0.0
        
        @staticmethod
        def cpu_count():
            return os.cpu_count() or 1
        
        @staticmethod
        def cpu_freq():
            return None
        
        @staticmethod
        def virtual_memory():
            class Memory:
                percent = 0.0
                available = 0
                total = 0
            return Memory()
        
        @staticmethod
        def disk_usage(path):
            class Disk:
                percent = 0.0
                free = 0
                total = 0
            return Disk()
        
        @staticmethod
        def net_io_counters():
            return None

from .gateway.gateway_agent import GraphFlowGatewayAgent
from .utils.logging import get_structured_logger
from .utils.metrics import MetricsCollector
from .models.stimuli import ProcessingResult
from .integrations.system1_interface import System1Interface
from .integrations.system2_interface import System2Interface


logger = get_structured_logger("background_tasks")


class BackgroundTaskManager:
    """Manages all background tasks for the GraphFlow system."""
    
    def __init__(self, gateway: GraphFlowGatewayAgent, config: Dict[str, Any]):
        self.gateway = gateway
        self.config = config
        self.metrics_collector = MetricsCollector()
        
        # Extract system interface configs from nested structure
        system1_config = config.get("system1", {})
        system2_config = config.get("system2", {})
        
        self.system1_interface = System1Interface(system1_config)
        self.system2_interface = System2Interface(system2_config)
        self.tasks: List[asyncio.Task] = []
        self.running = False
        
        # Storage paths
        self.results_path = "/app/data/results"
        self.metrics_path = "/app/data/metrics"
        self.state_path = "/app/data/state"
        
        # Ensure directories exist
        for path in [self.results_path, self.metrics_path, self.state_path]:
            os.makedirs(path, exist_ok=True)
    
    async def start(self):
        """Start all background tasks."""
        if self.running:
            return
        
        self.running = True
        logger.info("Starting background task manager")
        
        # Start tasks
        self.tasks = [
            asyncio.create_task(self._health_check_loop()),
            asyncio.create_task(self._metrics_aggregation_loop()),
            asyncio.create_task(self._cleanup_loop()),
            asyncio.create_task(self._state_sync_loop()),
            asyncio.create_task(self._system_monitor_loop()),
            asyncio.create_task(self._performance_optimization_loop())
        ]
        
        logger.info(f"Started {len(self.tasks)} background tasks")
    
    async def stop(self):
        """Stop all background tasks."""
        if not self.running:
            return
        
        self.running = False
        logger.info("Stopping background task manager")
        
        # Cancel all tasks
        for task in self.tasks:
            task.cancel()
        
        # Wait for all tasks to complete
        await asyncio.gather(*self.tasks, return_exceptions=True)
        
        logger.info("All background tasks stopped")
    
    async def _health_check_loop(self):
        """Periodic health checks for all systems."""
        interval = self.config.get("health_check_interval", 30)
        
        while self.running:
            try:
                # Check gateway health
                gateway_health = await self.gateway.health_check()
                
                # Check external systems
                system1_health = await self._check_system_health(self.system1_interface, "System1")
                system2_health = await self._check_system_health(self.system2_interface, "System2")
                
                # Aggregate health status
                overall_health = {
                    "timestamp": datetime.now().isoformat(),
                    "gateway": gateway_health,
                    "external_systems": {
                        "system1": system1_health,
                        "system2": system2_health
                    }
                }
                
                # Log health status
                if gateway_health["status"] != "healthy":
                    logger.warning(f"Gateway health check failed: {gateway_health}")
                
                # Save health status
                await self._save_health_status(overall_health)
                
                # Alert on critical issues
                await self._check_and_alert_health_issues(overall_health)
                
            except Exception as e:
                logger.error(f"Health check loop error: {e}")
            
            await asyncio.sleep(interval)
    
    async def _check_system_health(self, interface: Any, name: str) -> Dict[str, Any]:
        """Check health of an external system."""
        try:
            if hasattr(interface, 'health_check'):
                result = await interface.health_check()
                return {
                    "healthy": result.get("status") == "healthy",
                    "status": result.get("status", "unknown"),
                    "details": result
                }
        except Exception as e:
            logger.error(f"Failed to check {name} health: {e}")
            return {
                "healthy": False,
                "status": "error",
                "error": str(e)
            }
    
    async def _metrics_aggregation_loop(self):
        """Aggregate and report metrics periodically."""
        interval = self.config.get("metrics_interval", 60)
        
        while self.running:
            try:
                # Collect gateway metrics
                gateway_metrics = await self.gateway.get_metrics()
                
                # Collect system metrics
                system_metrics = {
                    "cpu_percent": psutil.cpu_percent(interval=1),
                    "memory_percent": psutil.virtual_memory().percent,
                    "disk_usage": psutil.disk_usage('/').percent,
                    "network_io": psutil.net_io_counters()._asdict() if psutil.net_io_counters() else {}
                }
                
                # Aggregate all metrics
                aggregated_metrics = {
                    "timestamp": datetime.now().isoformat(),
                    "gateway": gateway_metrics,
                    "system": system_metrics,
                    "custom": self.metrics_collector.get_all_metrics()
                }
                
                # Save metrics
                await self._save_metrics(aggregated_metrics)
                
                # Report to monitoring systems
                await self._report_metrics(aggregated_metrics)
                
            except Exception as e:
                logger.error(f"Metrics aggregation error: {e}")
            
            await asyncio.sleep(interval)
    
    async def _cleanup_loop(self):
        """Clean up old processing results and temporary files."""
        interval = self.config.get("cleanup_interval", 300)  # 5 minutes
        retention_hours = self.config.get("results_retention_hours", 24)
        
        while self.running:
            try:
                cutoff_time = datetime.now() - timedelta(hours=retention_hours)
                
                # Clean up old result files
                cleaned_count = await self._cleanup_old_files(
                    self.results_path,
                    cutoff_time,
                    "*.json"
                )
                
                # Clean up old metrics files
                metrics_cleaned = await self._cleanup_old_files(
                    self.metrics_path,
                    cutoff_time - timedelta(days=6),  # Keep metrics for 7 days
                    "*.json"
                )
                
                # Clean up temporary files
                temp_cleaned = await self._cleanup_temp_files()
                
                if cleaned_count > 0 or metrics_cleaned > 0 or temp_cleaned > 0:
                    logger.info(
                        f"Cleanup completed: {cleaned_count} results, "
                        f"{metrics_cleaned} metrics, {temp_cleaned} temp files"
                    )
                
                # Run garbage collection
                import gc
                gc.collect()
                
            except Exception as e:
                logger.error(f"Cleanup loop error: {e}")
            
            await asyncio.sleep(interval)
    
    async def _state_sync_loop(self):
        """Synchronize system state across components."""
        interval = self.config.get("state_sync_interval", 120)  # 2 minutes
        
        while self.running:
            try:
                # Get current gateway state
                gateway_state = await self._get_gateway_state()
                
                # Save state locally
                await self._save_state(gateway_state)
                
                # Sync with external systems if needed
                if self.config.get("enable_state_sync", False):
                    await self._sync_external_state(gateway_state)
                
                # Validate state consistency
                await self._validate_state_consistency()
                
            except Exception as e:
                logger.error(f"State sync loop error: {e}")
            
            await asyncio.sleep(interval)
    
    async def _system_monitor_loop(self):
        """Monitor system resources and performance."""
        interval = self.config.get("monitor_interval", 15)
        
        while self.running:
            try:
                # Monitor resource usage
                resources = {
                    "cpu": {
                        "percent": psutil.cpu_percent(interval=1),
                        "count": psutil.cpu_count(),
                        "freq": psutil.cpu_freq()._asdict() if psutil.cpu_freq() else {}
                    },
                    "memory": {
                        "percent": psutil.virtual_memory().percent,
                        "available": psutil.virtual_memory().available,
                        "total": psutil.virtual_memory().total
                    },
                    "disk": {
                        "percent": psutil.disk_usage('/').percent,
                        "free": psutil.disk_usage('/').free,
                        "total": psutil.disk_usage('/').total
                    }
                }
                
                # Check for resource alerts
                if resources["cpu"]["percent"] > 80:
                    logger.warning(f"High CPU usage: {resources['cpu']['percent']}%")
                
                if resources["memory"]["percent"] > 85:
                    logger.warning(f"High memory usage: {resources['memory']['percent']}%")
                
                if resources["disk"]["percent"] > 90:
                    logger.warning(f"High disk usage: {resources['disk']['percent']}%")
                
                # Save monitoring data
                await self._save_monitoring_data(resources)
                
            except Exception as e:
                logger.error(f"System monitor loop error: {e}")
            
            await asyncio.sleep(interval)
    
    async def _performance_optimization_loop(self):
        """Optimize system performance based on metrics."""
        interval = self.config.get("optimization_interval", 600)  # 10 minutes
        
        while self.running:
            try:
                # Analyze performance metrics
                metrics = await self._analyze_performance_metrics()
                
                # Apply optimizations
                if metrics.get("avg_processing_time", 0) > 2.0:
                    logger.info("High processing time detected, applying optimizations")
                    await self._apply_performance_optimizations()
                
                # Clean up caches if memory usage is high
                memory_percent = psutil.virtual_memory().percent
                if memory_percent > 75:
                    logger.info(f"High memory usage ({memory_percent}%), clearing caches")
                    await self._clear_caches()
                
            except Exception as e:
                logger.error(f"Performance optimization loop error: {e}")
            
            await asyncio.sleep(interval)
    
    # Helper methods
    
    async def _save_health_status(self, health_data: Dict[str, Any]):
        """Save health status to file."""
        filename = f"health_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        filepath = os.path.join(self.state_path, filename)
        
        async with aiofiles.open(filepath, 'w') as f:
            await f.write(json.dumps(health_data, indent=2))
    
    async def _save_metrics(self, metrics_data: Dict[str, Any]):
        """Save metrics to file."""
        filename = f"metrics_{datetime.now().strftime('%Y%m%d_%H')}.json"
        filepath = os.path.join(self.metrics_path, filename)
        
        # Append metrics to hourly file
        try:
            async with aiofiles.open(filepath, 'r') as f:
                existing = json.loads(await f.read())
        except:
            existing = {"entries": []}
        
        existing["entries"].append(metrics_data)
        
        async with aiofiles.open(filepath, 'w') as f:
            await f.write(json.dumps(existing, indent=2))
    
    async def _save_state(self, state_data: Dict[str, Any]):
        """Save system state."""
        filename = "current_state.json"
        filepath = os.path.join(self.state_path, filename)
        
        async with aiofiles.open(filepath, 'w') as f:
            await f.write(json.dumps(state_data, indent=2))
    
    async def _save_monitoring_data(self, data: Dict[str, Any]):
        """Save monitoring data."""
        filename = f"monitor_{datetime.now().strftime('%Y%m%d')}.json"
        filepath = os.path.join(self.metrics_path, filename)
        
        # Append to daily file
        try:
            async with aiofiles.open(filepath, 'r') as f:
                existing = json.loads(await f.read())
        except:
            existing = {"entries": []}
        
        existing["entries"].append({
            "timestamp": datetime.now().isoformat(),
            "data": data
        })
        
        async with aiofiles.open(filepath, 'w') as f:
            await f.write(json.dumps(existing, indent=2))
    
    async def _cleanup_old_files(self, directory: str, cutoff_time: datetime, pattern: str) -> int:
        """Clean up old files from a directory."""
        import glob
        cleaned = 0
        
        for filepath in glob.glob(os.path.join(directory, pattern)):
            try:
                stat = os.stat(filepath)
                file_time = datetime.fromtimestamp(stat.st_mtime)
                
                if file_time < cutoff_time:
                    os.remove(filepath)
                    cleaned += 1
            except Exception as e:
                logger.error(f"Failed to clean up {filepath}: {e}")
        
        return cleaned
    
    async def _cleanup_temp_files(self) -> int:
        """Clean up temporary files."""
        temp_dirs = ["/tmp", "/var/tmp"]
        cleaned = 0
        
        for temp_dir in temp_dirs:
            try:
                for filename in os.listdir(temp_dir):
                    if filename.startswith("graphflow_"):
                        filepath = os.path.join(temp_dir, filename)
                        try:
                            os.remove(filepath)
                            cleaned += 1
                        except:
                            pass
            except:
                pass
        
        return cleaned
    
    async def _get_gateway_state(self) -> Dict[str, Any]:
        """Get current gateway state."""
        return {
            "timestamp": datetime.now().isoformat(),
            "health": await self.gateway.health_check(),
            "metrics": await self.gateway.get_metrics(),
            "config": {
                "version": "1.0.0",
                "environment": os.getenv("ENVIRONMENT", "production")
            }
        }
    
    async def _sync_external_state(self, state: Dict[str, Any]):
        """Sync state with external systems."""
        # Implementation depends on external system requirements
        pass
    
    async def _validate_state_consistency(self):
        """Validate state consistency across components."""
        # Implementation for state validation
        pass
    
    async def _check_and_alert_health_issues(self, health: Dict[str, Any]):
        """Check for critical health issues and send alerts."""
        # Check gateway health
        if health["gateway"]["status"] != "healthy":
            logger.critical(f"Gateway unhealthy: {health['gateway']}")
            # Send alert (implement alert mechanism)
        
        # Check external systems
        for system, data in health["external_systems"].items():
            if not data.get("healthy", False):
                logger.error(f"{system} unhealthy: {data}")
    
    async def _report_metrics(self, metrics: Dict[str, Any]):
        """Report metrics to monitoring systems."""
        # Implementation for metric reporting (e.g., to Prometheus pushgateway)
        pass
    
    async def _analyze_performance_metrics(self) -> Dict[str, Any]:
        """Analyze performance metrics."""
        try:
            # Read recent metrics
            metrics_file = os.path.join(self.metrics_path, f"metrics_{datetime.now().strftime('%Y%m%d_%H')}.json")
            
            async with aiofiles.open(metrics_file, 'r') as f:
                data = json.loads(await f.read())
            
            # Calculate averages
            processing_times = []
            for entry in data.get("entries", []):
                if "gateway" in entry and "avg_processing_time" in entry["gateway"]:
                    processing_times.append(entry["gateway"]["avg_processing_time"])
            
            return {
                "avg_processing_time": sum(processing_times) / len(processing_times) if processing_times else 0
            }
        except:
            return {}
    
    async def _apply_performance_optimizations(self):
        """Apply performance optimizations."""
        # Implementation for performance optimizations
        logger.info("Applying performance optimizations")
        
        # Example: Adjust worker pool sizes, cache settings, etc.
        pass
    
    async def _clear_caches(self):
        """Clear system caches."""
        # Implementation for cache clearing
        logger.info("Clearing system caches")
        
        # Clear any in-memory caches
        if hasattr(self.gateway, 'clear_cache'):
            await self.gateway.clear_cache()


async def start_background_tasks(gateway: GraphFlowGatewayAgent, config: Dict[str, Any]) -> BackgroundTaskManager:
    """Start all background tasks."""
    manager = BackgroundTaskManager(gateway, config)
    await manager.start()
    return manager