#!/usr/bin/env python3
"""
Core Model Manager for Voice Platform
==================================

Orchestrates AI models and tracks GPU memory usage to optimize resource allocation.
Provides interfaces for model registration, loading, unloading, and memory management.

Features:
- GPU memory monitoring and enforcement
- Dynamic model lifecycle management 
- Resource allocation optimization
- Model registration and discovery
- Health monitoring and metrics
- Concurrent request handling
"""

import logging
import threading
import time
import gc
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Optional, Callable, Any, Set
from datetime import datetime, timedelta
import asyncio
from concurrent.futures import ThreadPoolExecutor

import torch
import psutil
import GPUtil
from functools import wraps


# =============================================================================
# CONFIGURATION AND CONSTANTS
# =============================================================================

@dataclass
class ModelConfig:
    """Configuration for a managed model"""
    name: str
    model_type: str  # 'llm', 'tts', 'stt'
    memory_requirement_mb: int
    load_time_estimate_ms: int
    priority: int = 1  # 1=highest, 5=lowest
    max_concurrent_requests: int = 4
    idle_timeout_seconds: int = 300  # 5 minutes
    health_check_interval_seconds: int = 60
    fallback_model: Optional[str] = None


class ModelState(Enum):
    """Model lifecycle states"""
    UNLOADED = "unloaded"
    LOADING = "loading"
    LOADED = "loaded"
    ACTIVE = "active"
    UNLOADING = "unloading"
    ERROR = "error"
    FAILED = "failed"


@dataclass
class ModelMetrics:
    """Model performance and usage metrics"""
    total_requests: int = 0
    active_requests: int = 0
    total_inference_time_ms: float = 0.0
    last_request_time: Optional[datetime] = None
    load_time_ms: float = 0.0
    memory_usage_mb: float = 0.0
    error_count: int = 0
    health_score: float = 1.0  # 0.0 to 1.0


# =============================================================================
# ABSTRACT MODEL INTERFACE
# =============================================================================

class BaseModel(ABC):
    """Abstract base class for all managed models"""
    
    def __init__(self, config: ModelConfig):
        self.config = config
        self.state = ModelState.UNLOADED
        self.metrics = ModelMetrics()
        self.logger = logging.getLogger(f"model.{config.name}")
        self._lock = threading.RLock()
        
    @abstractmethod
    async def load(self) -> bool:
        """Load the model into memory"""
        pass
        
    @abstractmethod
    async def unload(self) -> bool:
        """Unload the model from memory"""
        pass
        
    @abstractmethod
    async def inference(self, request_data: Dict[str, Any]) -> Dict[str, Any]:
        """Perform model inference"""
        pass
        
    @abstractmethod
    async def health_check(self) -> bool:
        """Check model health status"""
        pass
        
    def get_memory_usage(self) -> float:
        """Get current GPU memory usage in MB"""
        if torch.cuda.is_available() and self.state in [ModelState.LOADED, ModelState.ACTIVE]:
            return torch.cuda.memory_allocated() / 1024 / 1024
        return 0.0


# =============================================================================
# GPU MEMORY MANAGER
# =============================================================================

