"""
SCB to Neo4j Bridge Service
Transforms SCB states into semantic graph nodes in Neo4j
"""

import logging
import asyncio
from typing import Dict, List, Any, Optional
from datetime import datetime

from .neo4j_semantic_storage import (
    Neo4jSemanticStorage, 
    SemanticContext, 
    SemanticNode,
    get_neo4j_storage
)

logger = logging.getLogger(__name__)


class SCBNeo4jBridge:
    """Bridge between SCB and Neo4j semantic storage"""
    
    def __init__(self):
        """Initialize the bridge"""
        self.storage = get_neo4j_storage()
        self.buffer = {context: [] for context in SemanticContext}
        self.processing_active = True
        logger.info("🌉 [SCB_NEO4J_BRIDGE] Initialized bridge service")
    
    async def transform_scb_state(self, scb_state: Dict[str, Any]) -> List[SemanticNode]:
        """Transform SCB state into semantic nodes"""
        nodes = []
        
        try:
            # Extract timestamp
            timestamp = scb_state.get("timestamp", datetime.now().timestamp())
            
            # 1. Tool executions
            if "tool_used" in scb_state:
                tool_name = scb_state["tool_used"]
                success = scb_state.get("success", False)
                tool_result = scb_state.get("tool_result", {})
                
                content = f"Tool '{tool_name}' executed {'successfully' if success else 'with errors'}"
                if isinstance(tool_result, dict):
                    if "analysis" in tool_result:
                        content += f": {tool_result['analysis']}"
                    elif "result" in tool_result:
                        content += f": {tool_result['result']}"
                
                node = await self.storage.add_semantic_node(
                    content=content,
                    context=SemanticContext.TOOLS,
                    node_type="tool_execution",
                    metadata={
                        "tool": tool_name,
                        "success": success,
                        "result": tool_result,
                        "timestamp": timestamp
                    }
                )
                if node:
                    nodes.append(node)
            
            # 2. Agent communications
            agent_responses = scb_state.get("agent_responses", {})
            
            # S2 to S1 messages
            for agent, response in agent_responses.items():
                if "s2_to_s1" in agent or agent == "s2_to_s1":
                    message = response.get("message", "")
                    node = await self.storage.add_semantic_node(
                        content=message,
                        context=SemanticContext.S2_TO_S1,
                        node_type="communication",
                        metadata={
                            "from": "s2",
                            "to": "s1",
                            "priority": response.get("priority", "normal"),
                            "timestamp": timestamp
                        }
                    )
                    if node:
                        nodes.append(node)
                
                # S1 to S2 feedback
                elif "s1_to_s2" in agent or agent == "s1_to_s2":
                    message = response.get("message", "")
                    node = await self.storage.add_semantic_node(
                        content=message,
                        context=SemanticContext.S1_TO_S2,
                        node_type="feedback",
                        metadata={
                            "from": "s1",
                            "to": "s2",
                            "status": response.get("status", "unknown"),
                            "timestamp": timestamp
                        }
                    )
                    if node:
                        nodes.append(node)
                
                # General agent messages
                elif agent in ["s1_avatar", "s2_analyst", "s2_trader", "s2_programmer"]:
                    message = response.get("message", "")
                    node = await self.storage.add_semantic_node(
                        content=f"{agent}: {message}",
                        context=SemanticContext.AGENT_STATE,
                        node_type="agent_message",
                        metadata={
                            "agent": agent,
                            "reasoning": response.get("reasoning", ""),
                            "timestamp": timestamp
                        }
                    )
                    if node:
                        nodes.append(node)
            
            # 3. Stimuli processing
            if "stimuli_id" in scb_state:
                stimuli_id = scb_state["stimuli_id"]
                content = scb_state.get("stimuli_content", scb_state.get("content", ""))
                decision = scb_state.get("decision", "")
                
                node = await self.storage.add_semantic_node(
                    content=f"Stimuli {stimuli_id}: {content}",
                    context=SemanticContext.STIMULI,
                    node_type="stimuli",
                    metadata={
                        "stimuli_id": stimuli_id,
                        "decision": decision,
                        "routing": scb_state.get("routing", {}),
                        "priority": scb_state.get("priority", "normal"),
                        "timestamp": timestamp
                    }
                )
                if node:
                    nodes.append(node)
            
            # 4. Trading and finance
            if "trade" in scb_state or "portfolio" in scb_state:
                trade_info = scb_state.get("trade", "")
                portfolio = scb_state.get("portfolio", {})
                
                if trade_info:
                    node = await self.storage.add_semantic_node(
                        content=f"Trade executed: {trade_info}",
                        context=SemanticContext.TRADING,
                        node_type="trade",
                        metadata={
                            "trade": trade_info,
                            "portfolio": portfolio,
                            "timestamp": timestamp
                        }
                    )
                    if node:
                        nodes.append(node)
            
            # 5. System events (errors, status changes)
            if "error" in scb_state:
                error = scb_state["error"]
                node = await self.storage.add_semantic_node(
                    content=f"System error: {error}",
                    context=SemanticContext.SYSTEM,
                    node_type="error",
                    metadata={
                        "error": error,
                        "success": False,
                        "timestamp": timestamp
                    }
                )
                if node:
                    nodes.append(node)
            
            # 6. Create relationships between nodes
            if len(nodes) > 1:
                # Connect sequential nodes
                for i in range(len(nodes) - 1):
                    await self.storage.add_relationship(
                        source_id=nodes[i].id,
                        target_id=nodes[i + 1].id,
                        rel_type="FOLLOWED_BY",
                        properties={"timestamp": timestamp}
                    )
            
            # Connect tool executions to their results
            tool_nodes = [n for n in nodes if n.node_type == "tool_execution"]
            result_nodes = [n for n in nodes if n.node_type in ["agent_message", "communication"]]
            
            for tool_node in tool_nodes:
                for result_node in result_nodes:
                    if abs(tool_node.timestamp - result_node.timestamp) < 5:  # Within 5 seconds
                        await self.storage.add_relationship(
                            source_id=tool_node.id,
                            target_id=result_node.id,
                            rel_type="PRODUCED",
                            properties={"confidence": 0.8}
                        )
            
            logger.info(f"✅ [SCB_NEO4J_BRIDGE] Transformed SCB state into {len(nodes)} nodes")
            
        except Exception as e:
            logger.error(f"❌ [SCB_NEO4J_BRIDGE] Error transforming SCB state: {e}")
        
        return nodes
    
    async def process_scb_update(self, scb_state: Dict[str, Any]):
        """Process an SCB update"""
        if not self.processing_active:
            return
        
        try:
            nodes = await self.transform_scb_state(scb_state)
            logger.info(f"📊 [SCB_NEO4J_BRIDGE] Processed {len(nodes)} semantic nodes")
        except Exception as e:
            logger.error(f"❌ [SCB_NEO4J_BRIDGE] Error processing SCB update: {e}")
    
    def get_status(self) -> Dict[str, Any]:
        """Get bridge status"""
        metrics = asyncio.run(self.storage.get_metrics())
        
        return {
            "service": "scb_neo4j_bridge",
            "processing_active": self.processing_active,
            "storage": "neo4j",
            "metrics": metrics,
            "total_nodes": metrics.get("total_nodes", 0),
            "total_relationships": metrics.get("total_relationships", 0)
        }


# Global instance
_bridge_instance = None


def get_scb_neo4j_bridge() -> SCBNeo4jBridge:
    """Get or create global bridge instance"""
    global _bridge_instance
    if _bridge_instance is None:
        _bridge_instance = SCBNeo4jBridge()
    return _bridge_instance


async def transform_and_store_scb_state(scb_state: Dict[str, Any]):
    """Helper function to transform and store SCB state"""
    bridge = get_scb_neo4j_bridge()
    await bridge.process_scb_update(scb_state)