"""
Unified Queue Service
====================

High-performance, reliable queue system with Redis backend and file-based fallback.
Replaces all existing file-based queue implementations.
"""

import asyncio
import json
import logging
import time
import uuid
from abc import ABC, abstractmethod
from dataclasses import dataclass, asdict
from datetime import datetime, timedelta
from enum import Enum
from pathlib import Path
from typing import Dict, List, Optional, Any, Callable, AsyncGenerator
import redis.asyncio as redis

from ..config import get_config, QueueConfig
from ..di import ServiceLifecycle, singleton


logger = logging.getLogger(__name__)


class MessageStatus(str, Enum):
    """Message processing status"""
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    RETRY = "retry"


@dataclass
class QueueMessage:
    """Standard queue message format"""
    id: str
    queue_name: str
    payload: Dict[str, Any]
    created_at: datetime
    status: MessageStatus = MessageStatus.PENDING
    retry_count: int = 0
    max_retries: int = 3
    delay_until: Optional[datetime] = None
    error_message: Optional[str] = None
    metadata: Dict[str, Any] = None
    
    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization"""
        data = asdict(self)
        data['created_at'] = self.created_at.isoformat()
        if self.delay_until:
            data['delay_until'] = self.delay_until.isoformat()
        return data
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'QueueMessage':
        """Create from dictionary"""
        data['created_at'] = datetime.fromisoformat(data['created_at'])
        if data.get('delay_until'):
            data['delay_until'] = datetime.fromisoformat(data['delay_until'])
        return cls(**data)


class QueueBackend(ABC):
    """Abstract queue backend"""
    
    @abstractmethod
    async def enqueue(self, message: QueueMessage) -> bool:
        """Add message to queue"""
        pass
    
    @abstractmethod
    async def dequeue(self, queue_name: str, timeout: float = 1.0) -> Optional[QueueMessage]:
        """Get next message from queue"""
        pass
    
    @abstractmethod
    async def ack(self, message: QueueMessage) -> bool:
        """Acknowledge message processing"""
        pass
    
    @abstractmethod
    async def nack(self, message: QueueMessage, requeue: bool = True) -> bool:
        """Negative acknowledge - mark as failed"""
        pass
    
    @abstractmethod
    async def get_queue_stats(self, queue_name: str) -> Dict[str, int]:
        """Get queue statistics"""
        pass
    
    @abstractmethod
    async def purge_queue(self, queue_name: str) -> int:
        """Remove all messages from queue"""
        pass


class RedisQueueBackend(QueueBackend):
    """Redis-based queue backend with reliability features"""
    
    def __init__(self, config: QueueConfig):
        self.config = config
        self.redis_client: Optional[redis.Redis] = None
        self._scripts = {}
    
    async def connect(self):
        """Connect to Redis"""
        self.redis_client = redis.from_url(
            self.config.redis_url,
            db=self.config.redis_db,
            decode_responses=True
        )
        
        # Load Lua scripts for atomic operations
        self._scripts['dequeue'] = self.redis_client.register_script("""
            local queue_key = KEYS[1]
            local processing_key = KEYS[2]
            local message = redis.call('LPOP', queue_key)
            if message then
                redis.call('HSET', processing_key, message, ARGV[1])
                return message
            end
            return nil
        """)
        
        await self.redis_client.ping()
        logger.info("Connected to Redis queue backend")
    
    async def disconnect(self):
        """Disconnect from Redis"""
        if self.redis_client:
            await self.redis_client.close()
            logger.info("Disconnected from Redis")
    
    def _get_queue_key(self, queue_name: str) -> str:
        """Get Redis key for queue"""
        return f"{self.config.queue_prefix}:queue:{queue_name}"
    
    def _get_processing_key(self, queue_name: str) -> str:
        """Get Redis key for processing messages"""
        return f"{self.config.queue_prefix}:processing:{queue_name}"
    
    def _get_failed_key(self, queue_name: str) -> str:
        """Get Redis key for failed messages"""
        return f"{self.config.queue_prefix}:failed:{queue_name}"
    
    async def enqueue(self, message: QueueMessage) -> bool:
        """Add message to queue"""
        if not self.redis_client:
            raise RuntimeError("Redis client not connected")
        
        queue_key = self._get_queue_key(message.queue_name)
        message_data = json.dumps(message.to_dict())
        
        if message.delay_until and message.delay_until > datetime.now():
            # Delayed message - use sorted set with timestamp score
            delay_key = f"{queue_key}:delayed"
            score = message.delay_until.timestamp()
            await self.redis_client.zadd(delay_key, {message_data: score})
        else:
            # Immediate message
            await self.redis_client.rpush(queue_key, message_data)
        
        logger.debug(f"Enqueued message {message.id} to {message.queue_name}")
        return True
    
    async def dequeue(self, queue_name: str, timeout: float = 1.0) -> Optional[QueueMessage]:
        """Get next message from queue with timeout"""
        if not self.redis_client:
            raise RuntimeError("Redis client not connected")
        
        queue_key = self._get_queue_key(queue_name)
        processing_key = self._get_processing_key(queue_name)
        
        # First, move any ready delayed messages to main queue
        await self._move_ready_delayed_messages(queue_name)
        
        # Blocking pop with timeout
        result = await self.redis_client.blpop([queue_key], timeout=timeout)
        
        if not result:
            return None
        
        _, message_data = result
        message = QueueMessage.from_dict(json.loads(message_data))
        
        # Mark as processing
        message.status = MessageStatus.PROCESSING
        await self.redis_client.hset(
            processing_key, 
            message.id, 
            json.dumps(message.to_dict())
        )
        
        logger.debug(f"Dequeued message {message.id} from {queue_name}")
        return message
    
    async def _move_ready_delayed_messages(self, queue_name: str):
        """Move delayed messages that are ready to main queue"""
        if not self.redis_client:
            return
        
        queue_key = self._get_queue_key(queue_name)
        delay_key = f"{queue_key}:delayed"
        now = datetime.now().timestamp()
        
        # Get ready messages
        ready_messages = await self.redis_client.zrangebyscore(
            delay_key, 0, now, withscores=False
        )
        
        if ready_messages:
            # Move to main queue
            pipe = self.redis_client.pipeline()
            for message_data in ready_messages:
                pipe.rpush(queue_key, message_data)
                pipe.zrem(delay_key, message_data)
            await pipe.execute()
    
    async def ack(self, message: QueueMessage) -> bool:
        """Acknowledge successful processing"""
        if not self.redis_client:
            return False
        
        processing_key = self._get_processing_key(message.queue_name)
        await self.redis_client.hdel(processing_key, message.id)
        
        logger.debug(f"Acknowledged message {message.id}")
        return True
    
    async def nack(self, message: QueueMessage, requeue: bool = True) -> bool:
        """Handle failed message"""
        if not self.redis_client:
            return False
        
        processing_key = self._get_processing_key(message.queue_name)
        
        if requeue and message.retry_count < message.max_retries:
            # Retry with exponential backoff
            message.retry_count += 1
            message.status = MessageStatus.RETRY
            delay_seconds = min(300, 2 ** message.retry_count)  # Max 5 minutes
            message.delay_until = datetime.now() + timedelta(seconds=delay_seconds)
            
            await self.enqueue(message)
            logger.info(f"Requeued message {message.id} for retry {message.retry_count}")
        else:
            # Move to failed queue
            message.status = MessageStatus.FAILED
            failed_key = self._get_failed_key(message.queue_name)
            await self.redis_client.rpush(failed_key, json.dumps(message.to_dict()))
            logger.error(f"Message {message.id} moved to failed queue")
        
        # Remove from processing
        await self.redis_client.hdel(processing_key, message.id)
        return True
    
    async def get_queue_stats(self, queue_name: str) -> Dict[str, int]:
        """Get queue statistics"""
        if not self.redis_client:
            return {}
        
        queue_key = self._get_queue_key(queue_name)
        processing_key = self._get_processing_key(queue_name)
        failed_key = self._get_failed_key(queue_name)
        delay_key = f"{queue_key}:delayed"
        
        stats = {
            'pending': await self.redis_client.llen(queue_key),
            'processing': await self.redis_client.hlen(processing_key),
            'failed': await self.redis_client.llen(failed_key),
            'delayed': await self.redis_client.zcard(delay_key)
        }
        
        return stats
    
    async def purge_queue(self, queue_name: str) -> int:
        """Remove all messages from queue"""
        if not self.redis_client:
            return 0
        
        queue_key = self._get_queue_key(queue_name)
        processing_key = self._get_processing_key(queue_name)
        failed_key = self._get_failed_key(queue_name)
        delay_key = f"{queue_key}:delayed"
        
        pipe = self.redis_client.pipeline()
        pipe.delete(queue_key)
        pipe.delete(processing_key)
        pipe.delete(failed_key)
        pipe.delete(delay_key)
        results = await pipe.execute()
        
        return sum(results)


class FileQueueBackend(QueueBackend):
    """File-based queue backend for fallback"""
    
    def __init__(self, config: QueueConfig, data_dir: Path):
        self.config = config
        self.data_dir = data_dir
        self.queue_dir = data_dir / "queues"
        self.queue_dir.mkdir(parents=True, exist_ok=True)
        self._locks = {}
    
    def _get_queue_file(self, queue_name: str) -> Path:
        return self.queue_dir / f"{queue_name}.jsonl"
    
    def _get_lock(self, queue_name: str) -> asyncio.Lock:
        if queue_name not in self._locks:
            self._locks[queue_name] = asyncio.Lock()
        return self._locks[queue_name]
    
    async def enqueue(self, message: QueueMessage) -> bool:
        """Add message to file queue"""
        queue_file = self._get_queue_file(message.queue_name)
        lock = self._get_lock(message.queue_name)
        
        async with lock:
            with open(queue_file, 'a') as f:
                f.write(json.dumps(message.to_dict()) + '\n')
        
        return True
    
    async def dequeue(self, queue_name: str, timeout: float = 1.0) -> Optional[QueueMessage]:
        """Get next message from file queue"""
        queue_file = self._get_queue_file(queue_name)
        lock = self._get_lock(queue_name)
        
        start_time = time.time()
        
        while time.time() - start_time < timeout:
            async with lock:
                if not queue_file.exists():
                    await asyncio.sleep(0.1)
                    continue
                
                with open(queue_file, 'r') as f:
                    lines = f.readlines()
                
                if not lines:
                    await asyncio.sleep(0.1)
                    continue
                
                # Get first message
                message_data = json.loads(lines[0])
                message = QueueMessage.from_dict(message_data)
                
                # Remove from file
                with open(queue_file, 'w') as f:
                    f.writelines(lines[1:])
                
                message.status = MessageStatus.PROCESSING
                return message
            
            await asyncio.sleep(0.1)
        
        return None
    
    async def ack(self, message: QueueMessage) -> bool:
        """Acknowledge message"""
        return True
    
    async def nack(self, message: QueueMessage, requeue: bool = True) -> bool:
        """Handle failed message"""
        if requeue and message.retry_count < message.max_retries:
            message.retry_count += 1
            message.status = MessageStatus.RETRY
            await self.enqueue(message)
        return True
    
    async def get_queue_stats(self, queue_name: str) -> Dict[str, int]:
        """Get queue statistics"""
        queue_file = self._get_queue_file(queue_name)
        
        if not queue_file.exists():
            return {'pending': 0, 'processing': 0, 'failed': 0, 'delayed': 0}
        
        with open(queue_file, 'r') as f:
            lines = f.readlines()
        
        return {
            'pending': len(lines),
            'processing': 0,
            'failed': 0,
            'delayed': 0
        }
    
    async def purge_queue(self, queue_name: str) -> int:
        """Remove all messages from queue"""
        queue_file = self._get_queue_file(queue_name)
        
        if queue_file.exists():
            with open(queue_file, 'r') as f:
                count = len(f.readlines())
            queue_file.unlink()
            return count
        
        return 0


@singleton()
class QueueService(ServiceLifecycle):
    """
    Unified queue service with Redis backend and file fallback.
    
    Features:
    - High-performance Redis backend
    - Automatic fallback to file-based queues
    - Message reliability (ack/nack, retries)
    - Delayed message delivery
    - Queue statistics and monitoring
    """
    
    def __init__(self, config: QueueConfig = None):
        self.config = config or get_config().queue
        self.backend: Optional[QueueBackend] = None
        self._consumers: Dict[str, asyncio.Task] = {}
        self._running = False
    
    async def start(self):
        """Start the queue service"""
        if self._running:
            return
        
        # Try Redis first, fallback to file
        try:
            if self.config.type == "redis":
                backend = RedisQueueBackend(self.config)
                await backend.connect()
                self.backend = backend
                logger.info("Queue service started with Redis backend")
            else:
                raise ValueError("Forcing file backend")
        except Exception as e:
            logger.warning(f"Redis backend failed, using file backend: {e}")
            from ..config import get_config
            data_dir = get_config().data_dir
            self.backend = FileQueueBackend(self.config, data_dir)
            logger.info("Queue service started with file backend")
        
        self._running = True
    
    async def stop(self):
        """Stop the queue service"""
        if not self._running:
            return
        
        # Stop all consumers
        for consumer_task in self._consumers.values():
            consumer_task.cancel()
        
        if self._consumers:
            await asyncio.gather(*self._consumers.values(), return_exceptions=True)
        
        # Disconnect backend
        if hasattr(self.backend, 'disconnect'):
            await self.backend.disconnect()
        
        self._running = False
        logger.info("Queue service stopped")
    
    async def health_check(self) -> bool:
        """Check if queue service is healthy"""
        if not self._running or not self.backend:
            return False
        
        try:
            # Try to get stats for a test queue
            await self.backend.get_queue_stats("health_check")
            return True
        except Exception:
            return False
    
    async def enqueue(
        self,
        queue_name: str,
        payload: Dict[str, Any],
        delay: Optional[timedelta] = None,
        max_retries: int = None,
        metadata: Dict[str, Any] = None
    ) -> str:
        """
        Enqueue a message.
        
        Args:
            queue_name: Name of the queue
            payload: Message payload
            delay: Optional delay before processing
            max_retries: Maximum retry attempts
            metadata: Additional metadata
        
        Returns:
            Message ID
        """
        if not self.backend:
            raise RuntimeError("Queue service not started")
        
        message_id = str(uuid.uuid4())
        delay_until = datetime.now() + delay if delay else None
        
        message = QueueMessage(
            id=message_id,
            queue_name=queue_name,
            payload=payload,
            created_at=datetime.now(),
            max_retries=max_retries or self.config.max_retries,
            delay_until=delay_until,
            metadata=metadata or {}
        )
        
        await self.backend.enqueue(message)
        return message_id
    
    async def start_consumer(
        self,
        queue_name: str,
        handler: Callable[[Dict[str, Any]], bool],
        max_concurrent: int = 1
    ):
        """
        Start a queue consumer.
        
        Args:
            queue_name: Name of the queue to consume
            handler: Message handler function (should return True for success)
            max_concurrent: Maximum concurrent message processing
        """
        if queue_name in self._consumers:
            logger.warning(f"Consumer for {queue_name} already exists")
            return
        
        consumer_task = asyncio.create_task(
            self._consumer_loop(queue_name, handler, max_concurrent)
        )
        self._consumers[queue_name] = consumer_task
        logger.info(f"Started consumer for queue: {queue_name}")
    
    async def stop_consumer(self, queue_name: str):
        """Stop a queue consumer"""
        if queue_name in self._consumers:
            self._consumers[queue_name].cancel()
            try:
                await self._consumers[queue_name]
            except asyncio.CancelledError:
                pass
            del self._consumers[queue_name]
            logger.info(f"Stopped consumer for queue: {queue_name}")
    
    async def _consumer_loop(
        self,
        queue_name: str,
        handler: Callable[[Dict[str, Any]], bool],
        max_concurrent: int
    ):
        """Consumer loop with concurrency control"""
        semaphore = asyncio.Semaphore(max_concurrent)
        
        while self._running:
            try:
                message = await self.backend.dequeue(queue_name, timeout=1.0)
                if not message:
                    continue
                
                asyncio.create_task(
                    self._process_message(message, handler, semaphore)
                )
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in consumer loop for {queue_name}: {e}")
                await asyncio.sleep(1)
    
    async def _process_message(
        self,
        message: QueueMessage,
        handler: Callable[[Dict[str, Any]], bool],
        semaphore: asyncio.Semaphore
    ):
        """Process a single message"""
        async with semaphore:
            try:
                success = await handler(message.payload)
                
                if success:
                    await self.backend.ack(message)
                    logger.debug(f"Message {message.id} processed successfully")
                else:
                    message.error_message = "Handler returned False"
                    await self.backend.nack(message)
                    logger.warning(f"Message {message.id} processing failed")
                
            except Exception as e:
                message.error_message = str(e)
                await self.backend.nack(message)
                logger.error(f"Error processing message {message.id}: {e}")
    
    async def get_stats(self, queue_name: str = None) -> Dict[str, Any]:
        """Get queue statistics"""
        if not self.backend:
            return {}
        
        if queue_name:
            return await self.backend.get_queue_stats(queue_name)
        
        # Return stats for all known queues
        stats = {}
        for known_queue in self._consumers.keys():
            stats[known_queue] = await self.backend.get_queue_stats(known_queue)
        
        return stats
    
    async def purge(self, queue_name: str) -> int:
        """Purge all messages from a queue"""
        if not self.backend:
            return 0
        
        return await self.backend.purge_queue(queue_name)


# Convenience functions
async def enqueue_stimuli(
    stimuli_data: Dict[str, Any],
    team_type: str = None,
    priority: str = "normal"
) -> str:
    """Enqueue stimuli for processing"""
    from ..di import get_container
    
    queue_service = get_container().get(QueueService)
    
    queue_name = f"stimuli_{team_type}" if team_type else "stimuli"
    
    return await queue_service.enqueue(
        queue_name=queue_name,
        payload=stimuli_data,
        metadata={"priority": priority, "type": "stimuli"}
    )


async def enqueue_s2_processing(
    stimuli_data: Dict[str, Any],
    character_type: str = None
) -> str:
    """Enqueue S2 processing (backward compatibility)"""
    return await enqueue_stimuli(stimuli_data, character_type, "normal")