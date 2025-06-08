#!/usr/bin/env python3
"""
Request Queue System for AI Model Services
=========================================

Manages incoming inference requests with priority handling, load balancing,
and queue management to prevent overload and ensure fair resource allocation.

Features:
- Priority-based request queuing
- Configurable queue limits and timeouts
- Request batching for efficiency
- Load balancing and backpressure handling
- Comprehensive metrics and monitoring
"""

import logging
import asyncio
import time
from enum import IntEnum
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Callable, Any, Tuple
from datetime import datetime, timedelta
from collections import defaultdict
import heapq
import uuid


# =============================================================================
# CONFIGURATION AND ENUMS
# =============================================================================

class QueuePriority(IntEnum):
    """Request priority levels (lower values = higher priority)"""
    CRITICAL = 1    # Real-time voice processing
    HIGH = 2        # Interactive requests 
    NORMAL = 3      # Standard processing
    LOW = 4         # Batch operations
    BACKGROUND = 5  # Background tasks


@dataclass
class QueueConfig:
    """Configuration for request queue"""
    max_queue_size: int = 1000
    max_concurrent_requests: int = 10
    request_timeout_seconds: float = 30.0
    batch_size: int = 1
    batch_timeout_ms: float = 100.0
    enable_batching: bool = False
    priority_weights: Dict[QueuePriority, float] = field(default_factory=lambda: {
        QueuePriority.CRITICAL: 1.0,
        QueuePriority.HIGH: 0.8,
        QueuePriority.NORMAL: 0.6,
        QueuePriority.LOW: 0.4,
        QueuePriority.BACKGROUND: 0.2
    })


@dataclass
class QueueRequest:
    """Individual request in the queue"""
    id: str
    priority: QueuePriority
    data: Dict[str, Any]
    timestamp: datetime
    timeout: Optional[datetime] = None
    retries: int = 0
    max_retries: int = 3
    callback: Optional[Callable] = None
    
    def __post_init__(self):
        if self.timeout is None:
            self.timeout = self.timestamp + timedelta(seconds=30)
    
    def __lt__(self, other):
        """Priority comparison for heap queue"""
        # Lower priority value = higher actual priority
        return (self.priority.value, self.timestamp) < (other.priority.value, other.timestamp)


@dataclass
class QueueMetrics:
    """Queue performance metrics"""
    total_requests: int = 0
    completed_requests: int = 0
    failed_requests: int = 0
    timeout_requests: int = 0
    current_queue_size: int = 0
    max_queue_size_reached: int = 0
    average_wait_time_ms: float = 0.0
    average_processing_time_ms: float = 0.0
    requests_per_second: float = 0.0
    last_reset_time: datetime = field(default_factory=datetime.now)


# =============================================================================
# REQUEST QUEUE IMPLEMENTATION
# =============================================================================

