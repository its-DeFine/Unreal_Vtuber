import asyncio
import json
import logging
from typing import Dict, List, Optional, Any
from dataclasses import dataclass
import aiohttp
import asyncpg
from datetime import datetime

@dataclass
class MemoryEntry:
    id: str
    content: str
    context: Dict[str, Any]
    timestamp: str
    relevance_score: float = 0.0

class CognitiveMemoryManager:
    """Enhanced memory manager with Cognee knowledge graph integration"""
    
    def __init__(self, db_url: str, cognee_url: str = None, cognee_api_key: str = None):
        self.db_url = db_url
        self.cognee_url = cognee_url.rstrip('/') if cognee_url else None
        self.cognee_api_key = cognee_api_key
        self.dataset_name = "autogen_agent"
        self.db_pool = None
        self.cognee_available = False
        
        logging.info(f"🧠 [COGNITIVE_MEMORY] Initializing...")
        if self.cognee_url:
            logging.info(f"🧠 [COGNITIVE_MEMORY] Cognee URL configured: {self.cognee_url}")
        else:
            logging.info("🧠 [COGNITIVE_MEMORY] Cognee not configured - using PostgreSQL only")
    
    async def initialize(self):
        """Initialize database connection and check Cognee availability"""
        try:
            self.db_pool = await asyncpg.create_pool(self.db_url)
            await self._ensure_memory_tables()
            logging.info("✅ [COGNITIVE_MEMORY] Database connection established")
            
            # Check Cognee availability
            if self.cognee_url and self.cognee_api_key:
                self.cognee_available = await self._check_cognee_health()
                if self.cognee_available:
                    logging.info("✅ [COGNITIVE_MEMORY] Cognee service available")
                else:
                    logging.warning("⚠️ [COGNITIVE_MEMORY] Cognee service unavailable - using PostgreSQL fallback")
            
        except Exception as e:
            logging.error(f"❌ [COGNITIVE_MEMORY] Initialization failed: {e}")
            raise
    
    async def store_interaction(self, context: Dict, action: str, result: Dict) -> str:
        """Store interaction in both PostgreSQL and Cognee knowledge graph"""
        
        memory_id = f"mem_{datetime.now().strftime('%Y%m%d_%H%M%S_%f')}"
        
        # Create comprehensive memory content
        memory_content = f"""
        Interaction ID: {memory_id}
        Timestamp: {datetime.now().isoformat()}
        Context: {json.dumps(context, indent=2)}
        Action Taken: {action}
        Result: {json.dumps(result, indent=2)}
        Success: {result.get('success', False)}
        """
        
        try:
            # Store in PostgreSQL for immediate retrieval
            await self._store_in_postgres(memory_id, memory_content, context, action, result)
            
            # Store in Cognee for semantic understanding (if available)
            if self.cognee_available:
                await self._store_in_cognee(memory_content)
            
            logging.info(f"💾 [COGNITIVE_MEMORY] Stored interaction {memory_id}")
            return memory_id
            
        except Exception as e:
            logging.error(f"❌ [COGNITIVE_MEMORY] Failed to store interaction: {e}")
            raise
    
    async def retrieve_relevant_context(self, query: str, max_results: int = 10) -> List[MemoryEntry]:
        """Retrieve semantically relevant context using Cognee knowledge graph or PostgreSQL fallback"""
        
        try:
            if self.cognee_available:
                # Use Cognee for semantic search
                cognee_results = await self._search_cognee(query, max_results)
                if cognee_results:
                    enhanced_results = await self._enhance_with_postgres_context(cognee_results)
                    logging.info(f"🔍 [COGNITIVE_MEMORY] Retrieved {len(enhanced_results)} relevant memories via Cognee")
                    return enhanced_results
            
            # Fallback to PostgreSQL search
            fallback_results = await self._fallback_postgres_search(query, max_results)
            logging.info(f"🔍 [COGNITIVE_MEMORY] Retrieved {len(fallback_results)} relevant memories via PostgreSQL")
            return fallback_results
            
        except Exception as e:
            logging.error(f"❌ [COGNITIVE_MEMORY] Context retrieval failed: {e}")
            return []
    
    async def consolidate_knowledge(self):
        """Process and create relationships in Cognee knowledge graph"""
        if not self.cognee_available:
            logging.info("🧩 [COGNITIVE_MEMORY] Cognee not available - skipping consolidation")
            return
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    f"{self.cognee_url}/api/v1/cognify",
                    headers={'Authorization': f'Bearer {self.cognee_api_key}'},
                    json={'dataset_name': self.dataset_name}
                ) as response:
                    if response.status == 200:
                        result = await response.json()
                        logging.info(f"🧩 [COGNITIVE_MEMORY] Knowledge consolidation completed: {result}")
                    else:
                        logging.error(f"❌ [COGNITIVE_MEMORY] Consolidation failed: {response.status}")
        except Exception as e:
            logging.error(f"❌ [COGNITIVE_MEMORY] Consolidation error: {e}")
    
    # Private helper methods
    async def _ensure_memory_tables(self):
        """Create memory tables if they don't exist"""
        async with self.db_pool.acquire() as conn:
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS cognitive_memories (
                    id VARCHAR(100) PRIMARY KEY,
                    content TEXT NOT NULL,
                    context JSONB,
                    action VARCHAR(200),
                    result JSONB,
                    timestamp TIMESTAMP DEFAULT NOW(),
                    relevance_score FLOAT DEFAULT 0.0
                );
                
                CREATE INDEX IF NOT EXISTS idx_cognitive_memories_timestamp 
                ON cognitive_memories(timestamp DESC);
                
                CREATE INDEX IF NOT EXISTS idx_cognitive_memories_action 
                ON cognitive_memories(action);
            """)
    
    async def _store_in_postgres(self, memory_id: str, content: str, context: Dict, action: str, result: Dict):
        """Store memory in PostgreSQL"""
        async with self.db_pool.acquire() as conn:
            await conn.execute("""
                INSERT INTO cognitive_memories (id, content, context, action, result, timestamp)
                VALUES ($1, $2, $3, $4, $5, $6)
            """, memory_id, content, json.dumps(context), action, json.dumps(result), datetime.now())
    
    async def _check_cognee_health(self) -> bool:
        """Check if Cognee service is available"""
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(f"{self.cognee_url}/health", timeout=5) as response:
                    return response.status == 200
        except:
            return False
    
    async def _store_in_cognee(self, content: str):
        """Store content in Cognee knowledge graph"""
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    f"{self.cognee_url}/api/v1/add",
                    headers={'Authorization': f'Bearer {self.cognee_api_key}'},
                    json={
                        'data': [content],
                        'dataset_name': self.dataset_name
                    },
                    timeout=10
                ) as response:
                    if response.status != 200:
                        logging.error(f"❌ [COGNITIVE_MEMORY] Cognee storage failed: {response.status}")
        except Exception as e:
            logging.error(f"❌ [COGNITIVE_MEMORY] Cognee storage error: {e}")
    
    async def _search_cognee(self, query: str, max_results: int) -> List[Dict]:
        """Search Cognee knowledge graph"""
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    f"{self.cognee_url}/api/v1/search",
                    headers={'Authorization': f'Bearer {self.cognee_api_key}'},
                    json={
                        'query': query,
                        'dataset_name': self.dataset_name,
                        'limit': max_results
                    },
                    timeout=10
                ) as response:
                    if response.status == 200:
                        return await response.json()
                    else:
                        logging.error(f"❌ [COGNITIVE_MEMORY] Cognee search failed: {response.status}")
                        return []
        except Exception as e:
            logging.error(f"❌ [COGNITIVE_MEMORY] Cognee search error: {e}")
            return []
    
    async def _enhance_with_postgres_context(self, cognee_results: List[Dict]) -> List[MemoryEntry]:
        """Enhance Cognee results with PostgreSQL context"""
        enhanced_results = []
        
        for result in cognee_results:
            # Extract memory entry details from Cognee result
            memory_entry = MemoryEntry(
                id=result.get('id', 'cognee_result'),
                content=result.get('content', ''),
                context=result.get('metadata', {}),
                timestamp=result.get('timestamp', datetime.now().isoformat()),
                relevance_score=result.get('relevance_score', 0.8)
            )
            enhanced_results.append(memory_entry)
        
        return enhanced_results
    
    async def _fallback_postgres_search(self, query: str, max_results: int) -> List[MemoryEntry]:
        """Fallback search using PostgreSQL text search"""
        async with self.db_pool.acquire() as conn:
            rows = await conn.fetch("""
                SELECT id, content, context, timestamp
                FROM cognitive_memories
                WHERE content ILIKE $1 OR action ILIKE $1
                ORDER BY timestamp DESC
                LIMIT $2
            """, f"%{query}%", max_results)
            
            results = []
            for row in rows:
                entry = MemoryEntry(
                    id=row['id'],
                    content=row['content'],
                    context=json.loads(row['context']) if row['context'] else {},
                    timestamp=row['timestamp'].isoformat(),
                    relevance_score=0.6  # Default relevance for text search
                )
                results.append(entry)
            
            return results 