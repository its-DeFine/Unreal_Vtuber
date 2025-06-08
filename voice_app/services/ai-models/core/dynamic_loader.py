#!/usr/bin/env python3
"""
Dynamic Model Loading System
===========================

Advanced dynamic model loading with memory optimization, preloading strategies,
and intelligent model swapping for AI services.

Features:
- GPU memory-aware model loading/unloading
- Intelligent model preloading and caching
- Priority-based model management
- Background model preparation
- Memory pressure handling
- Performance optimization strategies
"""

import logging
import asyncio
import threading
import time
from typing import Dict, List, Optional, Any, Callable, Type, Tuple
from dataclasses import dataclass, field
from enum import Enum
from datetime import datetime, timedelta
import torch
import gc
from pathlib import Path

from .model_manager import BaseModel, ModelState, ModelManager
from ..utils.request_queue import RequestQueue, Priority


# =============================================================================
# DYNAMIC LOADING CONFIGURATION
# =============================================================================

class LoadingStrategy(Enum):
    """Model loading strategies"""
    LAZY = "lazy"              # Load only when needed
    EAGER = "eager"            # Preload all models
    PREDICTIVE = "predictive"  # Load based on usage patterns
    PRIORITY = "priority"      # Load based on priority
    MEMORY_AWARE = "memory_aware"  # Load based on memory availability


class UnloadingStrategy(Enum):
    """Model unloading strategies"""
    LRU = "lru"                # Least Recently Used
    LFU = "lfu"                # Least Frequently Used
    MEMORY_PRESSURE = "memory_pressure"  # Unload when memory is low
    TIME_BASED = "time_based"  # Unload after idle time
    PRIORITY_BASED = "priority_based"  # Unload low priority first


@dataclass
class ModelLoadRequest:
    """Request to load a model"""
    model_name: str
    model_class: Type[BaseModel]
    config: Dict[str, Any]
    priority: Priority = Priority.NORMAL
    preload: bool = False
    required_memory_mb: Optional[int] = None
    timestamp: datetime = field(default_factory=datetime.now)
    
    def __post_init__(self):
        # Estimate memory requirements if not provided
        if self.required_memory_mb is None:
            self.required_memory_mb = self._estimate_memory_requirement()
    
    def _estimate_memory_requirement(self) -> int:
        """Estimate memory requirement based on model configuration"""
        # Basic heuristics for common model types
        if "whisper" in self.model_name.lower():
            size_map = {
                "tiny": 50,
                "base": 100,
                "small": 250,
                "medium": 800,
                "large": 1500
            }
            for size, mb in size_map.items():
                if size in self.model_name.lower():
                    return mb
            return 500  # Default for unknown Whisper models
        
        elif "tts" in self.model_name.lower() or "coqui" in self.model_name.lower():
            return 300  # Typical TTS model size
        
        elif "llama" in self.model_name.lower():
            if "3b" in self.model_name.lower():
                return 2000
            elif "7b" in self.model_name.lower():
                return 4000
            elif "13b" in self.model_name.lower():
                return 8000
            return 3000  # Default for LLaMA variants
        
        return 500  # Conservative default


@dataclass
class ModelUsageStats:
    """Model usage statistics for intelligent loading"""
    model_name: str
    load_count: int = 0
    usage_count: int = 0
    last_used: datetime = field(default_factory=datetime.now)
    last_loaded: Optional[datetime] = None
    average_load_time_ms: float = 0.0
    average_memory_usage_mb: float = 0.0
    success_rate: float = 1.0
    priority_score: float = 0.0


@dataclass
class LoadingConfig:
    """Configuration for dynamic loading system"""
    max_loaded_models: int = 3
    memory_threshold_percent: float = 85.0
    preload_popular_models: bool = True
    background_loading: bool = True
    usage_prediction: bool = True
    idle_unload_minutes: int = 10
    loading_strategy: LoadingStrategy = LoadingStrategy.MEMORY_AWARE
    unloading_strategy: UnloadingStrategy = UnloadingStrategy.LRU


