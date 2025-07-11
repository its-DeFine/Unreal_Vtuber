"""
Team Insight Consolidator
========================

Extends the graph consolidation service to specifically handle team insights
and cross-team communications, creating enriched summaries for each team.
"""

import logging
import json
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
from collections import defaultdict

from .neo4j_semantic_storage import get_neo4j_storage, SemanticContext
from ..core.character_team_registry import CharacterType

logger = logging.getLogger(__name__)


class TeamInsightConsolidator:
    """
    Specialized consolidator for team insights and communications.
    Works alongside the main graph consolidation service.
    """
    
    def __init__(self):
        self.storage = get_neo4j_storage()
        logger.info("🎯 [TEAM_CONSOLIDATOR] Initialized team insight consolidator")
    
    async def consolidate_team_insights(self, start_time: datetime, end_time: datetime):
        """
        Consolidate team insights for a specific time period
        
        Args:
            start_time: Start of consolidation period
            end_time: End of consolidation period
        """
        try:
            logger.info(f"🎯 [TEAM_CONSOLIDATOR] Consolidating team insights from {start_time} to {end_time}")
            
            # Process each team type
            for team_type in CharacterType:
                await self._consolidate_team(team_type, start_time, end_time)
            
            # Create cross-team collaboration summary
            await self._create_collaboration_summary(start_time, end_time)
            
            # Analyze team performance patterns
            await self._analyze_team_patterns(start_time, end_time)
            
            logger.info("✅ [TEAM_CONSOLIDATOR] Team insight consolidation completed")
            
        except Exception as e:
            logger.error(f"❌ [TEAM_CONSOLIDATOR] Failed to consolidate team insights: {e}")
    
    async def _consolidate_team(self, team_type: CharacterType, start_time: datetime, end_time: datetime):
        """Consolidate insights for a specific team"""
        try:
            async with self.storage.async_driver.session() as session:
                # Get all team insights in the time range
                query = """
                MATCH (n:SemanticNode)
                WHERE n.node_type = 'team_insight'
                AND n.metadata CONTAINS 'team_type'
                AND n.timestamp >= $start_time 
                AND n.timestamp <= $end_time
                AND n.metadata CONTAINS $team_type
                RETURN n
                ORDER BY n.timestamp
                """
                
                result = await session.run(
                    query,
                    team_type=team_type.value,
                    start_time=start_time.timestamp(),
                    end_time=end_time.timestamp()
                )
                
                insights = []
                tools_used = defaultdict(int)
                focus_areas = defaultdict(int)
                collaboration_requests = []
                
                async for record in result:
                    node = record["n"]
                    insights.append(node)
                    
                    # Parse metadata
                    metadata = json.loads(node.get("metadata", "{}"))
                    
                    # Track tools used
                    for tool in metadata.get("tools_used", []):
                        tools_used[tool] += 1
                    
                    # Track focus areas
                    focus = metadata.get("focus", "general")
                    focus_areas[focus] += 1
                    
                    # Track collaboration requests
                    if metadata.get("collaboration_requested"):
                        collaboration_requests.append(metadata)
                
                if not insights:
                    return
                
                # Generate team-specific summary
                summary_content = self._generate_team_summary(
                    team_type, insights, tools_used, focus_areas, collaboration_requests
                )
                
                # Create consolidated team summary node
                summary_node = await self.storage.add_semantic_node(
                    content=summary_content,
                    context=self._get_team_context(team_type),
                    node_type="team_daily_summary",
                    metadata={
                        "date": start_time.date().isoformat(),
                        "team_type": team_type.value,
                        "insight_count": len(insights),
                        "tools_used": dict(tools_used),
                        "focus_areas": dict(focus_areas),
                        "collaboration_count": len(collaboration_requests),
                        "consolidated": True
                    },
                    initiating_agent="team_consolidator",
                    agent_category="system",
                    agent_team=team_type.value
                )
                
                if summary_node:
                    # Link insights to summary
                    await self._link_insights_to_summary(insights, summary_node.id)
                
                logger.info(f"📊 [TEAM_CONSOLIDATOR] Consolidated {len(insights)} insights for {team_type.value} team")
                
        except Exception as e:
            logger.error(f"❌ [TEAM_CONSOLIDATOR] Failed to consolidate {team_type.value} team: {e}")
    
    def _generate_team_summary(
        self, 
        team_type: CharacterType, 
        insights: List[Dict],
        tools_used: Dict[str, int],
        focus_areas: Dict[str, int],
        collaboration_requests: List[Dict]
    ) -> str:
        """Generate team-specific summary content"""
        date_str = datetime.fromtimestamp(insights[0]["timestamp"]).date().isoformat()
        
        summary_parts = [
            f"{team_type.value.title()} Team Daily Summary - {date_str}",
            "=" * 50,
            f"Total Insights Generated: {len(insights)}"
        ]
        
        # Add team-specific highlights
        if team_type == CharacterType.TRADER:
            summary_parts.extend([
                "",
                "Trading Activity:",
                f"- Market analyses performed: {tools_used.get('market_data_tool', 0)}",
                f"- Portfolio optimizations: {tools_used.get('portfolio_optimization_tool', 0)}",
                f"- Risk assessments: {tools_used.get('risk_assessment_tool', 0)}"
            ])
        elif team_type == CharacterType.STREAMER:
            summary_parts.extend([
                "",
                "Content & Engagement:",
                f"- Content strategies developed: {tools_used.get('content_strategy_tool', 0)}",
                f"- Analytics reviewed: {tools_used.get('analytics_tool', 0)}",
                f"- Community interactions: {tools_used.get('community_tool', 0)}"
            ])
        elif team_type == CharacterType.TEACHER:
            summary_parts.extend([
                "",
                "Educational Progress:",
                f"- Learning modules created: {tools_used.get('curriculum_design_tool', 0)}",
                f"- Student assessments: {tools_used.get('assessment_tool', 0)}",
                f"- Knowledge graphs updated: {tools_used.get('knowledge_management_tool', 0)}"
            ])
        elif team_type == CharacterType.DEFAULT:
            summary_parts.extend([
                "",
                "System Evolution:",
                f"- Evolution cycles: {tools_used.get('core_evolution_tool', 0)}",
                f"- Goal management: {tools_used.get('goal_management_tools', 0)}",
                f"- Performance optimizations: {focus_areas.get('performance_optimization', 0)}"
            ])
        
        # Add focus area breakdown
        if focus_areas:
            summary_parts.extend([
                "",
                "Focus Areas:"
            ])
            for focus, count in sorted(focus_areas.items(), key=lambda x: x[1], reverse=True)[:3]:
                summary_parts.append(f"- {focus}: {count} iterations")
        
        # Add collaboration summary
        if collaboration_requests:
            summary_parts.extend([
                "",
                f"Cross-team Collaborations: {len(collaboration_requests)}"
            ])
            
            # Group by target team
            collab_targets = defaultdict(int)
            for req in collaboration_requests:
                collab_targets[req.get("target_team", "unknown")] += 1
            
            for target, count in collab_targets.items():
                summary_parts.append(f"- With {target}: {count} requests")
        
        # Add key insights
        if insights:
            summary_parts.extend([
                "",
                "Key Insights:"
            ])
            # Extract top 3 insights based on confidence or importance
            top_insights = sorted(
                insights, 
                key=lambda x: json.loads(x.get("metadata", "{}")).get("confidence", 0),
                reverse=True
            )[:3]
            
            for i, insight in enumerate(top_insights, 1):
                content = insight["content"][:100] + "..." if len(insight["content"]) > 100 else insight["content"]
                summary_parts.append(f"{i}. {content}")
        
        return "\n".join(summary_parts)
    
    def _get_team_context(self, team_type: CharacterType) -> SemanticContext:
        """Map team type to semantic context"""
        context_map = {
            CharacterType.TRADER: SemanticContext.TRADING,
            CharacterType.STREAMER: SemanticContext.COMMUNICATION,
            CharacterType.TEACHER: SemanticContext.LEARNING,
            CharacterType.DEFAULT: SemanticContext.SYSTEM
        }
        return context_map.get(team_type, SemanticContext.GENERAL)
    
    async def _link_insights_to_summary(self, insights: List[Dict], summary_id: str):
        """Create relationships from insights to team summary"""
        try:
            async with self.storage.async_driver.session() as session:
                for insight in insights:
                    query = """
                    MATCH (n:SemanticNode {id: $insight_id})
                    MATCH (s:SemanticNode {id: $summary_id})
                    CREATE (n)-[:TEAM_SUMMARIZED_BY {timestamp: $timestamp}]->(s)
                    """
                    
                    await session.run(
                        query,
                        insight_id=insight["id"],
                        summary_id=summary_id,
                        timestamp=datetime.now().timestamp()
                    )
                    
        except Exception as e:
            logger.error(f"❌ [TEAM_CONSOLIDATOR] Failed to link insights: {e}")
    
    async def _create_collaboration_summary(self, start_time: datetime, end_time: datetime):
        """Create summary of cross-team collaborations"""
        try:
            async with self.storage.async_driver.session() as session:
                # Find all collaboration relationships
                query = """
                MATCH (n1:SemanticNode)-[r:COLLABORATED_WITH]->(n2:SemanticNode)
                WHERE r.timestamp >= $start_time AND r.timestamp <= $end_time
                RETURN n1, r, n2
                """
                
                result = await session.run(
                    query,
                    start_time=start_time.timestamp(),
                    end_time=end_time.timestamp()
                )
                
                collaborations = []
                team_interactions = defaultdict(lambda: defaultdict(int))
                
                async for record in result:
                    n1 = record["n1"]
                    n2 = record["n2"]
                    rel = record["r"]
                    
                    collaborations.append({
                        "from": n1.get("agent_team", "unknown"),
                        "to": n2.get("agent_team", "unknown"),
                        "type": rel.get("collaboration_type", "general")
                    })
                    
                    # Track team interactions
                    from_team = n1.get("agent_team", "unknown")
                    to_team = n2.get("agent_team", "unknown")
                    team_interactions[from_team][to_team] += 1
                
                if collaborations:
                    # Create collaboration summary
                    summary_content = f"Cross-Team Collaboration Summary - {start_time.date()}\n"
                    summary_content += "=" * 50 + "\n\n"
                    summary_content += f"Total Collaborations: {len(collaborations)}\n\n"
                    
                    summary_content += "Team Interaction Matrix:\n"
                    for from_team, targets in team_interactions.items():
                        summary_content += f"\n{from_team}:\n"
                        for to_team, count in targets.items():
                            summary_content += f"  → {to_team}: {count} interactions\n"
                    
                    # Create the collaboration summary node
                    await self.storage.add_semantic_node(
                        content=summary_content,
                        context=SemanticContext.COLLABORATION,
                        node_type="collaboration_summary",
                        metadata={
                            "date": start_time.date().isoformat(),
                            "total_collaborations": len(collaborations),
                            "team_interactions": dict(team_interactions)
                        },
                        initiating_agent="team_consolidator",
                        agent_category="system",
                        agent_team="coordination"
                    )
                    
                    logger.info(f"🤝 [TEAM_CONSOLIDATOR] Created collaboration summary with {len(collaborations)} interactions")
                    
        except Exception as e:
            logger.error(f"❌ [TEAM_CONSOLIDATOR] Failed to create collaboration summary: {e}")
    
    async def _analyze_team_patterns(self, start_time: datetime, end_time: datetime):
        """Analyze patterns in team behavior and performance"""
        try:
            async with self.storage.async_driver.session() as session:
                # Analyze tool usage patterns
                query = """
                MATCH (n:SemanticNode)
                WHERE n.node_type = 'tool_execution'
                AND n.timestamp >= $start_time 
                AND n.timestamp <= $end_time
                AND n.agent_team IS NOT NULL
                RETURN n.agent_team as team,
                       n.metadata as metadata,
                       count(n) as executions
                """
                
                result = await session.run(
                    query,
                    start_time=start_time.timestamp(),
                    end_time=end_time.timestamp()
                )
                
                team_patterns = defaultdict(lambda: {
                    "total_executions": 0,
                    "successful_executions": 0,
                    "tool_diversity": set(),
                    "peak_hours": defaultdict(int)
                })
                
                async for record in result:
                    team = record["team"]
                    metadata = json.loads(record["metadata"] or "{}")
                    executions = record["executions"]
                    
                    team_patterns[team]["total_executions"] += executions
                    if metadata.get("success", False):
                        team_patterns[team]["successful_executions"] += executions
                    
                    tool = metadata.get("tool", "unknown")
                    team_patterns[team]["tool_diversity"].add(tool)
                
                # Create pattern analysis node
                if team_patterns:
                    analysis_content = f"Team Performance Pattern Analysis - {start_time.date()}\n"
                    analysis_content += "=" * 50 + "\n\n"
                    
                    for team, patterns in team_patterns.items():
                        success_rate = (patterns["successful_executions"] / patterns["total_executions"] * 100) if patterns["total_executions"] > 0 else 0
                        
                        analysis_content += f"\n{team} Team:\n"
                        analysis_content += f"- Total Executions: {patterns['total_executions']}\n"
                        analysis_content += f"- Success Rate: {success_rate:.1f}%\n"
                        analysis_content += f"- Tool Diversity: {len(patterns['tool_diversity'])} unique tools\n"
                    
                    await self.storage.add_semantic_node(
                        content=analysis_content,
                        context=SemanticContext.ANALYTICS,
                        node_type="team_pattern_analysis",
                        metadata={
                            "date": start_time.date().isoformat(),
                            "team_patterns": {k: {
                                "total": v["total_executions"],
                                "successful": v["successful_executions"],
                                "tools": list(v["tool_diversity"])
                            } for k, v in team_patterns.items()}
                        },
                        initiating_agent="team_consolidator",
                        agent_category="system",
                        agent_team="analytics"
                    )
                    
                    logger.info("📈 [TEAM_CONSOLIDATOR] Created team pattern analysis")
                    
        except Exception as e:
            logger.error(f"❌ [TEAM_CONSOLIDATOR] Failed to analyze team patterns: {e}")


# Integration with main consolidation service
async def consolidate_team_insights_daily(date: Optional[datetime] = None):
    """
    Run team insight consolidation for a specific date
    
    Args:
        date: Date to consolidate (default: yesterday)
    """
    consolidator = TeamInsightConsolidator()
    
    if date is None:
        date = datetime.now() - timedelta(days=1)
    
    start_time = datetime.combine(date.date(), datetime.min.time())
    end_time = datetime.combine(date.date(), datetime.max.time())
    
    await consolidator.consolidate_team_insights(start_time, end_time)