class GPUMemoryManager:
    """Manages GPU memory allocation and optimization"""
    
    def __init__(self, memory_limit_percent: float = 90.0):
        self.memory_limit_percent = memory_limit_percent
        self.logger = logging.getLogger("gpu_memory")
        self._lock = threading.Lock()
        
        # Initialize GPU information
        self.gpu_count = torch.cuda.device_count() if torch.cuda.is_available() else 0
        self.total_memory_mb = 0
        self.memory_limit_mb = 0
        
        if self.gpu_count > 0:
            # Use first GPU for now (can be extended for multi-GPU)
            gpu_props = torch.cuda.get_device_properties(0)
            self.total_memory_mb = gpu_props.total_memory / 1024 / 1024
            self.memory_limit_mb = self.total_memory_mb * (memory_limit_percent / 100.0)
            
            self.logger.info(f"GPU Memory Manager initialized:")
            self.logger.info(f"  - GPU Count: {self.gpu_count}")
            self.logger.info(f"  - Total Memory: {self.total_memory_mb:.1f} MB")
            self.logger.info(f"  - Memory Limit: {self.memory_limit_mb:.1f} MB ({memory_limit_percent}%)")
        else:
            self.logger.warning("No CUDA GPUs available")
    
    def get_available_memory(self) -> float:
        """Get available GPU memory in MB"""
        if not torch.cuda.is_available():
            return 0.0
            
        with self._lock:
            allocated = torch.cuda.memory_allocated() / 1024 / 1024
            return max(0, self.memory_limit_mb - allocated)
    
    def get_memory_stats(self) -> Dict[str, float]:
        """Get comprehensive memory statistics"""
        if not torch.cuda.is_available():
            return {
                "total_mb": 0,
                "allocated_mb": 0,
                "cached_mb": 0,
                "available_mb": 0,
                "utilization_percent": 0.0
            }
            
        with self._lock:
            allocated = torch.cuda.memory_allocated() / 1024 / 1024
            cached = torch.cuda.memory_reserved() / 1024 / 1024
            available = self.get_available_memory()
            utilization = (allocated / self.total_memory_mb) * 100.0
            
            return {
                "total_mb": self.total_memory_mb,
                "allocated_mb": allocated,
                "cached_mb": cached,
                "available_mb": available,
                "utilization_percent": utilization,
                "limit_mb": self.memory_limit_mb
            }
    
    def can_allocate(self, required_mb: float) -> bool:
        """Check if the required memory can be allocated"""
        available = self.get_available_memory()
        return available >= required_mb
    
    def optimize_memory(self) -> Dict[str, Any]:
        """Optimize GPU memory usage"""
        if not torch.cuda.is_available():
            return {"status": "no_gpu"}
            
        with self._lock:
            before_stats = self.get_memory_stats()
            
            # Clear GPU cache
            torch.cuda.empty_cache()
            
            # Force garbage collection
            gc.collect()
            
            after_stats = self.get_memory_stats()
            freed_mb = before_stats["cached_mb"] - after_stats["cached_mb"]
            
            self.logger.info(f"Memory optimization completed - freed {freed_mb:.1f} MB")
            
            return {
                "status": "optimized",
                "freed_mb": freed_mb,
                "before": before_stats,
                "after": after_stats
            }


# =============================================================================
# CORE MODEL MANAGER
# =============================================================================