class RequestQueue:
    """
    High-performance request queue with priority handling and load balancing
    """
    
    def __init__(self, config: QueueConfig, processor_func: Callable):
        self.config = config
        self.processor_func = processor_func
        self.logger = logging.getLogger("request_queue")
        
        # Queue state
        self._priority_queue: List[QueueRequest] = []
        self._active_requests: Dict[str, QueueRequest] = {}
        self._pending_batches: Dict[QueuePriority, List[QueueRequest]] = defaultdict(list)
        
        # Synchronization
        self._queue_lock = asyncio.Lock()
        self._processing_semaphore = asyncio.Semaphore(config.max_concurrent_requests)
        self._shutdown_event = asyncio.Event()
        
        # Metrics tracking
        self.metrics = QueueMetrics()
        self._processing_times: List[float] = []
        self._wait_times: List[float] = []
        
        # Background tasks
        self._processor_task: Optional[asyncio.Task] = None
        self._metrics_task: Optional[asyncio.Task] = None
        self._cleanup_task: Optional[asyncio.Task] = None
        
        self.logger.info("Request Queue initialized")
        self.logger.info(f"  - Max Queue Size: {config.max_queue_size}")
        self.logger.info(f"  - Max Concurrent: {config.max_concurrent_requests}")
        self.logger.info(f"  - Request Timeout: {config.request_timeout_seconds}s")
        self.logger.info(f"  - Batching Enabled: {config.enable_batching}")
        
    async def start(self):
        """Start the queue processing"""
        if self._processor_task is not None:
            self.logger.warning("Queue already started")
            return
            
        self._processor_task = asyncio.create_task(self._process_requests())
        self._metrics_task = asyncio.create_task(self._update_metrics())
        self._cleanup_task = asyncio.create_task(self._cleanup_expired_requests())
        
        self.logger.info("Request Queue started")
    
    async def stop(self):
        """Stop the queue processing"""
        self.logger.info("Stopping Request Queue...")
        
        self._shutdown_event.set()
        
        # Cancel background tasks
        for task in [self._processor_task, self._metrics_task, self._cleanup_task]:
            if task and not task.done():
                task.cancel()
                try:
                    await task
                except asyncio.CancelledError:
                    pass
        
        # Wait for active requests to complete (with timeout)
        wait_start = time.time()
        while self._active_requests and (time.time() - wait_start) < 10:
            await asyncio.sleep(0.1)
        
        self.logger.info("Request Queue stopped")
    
    async def submit_request(
        self, 
        data: Dict[str, Any], 
        priority: QueuePriority = QueuePriority.NORMAL,
        timeout_seconds: Optional[float] = None,
        callback: Optional[Callable] = None
    ) -> str:
        """
        Submit a request to the queue
        
        Args:
            data: Request data to process
            priority: Request priority level
            timeout_seconds: Optional custom timeout
            callback: Optional callback function
            
        Returns:
            Request ID for tracking
        """
        request_id = str(uuid.uuid4())
        
        # Create request
        request = QueueRequest(
            id=request_id,
            priority=priority,
            data=data,
            timestamp=datetime.now(),
            callback=callback
        )
        
        # Set custom timeout if provided
        if timeout_seconds is not None:
            request.timeout = request.timestamp + timedelta(seconds=timeout_seconds)
        
        async with self._queue_lock:
            # Check queue capacity
            if len(self._priority_queue) >= self.config.max_queue_size:
                self.logger.warning(f"Queue full, rejecting request {request_id}")
                raise RuntimeError("Queue is full")
            
            # Add to priority queue
            heapq.heappush(self._priority_queue, request)
            self.metrics.total_requests += 1
            self.metrics.current_queue_size = len(self._priority_queue)
            
            # Track max queue size
            if self.metrics.current_queue_size > self.metrics.max_queue_size_reached:
                self.metrics.max_queue_size_reached = self.metrics.current_queue_size
        
        self.logger.debug(f"Queued request {request_id} with priority {priority.name}")
        return request_id
    
    async def get_request_status(self, request_id: str) -> Dict[str, Any]:
        """Get status of a specific request"""
        async with self._queue_lock:
            # Check if request is active
            if request_id in self._active_requests:
                request = self._active_requests[request_id]
                return {
                    "id": request_id,
                    "status": "processing",
                    "priority": request.priority.name,
                    "queued_at": request.timestamp.isoformat(),
                    "retries": request.retries
                }
            
            # Check if request is in queue
            for request in self._priority_queue:
                if request.id == request_id:
                    wait_time = (datetime.now() - request.timestamp).total_seconds()
                    return {
                        "id": request_id,
                        "status": "queued",
                        "priority": request.priority.name,
                        "queued_at": request.timestamp.isoformat(),
                        "wait_time_seconds": wait_time,
                        "position_in_queue": self._get_queue_position(request)
                    }
            
            return {"id": request_id, "status": "not_found"}
    
    def _get_queue_position(self, target_request: QueueRequest) -> int:
        """Get the position of a request in the queue"""
        position = 1
        for request in sorted(self._priority_queue):
            if request.id == target_request.id:
                return position
            position += 1
        return -1
    
    async def _process_requests(self):
        """Main request processing loop"""
        while not self._shutdown_event.is_set():
            try:
                # Get next request from queue
                request = await self._get_next_request()
                if request is None:
                    await asyncio.sleep(0.01)  # Short sleep if no requests
                    continue
                
                # Process request with concurrency control
                asyncio.create_task(self._process_single_request(request))
                
            except Exception as e:
                self.logger.error(f"Error in request processing loop: {e}")
                await asyncio.sleep(1)
    
    async def _get_next_request(self) -> Optional[QueueRequest]:
        """Get the next request to process"""
        async with self._queue_lock:
            if not self._priority_queue:
                return None
            
            # Check if we can process more requests
            if len(self._active_requests) >= self.config.max_concurrent_requests:
                return None
            
            # Get highest priority request
            request = heapq.heappop(self._priority_queue)
            self.metrics.current_queue_size = len(self._priority_queue)
            
            # Check if request has expired
            if datetime.now() > request.timeout:
                self.logger.warning(f"Request {request.id} expired before processing")
                self.metrics.timeout_requests += 1
                return await self._get_next_request()  # Try next request
            
            # Mark as active
            self._active_requests[request.id] = request
            
            return request
    
    async def _process_single_request(self, request: QueueRequest):
        """Process a single request"""
        async with self._processing_semaphore:
            start_time = time.time()
            wait_time = (datetime.now() - request.timestamp).total_seconds() * 1000
            
            try:
                self.logger.debug(f"Processing request {request.id}")
                
                # Process the request
                result = await self.processor_func(request.data)
                
                # Calculate timing
                processing_time = (time.time() - start_time) * 1000
                
                # Update metrics
                async with self._queue_lock:
                    self.metrics.completed_requests += 1
                    self._wait_times.append(wait_time)
                    self._processing_times.append(processing_time)
                    
                    # Remove from active requests
                    self._active_requests.pop(request.id, None)
                
                # Execute callback if provided
                if request.callback:
                    try:
                        await request.callback(request.id, result, None)
                    except Exception as e:
                        self.logger.error(f"Callback error for request {request.id}: {e}")
                
                self.logger.debug(f"Completed request {request.id} in {processing_time:.1f}ms")
                
            except Exception as e:
                self.logger.error(f"Processing error for request {request.id}: {e}")
                
                # Handle retries
                if request.retries < request.max_retries:
                    request.retries += 1
                    self.logger.info(f"Retrying request {request.id} (attempt {request.retries})")
                    
                    # Re-queue the request
                    async with self._queue_lock:
                        heapq.heappush(self._priority_queue, request)
                        self.metrics.current_queue_size = len(self._priority_queue)
                        self._active_requests.pop(request.id, None)
                else:
                    # Max retries exceeded
                    async with self._queue_lock:
                        self.metrics.failed_requests += 1
                        self._active_requests.pop(request.id, None)
                    
                    # Execute error callback
                    if request.callback:
                        try:
                            await request.callback(request.id, None, str(e))
                        except Exception as cb_e:
                            self.logger.error(f"Error callback failed for request {request.id}: {cb_e}")
    
    async def _cleanup_expired_requests(self):
        """Cleanup expired requests from the queue"""
        while not self._shutdown_event.is_set():
            try:
                current_time = datetime.now()
                expired_count = 0
                
                async with self._queue_lock:
                    # Filter out expired requests
                    new_queue = []
                    for request in self._priority_queue:
                        if current_time <= request.timeout:
                            new_queue.append(request)
                        else:
                            expired_count += 1
                            self.metrics.timeout_requests += 1
                    
                    # Rebuild heap if any expired requests were found
                    if expired_count > 0:
                        self._priority_queue = new_queue
                        heapq.heapify(self._priority_queue)
                        self.metrics.current_queue_size = len(self._priority_queue)
                        
                        self.logger.info(f"Cleaned up {expired_count} expired requests")
                
                # Sleep for cleanup interval
                await asyncio.sleep(10)  # Check every 10 seconds
                
            except Exception as e:
                self.logger.error(f"Error in cleanup task: {e}")
                await asyncio.sleep(10)
    
    async def _update_metrics(self):
        """Update performance metrics"""
        while not self._shutdown_event.is_set():
            try:
                async with self._queue_lock:
                    # Calculate average wait time
                    if self._wait_times:
                        self.metrics.average_wait_time_ms = sum(self._wait_times) / len(self._wait_times)
                        # Keep only recent measurements
                        if len(self._wait_times) > 1000:
                            self._wait_times = self._wait_times[-500:]
                    
                    # Calculate average processing time
                    if self._processing_times:
                        self.metrics.average_processing_time_ms = sum(self._processing_times) / len(self._processing_times)
                        # Keep only recent measurements
                        if len(self._processing_times) > 1000:
                            self._processing_times = self._processing_times[-500:]
                    
                    # Calculate requests per second
                    time_elapsed = (datetime.now() - self.metrics.last_reset_time).total_seconds()
                    if time_elapsed > 0:
                        self.metrics.requests_per_second = self.metrics.completed_requests / time_elapsed
                
                # Sleep for metrics update interval
                await asyncio.sleep(5)  # Update every 5 seconds
                
            except Exception as e:
                self.logger.error(f"Error updating metrics: {e}")
                await asyncio.sleep(5)
    
    def get_queue_metrics(self) -> Dict[str, Any]:
        """Get current queue metrics"""
        return {
            "total_requests": self.metrics.total_requests,
            "completed_requests": self.metrics.completed_requests,
            "failed_requests": self.metrics.failed_requests,
            "timeout_requests": self.metrics.timeout_requests,
            "current_queue_size": self.metrics.current_queue_size,
            "max_queue_size_reached": self.metrics.max_queue_size_reached,
            "active_requests": len(self._active_requests),
            "average_wait_time_ms": self.metrics.average_wait_time_ms,
            "average_processing_time_ms": self.metrics.average_processing_time_ms,
            "requests_per_second": self.metrics.requests_per_second,
            "success_rate": (
                self.metrics.completed_requests / max(1, self.metrics.total_requests) * 100
            ),
            "queue_utilization": (
                self.metrics.current_queue_size / self.config.max_queue_size * 100
            ),
            "processing_utilization": (
                len(self._active_requests) / self.config.max_concurrent_requests * 100
            )
        }
    
    def reset_metrics(self):
        """Reset metrics counters"""
        self.metrics = QueueMetrics()
        self._wait_times.clear()
        self._processing_times.clear()
        self.logger.info("Queue metrics reset")


