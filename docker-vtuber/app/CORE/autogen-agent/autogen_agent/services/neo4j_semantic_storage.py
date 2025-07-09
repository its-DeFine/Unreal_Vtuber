"""
Neo4j Semantic Storage Service
Replaces Cognee for more robust graph database operations
"""

import os
import logging
import hashlib
import json
from datetime import datetime
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass, asdict
from enum import Enum

from neo4j import GraphDatabase, AsyncGraphDatabase
import requests
import json
import numpy as np

logger = logging.getLogger(__name__)


class SemanticContext(Enum):
    """Different semantic contexts for organizing knowledge"""
    GENERAL = "general_context"
    S2_TO_S1 = "s2_to_s1_messages"
    S1_TO_S2 = "s1_to_s2_feedback"
    TOOLS = "tool_executions"
    STIMULI = "stimuli_context"
    AGENT_STATE = "agent_state"
    TRADING = "trading_finance"
    SYSTEM = "system_events"


@dataclass
class SemanticNode:
    """Represents a node in the semantic graph"""
    id: str
    content: str
    context: SemanticContext
    node_type: str
    timestamp: float
    metadata: Dict[str, Any]
    embedding: Optional[List[float]] = None
    # Agent tracking fields
    initiating_agent: Optional[str] = None
    agent_category: Optional[str] = None  # s1_agent, s2_team, character_agent, system
    agent_team: Optional[str] = None  # main_autonomous, character_weatherman, etc.
    action_chain: Optional[List[str]] = None  # Track agent chain of actions
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for Neo4j"""
        data = asdict(self)
        data['context'] = self.context.value
        # Convert action_chain list to JSON string for Neo4j storage
        if data.get('action_chain'):
            data['action_chain'] = json.dumps(data['action_chain'])
        return data


class Neo4jSemanticStorage:
    """Neo4j-based semantic storage service"""
    
    def __init__(self, uri: str = None, user: str = None, password: str = None):
        """Initialize Neo4j connection"""
        self.uri = uri or os.getenv("NEO4J_URI", "bolt://localhost:7687")
        self.user = user or os.getenv("NEO4J_USER", "neo4j")
        self.password = password or os.getenv("NEO4J_PASSWORD", "password")
        
        # Initialize embedding via Ollama
        self.ollama_endpoint = os.getenv("OLLAMA_ENDPOINT", "http://vtuber-ollama:11434")
        self.embedding_model = "nomic-embed-text"
        
        # Connection pools
        self.driver = None
        self.async_driver = None
        
        # Deduplication cache
        self.processed_hashes = set()
        
        logger.info(f"🔗 [NEO4J] Initialized semantic storage with URI: {self.uri}")
    
    def connect(self):
        """Establish connection to Neo4j"""
        try:
            self.driver = GraphDatabase.driver(self.uri, auth=(self.user, self.password))
            self.async_driver = AsyncGraphDatabase.driver(self.uri, auth=(self.user, self.password))
            
            # Create constraints and indexes
            with self.driver.session() as session:
                # Unique constraint on node ID
                session.run("""
                    CREATE CONSTRAINT IF NOT EXISTS FOR (n:SemanticNode) 
                    REQUIRE n.id IS UNIQUE
                """)
                
                # Indexes for better query performance
                session.run("CREATE INDEX IF NOT EXISTS FOR (n:SemanticNode) ON (n.context)")
                session.run("CREATE INDEX IF NOT EXISTS FOR (n:SemanticNode) ON (n.node_type)")
                session.run("CREATE INDEX IF NOT EXISTS FOR (n:SemanticNode) ON (n.timestamp)")
                
                # Full-text index for content search
                session.run("""
                    CREATE FULLTEXT INDEX semantic_content IF NOT EXISTS 
                    FOR (n:SemanticNode) ON EACH [n.content]
                """)
            
            logger.info("✅ [NEO4J] Connected and initialized database schema")
            return True
            
        except Exception as e:
            logger.error(f"❌ [NEO4J] Connection failed: {e}")
            return False
    
    async def close(self):
        """Close Neo4j connections"""
        if self.driver:
            self.driver.close()
        if self.async_driver:
            await self.async_driver.close()
    
    def _generate_node_id(self, content: str, context: str) -> str:
        """Generate unique node ID based on content and context"""
        hash_input = f"{content}:{context}"
        return hashlib.sha256(hash_input.encode()).hexdigest()[:16]
    
    def _compute_embedding(self, text: str) -> List[float]:
        """Compute text embedding using Ollama"""
        try:
            response = requests.post(
                f"{self.ollama_endpoint}/api/embeddings",
                json={
                    "model": self.embedding_model,
                    "prompt": text
                },
                timeout=30
            )
            if response.status_code == 200:
                embedding = response.json().get("embedding", [])
                return embedding
            else:
                logger.warning(f"Ollama embedding failed: {response.status_code}")
                return [0.0] * 384  # Fallback embedding dimension
        except Exception as e:
            logger.error(f"Failed to compute embedding via Ollama: {e}")
            return [0.0] * 384  # Fallback embedding dimension
    
    async def add_semantic_node(
        self, 
        content: str, 
        context: SemanticContext,
        node_type: str,
        metadata: Dict[str, Any] = None,
        initiating_agent: str = None,
        agent_category: str = None,
        agent_team: str = None,
        action_chain: List[str] = None
    ) -> Optional[SemanticNode]:
        """Add a semantic node to the graph"""
        try:
            # Check for duplicate
            node_id = self._generate_node_id(content, context.value)
            if node_id in self.processed_hashes:
                logger.debug(f"🔄 [NEO4J] Skipping duplicate node: {node_id}")
                return None
            
            # Create node with agent tracking
            node = SemanticNode(
                id=node_id,
                content=content,
                context=context,
                node_type=node_type,
                timestamp=datetime.now().timestamp(),
                metadata=metadata or {},
                embedding=self._compute_embedding(content),
                initiating_agent=initiating_agent,
                agent_category=agent_category,
                agent_team=agent_team,
                action_chain=action_chain or []
            )
            
            # Store in Neo4j
            async with self.async_driver.session() as session:
                query = """
                    CREATE (n:SemanticNode {
                        id: $id,
                        content: $content,
                        context: $context,
                        node_type: $node_type,
                        timestamp: $timestamp,
                        metadata: $metadata,
                        embedding: $embedding,
                        initiating_agent: $initiating_agent,
                        agent_category: $agent_category,
                        agent_team: $agent_team,
                        action_chain: $action_chain
                    })
                    RETURN n
                """
                
                result = await session.run(
                    query,
                    id=node.id,
                    content=node.content,
                    context=node.context.value,
                    node_type=node.node_type,
                    timestamp=node.timestamp,
                    metadata=json.dumps(node.metadata),
                    embedding=node.embedding,
                    initiating_agent=node.initiating_agent,
                    agent_category=node.agent_category,
                    agent_team=node.agent_team,
                    action_chain=json.dumps(node.action_chain) if node.action_chain else "[]"
                )
                
                self.processed_hashes.add(node_id)
                logger.info(f"✅ [NEO4J] Added node: {node_type} in {context.value}")
                return node
                
        except Exception as e:
            logger.error(f"❌ [NEO4J] Failed to add node: {e}")
            return None
    
    async def add_relationship(
        self,
        source_id: str,
        target_id: str,
        rel_type: str,
        properties: Dict[str, Any] = None
    ) -> bool:
        """Add a relationship between nodes"""
        try:
            async with self.async_driver.session() as session:
                query = """
                    MATCH (a:SemanticNode {id: $source_id})
                    MATCH (b:SemanticNode {id: $target_id})
                    CREATE (a)-[r:%s {properties: $properties}]->(b)
                    RETURN r
                """ % rel_type.upper()
                
                await session.run(
                    query,
                    source_id=source_id,
                    target_id=target_id,
                    properties=json.dumps(properties or {})
                )
                
                logger.info(f"✅ [NEO4J] Added relationship: {source_id} -[{rel_type}]-> {target_id}")
                return True
                
        except Exception as e:
            logger.error(f"❌ [NEO4J] Failed to add relationship: {e}")
            return False
    
    async def search_semantic(
        self,
        query: str,
        context: Optional[SemanticContext] = None,
        limit: int = 10
    ) -> List[Dict[str, Any]]:
        """Search for semantic nodes"""
        try:
            results = []
            
            async with self.async_driver.session() as session:
                # Use full-text search
                if context:
                    cypher_query = """
                        CALL db.index.fulltext.queryNodes('semantic_content', $query)
                        YIELD node, score
                        WHERE node.context = $context
                        RETURN node, score
                        ORDER BY score DESC
                        LIMIT $limit
                    """
                    result = await session.run(
                        cypher_query, 
                        query=query, 
                        context=context.value,
                        limit=limit
                    )
                else:
                    cypher_query = """
                        CALL db.index.fulltext.queryNodes('semantic_content', $query)
                        YIELD node, score
                        RETURN node, score
                        ORDER BY score DESC
                        LIMIT $limit
                    """
                    result = await session.run(
                        cypher_query,
                        query=query,
                        limit=limit
                    )
                
                async for record in result:
                    node = record["node"]
                    results.append({
                        "id": node["id"],
                        "content": node["content"],
                        "context": node["context"],
                        "node_type": node["node_type"],
                        "timestamp": node["timestamp"],
                        "metadata": json.loads(node["metadata"]),
                        "score": record["score"]
                    })
            
            logger.info(f"🔍 [NEO4J] Search '{query}' found {len(results)} results")
            return results
            
        except Exception as e:
            logger.error(f"❌ [NEO4J] Search failed: {e}")
            return []
    
    async def get_graph_data(self, context_filter: Optional[SemanticContext] = None) -> Dict[str, Any]:
        """Get graph data for visualization"""
        try:
            nodes = []
            relationships = []
            
            async with self.async_driver.session() as session:
                # Get nodes
                if context_filter:
                    node_query = """
                        MATCH (n:SemanticNode)
                        WHERE n.context = $context
                        RETURN n
                        ORDER BY n.timestamp DESC
                        LIMIT 1000
                    """
                    node_result = await session.run(node_query, context=context_filter.value)
                else:
                    node_query = """
                        MATCH (n:SemanticNode)
                        RETURN n
                        ORDER BY n.timestamp DESC
                        LIMIT 1000
                    """
                    node_result = await session.run(node_query)
                
                node_ids = set()
                async for record in node_result:
                    node = record["n"]
                    node_ids.add(node["id"])
                    nodes.append({
                        "id": node["id"],
                        "label": node["content"][:50] + "..." if len(node["content"]) > 50 else node["content"],
                        "title": node["content"],
                        "group": node["context"],
                        "type": node["node_type"],
                        "metadata": json.loads(node["metadata"])
                    })
                
                # Get relationships
                rel_query = """
                    MATCH (a:SemanticNode)-[r]->(b:SemanticNode)
                    WHERE a.id IN $node_ids AND b.id IN $node_ids
                    RETURN a.id as source, b.id as target, type(r) as rel_type, r.properties as properties
                """
                rel_result = await session.run(rel_query, node_ids=list(node_ids))
                
                async for record in rel_result:
                    relationships.append({
                        "source": record["source"],
                        "target": record["target"],
                        "type": record["rel_type"],
                        "properties": json.loads(record["properties"]) if record["properties"] else {}
                    })
            
            logger.info(f"📊 [NEO4J] Retrieved graph: {len(nodes)} nodes, {len(relationships)} relationships")
            
            return {
                "nodes": nodes,
                "links": relationships
            }
            
        except Exception as e:
            logger.error(f"❌ [NEO4J] Failed to get graph data: {e}")
            return {"nodes": [], "links": []}
    
    async def get_metrics(self) -> Dict[str, Any]:
        """Get graph metrics"""
        try:
            async with self.async_driver.session() as session:
                # Count nodes by context
                context_query = """
                    MATCH (n:SemanticNode)
                    RETURN n.context as context, count(n) as count
                """
                context_result = await session.run(context_query)
                
                contexts = {}
                async for record in context_result:
                    contexts[record["context"]] = record["count"]
                
                # Total counts
                total_query = """
                    MATCH (n:SemanticNode)
                    WITH count(n) as node_count
                    MATCH ()-[r]->()
                    WITH node_count, count(r) as rel_count
                    RETURN node_count, rel_count
                """
                total_result = await session.run(total_query)
                
                record = await total_result.single()
                
                metrics = {
                    "total_nodes": record["node_count"] if record else 0,
                    "total_relationships": record["rel_count"] if record else 0,
                    "contexts": contexts,
                    "processed_hashes": len(self.processed_hashes)
                }
                
                return metrics
                
        except Exception as e:
            logger.error(f"❌ [NEO4J] Failed to get metrics: {e}")
            return {
                "total_nodes": 0,
                "total_relationships": 0,
                "contexts": {},
                "error": str(e)
            }


# Global instance
_neo4j_storage = None


def get_neo4j_storage() -> Neo4jSemanticStorage:
    """Get or create global Neo4j storage instance"""
    global _neo4j_storage
    if _neo4j_storage is None:
        _neo4j_storage = Neo4jSemanticStorage()
        _neo4j_storage.connect()
    return _neo4j_storage