class ModelManager:
    """
    Core model manager for orchestrating AI models with GPU memory optimization
    """
    
    def __init__(self, memory_limit_percent: float = 90.0, max_workers: int = 4):
        self.logger = logging.getLogger("model_manager")
        self.gpu_memory = GPUMemoryManager(memory_limit_percent)
        self.max_workers = max_workers
        
        # Model registry and state tracking
        self._models: Dict[str, BaseModel] = {}
        self._model_configs: Dict[str, ModelConfig] = {}
        self._lock = threading.RLock()
        
        # Monitoring and metrics
        self._metrics = {
            "total_requests": 0,
            "active_requests": 0,
            "models_loaded": 0,
            "memory_optimizations": 0,
            "start_time": datetime.now()
        }
        
        # Background tasks
        self._executor = ThreadPoolExecutor(max_workers=max_workers)
        self._monitoring_task = None
        self._shutdown_event = threading.Event()
        
        self.logger.info("Model Manager initialized")
        self.logger.info(f"  - Max Workers: {max_workers}")
        self.logger.info(f"  - Memory Limit: {memory_limit_percent}%")
        
    def register_model(self, model: BaseModel) -> bool:
        """Register a model with the manager"""
        try:
            with self._lock:
                model_name = model.config.name
                
                if model_name in self._models:
                    self.logger.warning(f"Model {model_name} already registered")
                    return False
                
                self._models[model_name] = model
                self._model_configs[model_name] = model.config
                
                self.logger.info(f"Registered model: {model_name}")
                self.logger.info(f"  - Type: {model.config.model_type}")
                self.logger.info(f"  - Memory Requirement: {model.config.memory_requirement_mb} MB")
                self.logger.info(f"  - Priority: {model.config.priority}")
                
                return True
                
        except Exception as e:
            self.logger.error(f"Failed to register model {model.config.name}: {e}")
            return False
    
    def unregister_model(self, model_name: str) -> bool:
        """Unregister a model from the manager"""
        try:
            with self._lock:
                if model_name not in self._models:
                    self.logger.warning(f"Model {model_name} not registered")
                    return False
                
                model = self._models[model_name]
                
                # Unload if loaded
                if model.state in [ModelState.LOADED, ModelState.ACTIVE]:
                    asyncio.create_task(self._unload_model(model_name))
                
                del self._models[model_name]
                del self._model_configs[model_name]
                
                self.logger.info(f"Unregistered model: {model_name}")
                return True
                
        except Exception as e:
            self.logger.error(f"Failed to unregister model {model_name}: {e}")
            return False
    
    async def load_model(self, model_name: str, force: bool = False) -> bool:
        """Load a model with memory management"""
        try:
            with self._lock:
                if model_name not in self._models:
                    self.logger.error(f"Model {model_name} not registered")
                    return False
                
                model = self._models[model_name]
                
                if model.state in [ModelState.LOADED, ModelState.ACTIVE] and not force:
                    self.logger.info(f"Model {model_name} already loaded")
                    return True
                
                if model.state == ModelState.LOADING:
                    self.logger.info(f"Model {model_name} already loading")
                    return False
                
                # Check memory availability
                required_mb = model.config.memory_requirement_mb
                if not self.gpu_memory.can_allocate(required_mb):
                    self.logger.warning(f"Insufficient memory for {model_name} ({required_mb} MB required)")
                    
                    # Try memory optimization
                    optimization_result = self.gpu_memory.optimize_memory()
                    self._metrics["memory_optimizations"] += 1
                    
                    # Try freeing up memory by unloading idle models
                    if not self.gpu_memory.can_allocate(required_mb):
                        await self._free_memory_for_model(required_mb, exclude_model=model_name)
                    
                    # Final check
                    if not self.gpu_memory.can_allocate(required_mb):
                        self.logger.error(f"Cannot free enough memory for {model_name}")
                        return False
                
                # Update state and load
                model.state = ModelState.LOADING
                
            # Load model (outside lock to prevent blocking)
            start_time = time.time()
            success = await model.load()
            load_time_ms = (time.time() - start_time) * 1000
            
            with self._lock:
                if success:
                    model.state = ModelState.LOADED
                    model.metrics.load_time_ms = load_time_ms
                    model.metrics.memory_usage_mb = model.get_memory_usage()
                    self._metrics["models_loaded"] += 1
                    
                    self.logger.info(f"Successfully loaded {model_name} in {load_time_ms:.1f}ms")
                    return True
                else:
                    model.state = ModelState.FAILED
                    self.logger.error(f"Failed to load {model_name}")
                    return False
                    
        except Exception as e:
            self.logger.error(f"Error loading model {model_name}: {e}")
            if model_name in self._models:
                self._models[model_name].state = ModelState.ERROR
            return False
    
    async def unload_model(self, model_name: str) -> bool:
        """Unload a model and free memory"""
        return await self._unload_model(model_name)
    
    async def _unload_model(self, model_name: str) -> bool:
        """Internal model unloading"""
        try:
            with self._lock:
                if model_name not in self._models:
                    return False
                
                model = self._models[model_name]
                
                if model.state == ModelState.UNLOADED:
                    return True
                
                if model.state == ModelState.UNLOADING:
                    return False
                
                model.state = ModelState.UNLOADING
            
            # Unload model (outside lock)
            success = await model.unload()
            
            with self._lock:
                if success:
                    model.state = ModelState.UNLOADED
                    model.metrics.memory_usage_mb = 0.0
                    self.logger.info(f"Successfully unloaded {model_name}")
                else:
                    model.state = ModelState.ERROR
                    self.logger.error(f"Failed to unload {model_name}")
                
                return success
                
        except Exception as e:
            self.logger.error(f"Error unloading model {model_name}: {e}")
            return False
    
    async def _free_memory_for_model(self, required_mb: float, exclude_model: str = None) -> float:
        """Free memory by unloading idle models"""
        freed_mb = 0.0
        
        with self._lock:
            # Find idle models to unload (sorted by last activity and priority)
            idle_models = []
            current_time = datetime.now()
            
            for model_name, model in self._models.items():
                if model_name == exclude_model:
                    continue
                    
                if model.state in [ModelState.LOADED, ModelState.ACTIVE]:
                    idle_time = current_time - (model.metrics.last_request_time or current_time)
                    is_idle = idle_time.total_seconds() > model.config.idle_timeout_seconds
                    
                    if is_idle and model.metrics.active_requests == 0:
                        idle_models.append((model_name, model, idle_time.total_seconds()))
            
            # Sort by idle time (longest first) and priority (lowest priority first)
            idle_models.sort(key=lambda x: (x[1].config.priority, -x[2]))
        
        # Unload idle models until we have enough memory
        for model_name, model, idle_time in idle_models:
            if freed_mb >= required_mb:
                break
                
            self.logger.info(f"Unloading idle model {model_name} (idle for {idle_time:.1f}s)")
            
            if await self._unload_model(model_name):
                freed_mb += model.config.memory_requirement_mb
        
        return freed_mb
    
    async def inference(self, model_name: str, request_data: Dict[str, Any]) -> Dict[str, Any]:
        """Perform inference with a model"""
        try:
            with self._lock:
                if model_name not in self._models:
                    return {"error": f"Model {model_name} not registered"}
                
                model = self._models[model_name]
                
                # Ensure model is loaded
                if model.state == ModelState.UNLOADED:
                    # Try to load the model
                    if not await self.load_model(model_name):
                        return {"error": f"Failed to load model {model_name}"}
                
                if model.state not in [ModelState.LOADED, ModelState.ACTIVE]:
                    return {"error": f"Model {model_name} not available (state: {model.state})"}
                
                # Check concurrent request limit
                if model.metrics.active_requests >= model.config.max_concurrent_requests:
                    return {"error": f"Model {model_name} at maximum concurrent requests"}
                
                # Update metrics
                model.state = ModelState.ACTIVE
                model.metrics.active_requests += 1
                model.metrics.total_requests += 1
                model.metrics.last_request_time = datetime.now()
                self._metrics["total_requests"] += 1
                self._metrics["active_requests"] += 1
            
            # Perform inference (outside lock)
            start_time = time.time()
            result = await model.inference(request_data)
            inference_time_ms = (time.time() - start_time) * 1000
            
            # Update metrics
            with self._lock:
                model.metrics.active_requests -= 1
                model.metrics.total_inference_time_ms += inference_time_ms
                self._metrics["active_requests"] -= 1
                
                # Update state if no active requests
                if model.metrics.active_requests == 0:
                    model.state = ModelState.LOADED
            
            # Add timing information to result
            if isinstance(result, dict):
                result["inference_time_ms"] = inference_time_ms
            
            return result
            
        except Exception as e:
            self.logger.error(f"Inference error for {model_name}: {e}")
            
            # Update error metrics
            with self._lock:
                if model_name in self._models:
                    model = self._models[model_name]
                    model.metrics.active_requests = max(0, model.metrics.active_requests - 1)
                    model.metrics.error_count += 1
                    
                self._metrics["active_requests"] = max(0, self._metrics["active_requests"] - 1)
            
            return {"error": str(e)}
    
    def get_model_status(self, model_name: str = None) -> Dict[str, Any]:
        """Get status information for models"""
        with self._lock:
            if model_name:
                if model_name not in self._models:
                    return {"error": f"Model {model_name} not found"}
                
                model = self._models[model_name]
                return {
                    "name": model_name,
                    "state": model.state.value,
                    "config": {
                        "type": model.config.model_type,
                        "memory_requirement_mb": model.config.memory_requirement_mb,
                        "priority": model.config.priority,
                        "max_concurrent_requests": model.config.max_concurrent_requests
                    },
                    "metrics": {
                        "total_requests": model.metrics.total_requests,
                        "active_requests": model.metrics.active_requests,
                        "total_inference_time_ms": model.metrics.total_inference_time_ms,
                        "average_inference_time_ms": (
                            model.metrics.total_inference_time_ms / model.metrics.total_requests
                            if model.metrics.total_requests > 0 else 0
                        ),
                        "load_time_ms": model.metrics.load_time_ms,
                        "memory_usage_mb": model.metrics.memory_usage_mb,
                        "error_count": model.metrics.error_count,
                        "health_score": model.metrics.health_score,
                        "last_request_time": model.metrics.last_request_time.isoformat() if model.metrics.last_request_time else None
                    }
                }
            else:
                # Return status for all models
                models_status = {}
                for name, model in self._models.items():
                    models_status[name] = self.get_model_status(name)
                
                return {
                    "models": models_status,
                    "manager_metrics": self._metrics.copy(),
                    "gpu_memory": self.gpu_memory.get_memory_stats()
                }
    
    def start_monitoring(self):
        """Start background monitoring tasks"""
        if self._monitoring_task is None:
            self._monitoring_task = self._executor.submit(self._monitoring_loop)
            self.logger.info("Started model monitoring")
    
    def stop_monitoring(self):
        """Stop background monitoring tasks"""
        self._shutdown_event.set()
        if self._monitoring_task:
            self._monitoring_task.result(timeout=5)
            self._monitoring_task = None
        self.logger.info("Stopped model monitoring")
    
    def _monitoring_loop(self):
        """Background monitoring loop"""
        while not self._shutdown_event.is_set():
            try:
                # Health checks and idle model cleanup
                self._run_health_checks()
                self._cleanup_idle_models()
                
                # Sleep for monitoring interval
                self._shutdown_event.wait(30)  # Check every 30 seconds
                
            except Exception as e:
                self.logger.error(f"Monitoring loop error: {e}")
                self._shutdown_event.wait(30)
    
    def _run_health_checks(self):
        """Run health checks on all loaded models"""
        with self._lock:
            models_to_check = [
                (name, model) for name, model in self._models.items()
                if model.state in [ModelState.LOADED, ModelState.ACTIVE]
            ]
        
        for model_name, model in models_to_check:
            try:
                # Run health check asynchronously
                health_ok = asyncio.run(model.health_check())
                
                with self._lock:
                    if health_ok:
                        model.metrics.health_score = min(1.0, model.metrics.health_score + 0.1)
                    else:
                        model.metrics.health_score = max(0.0, model.metrics.health_score - 0.2)
                        self.logger.warning(f"Health check failed for {model_name}")
                        
            except Exception as e:
                self.logger.error(f"Health check error for {model_name}: {e}")
                with self._lock:
                    model.metrics.health_score = max(0.0, model.metrics.health_score - 0.3)
    
    def _cleanup_idle_models(self):
        """Cleanup idle models based on timeout"""
        current_time = datetime.now()
        models_to_unload = []
        
        with self._lock:
            for model_name, model in self._models.items():
                if model.state in [ModelState.LOADED, ModelState.ACTIVE]:
                    if model.metrics.last_request_time:
                        idle_time = current_time - model.metrics.last_request_time
                        if (idle_time.total_seconds() > model.config.idle_timeout_seconds and 
                            model.metrics.active_requests == 0):
                            models_to_unload.append(model_name)
        
        # Unload idle models
        for model_name in models_to_unload:
            self.logger.info(f"Unloading idle model: {model_name}")
            asyncio.run(self._unload_model(model_name))
    
    def shutdown(self):
        """Shutdown the model manager"""
        self.logger.info("Shutting down Model Manager...")
        
        # Stop monitoring
        self.stop_monitoring()
        
        # Unload all models
        with self._lock:
            model_names = list(self._models.keys())
        
        for model_name in model_names:
            asyncio.run(self._unload_model(model_name))
        
        # Shutdown executor
        self._executor.shutdown(wait=True)
        
        self.logger.info("Model Manager shutdown complete")