# =============================================================================
# EXAMPLE USAGE
# =============================================================================

async def example_processor(data: Dict[str, Any]) -> Dict[str, Any]:
    """Example request processor function"""
    # Simulate processing time
    await asyncio.sleep(0.1)
    return {"result": f"Processed: {data.get('input', 'unknown')}", "timestamp": datetime.now().isoformat()}


async def main():
    """Example usage of the request queue"""
    # Configure queue
    config = QueueConfig(
        max_queue_size=100,
        max_concurrent_requests=5,
        request_timeout_seconds=10.0
    )
    
    # Create queue
    queue = RequestQueue(config, example_processor)
    
    try:
        # Start processing
        await queue.start()
        
        # Submit test requests
        request_ids = []
        for i in range(10):
            request_id = await queue.submit_request(
                data={"input": f"test_data_{i}"},
                priority=QueuePriority.NORMAL
            )
            request_ids.append(request_id)
        
        # Wait for processing
        await asyncio.sleep(2)
        
        # Check metrics
        metrics = queue.get_queue_metrics()
        print("Queue Metrics:", metrics)
        
        # Check request status
        for request_id in request_ids[:3]:
            status = await queue.get_request_status(request_id)
            print(f"Request {request_id}: {status}")
        
    finally:
        await queue.stop()


if __name__ == "__main__":
    asyncio.run(main()) 