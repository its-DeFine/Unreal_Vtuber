"""
Conversation Storage Service for Autonomous Agent System
Stores and retrieves agent conversations with semantic search capability
"""
import asyncio
import json
import hashlib
from datetime import datetime
from typing import Dict, List, Optional, Any
from contextlib import asynccontextmanager

import asyncpg
import logging

logger = logging.getLogger(__name__)


class ConversationStorageService:
    """
    Store and retrieve agent conversations with semantic search
    """
    
    def __init__(self, db_url: str, cognee_service=None):
        self.db_url = db_url
        self.cognee_service = cognee_service
        self.pool = None
        
    async def initialize(self):
        """Initialize database connection pool"""
        try:
            self.pool = await asyncpg.create_pool(
                self.db_url,
                min_size=2,
                max_size=10,
                timeout=30
            )
            logger.info("💬 [CONVERSATIONS] Storage service initialized")
            
        except Exception as e:
            logger.error(f"❌ [CONVERSATIONS] Failed to initialize: {e}")
            raise
            
    async def close(self):
        """Clean up resources"""
        if self.pool:
            await self.pool.close()
            
    async def store_conversation(self, conversation_data: Dict):
        """Store complete conversation thread"""
        conversation = {
            "id": self._generate_conversation_id(conversation_data),
            "iteration": conversation_data.get("iteration"),
            "timestamp": datetime.utcnow(),
            "agents": json.dumps(conversation_data.get("agents", [])),
            "messages": json.dumps(conversation_data.get("messages", [])),
            "outcome": json.dumps(conversation_data.get("outcome", {})),
            "tools_triggered": json.dumps(conversation_data.get("tools_triggered", [])),
            "duration": conversation_data.get("duration", 0.0)
        }
        
        # Generate search vector from messages
        search_text = self._extract_search_text(conversation_data.get("messages", []))
        
        # Store in PostgreSQL
        await self._persist_to_postgres(conversation, search_text)
        
        # Store summary in Cognee for semantic search
        if self.cognee_service:
            try:
                summary = self._generate_conversation_summary(conversation_data)
                await self.cognee_service.add_data([summary])
                logger.info(f"📝 [CONVERSATIONS] Stored summary in Cognee for iteration {conversation['iteration']}")
            except Exception as e:
                logger.warning(f"⚠️ [CONVERSATIONS] Failed to store in Cognee: {e}")
                
    async def get_conversations(self, iteration: Optional[int] = None, 
                               limit: int = 50, offset: int = 0) -> List[Dict]:
        """Retrieve stored conversations with optional filtering"""
        if not self.pool:
            return []
            
        async with self.pool.acquire() as conn:
            query = """
                SELECT 
                    id, iteration, timestamp, agents, messages,
                    outcome, tools_triggered, duration
                FROM conversations
            """
            
            params = []
            param_count = 0
            
            if iteration is not None:
                param_count += 1
                query += f" WHERE iteration = ${param_count}"
                params.append(iteration)
                
            query += f" ORDER BY timestamp DESC LIMIT ${param_count + 1} OFFSET ${param_count + 2}"
            params.extend([limit, offset])
            
            results = await conn.fetch(query, *params)
            
            conversations = []
            for row in results:
                conv = dict(row)
                # Parse JSON fields
                conv['agents'] = json.loads(conv['agents'])
                conv['messages'] = json.loads(conv['messages'])
                conv['outcome'] = json.loads(conv['outcome'])
                conv['tools_triggered'] = json.loads(conv['tools_triggered'])
                conversations.append(conv)
                
            return conversations
            
    async def search_conversations(self, query: str, limit: int = 20) -> List[Dict]:
        """Search conversations using full-text search"""
        if not self.pool:
            return []
            
        async with self.pool.acquire() as conn:
            # Use PostgreSQL full-text search
            results = await conn.fetch("""
                SELECT 
                    id, iteration, timestamp, agents, messages,
                    outcome, tools_triggered, duration,
                    ts_rank(search_vector, plainto_tsquery('english', $1)) as rank
                FROM conversations
                WHERE search_vector @@ plainto_tsquery('english', $1)
                ORDER BY rank DESC
                LIMIT $2
            """, query, limit)
            
            conversations = []
            for row in results:
                conv = dict(row)
                # Parse JSON fields
                conv['agents'] = json.loads(conv['agents'])
                conv['messages'] = json.loads(conv['messages'])
                conv['outcome'] = json.loads(conv['outcome'])
                conv['tools_triggered'] = json.loads(conv['tools_triggered'])
                conversations.append(conv)
                
            return conversations
            
    async def get_conversation_by_id(self, conversation_id: str) -> Optional[Dict]:
        """Retrieve a specific conversation by ID"""
        if not self.pool:
            return None
            
        async with self.pool.acquire() as conn:
            row = await conn.fetchrow("""
                SELECT 
                    id, iteration, timestamp, agents, messages,
                    outcome, tools_triggered, duration
                FROM conversations
                WHERE id = $1
            """, conversation_id)
            
            if row:
                conv = dict(row)
                # Parse JSON fields
                conv['agents'] = json.loads(conv['agents'])
                conv['messages'] = json.loads(conv['messages'])
                conv['outcome'] = json.loads(conv['outcome'])
                conv['tools_triggered'] = json.loads(conv['tools_triggered'])
                return conv
                
            return None
            
    async def get_conversation_stats(self) -> Dict:
        """Get statistics about stored conversations"""
        if not self.pool:
            return {}
            
        async with self.pool.acquire() as conn:
            stats = await conn.fetchrow("""
                SELECT 
                    COUNT(*) as total_conversations,
                    COUNT(DISTINCT iteration) as unique_iterations,
                    AVG(duration) as avg_duration,
                    AVG(array_length(string_to_array(agents::text, ','), 1)) as avg_agents_per_conversation,
                    AVG(jsonb_array_length(messages::jsonb)) as avg_messages_per_conversation
                FROM conversations
            """)
            
            tool_stats = await conn.fetch("""
                SELECT 
                    tool_name,
                    COUNT(*) as trigger_count
                FROM conversations,
                    jsonb_array_elements_text(tools_triggered::jsonb) as tool_name
                GROUP BY tool_name
                ORDER BY trigger_count DESC
                LIMIT 10
            """)
            
            return {
                "total_conversations": stats['total_conversations'] or 0,
                "unique_iterations": stats['unique_iterations'] or 0,
                "avg_duration": float(stats['avg_duration'] or 0),
                "avg_agents_per_conversation": float(stats['avg_agents_per_conversation'] or 0),
                "avg_messages_per_conversation": float(stats['avg_messages_per_conversation'] or 0),
                "top_triggered_tools": [dict(row) for row in tool_stats]
            }
            
    # Private helper methods
    
    def _generate_conversation_id(self, conversation_data: Dict) -> str:
        """Generate unique conversation ID"""
        # Use iteration and timestamp to create unique ID
        iteration = conversation_data.get("iteration", 0)
        timestamp = datetime.utcnow().strftime('%Y%m%d_%H%M%S_%f')
        return f"conv_{iteration}_{timestamp}"
        
    def _extract_search_text(self, messages: List[Dict]) -> str:
        """Extract searchable text from messages"""
        search_parts = []
        
        for msg in messages:
            if isinstance(msg, dict):
                # Handle different message formats
                content = msg.get('content', '') or msg.get('message', '') or str(msg)
                role = msg.get('role', '') or msg.get('name', '')
                search_parts.append(f"{role}: {content}")
            else:
                search_parts.append(str(msg))
                
        return " ".join(search_parts)
        
    def _generate_conversation_summary(self, conversation_data: Dict) -> str:
        """Generate a summary for Cognee storage"""
        iteration = conversation_data.get("iteration", "unknown")
        agents = conversation_data.get("agents", [])
        messages = conversation_data.get("messages", [])
        outcome = conversation_data.get("outcome", {})
        tools = conversation_data.get("tools_triggered", [])
        
        # Extract key information
        agent_list = ", ".join(agents) if agents else "No agents"
        tool_list = ", ".join(tools) if tools else "No tools"
        message_count = len(messages)
        
        # Build summary
        summary = f"""
Conversation Summary - Iteration {iteration}
Timestamp: {datetime.utcnow().isoformat()}
Participating Agents: {agent_list}
Total Messages: {message_count}
Tools Triggered: {tool_list}
"""
        
        # Add outcome information
        if outcome:
            if outcome.get('tools_executed'):
                summary += f"\nTools Executed: {outcome['tools_executed']}"
            if outcome.get('final_response'):
                summary += f"\nFinal Response: {outcome['final_response'][:200]}..."
                
        # Add sample messages
        if messages:
            summary += "\n\nKey Messages:"
            for i, msg in enumerate(messages[:3]):  # First 3 messages
                if isinstance(msg, dict):
                    role = msg.get('role', 'Unknown')
                    content = msg.get('content', '')[:100]
                    summary += f"\n- {role}: {content}..."
                    
        return summary
        
    async def _persist_to_postgres(self, conversation: Dict, search_text: str):
        """Persist conversation to PostgreSQL"""
        if not self.pool:
            return
            
        async with self.pool.acquire() as conn:
            await conn.execute("""
                INSERT INTO conversations (
                    id, iteration, timestamp, agents, messages,
                    outcome, tools_triggered, duration, search_vector
                ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, to_tsvector('english', $9))
            """,
            conversation['id'], conversation['iteration'], conversation['timestamp'],
            conversation['agents'], conversation['messages'], conversation['outcome'],
            conversation['tools_triggered'], conversation['duration'], search_text
            )
            
            logger.info(f"💾 [CONVERSATIONS] Stored conversation {conversation['id']} for iteration {conversation['iteration']}")
            
    async def analyze_conversation_patterns(self, days: int = 7) -> Dict:
        """Analyze conversation patterns over time"""
        if not self.pool:
            return {}
            
        async with self.pool.acquire() as conn:
            # Get conversation patterns
            patterns = await conn.fetch("""
                SELECT 
                    DATE(timestamp) as date,
                    COUNT(*) as conversation_count,
                    AVG(duration) as avg_duration,
                    COUNT(DISTINCT iteration) as unique_iterations
                FROM conversations
                WHERE timestamp >= CURRENT_TIMESTAMP - INTERVAL '%s days'
                GROUP BY DATE(timestamp)
                ORDER BY date
            """ % days)
            
            # Get agent collaboration patterns
            collaborations = await conn.fetch("""
                SELECT 
                    agents,
                    COUNT(*) as collaboration_count
                FROM conversations
                WHERE timestamp >= CURRENT_TIMESTAMP - INTERVAL '%s days'
                GROUP BY agents
                ORDER BY collaboration_count DESC
                LIMIT 10
            """ % days)
            
            return {
                "daily_patterns": [dict(row) for row in patterns],
                "top_collaborations": [dict(row) for row in collaborations]
            }