# =============================================================================
# DECORATORS AND UTILITIES
# =============================================================================

def track_inference_metrics(func):
    """Decorator to track inference metrics"""
    @wraps(func)
    async def wrapper(self, *args, **kwargs):
        start_time = time.time()
        try:
            result = await func(self, *args, **kwargs)
            return result
        finally:
            inference_time = (time.time() - start_time) * 1000
            self.logger.debug(f"Inference completed in {inference_time:.1f}ms")
    return wrapper


def require_gpu_memory(required_mb: float):
    """Decorator to check GPU memory requirements"""
    def decorator(func):
        @wraps(func)
        async def wrapper(self, *args, **kwargs):
            if hasattr(self, 'gpu_memory'):
                if not self.gpu_memory.can_allocate(required_mb):
                    raise RuntimeError(f"Insufficient GPU memory: {required_mb}MB required")
            return await func(self, *args, **kwargs)
        return wrapper
    return decorator


# =============================================================================
# LOGGING CONFIGURATION
# =============================================================================

def setup_logging():
    """Configure logging for the model manager"""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.StreamHandler(),
            logging.FileHandler('/tmp/model_manager.log')
        ]
    )


if __name__ == "__main__":
    """Example usage and testing"""
    setup_logging()
    
    # Create model manager
    manager = ModelManager()
    
    # Start monitoring
    manager.start_monitoring()
    
    try:
        # Example model registration would go here
        # This requires actual model implementations
        
        # Get status
        status = manager.get_model_status()
        print("Model Manager Status:", status)
        
        # Keep running for testing
        import time
        time.sleep(10)
        
    finally:
        manager.shutdown() 