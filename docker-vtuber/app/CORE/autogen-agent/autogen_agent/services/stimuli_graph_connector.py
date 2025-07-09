"""
Stimuli Graph Connector Service
Tracks stimuli as root nodes and connects them to resulting action chains
"""

import logging
import asyncio
from typing import Dict, List, Any, Optional
from datetime import datetime
from collections import defaultdict

from .neo4j_semantic_storage import get_neo4j_storage, SemanticContext

logger = logging.getLogger(__name__)


class StimuliGraphConnector:
    """Service for connecting stimuli to their resulting action chains"""
    
    def __init__(self):
        """Initialize the stimuli connector"""
        self.storage = get_neo4j_storage()
        self.active_stimuli = {}  # Track active stimuli and their chains
        self.connection_queue = asyncio.Queue()
        self.processing_task = None
        logger.info("🔗 [STIMULI_CONNECTOR] Initialized")
    
    async def start(self):
        """Start the background connection processor"""
        self.processing_task = asyncio.create_task(self._process_connections())
        logger.info("🚀 [STIMULI_CONNECTOR] Background processor started")
    
    async def stop(self):
        """Stop the background processor"""
        if self.processing_task:
            self.processing_task.cancel()
            try:
                await self.processing_task
            except asyncio.CancelledError:
                pass
        logger.info("🛑 [STIMULI_CONNECTOR] Stopped")
    
    async def register_stimuli(self, stimuli_id: str, stimuli_node_id: str, metadata: Dict[str, Any] = None):
        """Register a new stimuli as a root node"""
        self.active_stimuli[stimuli_id] = {
            "node_id": stimuli_node_id,
            "start_time": datetime.now(),
            "metadata": metadata or {},
            "connected_nodes": [],
            "status": "active"
        }
        logger.info(f"📍 [STIMULI_CONNECTOR] Registered stimuli {stimuli_id} as root")
    
    async def connect_to_stimuli(self, stimuli_id: str, node_id: str, relationship_type: str = "TRIGGERED_BY"):
        """Queue a connection from stimuli to a resulting node"""
        if stimuli_id not in self.active_stimuli:
            logger.warning(f"⚠️ [STIMULI_CONNECTOR] Unknown stimuli {stimuli_id}")
            return
        
        connection = {
            "stimuli_id": stimuli_id,
            "node_id": node_id,
            "relationship_type": relationship_type,
            "timestamp": datetime.now()
        }
        
        await self.connection_queue.put(connection)
        logger.debug(f"🔗 [STIMULI_CONNECTOR] Queued connection: {stimuli_id} -> {node_id}")
    
    async def _process_connections(self):
        """Background task to process connections without blocking"""
        while True:
            try:
                # Process connections in batches for efficiency
                connections = []
                
                # Collect up to 10 connections or wait 1 second
                try:
                    for _ in range(10):
                        connection = await asyncio.wait_for(
                            self.connection_queue.get(), 
                            timeout=1.0
                        )
                        connections.append(connection)
                except asyncio.TimeoutError:
                    pass
                
                if connections:
                    await self._create_connections_batch(connections)
                
                # Clean up old stimuli (older than 1 hour)
                await self._cleanup_old_stimuli()
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"❌ [STIMULI_CONNECTOR] Processing error: {e}")
                await asyncio.sleep(5)
    
    async def _create_connections_batch(self, connections: List[Dict[str, Any]]):
        """Create multiple connections in a single transaction"""
        try:
            async with self.storage.driver.session() as session:
                for conn in connections:
                    stimuli_id = conn["stimuli_id"]
                    
                    if stimuli_id not in self.active_stimuli:
                        continue
                    
                    stimuli_data = self.active_stimuli[stimuli_id]
                    
                    # Create the relationship
                    query = """
                    MATCH (s:SemanticNode {id: $stimuli_node_id})
                    MATCH (n:SemanticNode {id: $node_id})
                    CREATE (s)-[r:TRIGGERED {
                        timestamp: $timestamp,
                        relationship_type: $rel_type,
                        stimuli_id: $stimuli_id
                    }]->(n)
                    RETURN r
                    """
                    
                    await session.run(
                        query,
                        stimuli_node_id=stimuli_data["node_id"],
                        node_id=conn["node_id"],
                        timestamp=conn["timestamp"].timestamp(),
                        rel_type=conn["relationship_type"],
                        stimuli_id=stimuli_id
                    )
                    
                    # Track connected nodes
                    stimuli_data["connected_nodes"].append(conn["node_id"])
                
                logger.info(f"✅ [STIMULI_CONNECTOR] Created {len(connections)} connections")
                
        except Exception as e:
            logger.error(f"❌ [STIMULI_CONNECTOR] Batch connection error: {e}")
    
    async def _cleanup_old_stimuli(self):
        """Remove stimuli older than 1 hour from active tracking"""
        current_time = datetime.now()
        to_remove = []
        
        for stimuli_id, data in self.active_stimuli.items():
            age = (current_time - data["start_time"]).total_seconds()
            if age > 3600:  # 1 hour
                to_remove.append(stimuli_id)
        
        for stimuli_id in to_remove:
            del self.active_stimuli[stimuli_id]
            logger.debug(f"🧹 [STIMULI_CONNECTOR] Cleaned up old stimuli {stimuli_id}")
    
    async def complete_stimuli(self, stimuli_id: str, final_status: str = "completed"):
        """Mark a stimuli as complete and create final summary relationship"""
        if stimuli_id not in self.active_stimuli:
            return
        
        stimuli_data = self.active_stimuli[stimuli_id]
        stimuli_data["status"] = final_status
        
        try:
            # Create a summary relationship if there were multiple actions
            if len(stimuli_data["connected_nodes"]) > 1:
                async with self.storage.driver.session() as session:
                    query = """
                    MATCH (s:SemanticNode {id: $stimuli_node_id})
                    SET s.total_triggered = $total_triggered,
                        s.completion_status = $status
                    """
                    
                    await session.run(
                        query,
                        stimuli_node_id=stimuli_data["node_id"],
                        total_triggered=len(stimuli_data["connected_nodes"]),
                        status=final_status
                    )
            
            logger.info(f"✅ [STIMULI_CONNECTOR] Completed stimuli {stimuli_id} with {len(stimuli_data['connected_nodes'])} connections")
            
        except Exception as e:
            logger.error(f"❌ [STIMULI_CONNECTOR] Error completing stimuli: {e}")
    
    def get_active_stimuli(self) -> Dict[str, Any]:
        """Get currently active stimuli"""
        return {
            stimuli_id: {
                "start_time": data["start_time"].isoformat(),
                "connected_nodes": len(data["connected_nodes"]),
                "status": data["status"]
            }
            for stimuli_id, data in self.active_stimuli.items()
        }


# Global instance
_connector_instance = None


def get_stimuli_connector() -> StimuliGraphConnector:
    """Get or create global stimuli connector instance"""
    global _connector_instance
    if _connector_instance is None:
        _connector_instance = StimuliGraphConnector()
    return _connector_instance


async def track_stimuli_connection(stimuli_id: str, node_id: str):
    """Helper function to track stimuli connections"""
    connector = get_stimuli_connector()
    await connector.connect_to_stimuli(stimuli_id, node_id)