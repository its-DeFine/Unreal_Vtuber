"""
Graph Consolidation Service
Daily consolidation of semantic graph nodes to maintain performance and create summaries
"""

import logging
import asyncio
import json
from datetime import datetime, timedelta, time
from typing import Dict, List, Any, Optional
from collections import defaultdict

from .neo4j_semantic_storage import get_neo4j_storage, SemanticContext, SemanticNode
from .team_insight_consolidator import consolidate_team_insights_daily

logger = logging.getLogger(__name__)


class GraphConsolidationService:
    """Service for consolidating semantic graph nodes daily"""
    
    def __init__(self, consolidation_hour: int = 2):
        """
        Initialize consolidation service
        
        Args:
            consolidation_hour: Hour of day to run consolidation (0-23), default 2 AM
        """
        self.storage = get_neo4j_storage()
        self.consolidation_hour = consolidation_hour
        self.is_running = False
        self.last_consolidation = None
        logger.info(f"📊 [CONSOLIDATION] Initialized - scheduled for {consolidation_hour}:00 daily")
    
    async def start(self):
        """Start the consolidation service"""
        self.is_running = True
        logger.info("🚀 [CONSOLIDATION] Service started")
        
        while self.is_running:
            try:
                # Check if it's time to consolidate
                now = datetime.now()
                scheduled_time = datetime.combine(
                    now.date(), 
                    time(hour=self.consolidation_hour)
                )
                
                # If we've passed today's scheduled time, schedule for tomorrow
                if now > scheduled_time:
                    scheduled_time += timedelta(days=1)
                
                # Calculate sleep duration
                sleep_seconds = (scheduled_time - now).total_seconds()
                
                logger.info(f"⏰ [CONSOLIDATION] Next consolidation at {scheduled_time}")
                await asyncio.sleep(sleep_seconds)
                
                # Run consolidation
                if self.is_running:
                    await self.consolidate_daily()
                    
            except Exception as e:
                logger.error(f"❌ [CONSOLIDATION] Error in service loop: {e}")
                await asyncio.sleep(3600)  # Sleep 1 hour on error
    
    async def stop(self):
        """Stop the consolidation service"""
        self.is_running = False
        logger.info("🛑 [CONSOLIDATION] Service stopped")
    
    async def consolidate_daily(self, date: Optional[datetime] = None):
        """
        Consolidate nodes for a specific day
        
        Args:
            date: Date to consolidate (default: yesterday)
        """
        try:
            # Default to yesterday if no date specified
            if date is None:
                date = datetime.now() - timedelta(days=1)
            
            start_time = datetime.combine(date.date(), time.min)
            end_time = datetime.combine(date.date(), time.max)
            
            logger.info(f"📅 [CONSOLIDATION] Starting daily consolidation for {date.date()}")
            
            # Process each context separately
            for context in SemanticContext:
                await self._consolidate_context(context, start_time, end_time)
            
            # Create daily summary
            await self._create_daily_summary(start_time, end_time)
            
            # Consolidate team insights
            await consolidate_team_insights_daily(date)
            logger.info("🎯 [CONSOLIDATION] Team insights consolidated")
            
            # Archive old nodes
            await self._archive_nodes(start_time, end_time)
            
            self.last_consolidation = datetime.now()
            logger.info(f"✅ [CONSOLIDATION] Completed daily consolidation for {date.date()}")
            
        except Exception as e:
            logger.error(f"❌ [CONSOLIDATION] Failed to consolidate: {e}")
    
    async def _consolidate_context(self, context: SemanticContext, start_time: datetime, end_time: datetime):
        """Consolidate nodes for a specific context"""
        try:
            async with self.storage.async_driver.session() as session:
                # Get all nodes for the context in the time range
                query = """
                MATCH (n:SemanticNode)
                WHERE n.context = $context 
                AND n.timestamp >= $start_time 
                AND n.timestamp <= $end_time
                RETURN n
                ORDER BY n.timestamp
                """
                
                result = await session.run(
                    query,
                    context=context.value,
                    start_time=start_time.timestamp(),
                    end_time=end_time.timestamp()
                )
                
                nodes = []
                agent_stats = defaultdict(lambda: {"count": 0, "actions": []})
                
                async for record in result:
                    node = record["n"]
                    nodes.append(node)
                    
                    # Track agent statistics
                    agent = node.get("initiating_agent", "unknown")
                    agent_stats[agent]["count"] += 1
                    agent_stats[agent]["actions"].append(node["node_type"])
                
                if not nodes:
                    return
                
                # Create consolidated summary node
                summary_content = self._generate_summary(context, nodes, agent_stats)
                
                summary_node = await self.storage.add_semantic_node(
                    content=summary_content,
                    context=context,
                    node_type="daily_summary",
                    metadata={
                        "date": start_time.date().isoformat(),
                        "node_count": len(nodes),
                        "agent_statistics": dict(agent_stats),
                        "consolidated": True
                    },
                    initiating_agent="system_consolidator",
                    agent_category="system",
                    agent_team="maintenance"
                )
                
                if summary_node:
                    # Create relationships from original nodes to summary
                    await self._link_to_summary(nodes, summary_node.id)
                
                logger.info(f"📊 [CONSOLIDATION] Consolidated {len(nodes)} nodes in {context.value}")
                
        except Exception as e:
            logger.error(f"❌ [CONSOLIDATION] Failed to consolidate {context.value}: {e}")
    
    def _generate_summary(self, context: SemanticContext, nodes: List[Dict], agent_stats: Dict) -> str:
        """Generate summary content for consolidated nodes"""
        date_str = datetime.fromtimestamp(nodes[0]["timestamp"]).date().isoformat()
        
        summary_parts = [
            f"Daily Summary for {context.value} - {date_str}",
            f"Total Events: {len(nodes)}"
        ]
        
        # Add context-specific summaries
        if context == SemanticContext.TRADING:
            trades = [n for n in nodes if n["node_type"] == "trade"]
            summary_parts.append(f"Trades Executed: {len(trades)}")
            
        elif context == SemanticContext.TOOLS:
            successful = [n for n in nodes if json.loads(n.get("metadata", "{}")).get("success", False)]
            summary_parts.append(f"Successful Tool Executions: {len(successful)}/{len(nodes)}")
            
        elif context == SemanticContext.S2_TO_S1:
            summary_parts.append(f"S2→S1 Messages: {len(nodes)}")
        
        # Add agent activity summary
        summary_parts.append("\nAgent Activity:")
        for agent, stats in sorted(agent_stats.items(), key=lambda x: x[1]["count"], reverse=True)[:5]:
            summary_parts.append(f"  - {agent}: {stats['count']} actions")
        
        return "\n".join(summary_parts)
    
    async def _link_to_summary(self, nodes: List[Dict], summary_id: str):
        """Create relationships from original nodes to summary node"""
        try:
            async with self.storage.async_driver.session() as session:
                # Create SUMMARIZED_BY relationships
                for node in nodes:
                    query = """
                    MATCH (n:SemanticNode {id: $node_id})
                    MATCH (s:SemanticNode {id: $summary_id})
                    CREATE (n)-[:SUMMARIZED_BY {timestamp: $timestamp}]->(s)
                    """
                    
                    await session.run(
                        query,
                        node_id=node["id"],
                        summary_id=summary_id,
                        timestamp=datetime.now().timestamp()
                    )
                    
        except Exception as e:
            logger.error(f"❌ [CONSOLIDATION] Failed to link to summary: {e}")
    
    async def _create_daily_summary(self, start_time: datetime, end_time: datetime):
        """Create overall daily summary across all contexts"""
        try:
            async with self.storage.async_driver.session() as session:
                # Get statistics across all contexts
                query = """
                MATCH (n:SemanticNode)
                WHERE n.timestamp >= $start_time AND n.timestamp <= $end_time
                RETURN n.context as context, 
                       n.agent_category as category,
                       count(n) as count
                """
                
                result = await session.run(
                    query,
                    start_time=start_time.timestamp(),
                    end_time=end_time.timestamp()
                )
                
                stats = defaultdict(lambda: {"total": 0, "by_category": defaultdict(int)})
                
                async for record in result:
                    context = record["context"]
                    category = record["category"] or "unknown"
                    count = record["count"]
                    
                    stats[context]["total"] += count
                    stats[context]["by_category"][category] += count
                
                # Create master daily summary
                summary_content = f"System Daily Summary - {start_time.date()}\n"
                summary_content += "=" * 50 + "\n\n"
                
                total_nodes = sum(s["total"] for s in stats.values())
                summary_content += f"Total Nodes Created: {total_nodes}\n\n"
                
                summary_content += "Activity by Context:\n"
                for context, data in sorted(stats.items()):
                    summary_content += f"\n{context}: {data['total']} nodes\n"
                    for category, count in data["by_category"].items():
                        summary_content += f"  - {category}: {count}\n"
                
                # Create the master summary node
                await self.storage.add_semantic_node(
                    content=summary_content,
                    context=SemanticContext.SYSTEM,
                    node_type="master_daily_summary",
                    metadata={
                        "date": start_time.date().isoformat(),
                        "total_nodes": total_nodes,
                        "statistics": dict(stats)
                    },
                    initiating_agent="system_consolidator",
                    agent_category="system",
                    agent_team="maintenance"
                )
                
                logger.info(f"📈 [CONSOLIDATION] Created master daily summary with {total_nodes} nodes")
                
        except Exception as e:
            logger.error(f"❌ [CONSOLIDATION] Failed to create daily summary: {e}")
    
    async def _archive_nodes(self, start_time: datetime, end_time: datetime):
        """Archive nodes by adding archived label"""
        try:
            async with self.storage.async_driver.session() as session:
                # Add archived label to old nodes (except summaries)
                query = """
                MATCH (n:SemanticNode)
                WHERE n.timestamp >= $start_time 
                AND n.timestamp <= $end_time
                AND n.node_type <> 'daily_summary'
                AND n.node_type <> 'master_daily_summary'
                SET n:Archived
                SET n.archived_date = $archived_date
                RETURN count(n) as archived_count
                """
                
                result = await session.run(
                    query,
                    start_time=start_time.timestamp(),
                    end_time=end_time.timestamp(),
                    archived_date=datetime.now().isoformat()
                )
                
                record = await result.single()
                archived_count = record["archived_count"] if record else 0
                
                logger.info(f"📦 [CONSOLIDATION] Archived {archived_count} nodes")
                
        except Exception as e:
            logger.error(f"❌ [CONSOLIDATION] Failed to archive nodes: {e}")
    
    async def get_consolidation_status(self) -> Dict[str, Any]:
        """Get current consolidation status"""
        try:
            async with self.storage.async_driver.session() as session:
                # Get summary statistics
                query = """
                MATCH (n:SemanticNode)
                WHERE n.node_type IN ['daily_summary', 'master_daily_summary']
                RETURN n.node_type as type, count(n) as count
                ORDER BY type
                """
                
                result = await session.run(query)
                
                summaries = {}
                async for record in result:
                    summaries[record["type"]] = record["count"]
                
                # Get archived node count
                archive_query = """
                MATCH (n:Archived)
                RETURN count(n) as archived_count
                """
                
                archive_result = await session.run(archive_query)
                archive_record = await archive_result.single()
                archived_count = archive_record["archived_count"] if archive_record else 0
                
                return {
                    "service": "graph_consolidation",
                    "is_running": self.is_running,
                    "last_consolidation": self.last_consolidation.isoformat() if self.last_consolidation else None,
                    "next_consolidation": self._get_next_consolidation_time().isoformat(),
                    "summaries": summaries,
                    "archived_nodes": archived_count
                }
                
        except Exception as e:
            logger.error(f"❌ [CONSOLIDATION] Failed to get status: {e}")
            return {"error": str(e)}
    
    def _get_next_consolidation_time(self) -> datetime:
        """Calculate next consolidation time"""
        now = datetime.now()
        scheduled_time = datetime.combine(now.date(), time(hour=self.consolidation_hour))
        
        if now > scheduled_time:
            scheduled_time += timedelta(days=1)
            
        return scheduled_time


# Global instance
_consolidation_service = None


def get_consolidation_service(consolidation_hour: int = 2) -> GraphConsolidationService:
    """Get or create global consolidation service instance"""
    global _consolidation_service
    if _consolidation_service is None:
        _consolidation_service = GraphConsolidationService(consolidation_hour)
    return _consolidation_service


async def start_consolidation_service(consolidation_hour: int = 2):
    """Start the consolidation service"""
    service = get_consolidation_service(consolidation_hour)
    await service.start()


async def consolidate_now(date: Optional[datetime] = None):
    """Manually trigger consolidation for a specific date"""
    service = get_consolidation_service()
    await service.consolidate_daily(date)