# =============================================================================
# DYNAMIC MODEL LOADER
# =============================================================================

class DynamicModelLoader:
    """Advanced dynamic model loading system"""
    
    def __init__(
        self, 
        model_manager: ModelManager,
        config: Optional[LoadingConfig] = None
    ):
        self.model_manager = model_manager
        self.config = config or LoadingConfig()
        self.logger = logging.getLogger("dynamic_loader")
        
        # Model tracking
        self.registered_models: Dict[str, Type[BaseModel]] = {}
        self.model_configs: Dict[str, Dict[str, Any]] = {}
        self.usage_stats: Dict[str, ModelUsageStats] = {}
        self.load_queue = RequestQueue(max_concurrent=2)
        
        # Loading state
        self._loading_tasks: Dict[str, asyncio.Task] = {}
        self._preload_task: Optional[asyncio.Task] = None
        self._background_task: Optional[asyncio.Task] = None
        self._shutdown_event = asyncio.Event()
        
        # Usage prediction
        self._usage_patterns: Dict[str, List[datetime]] = {}
        self._pattern_lock = threading.RLock()
        
        self.logger.info("Dynamic Model Loader initialized")
    
    def register_model(
        self, 
        model_name: str, 
        model_class: Type[BaseModel],
        config: Dict[str, Any],
        preload: bool = False
    ) -> None:
        """
        Register a model for dynamic loading
        
        Args:
            model_name: Unique model identifier
            model_class: Model class to instantiate
            config: Model configuration
            preload: Whether to preload this model
        """
        self.registered_models[model_name] = model_class
        self.model_configs[model_name] = config
        
        # Initialize usage stats
        if model_name not in self.usage_stats:
            self.usage_stats[model_name] = ModelUsageStats(model_name=model_name)
        
        # Initialize usage patterns
        with self._pattern_lock:
            if model_name not in self._usage_patterns:
                self._usage_patterns[model_name] = []
        
        self.logger.info(f"Registered model: {model_name} (preload: {preload})")
        
        # Add to preload queue if requested
        if preload:
            asyncio.create_task(self._queue_preload(model_name))
    
    def unregister_model(self, model_name: str) -> None:
        """Unregister a model"""
        # Unload if currently loaded
        asyncio.create_task(self.unload_model(model_name))
        
        # Remove from tracking
        self.registered_models.pop(model_name, None)
        self.model_configs.pop(model_name, None)
        self.usage_stats.pop(model_name, None)
        
        with self._pattern_lock:
            self._usage_patterns.pop(model_name, None)
        
        self.logger.info(f"Unregistered model: {model_name}")
    
    async def load_model(
        self, 
        model_name: str, 
        priority: Priority = Priority.NORMAL,
        timeout_seconds: Optional[float] = None
    ) -> Optional[BaseModel]:
        """
        Load a model dynamically
        
        Args:
            model_name: Model to load
            priority: Loading priority
            timeout_seconds: Maximum time to wait for loading
            
        Returns:
            Loaded model instance or None if failed
        """
        if model_name not in self.registered_models:
            self.logger.error(f"Model not registered: {model_name}")
            return None
        
        # Check if already loaded
        if self.model_manager.is_model_loaded(model_name):
            self._record_usage(model_name)
            return self.model_manager.get_model(model_name)
        
        # Check if currently loading
        if model_name in self._loading_tasks:
            loading_task = self._loading_tasks[model_name]
            if not loading_task.done():
                try:
                    timeout = timeout_seconds or 60.0
                    await asyncio.wait_for(loading_task, timeout=timeout)
                except asyncio.TimeoutError:
                    self.logger.warning(f"Loading timeout for model: {model_name}")
                    return None
        
        # Create load request
        model_class = self.registered_models[model_name]
        config = self.model_configs[model_name].copy()
        
        request = ModelLoadRequest(
            model_name=model_name,
            model_class=model_class,
            config=config,
            priority=priority
        )
        
        # Queue the loading request
        try:
            result = await self.load_queue.enqueue(
                self._load_model_worker,
                request,
                priority=priority,
                timeout_seconds=timeout_seconds or 60.0
            )
            
            if result:
                self._record_usage(model_name)
                return result
            
        except Exception as e:
            self.logger.error(f"Failed to load model {model_name}: {e}")
        
        return None
    
    async def unload_model(self, model_name: str) -> bool:
        """
        Unload a model
        
        Args:
            model_name: Model to unload
            
        Returns:
            Success status
        """
        try:
            # Cancel any pending load task
            if model_name in self._loading_tasks:
                task = self._loading_tasks[model_name]
                if not task.done():
                    task.cancel()
                    try:
                        await task
                    except asyncio.CancelledError:
                        pass
                del self._loading_tasks[model_name]
            
            # Unload from model manager
            success = await self.model_manager.unload_model(model_name)
            
            if success:
                self.logger.info(f"Unloaded model: {model_name}")
            
            return success
            
        except Exception as e:
            self.logger.error(f"Failed to unload model {model_name}: {e}")
            return False
    
    async def _load_model_worker(self, request: ModelLoadRequest) -> Optional[BaseModel]:
        """Worker function to actually load a model"""
        model_name = request.model_name
        
        try:
            self.logger.info(f"Loading model: {model_name}")
            start_time = time.time()
            
            # Check memory availability
            if not await self._ensure_memory_available(request.required_memory_mb):
                self.logger.warning(f"Insufficient memory for model: {model_name}")
                return None
            
            # Create loading task
            loading_task = asyncio.create_task(
                self._do_model_load(request)
            )
            self._loading_tasks[model_name] = loading_task
            
            try:
                model = await loading_task
                
                if model:
                    load_time = (time.time() - start_time) * 1000
                    self._update_load_stats(model_name, load_time, success=True)
                    self.logger.info(f"Successfully loaded {model_name} in {load_time:.1f}ms")
                    return model
                else:
                    self._update_load_stats(model_name, 0, success=False)
                    return None
                    
            finally:
                self._loading_tasks.pop(model_name, None)
            
        except Exception as e:
            self.logger.error(f"Model loading failed for {model_name}: {e}")
            self._update_load_stats(model_name, 0, success=False)
            return None
    
    async def _do_model_load(self, request: ModelLoadRequest) -> Optional[BaseModel]:
        """Actually perform the model loading"""
        try:
            # Create model instance
            model = request.model_class(**request.config)
            
            # Load the model
            await model.load()
            
            # Register with model manager
            self.model_manager.add_model(request.model_name, model)
            
            return model
            
        except Exception as e:
            self.logger.error(f"Model instantiation failed: {e}")
            return None
    
    async def _ensure_memory_available(self, required_mb: int) -> bool:
        """Ensure sufficient memory is available for loading"""
        if not torch.cuda.is_available():
            return True  # Can't check CPU memory effectively
        
        try:
            # Get current GPU memory usage
            memory_allocated = torch.cuda.memory_allocated()
            memory_total = torch.cuda.get_device_properties(0).total_memory
            memory_used_percent = (memory_allocated / memory_total) * 100
            
            # Calculate required memory
            required_bytes = required_mb * 1024 * 1024
            
            # Check if we have enough memory
            available_bytes = memory_total - memory_allocated
            
            if available_bytes < required_bytes:
                # Need to free up memory
                await self._free_memory(required_bytes - available_bytes)
                
                # Recheck after cleanup
                memory_allocated = torch.cuda.memory_allocated()
                available_bytes = memory_total - memory_allocated
                
                if available_bytes < required_bytes:
                    self.logger.warning(
                        f"Insufficient GPU memory: need {required_mb}MB, "
                        f"available {available_bytes // (1024*1024)}MB"
                    )
                    return False
            
            return True
            
        except Exception as e:
            self.logger.error(f"Memory check failed: {e}")
            return True  # Assume okay if we can't check
    
    async def _free_memory(self, bytes_needed: int) -> None:
        """Free up GPU memory by unloading models"""
        self.logger.info(f"Freeing up {bytes_needed // (1024*1024)}MB of GPU memory")
        
        # Get loaded models sorted by unloading strategy
        loaded_models = self.model_manager.get_loaded_models()
        
        if self.config.unloading_strategy == UnloadingStrategy.LRU:
            # Sort by last used time
            models_to_consider = sorted(
                loaded_models.items(),
                key=lambda x: self.usage_stats.get(x[0], ModelUsageStats(x[0])).last_used
            )
        elif self.config.unloading_strategy == UnloadingStrategy.LFU:
            # Sort by usage count
            models_to_consider = sorted(
                loaded_models.items(),
                key=lambda x: self.usage_stats.get(x[0], ModelUsageStats(x[0])).usage_count
            )
        else:
            # Default to LRU
            models_to_consider = sorted(
                loaded_models.items(),
                key=lambda x: self.usage_stats.get(x[0], ModelUsageStats(x[0])).last_used
            )
        
        freed_bytes = 0
        for model_name, model in models_to_consider:
            if freed_bytes >= bytes_needed:
                break
            
            # Estimate model memory usage
            estimated_mb = self.usage_stats.get(model_name, ModelUsageStats(model_name)).average_memory_usage_mb
            if estimated_mb == 0:
                estimated_mb = 500  # Conservative estimate
            
            # Unload the model
            if await self.unload_model(model_name):
                freed_bytes += estimated_mb * 1024 * 1024
                self.logger.info(f"Freed memory by unloading: {model_name}")
        
        # Force garbage collection
        if torch.cuda.is_available():
            torch.cuda.empty_cache()
        gc.collect()
    
    def _record_usage(self, model_name: str) -> None:
        """Record model usage for statistics"""
        if model_name not in self.usage_stats:
            self.usage_stats[model_name] = ModelUsageStats(model_name=model_name)
        
        stats = self.usage_stats[model_name]
        stats.usage_count += 1
        stats.last_used = datetime.now()
        
        # Update usage patterns
        with self._pattern_lock:
            if model_name not in self._usage_patterns:
                self._usage_patterns[model_name] = []
            
            patterns = self._usage_patterns[model_name]
            patterns.append(datetime.now())
            
            # Keep only recent patterns (last 24 hours)
            cutoff = datetime.now() - timedelta(hours=24)
            self._usage_patterns[model_name] = [
                t for t in patterns if t >= cutoff
            ]
    
    def _update_load_stats(self, model_name: str, load_time_ms: float, success: bool) -> None:
        """Update loading statistics"""
        if model_name not in self.usage_stats:
            self.usage_stats[model_name] = ModelUsageStats(model_name=model_name)
        
        stats = self.usage_stats[model_name]
        stats.load_count += 1
        
        if success:
            stats.last_loaded = datetime.now()
            
            # Update average load time
            if stats.average_load_time_ms == 0:
                stats.average_load_time_ms = load_time_ms
            else:
                stats.average_load_time_ms = (
                    stats.average_load_time_ms * 0.8 + load_time_ms * 0.2
                )
        
        # Update success rate
        total_attempts = stats.load_count
        if success:
            stats.success_rate = (stats.success_rate * (total_attempts - 1) + 1.0) / total_attempts
        else:
            stats.success_rate = (stats.success_rate * (total_attempts - 1)) / total_attempts
    
    async def _queue_preload(self, model_name: str) -> None:
        """Queue a model for preloading"""
        try:
            await self.load_model(model_name, priority=Priority.LOW)
        except Exception as e:
            self.logger.error(f"Preload failed for {model_name}: {e}")
    
    def predict_next_models(self, lookahead_minutes: int = 30) -> List[str]:
        """Predict which models will likely be needed soon"""
        predicted = []
        
        with self._pattern_lock:
            for model_name, patterns in self._usage_patterns.items():
                if not patterns:
                    continue
                
                # Analyze usage patterns
                now = datetime.now()
                recent_patterns = [p for p in patterns if (now - p).total_seconds() < 3600]  # Last hour
                
                if len(recent_patterns) >= 2:
                    # Simple pattern: if used in last hour, likely to be used again
                    intervals = []
                    for i in range(1, len(recent_patterns)):
                        interval = (recent_patterns[i] - recent_patterns[i-1]).total_seconds() / 60
                        intervals.append(interval)
                    
                    if intervals:
                        avg_interval = sum(intervals) / len(intervals)
                        last_use = recent_patterns[-1]
                        time_since_last = (now - last_use).total_seconds() / 60
                        
                        # Predict if model will be needed within lookahead window
                        if avg_interval > 0 and time_since_last >= avg_interval * 0.8:
                            predicted.append(model_name)
        
        return predicted
    
    async def start_background_tasks(self) -> None:
        """Start background optimization tasks"""
        if self.config.background_loading:
            self._background_task = asyncio.create_task(self._background_optimization_loop())
            self.logger.info("Started background optimization")
    
    async def stop_background_tasks(self) -> None:
        """Stop background tasks"""
        self._shutdown_event.set()
        
        if self._background_task:
            try:
                await asyncio.wait_for(self._background_task, timeout=5.0)
            except asyncio.TimeoutError:
                self._background_task.cancel()
            self._background_task = None
        
        self.logger.info("Stopped background optimization")
    
    async def _background_optimization_loop(self) -> None:
        """Background loop for model optimization"""
        while not self._shutdown_event.is_set():
            try:
                # Predictive loading
                if self.config.usage_prediction:
                    predicted_models = self.predict_next_models()
                    for model_name in predicted_models:
                        if not self.model_manager.is_model_loaded(model_name):
                            await self._queue_preload(model_name)
                
                # Idle unloading
                await self._unload_idle_models()
                
                # Memory optimization
                if torch.cuda.is_available():
                    memory_percent = self._get_gpu_memory_usage()
                    if memory_percent > self.config.memory_threshold_percent:
                        await self._free_memory(100 * 1024 * 1024)  # Free 100MB
                
                # Wait before next optimization cycle
                await asyncio.sleep(60)  # Check every minute
                
            except Exception as e:
                self.logger.error(f"Background optimization error: {e}")
                await asyncio.sleep(60)
    
    async def _unload_idle_models(self) -> None:
        """Unload models that have been idle for too long"""
        idle_threshold = timedelta(minutes=self.config.idle_unload_minutes)
        now = datetime.now()
        
        for model_name in list(self.model_manager.get_loaded_models().keys()):
            stats = self.usage_stats.get(model_name)
            if stats and (now - stats.last_used) > idle_threshold:
                self.logger.info(f"Unloading idle model: {model_name}")
                await self.unload_model(model_name)
    
    def _get_gpu_memory_usage(self) -> float:
        """Get current GPU memory usage percentage"""
        if not torch.cuda.is_available():
            return 0.0
        
        try:
            allocated = torch.cuda.memory_allocated()
            total = torch.cuda.get_device_properties(0).total_memory
            return (allocated / total) * 100
        except Exception:
            return 0.0
    
    def get_loading_stats(self) -> Dict[str, Any]:
        """Get loading system statistics"""
        total_models = len(self.registered_models)
        loaded_models = len(self.model_manager.get_loaded_models())
        
        return {
            "total_registered": total_models,
            "currently_loaded": loaded_models,
            "loading_ratio": loaded_models / total_models if total_models > 0 else 0,
            "gpu_memory_usage": self._get_gpu_memory_usage(),
            "queue_size": self.load_queue.qsize(),
            "background_optimization": self._background_task is not None and not self._background_task.done(),
            "model_stats": {
                name: {
                    "load_count": stats.load_count,
                    "usage_count": stats.usage_count,
                    "success_rate": stats.success_rate,
                    "average_load_time_ms": stats.average_load_time_ms,
                    "last_used": stats.last_used.isoformat() if stats.last_used else None
                }
                for name, stats in self.usage_stats.items()
            }
        } 