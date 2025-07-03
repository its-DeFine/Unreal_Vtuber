"""
Cognee Memory System Client for GraphFlow.

This module provides the client for interacting with the Cognee memory system,
handling memory queries, context retrieval, and memory storage operations.
"""

import asyncio
import aiohttp
from typing import Dict, Any, Optional, List, Tuple
from datetime import datetime
import json
from enum import Enum
from dataclasses import dataclass

from ..utils.logging import get_structured_logger


class MemoryType(Enum):
    """Types of memory in Cognee system."""
    EPISODIC = "episodic"
    SEMANTIC = "semantic"
    PROCEDURAL = "procedural"
    WORKING = "working"
    CONTEXTUAL = "contextual"


@dataclass
class MemoryQuery:
    """Query parameters for memory retrieval."""
    query_text: str
    memory_types: List[MemoryType] = None
    time_range: Optional[Tuple[datetime, datetime]] = None
    relevance_threshold: float = 0.5
    max_results: int = 10
    include_metadata: bool = True
    context_filters: Optional[Dict[str, Any]] = None


@dataclass
class MemoryItem:
    """Individual memory item from Cognee."""
    id: str
    content: str
    memory_type: MemoryType
    relevance_score: float
    timestamp: datetime
    metadata: Dict[str, Any]
    embeddings: Optional[List[float]] = None
    related_memories: Optional[List[str]] = None


