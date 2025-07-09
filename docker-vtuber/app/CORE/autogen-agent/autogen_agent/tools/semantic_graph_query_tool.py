"""
Semantic Graph Query Tool
Allows agents to query the Neo4j semantic graph for historical patterns and relationships
"""

import json
import logging
from typing import Dict, List, Any, Optional
from datetime import datetime, timedelta

from ..services.neo4j_semantic_storage import get_neo4j_storage, SemanticContext

logger = logging.getLogger(__name__)


class SemanticGraphQueryTool:
    """Tool for querying the semantic graph"""
    
    def __init__(self):
        """Initialize the query tool"""
        self.storage = get_neo4j_storage()
        self.name = "semantic_graph_query"
        self.description = (
            "Query the semantic knowledge graph for historical patterns, relationships, "
            "and insights. Supports full-text search, pattern matching, and temporal queries."
        )
        logger.info("🔍 [SEMANTIC_QUERY_TOOL] Initialized")
    
    def get_tool_spec(self) -> Dict[str, Any]:
        """Get the tool specification for AutoGen agents"""
        return {
            "name": self.name,
            "description": self.description,
            "parameters": {
                "type": "object",
                "properties": {
                    "query_type": {
                        "type": "string",
                        "enum": ["search", "pattern", "temporal", "context", "relationships"],
                        "description": "Type of query to perform"
                    },
                    "query": {
                        "type": "string",
                        "description": "The search query or pattern to match"
                    },
                    "context": {
                        "type": "string",
                        "enum": ["general", "s2_to_s1_messages", "s1_to_s2_feedback", 
                                 "tool_executions", "stimuli_context", "agent_state", 
                                 "trading_finance", "system_events"],
                        "description": "Semantic context to search within (optional)"
                    },
                    "time_range": {
                        "type": "object",
                        "properties": {
                            "hours": {"type": "integer", "description": "Hours to look back"},
                            "days": {"type": "integer", "description": "Days to look back"}
                        },
                        "description": "Time range for temporal queries"
                    },
                    "limit": {
                        "type": "integer",
                        "default": 10,
                        "description": "Maximum number of results to return"
                    }
                },
                "required": ["query_type", "query"]
            }
        }
    
    async def execute(self, **kwargs) -> Dict[str, Any]:
        """Execute a semantic graph query"""
        # Check for S1 agent access
        requesting_agent = kwargs.get("requesting_agent", "").lower()
        if "s1" in requesting_agent or requesting_agent == "avatar":
            logger.warning("🚫 [SEMANTIC_QUERY_TOOL] S1 agent access denied")
            return {
                "success": False,
                "error": "S1 agents do not have access to the semantic graph. Please use SCB for state management."
            }
        
        query_type = kwargs.get("query_type", "search")
        query = kwargs.get("query", "")
        context = kwargs.get("context")
        time_range = kwargs.get("time_range", {})
        limit = kwargs.get("limit", 10)
        
        try:
            if query_type == "search":
                return await self._full_text_search(query, context, limit)
            
            elif query_type == "pattern":
                return await self._pattern_match(query, context, limit)
            
            elif query_type == "temporal":
                return await self._temporal_query(query, time_range, context, limit)
            
            elif query_type == "context":
                return await self._context_analysis(context or "general", limit)
            
            elif query_type == "relationships":
                return await self._relationship_query(query, limit)
            
            else:
                return {
                    "success": False,
                    "error": f"Unknown query type: {query_type}"
                }
                
        except Exception as e:
            logger.error(f"❌ [SEMANTIC_QUERY_TOOL] Error executing query: {e}")
            return {
                "success": False,
                "error": str(e)
            }
    
    async def _full_text_search(self, query: str, context: Optional[str], limit: int) -> Dict[str, Any]:
        """Perform full-text search across the graph"""
        try:
            # Build context filter
            context_filter = ""
            if context:
                context_enum = SemanticContext[context.upper()]
                context_filter = f"AND n.context = '{context_enum.value}'"
            
            # Search query
            cypher_query = f"""
            MATCH (n:SemanticNode)
            WHERE n.content CONTAINS $query {context_filter}
            RETURN n
            ORDER BY n.timestamp DESC
            LIMIT $limit
            """
            
            async with self.storage.driver.session() as session:
                result = await session.run(
                    cypher_query,
                    query=query,
                    limit=limit
                )
                
                nodes = []
                async for record in result:
                    node = record["n"]
                    nodes.append({
                        "id": node["id"],
                        "content": node["content"],
                        "context": node["context"],
                        "type": node["node_type"],
                        "timestamp": datetime.fromtimestamp(node["timestamp"]).isoformat(),
                        "metadata": json.loads(node.get("metadata", "{}"))
                    })
                
                # Find related nodes
                if nodes:
                    node_ids = [n["id"] for n in nodes[:3]]  # Top 3 results
                    relationships = await self._get_relationships_for_nodes(node_ids)
                else:
                    relationships = []
                
                return {
                    "success": True,
                    "query": query,
                    "query_type": "full_text_search",
                    "results": nodes,
                    "relationships": relationships,
                    "count": len(nodes)
                }
                
        except Exception as e:
            logger.error(f"❌ [SEMANTIC_QUERY_TOOL] Search error: {e}")
            raise
    
    async def _pattern_match(self, pattern: str, context: Optional[str], limit: int) -> Dict[str, Any]:
        """Match specific patterns in the graph"""
        try:
            # Pattern examples:
            # "tool:* -> communication" - Tools that led to communications
            # "s2:* -> s1:*" - S2 to S1 message flows
            # "error -> *" - What errors led to
            
            # Parse pattern
            parts = pattern.split("->")
            if len(parts) != 2:
                return {
                    "success": False,
                    "error": "Pattern must be in format 'source -> target'"
                }
            
            source_pattern = parts[0].strip()
            target_pattern = parts[1].strip()
            
            # Build query
            source_filter = self._build_pattern_filter("source", source_pattern)
            target_filter = self._build_pattern_filter("target", target_pattern)
            
            cypher_query = f"""
            MATCH (source:SemanticNode)-[r]->(target:SemanticNode)
            WHERE {source_filter} AND {target_filter}
            RETURN source, r, target
            ORDER BY source.timestamp DESC
            LIMIT $limit
            """
            
            async with self.storage.driver.session() as session:
                result = await session.run(cypher_query, limit=limit)
                
                patterns = []
                async for record in result:
                    source = record["source"]
                    rel = record["r"]
                    target = record["target"]
                    
                    patterns.append({
                        "source": {
                            "id": source["id"],
                            "content": source["content"],
                            "type": source["node_type"]
                        },
                        "relationship": {
                            "type": rel.type,
                            "properties": dict(rel)
                        },
                        "target": {
                            "id": target["id"],
                            "content": target["content"],
                            "type": target["node_type"]
                        },
                        "timestamp": datetime.fromtimestamp(source["timestamp"]).isoformat()
                    })
                
                return {
                    "success": True,
                    "query": pattern,
                    "query_type": "pattern_match",
                    "patterns": patterns,
                    "count": len(patterns)
                }
                
        except Exception as e:
            logger.error(f"❌ [SEMANTIC_QUERY_TOOL] Pattern match error: {e}")
            raise
    
    async def _temporal_query(self, query: str, time_range: Dict, context: Optional[str], limit: int) -> Dict[str, Any]:
        """Query nodes within a specific time range"""
        try:
            # Calculate time boundaries
            hours_back = time_range.get("hours", 0)
            days_back = time_range.get("days", 0)
            
            end_time = datetime.now()
            start_time = end_time - timedelta(hours=hours_back, days=days_back)
            
            # Build query
            context_filter = ""
            if context:
                context_enum = SemanticContext[context.upper()]
                context_filter = f"AND n.context = '{context_enum.value}'"
            
            cypher_query = f"""
            MATCH (n:SemanticNode)
            WHERE n.timestamp >= $start_time AND n.timestamp <= $end_time
            AND n.content CONTAINS $query {context_filter}
            RETURN n
            ORDER BY n.timestamp DESC
            LIMIT $limit
            """
            
            async with self.storage.driver.session() as session:
                result = await session.run(
                    cypher_query,
                    query=query,
                    start_time=start_time.timestamp(),
                    end_time=end_time.timestamp(),
                    limit=limit
                )
                
                timeline = []
                async for record in result:
                    node = record["n"]
                    timeline.append({
                        "id": node["id"],
                        "content": node["content"],
                        "context": node["context"],
                        "type": node["node_type"],
                        "timestamp": datetime.fromtimestamp(node["timestamp"]).isoformat(),
                        "metadata": json.loads(node.get("metadata", "{}"))
                    })
                
                return {
                    "success": True,
                    "query": query,
                    "query_type": "temporal",
                    "time_range": {
                        "start": start_time.isoformat(),
                        "end": end_time.isoformat()
                    },
                    "timeline": timeline,
                    "count": len(timeline)
                }
                
        except Exception as e:
            logger.error(f"❌ [SEMANTIC_QUERY_TOOL] Temporal query error: {e}")
            raise
    
    async def _context_analysis(self, context: str, limit: int) -> Dict[str, Any]:
        """Analyze a specific semantic context"""
        try:
            context_enum = SemanticContext[context.upper()]
            
            # Get recent nodes in context
            cypher_query = """
            MATCH (n:SemanticNode)
            WHERE n.context = $context
            WITH n
            ORDER BY n.timestamp DESC
            LIMIT $limit
            WITH collect(n) as recent_nodes
            
            // Get statistics
            MATCH (all:SemanticNode)
            WHERE all.context = $context
            WITH recent_nodes, count(all) as total_count, 
                 avg(all.embedding_norm) as avg_embedding
            
            // Get relationship patterns
            MATCH (n:SemanticNode)-[r]->(m:SemanticNode)
            WHERE n.context = $context
            WITH recent_nodes, total_count, avg_embedding, 
                 type(r) as rel_type, count(r) as rel_count
            ORDER BY rel_count DESC
            
            RETURN recent_nodes, total_count, avg_embedding, 
                   collect({type: rel_type, count: rel_count}) as relationships
            """
            
            async with self.storage.driver.session() as session:
                result = await session.run(
                    cypher_query,
                    context=context_enum.value,
                    limit=limit
                )
                
                record = await result.single()
                if not record:
                    return {
                        "success": True,
                        "context": context,
                        "query_type": "context_analysis",
                        "analysis": {
                            "total_nodes": 0,
                            "recent_nodes": [],
                            "relationship_patterns": []
                        }
                    }
                
                recent_nodes = []
                for node in record["recent_nodes"]:
                    recent_nodes.append({
                        "id": node["id"],
                        "content": node["content"],
                        "type": node["node_type"],
                        "timestamp": datetime.fromtimestamp(node["timestamp"]).isoformat()
                    })
                
                return {
                    "success": True,
                    "context": context,
                    "query_type": "context_analysis",
                    "analysis": {
                        "total_nodes": record["total_count"],
                        "average_embedding_norm": record["avg_embedding"],
                        "recent_nodes": recent_nodes,
                        "relationship_patterns": record["relationships"]
                    }
                }
                
        except Exception as e:
            logger.error(f"❌ [SEMANTIC_QUERY_TOOL] Context analysis error: {e}")
            raise
    
    async def _relationship_query(self, node_id: str, limit: int) -> Dict[str, Any]:
        """Query relationships for a specific node"""
        try:
            cypher_query = """
            MATCH (n:SemanticNode {id: $node_id})
            OPTIONAL MATCH (n)-[out]->(target:SemanticNode)
            OPTIONAL MATCH (source:SemanticNode)-[inc]->(n)
            
            WITH n, 
                 collect(DISTINCT {
                     rel: type(out), 
                     node: {
                         id: target.id, 
                         content: target.content,
                         type: target.node_type
                     }
                 }) as outgoing,
                 collect(DISTINCT {
                     rel: type(inc), 
                     node: {
                         id: source.id, 
                         content: source.content,
                         type: source.node_type
                     }
                 }) as incoming
            
            RETURN n, outgoing, incoming
            """
            
            async with self.storage.driver.session() as session:
                result = await session.run(cypher_query, node_id=node_id)
                
                record = await result.single()
                if not record:
                    return {
                        "success": False,
                        "error": f"Node {node_id} not found"
                    }
                
                node = record["n"]
                
                return {
                    "success": True,
                    "query_type": "relationships",
                    "node": {
                        "id": node["id"],
                        "content": node["content"],
                        "context": node["context"],
                        "type": node["node_type"],
                        "timestamp": datetime.fromtimestamp(node["timestamp"]).isoformat()
                    },
                    "outgoing_relationships": [r for r in record["outgoing"] if r["node"]],
                    "incoming_relationships": [r for r in record["incoming"] if r["node"]]
                }
                
        except Exception as e:
            logger.error(f"❌ [SEMANTIC_QUERY_TOOL] Relationship query error: {e}")
            raise
    
    async def _get_relationships_for_nodes(self, node_ids: List[str]) -> List[Dict[str, Any]]:
        """Get relationships between a set of nodes"""
        try:
            cypher_query = """
            MATCH (n:SemanticNode)-[r]->(m:SemanticNode)
            WHERE n.id IN $node_ids AND m.id IN $node_ids
            RETURN n.id as source, type(r) as rel_type, m.id as target
            """
            
            relationships = []
            async with self.storage.driver.session() as session:
                result = await session.run(cypher_query, node_ids=node_ids)
                
                async for record in result:
                    relationships.append({
                        "source": record["source"],
                        "type": record["rel_type"],
                        "target": record["target"]
                    })
            
            return relationships
            
        except Exception as e:
            logger.error(f"❌ [SEMANTIC_QUERY_TOOL] Relationship fetch error: {e}")
            return []
    
    def _build_pattern_filter(self, node_var: str, pattern: str) -> str:
        """Build a Cypher filter from a pattern string"""
        if pattern == "*":
            return "true"
        
        if ":" in pattern:
            # Type pattern like "tool:*" or "s2:analyst"
            parts = pattern.split(":", 1)
            type_pattern = parts[0]
            content_pattern = parts[1]
            
            filters = []
            
            # Type filter
            if type_pattern == "tool":
                filters.append(f"{node_var}.node_type = 'tool_execution'")
            elif type_pattern == "s1":
                filters.append(f"({node_var}.context = 's1_to_s2_feedback' OR {node_var}.content STARTS WITH 'S1:')")
            elif type_pattern == "s2":
                filters.append(f"({node_var}.context = 's2_to_s1_messages' OR {node_var}.content STARTS WITH 'S2:')")
            elif type_pattern == "error":
                filters.append(f"{node_var}.node_type = 'error'")
            else:
                filters.append(f"{node_var}.node_type = '{type_pattern}'")
            
            # Content filter
            if content_pattern != "*":
                filters.append(f"{node_var}.content CONTAINS '{content_pattern}'")
            
            return " AND ".join(filters)
        
        else:
            # Simple content pattern
            return f"{node_var}.content CONTAINS '{pattern}'"


# Global instance
_query_tool = None


def get_semantic_query_tool() -> SemanticGraphQueryTool:
    """Get or create the semantic query tool instance"""
    global _query_tool
    if _query_tool is None:
        _query_tool = SemanticGraphQueryTool()
    return _query_tool


# AutoGen tool function
async def query_semantic_graph(**kwargs) -> Dict[str, Any]:
    """
    Query the semantic knowledge graph for patterns and insights.
    
    Parameters:
    - query_type: Type of query ("search", "pattern", "temporal", "context", "relationships")
    - query: The search query or pattern
    - context: Optional semantic context to search within
    - time_range: Time range for temporal queries (hours/days to look back)
    - limit: Maximum results to return
    - requesting_agent: Agent making the request (used for access control)
    
    Returns:
    Query results with relevant nodes and relationships
    """
    tool = get_semantic_query_tool()
    return await tool.execute(**kwargs)