class CogneeClient:
    """
    Client for Cognee memory system integration.
    
    Provides methods for:
    - Memory queries and retrieval
    - Context enrichment
    - Memory storage and updates
    - Semantic search operations
    """
    
    def __init__(
        self,
        endpoint: str,
        api_key: Optional[str] = None,
        timeout: float = 30.0,
        max_retries: int = 3
    ):
        """
        Initialize Cognee client.
        
        Args:
            endpoint: Base URL for Cognee API
            api_key: Optional API key for authentication
            timeout: Request timeout in seconds
            max_retries: Maximum number of retry attempts
        """
        self.endpoint = endpoint.rstrip('/')
        self.api_key = api_key
        self.timeout = timeout
        self.max_retries = max_retries
        self.logger = get_structured_logger("cognee_client")
        
        # Session management
        self.session: Optional[aiohttp.ClientSession] = None
        self._session_lock = asyncio.Lock()
        
        # Cache for frequently accessed memories
        self._memory_cache: Dict[str, MemoryItem] = {}
        self._cache_ttl = 300  # 5 minutes
        self._cache_timestamps: Dict[str, datetime] = {}
    
    async def ensure_session(self) -> aiohttp.ClientSession:
        """Ensure HTTP session is available."""
        async with self._session_lock:
            if self.session is None or self.session.closed:
                timeout = aiohttp.ClientTimeout(total=self.timeout)
                headers = {
                    "User-Agent": "GraphFlow/1.0",
                    "Accept": "application/json"
                }
                
                if self.api_key:
                    headers["Authorization"] = f"Bearer {self.api_key}"
                
                self.session = aiohttp.ClientSession(
                    timeout=timeout,
                    headers=headers
                )
            return self.session
    
    async def close(self) -> None:
        """Close the HTTP session."""
        async with self._session_lock:
            if self.session and not self.session.closed:
                await self.session.close()
                self.session = None
    
    async def query_memories(
        self,
        query: MemoryQuery
    ) -> List[MemoryItem]:
        """
        Query memories from Cognee system.
        
        Args:
            query: Memory query parameters
            
        Returns:
            List of relevant memory items
        """
        session = await self.ensure_session()
        url = f"{self.endpoint}/api/v1/memory/query"
        
        # Build query payload
        payload = {
            "query": query.query_text,
            "limit": query.max_results,
            "relevance_threshold": query.relevance_threshold,
            "include_metadata": query.include_metadata
        }
        
        if query.memory_types:
            payload["memory_types"] = [mt.value for mt in query.memory_types]
        
        if query.time_range:
            payload["time_range"] = {
                "start": query.time_range[0].isoformat(),
                "end": query.time_range[1].isoformat()
            }
        
        if query.context_filters:
            payload["filters"] = query.context_filters
        
        for attempt in range(self.max_retries):
            try:
                async with session.post(
                    url,
                    json=payload,
                    headers={"Content-Type": "application/json"}
                ) as response:
                    if response.status == 200:
                        data = await response.json()
                        memories = self._parse_memory_results(data.get("memories", []))
                        
                        # Update cache
                        for memory in memories:
                            self._update_cache(memory)
                        
                        self.logger.info(
                            f"Memory query returned {len(memories)} results",
                            query=query.query_text[:50]
                        )
                        
                        return memories
                    else:
                        error_data = await response.json()
                        self.logger.warning(
                            f"Memory query failed: {response.status}",
                            error=error_data.get("error")
                        )
                        
                        if 400 <= response.status < 500:
                            return []  # Don't retry client errors
                            
            except asyncio.TimeoutError:
                self.logger.error(f"Memory query timeout (attempt {attempt + 1})")
            except Exception as e:
                self.logger.error(f"Memory query error: {e}")
            
            if attempt < self.max_retries - 1:
                await asyncio.sleep(2 ** attempt)
        
        return []
    
    async def store_memory(
        self,
        content: str,
        memory_type: MemoryType,
        metadata: Optional[Dict[str, Any]] = None,
        embeddings: Optional[List[float]] = None
    ) -> Optional[str]:
        """
        Store a new memory in Cognee.
        
        Args:
            content: Memory content
            memory_type: Type of memory
            metadata: Optional metadata
            embeddings: Optional pre-computed embeddings
            
        Returns:
            Memory ID if successful, None otherwise
        """
        session = await self.ensure_session()
        url = f"{self.endpoint}/api/v1/memory/store"
        
        payload = {
            "content": content,
            "memory_type": memory_type.value,
            "metadata": metadata or {},
            "timestamp": datetime.utcnow().isoformat()
        }
        
        if embeddings:
            payload["embeddings"] = embeddings
        
        try:
            async with session.post(
                url,
                json=payload,
                headers={"Content-Type": "application/json"}
            ) as response:
                if response.status == 201:
                    data = await response.json()
                    memory_id = data.get("memory_id")
                    
                    self.logger.info(
                        f"Memory stored successfully",
                        memory_id=memory_id,
                        memory_type=memory_type.value
                    )
                    
                    return memory_id
                else:
                    error_data = await response.json()
                    self.logger.error(
                        f"Failed to store memory: {response.status}",
                        error=error_data.get("error")
                    )
                    return None
                    
        except Exception as e:
            self.logger.error(f"Memory storage error: {e}")
            return None
    
    async def update_memory(
        self,
        memory_id: str,
        updates: Dict[str, Any]
    ) -> bool:
        """
        Update an existing memory.
        
        Args:
            memory_id: ID of memory to update
            updates: Dictionary of updates
            
        Returns:
            Success status
        """
        session = await self.ensure_session()
        url = f"{self.endpoint}/api/v1/memory/{memory_id}"
        
        try:
            async with session.patch(
                url,
                json=updates,
                headers={"Content-Type": "application/json"}
            ) as response:
                if response.status == 200:
                    # Invalidate cache
                    self._invalidate_cache(memory_id)
                    
                    self.logger.info(f"Memory {memory_id} updated successfully")
                    return True
                else:
                    error_data = await response.json()
                    self.logger.error(
                        f"Failed to update memory: {response.status}",
                        error=error_data.get("error")
                    )
                    return False
                    
        except Exception as e:
            self.logger.error(f"Memory update error: {e}")
            return False
    
    async def get_memory_context(
        self,
        memory_ids: List[str],
        depth: int = 1
    ) -> Dict[str, Any]:
        """
        Get extended context for specific memories.
        
        Args:
            memory_ids: List of memory IDs
            depth: Depth of related memories to fetch
            
        Returns:
            Context dictionary with memories and relationships
        """
        session = await self.ensure_session()
        url = f"{self.endpoint}/api/v1/memory/context"
        
        payload = {
            "memory_ids": memory_ids,
            "depth": depth,
            "include_embeddings": False
        }
        
        try:
            async with session.post(
                url,
                json=payload,
                headers={"Content-Type": "application/json"}
            ) as response:
                if response.status == 200:
                    data = await response.json()
                    return data
                else:
                    self.logger.warning(f"Context retrieval failed: {response.status}")
                    return {}
                    
        except Exception as e:
            self.logger.error(f"Context retrieval error: {e}")
            return {}
    
    async def semantic_search(
        self,
        query_embedding: List[float],
        memory_types: Optional[List[MemoryType]] = None,
        top_k: int = 10
    ) -> List[MemoryItem]:
        """
        Perform semantic search using embeddings.
        
        Args:
            query_embedding: Query embedding vector
            memory_types: Optional filter by memory types
            top_k: Number of results to return
            
        Returns:
            List of semantically similar memories
        """
        session = await self.ensure_session()
        url = f"{self.endpoint}/api/v1/memory/semantic_search"
        
        payload = {
            "embedding": query_embedding,
            "top_k": top_k
        }
        
        if memory_types:
            payload["memory_types"] = [mt.value for mt in memory_types]
        
        try:
            async with session.post(
                url,
                json=payload,
                headers={"Content-Type": "application/json"}
            ) as response:
                if response.status == 200:
                    data = await response.json()
                    memories = self._parse_memory_results(data.get("memories", []))
                    
                    self.logger.info(f"Semantic search returned {len(memories)} results")
                    return memories
                else:
                    self.logger.warning(f"Semantic search failed: {response.status}")
                    return []
                    
        except Exception as e:
            self.logger.error(f"Semantic search error: {e}")
            return []
    
    async def delete_memory(self, memory_id: str) -> bool:
        """
        Delete a memory from Cognee.
        
        Args:
            memory_id: ID of memory to delete
            
        Returns:
            Success status
        """
        session = await self.ensure_session()
        url = f"{self.endpoint}/api/v1/memory/{memory_id}"
        
        try:
            async with session.delete(url) as response:
                if response.status == 204:
                    self._invalidate_cache(memory_id)
                    self.logger.info(f"Memory {memory_id} deleted successfully")
                    return True
                else:
                    self.logger.error(f"Failed to delete memory: {response.status}")
                    return False
                    
        except Exception as e:
            self.logger.error(f"Memory deletion error: {e}")
            return False
    
    async def get_memory_stats(self) -> Dict[str, Any]:
        """
        Get statistics about the memory system.
        
        Returns:
            Dictionary of memory statistics
        """
        session = await self.ensure_session()
        url = f"{self.endpoint}/api/v1/memory/stats"
        
        try:
            async with session.get(url) as response:
                if response.status == 200:
                    return await response.json()
                else:
                    return {}
                    
        except Exception as e:
            self.logger.error(f"Stats retrieval error: {e}")
            return {}
    
    def _parse_memory_results(self, raw_memories: List[Dict[str, Any]]) -> List[MemoryItem]:
        """Parse raw memory data into MemoryItem objects."""
        memories = []
        
        for raw in raw_memories:
            try:
                memory_type = MemoryType(raw.get("memory_type", "contextual"))
                
                memory = MemoryItem(
                    id=raw["id"],
                    content=raw["content"],
                    memory_type=memory_type,
                    relevance_score=raw.get("relevance_score", 1.0),
                    timestamp=datetime.fromisoformat(raw["timestamp"]),
                    metadata=raw.get("metadata", {}),
                    embeddings=raw.get("embeddings"),
                    related_memories=raw.get("related_memories", [])
                )
                
                memories.append(memory)
                
            except Exception as e:
                self.logger.warning(f"Failed to parse memory: {e}")
                continue
        
        return memories
    
    def _update_cache(self, memory: MemoryItem) -> None:
        """Update memory cache."""
        self._memory_cache[memory.id] = memory
        self._cache_timestamps[memory.id] = datetime.utcnow()
        
        # Clean old entries
        self._clean_cache()
    
    def _invalidate_cache(self, memory_id: str) -> None:
        """Invalidate cached memory."""
        self._memory_cache.pop(memory_id, None)
        self._cache_timestamps.pop(memory_id, None)
    
    def _clean_cache(self) -> None:
        """Remove expired cache entries."""
        now = datetime.utcnow()
        expired_ids = [
            mid for mid, timestamp in self._cache_timestamps.items()
            if (now - timestamp).seconds > self._cache_ttl
        ]
        
        for mid in expired_ids:
            self._invalidate_cache(mid)
    
    async def batch_query_memories(
        self,
        queries: List[MemoryQuery]
    ) -> List[List[MemoryItem]]:
        """
        Execute multiple memory queries in batch.
        
        Args:
            queries: List of memory queries
            
        Returns:
            List of results for each query
        """
        # Execute queries concurrently with rate limiting
        semaphore = asyncio.Semaphore(3)  # Max 3 concurrent queries
        
        async def query_with_limit(query):
            async with semaphore:
                return await self.query_memories(query)
        
        results = await asyncio.gather(
            *[query_with_limit(query) for query in queries],
            return_exceptions=True
        )
        
        # Convert exceptions to empty results
        processed_results = []
        for result in results:
            if isinstance(result, Exception):
                self.logger.error(f"Batch query error: {result}")
                processed_results.append([])
            else:
                processed_results.append(result)
        
        return processed_results