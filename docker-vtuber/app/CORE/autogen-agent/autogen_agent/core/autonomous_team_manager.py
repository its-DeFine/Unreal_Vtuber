"""
Autonomous Team Manager
======================

Manages background execution of character-specific autonomous teams.
Each character has its own specialized team that runs autonomously,
processing tasks and sharing insights through SCB channels.
"""

import asyncio
import logging
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, List
from dataclasses import dataclass, field
from enum import Enum

from .character_team_registry import CharacterType, get_character_team_registry
from .stimuli_autogen_team import StimuliAutoGenTeam
from .specialized_teams import create_specialized_team
from ..services.character_state_manager import get_character_state_manager
from ..utils.scb_utils import SCBWriter, SCBCoordinator, publish_team_insight, MessagePriority
from ..services.neo4j_semantic_storage import get_neo4j_storage, SemanticContext


class TeamStatus(Enum):
    """Status of an autonomous team"""
    IDLE = "idle"
    RUNNING = "running"
    PAUSED = "paused"
    ERROR = "error"


@dataclass
class TeamExecutionContext:
    """Context for autonomous team execution"""
    character_id: str
    character_type: CharacterType
    team_name: str
    iteration_count: int = 0
    last_execution: Optional[datetime] = None
    status: TeamStatus = TeamStatus.IDLE
    current_focus: Optional[str] = None
    recent_insights: List[Dict[str, Any]] = field(default_factory=list)


class AutonomousTeamManager:
    """
    Manages autonomous execution of character-specific teams.
    Each team runs in the background, pursuing character-aligned goals.
    """
    
    def __init__(
        self,
        tool_registry,
        scb_client=None,
        vtuber_client=None,
        execution_interval: int = 60,  # seconds between autonomous iterations
        max_iterations_per_session: int = 100
    ):
        self.tool_registry = tool_registry
        self.scb_client = scb_client
        self.vtuber_client = vtuber_client
        self.execution_interval = execution_interval
        self.max_iterations_per_session = max_iterations_per_session
        
        # Team management
        self.character_teams: Dict[str, StimuliAutoGenTeam] = {}
        self.execution_contexts: Dict[str, TeamExecutionContext] = {}
        self.active_tasks: Dict[str, asyncio.Task] = {}
        
        # Current character tracking
        self.current_character_id: Optional[str] = None
        self.current_team: Optional[StimuliAutoGenTeam] = None
        
        # SCB integration
        self.scb_writer = SCBWriter(scb_client) if scb_client else None
        self.scb_coordinator = SCBCoordinator(scb_client) if scb_client else None
        
        # Neo4j semantic storage
        self.semantic_storage = None
        try:
            self.semantic_storage = get_neo4j_storage()
            logging.info("🌐 [TEAM_MANAGER] Neo4j semantic storage connected")
        except Exception as e:
            logging.warning(f"⚠️ [TEAM_MANAGER] Neo4j not available: {e}")
        
        # Service state
        self.running = False
        
        logging.info("🤖 [TEAM_MANAGER] Autonomous team manager initialized")
    
    async def initialize(self) -> bool:
        """Initialize the autonomous team manager"""
        
        try:
            # Get character team registry
            registry = get_character_team_registry()
            
            # Initialize teams for each character type
            for char_type in CharacterType:
                team_config = registry.get_team_config(char_type)
                if not team_config:
                    continue
                
                logging.info(f"🔧 [TEAM_MANAGER] Initializing {team_config.team_name}")
                
                # Create specialized team instance
                team = create_specialized_team(char_type)
                
                # Initialize team
                if team and team.initialize_team():
                    self.character_teams[char_type.value] = team
                    
                    # Create execution context
                    self.execution_contexts[char_type.value] = TeamExecutionContext(
                        character_id=char_type.value,
                        character_type=char_type,
                        team_name=team_config.team_name
                    )
                    
                    logging.info(f"✅ [TEAM_MANAGER] Initialized {team_config.team_name}")
                else:
                    logging.error(f"❌ [TEAM_MANAGER] Failed to initialize {team_config.team_name}")
            
            # Get current character
            await self._sync_current_character()
            
            self.running = True
            logging.info(f"✅ [TEAM_MANAGER] Initialized {len(self.character_teams)} autonomous teams")
            
            return len(self.character_teams) > 0
            
        except Exception as e:
            logging.error(f"❌ [TEAM_MANAGER] Initialization failed: {e}")
            return False
    
    async def _sync_current_character(self):
        """Sync with current character from character state manager"""
        
        try:
            char_manager = get_character_state_manager()
            if char_manager:
                current_char = await char_manager.get_current_character()
                if current_char:
                    await self.handle_character_change(current_char.get("id"))
        except Exception as e:
            logging.warning(f"⚠️ [TEAM_MANAGER] Could not sync character: {e}")
    
    async def handle_character_change(self, new_character_id: str):
        """Handle character change - activate appropriate autonomous team"""
        
        old_character = self.current_character_id
        self.current_character_id = new_character_id
        
        logging.info(f"🎭 [TEAM_MANAGER] Character changed: {old_character} → {new_character_id}")
        
        # Stop current team execution
        if old_character and old_character in self.active_tasks:
            task = self.active_tasks[old_character]
            task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                pass
            del self.active_tasks[old_character]
            
            # Update context status
            if old_character in self.execution_contexts:
                self.execution_contexts[old_character].status = TeamStatus.PAUSED
        
        # Get character type from registry
        registry = get_character_team_registry()
        team_config = registry.get_team_config_by_character_id(new_character_id)
        
        if not team_config:
            logging.warning(f"⚠️ [TEAM_MANAGER] No team config for character: {new_character_id}")
            return
        
        # Get corresponding team
        team_key = team_config.character_type.value
        self.current_team = self.character_teams.get(team_key)
        
        if not self.current_team:
            logging.error(f"❌ [TEAM_MANAGER] No team found for character type: {team_key}")
            return
        
        # Start autonomous execution for new character
        context = self.execution_contexts.get(team_key)
        if context:
            context.character_id = new_character_id
            context.status = TeamStatus.RUNNING
            
            # Start execution task
            task = asyncio.create_task(
                self._autonomous_execution_loop(team_key, context)
            )
            self.active_tasks[team_key] = task
            
            logging.info(f"🚀 [TEAM_MANAGER] Started autonomous execution for {team_config.team_name}")
            
            # Publish character change to SCB
            if self.scb_writer:
                await self.scb_writer.publish_event(
                    channel=f"character_change",
                    event_type="team_activated",
                    data={
                        "character_id": new_character_id,
                        "team_name": team_config.team_name,
                        "team_type": team_key,
                        "timestamp": datetime.now().isoformat()
                    }
                )
    
    async def _autonomous_execution_loop(self, team_key: str, context: TeamExecutionContext):
        """Main autonomous execution loop for a team"""
        
        team = self.character_teams.get(team_key)
        if not team:
            return
        
        logging.info(f"🔄 [TEAM_MANAGER] Starting autonomous loop for {context.team_name}")
        
        while context.status == TeamStatus.RUNNING and self.running:
            try:
                # Check iteration limit
                if context.iteration_count >= self.max_iterations_per_session:
                    logging.info(f"🛑 [TEAM_MANAGER] {context.team_name} reached iteration limit")
                    break
                
                # Execute autonomous iteration
                await self._execute_autonomous_iteration(team, context)
                
                # Update iteration count
                context.iteration_count += 1
                context.last_execution = datetime.now()
                
                # Wait before next iteration
                await asyncio.sleep(self.execution_interval)
                
            except asyncio.CancelledError:
                logging.info(f"🛑 [TEAM_MANAGER] {context.team_name} execution cancelled")
                break
                
            except Exception as e:
                logging.error(f"❌ [TEAM_MANAGER] Error in {context.team_name} loop: {e}")
                context.status = TeamStatus.ERROR
                await asyncio.sleep(self.execution_interval * 2)  # Longer wait on error
        
        context.status = TeamStatus.IDLE
        logging.info(f"💤 [TEAM_MANAGER] {context.team_name} autonomous loop ended")
    
    async def _execute_autonomous_iteration(self, team: StimuliAutoGenTeam, context: TeamExecutionContext):
        """Execute a single autonomous iteration"""
        
        try:
            # Generate autonomous prompt based on character type
            prompt = self._generate_autonomous_prompt(context)
            
            # Create stimuli data
            stimuli_data = {
                "stimuli_id": f"auto_{context.character_type.value}_{context.iteration_count}",
                "content": prompt,
                "source": "autonomous_execution",
                "priority": "medium",
                "metadata": {
                    "iteration": context.iteration_count,
                    "character_id": context.character_id,
                    "team_name": context.team_name,
                    "focus": context.current_focus
                }
            }
            
            logging.info(f"🤔 [TEAM_MANAGER] {context.team_name} iteration {context.iteration_count}")
            
            # Process through team
            result = await team.process_stimuli_with_team(stimuli_data)
            
            if result.get("success"):
                # Extract insights
                insights = self._extract_insights(result)
                if insights:
                    context.recent_insights.append(insights)
                    
                    # Keep only recent insights
                    if len(context.recent_insights) > 10:
                        context.recent_insights = context.recent_insights[-10:]
                    
                    # Publish to SCB
                    if self.scb_writer:
                        await self._publish_team_insights(context, insights)
                    
                    # Check for cross-team collaboration opportunities
                    await self._check_collaboration_opportunities(context, insights)
                
                # Update focus based on results
                context.current_focus = self._determine_next_focus(context, result)
                
                logging.info(f"✅ [TEAM_MANAGER] {context.team_name} iteration completed")
                
            else:
                logging.warning(f"⚠️ [TEAM_MANAGER] {context.team_name} iteration failed")
                
        except Exception as e:
            logging.error(f"❌ [TEAM_MANAGER] Error in autonomous iteration: {e}")
    
    def _generate_autonomous_prompt(self, context: TeamExecutionContext) -> str:
        """Generate appropriate autonomous prompt based on character type"""
        
        prompts = {
            CharacterType.TRADER: [
                "Analyze current market conditions and identify trading opportunities",
                "Review portfolio performance and suggest optimization strategies",
                "Assess market risks and update risk management protocols",
                "Research emerging market trends and their potential impact"
            ],
            CharacterType.STREAMER: [
                "Analyze trending content and suggest new video ideas",
                "Review community engagement metrics and propose improvements",
                "Plan upcoming streaming schedule and content calendar",
                "Identify collaboration opportunities with other creators"
            ],
            CharacterType.TEACHER: [
                "Design new learning modules based on student progress data",
                "Analyze assessment results and identify knowledge gaps",
                "Create personalized learning paths for different student groups",
                "Research innovative teaching methods and technologies"
            ],
            CharacterType.DEFAULT: [
                "Analyze system performance and identify optimization opportunities",
                "Review recent learning patterns and synthesize insights",
                "Evaluate architectural improvements for enhanced capability",
                "Explore cross-domain knowledge integration possibilities"
            ]
        }
        
        # Get prompts for character type
        type_prompts = prompts.get(context.character_type, prompts[CharacterType.DEFAULT])
        
        # Select prompt based on iteration
        prompt_index = context.iteration_count % len(type_prompts)
        base_prompt = type_prompts[prompt_index]
        
        # Add context from recent insights
        if context.recent_insights:
            recent = context.recent_insights[-1]
            base_prompt += f"\n\nBuilding on recent insight: {recent.get('summary', '')}"
        
        # Add current focus if set
        if context.current_focus:
            base_prompt += f"\n\nCurrent focus area: {context.current_focus}"
        
        return base_prompt
    
    def _extract_insights(self, result: Dict[str, Any]) -> Dict[str, Any]:
        """Extract key insights from team processing result"""
        
        response_content = result.get("response_content", "")
        
        if not response_content:
            return {}
        
        # Extract key points (simplified - could use NLP in production)
        lines = response_content.split('\n')
        key_points = [line.strip('- •*') for line in lines if line.strip().startswith(('-', '•', '*'))]
        
        return {
            "timestamp": datetime.now().isoformat(),
            "summary": response_content[:200] + "..." if len(response_content) > 200 else response_content,
            "key_points": key_points[:3],  # Top 3 points
            "tools_used": result.get("tools_triggered", []),
            "confidence": 0.8  # Could be calculated based on team consensus
        }
    
    def _determine_next_focus(self, context: TeamExecutionContext, result: Dict[str, Any]) -> Optional[str]:
        """Determine next focus area based on results"""
        
        # Simple focus rotation for now
        focus_areas = {
            CharacterType.TRADER: ["market_analysis", "portfolio_optimization", "risk_management", "opportunity_research"],
            CharacterType.STREAMER: ["content_creation", "community_engagement", "growth_strategies", "monetization"],
            CharacterType.TEACHER: ["curriculum_design", "student_assessment", "learning_innovation", "progress_tracking"],
            CharacterType.DEFAULT: ["performance_optimization", "knowledge_synthesis", "architecture_evolution", "capability_enhancement"]
        }
        
        areas = focus_areas.get(context.character_type, focus_areas[CharacterType.DEFAULT])
        
        # Rotate through focus areas
        if context.current_focus:
            try:
                current_index = areas.index(context.current_focus)
                next_index = (current_index + 1) % len(areas)
                return areas[next_index]
            except ValueError:
                pass
        
        return areas[0]
    
    async def _publish_team_insights(self, context: TeamExecutionContext, insights: Dict[str, Any]):
        """Publish team insights to SCB channels and Neo4j"""
        
        # Store in Neo4j semantic graph
        if self.semantic_storage:
            try:
                # Determine semantic context based on team type
                context_map = {
                    CharacterType.TRADER: SemanticContext.TRADING,
                    CharacterType.STREAMER: SemanticContext.COMMUNICATION,
                    CharacterType.TEACHER: SemanticContext.LEARNING,
                    CharacterType.DEFAULT: SemanticContext.SYSTEM
                }
                
                semantic_context = context_map.get(context.character_type, SemanticContext.GENERAL)
                
                # Create semantic node for the insight
                await self.semantic_storage.add_semantic_node(
                    content=insights.get("summary", ""),
                    context=semantic_context,
                    node_type="team_insight",
                    metadata={
                        "team_type": context.character_type.value,
                        "team_name": context.team_name,
                        "iteration": context.iteration_count,
                        "focus": context.current_focus,
                        "key_points": insights.get("key_points", []),
                        "tools_used": insights.get("tools_used", []),
                        "confidence": insights.get("confidence", 0.8),
                        "collaboration_requested": False
                    },
                    initiating_agent=f"{context.team_name}_autonomous",
                    agent_category="autonomous_team",
                    agent_team=context.character_type.value
                )
                
                logging.debug(f"🌐 [TEAM_MANAGER] Stored insight in Neo4j for {context.team_name}")
                
            except Exception as e:
                logging.error(f"❌ [TEAM_MANAGER] Failed to store insight in Neo4j: {e}")
        
        if not self.scb_writer:
            return
        
        # Get SCB channels for team
        registry = get_character_team_registry()
        channels = registry.get_scb_channels(context.character_type)
        
        # Publish to team-specific channels
        for channel in channels:
            await self.scb_writer.publish_event(
                channel=channel,
                event_type="team_insight",
                data={
                    "team_name": context.team_name,
                    "character_id": context.character_id,
                    "iteration": context.iteration_count,
                    "insights": insights
                }
            )
        
        # Also publish to general insights channel
        await self.scb_writer.publish_event(
            channel="autonomous_insights",
            event_type="team_insight",
            data={
                "team_type": context.character_type.value,
                "team_name": context.team_name,
                "insights": insights
            }
        )
    
    async def _check_collaboration_opportunities(self, context: TeamExecutionContext, insights: Dict[str, Any]):
        """Check if insights suggest collaboration with other teams"""
        
        if not self.scb_coordinator:
            return
        
        # Define collaboration triggers based on team type
        collaboration_triggers = {
            CharacterType.TRADER: {
                "keywords": ["market crash", "volatility spike", "major trend"],
                "target_teams": ["streamer", "default"],
                "action": "market_alert"
            },
            CharacterType.STREAMER: {
                "keywords": ["viral", "trending", "collaboration"],
                "target_teams": ["teacher", "trader"],
                "action": "content_opportunity"
            },
            CharacterType.TEACHER: {
                "keywords": ["breakthrough", "new method", "learning pattern"],
                "target_teams": ["default", "streamer"],
                "action": "knowledge_sharing"
            },
            CharacterType.DEFAULT: {
                "keywords": ["optimization", "improvement", "evolution"],
                "target_teams": ["trader", "streamer", "teacher"],
                "action": "system_enhancement"
            }
        }
        
        triggers = collaboration_triggers.get(context.character_type, {})
        if not triggers:
            return
        
        # Check if any keywords are present in insights
        insight_text = insights.get("summary", "").lower()
        for keyword in triggers["keywords"]:
            if keyword in insight_text:
                # Share insight with relevant teams
                await self.scb_coordinator.share_cross_team_insight(
                    source_team=context.character_type.value,
                    insight=f"Important discovery: {insights.get('summary', '')}",
                    relevant_teams=triggers["target_teams"],
                    data={
                        "trigger": keyword,
                        "action_type": triggers["action"],
                        "insights": insights
                    }
                )
                
                logging.info(f"🤝 [TEAM_MANAGER] Shared cross-team insight triggered by '{keyword}'")
                
                # Store collaboration in Neo4j
                if self.semantic_storage:
                    try:
                        # Create collaboration node
                        collab_node = await self.semantic_storage.add_semantic_node(
                            content=f"Cross-team collaboration: {context.character_type.value} → {', '.join(triggers['target_teams'])}",
                            context=SemanticContext.COLLABORATION,
                            node_type="collaboration_request",
                            metadata={
                                "source_team": context.character_type.value,
                                "target_teams": triggers["target_teams"],
                                "trigger": keyword,
                                "action_type": triggers["action"],
                                "insight_summary": insights.get("summary", "")[:200]
                            },
                            initiating_agent=f"{context.team_name}_autonomous",
                            agent_category="autonomous_team",
                            agent_team=context.character_type.value
                        )
                        
                        logging.debug(f"🌐 [TEAM_MANAGER] Stored collaboration request in Neo4j")
                        
                    except Exception as e:
                        logging.error(f"❌ [TEAM_MANAGER] Failed to store collaboration in Neo4j: {e}")
                
                break
    
    async def pause_team(self, team_key: str):
        """Pause a specific team's execution"""
        
        if team_key in self.active_tasks:
            task = self.active_tasks[team_key]
            task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                pass
            del self.active_tasks[team_key]
        
        if team_key in self.execution_contexts:
            self.execution_contexts[team_key].status = TeamStatus.PAUSED
            
        logging.info(f"⏸️ [TEAM_MANAGER] Paused team: {team_key}")
    
    async def resume_team(self, team_key: str):
        """Resume a paused team's execution"""
        
        if team_key not in self.execution_contexts:
            return
        
        context = self.execution_contexts[team_key]
        if context.status == TeamStatus.PAUSED:
            context.status = TeamStatus.RUNNING
            
            # Start execution task
            task = asyncio.create_task(
                self._autonomous_execution_loop(team_key, context)
            )
            self.active_tasks[team_key] = task
            
            logging.info(f"▶️ [TEAM_MANAGER] Resumed team: {team_key}")
    
    async def stop_all(self):
        """Stop all autonomous teams"""
        
        self.running = False
        
        # Cancel all active tasks
        for team_key, task in self.active_tasks.items():
            task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                pass
        
        self.active_tasks.clear()
        
        # Update all contexts
        for context in self.execution_contexts.values():
            context.status = TeamStatus.IDLE
        
        logging.info("🛑 [TEAM_MANAGER] All autonomous teams stopped")
    
    def get_status(self) -> Dict[str, Any]:
        """Get current status of all teams"""
        
        team_status = {}
        
        for team_key, context in self.execution_contexts.items():
            team_status[team_key] = {
                "team_name": context.team_name,
                "character_id": context.character_id,
                "status": context.status.value,
                "iteration_count": context.iteration_count,
                "last_execution": context.last_execution.isoformat() if context.last_execution else None,
                "current_focus": context.current_focus,
                "recent_insights_count": len(context.recent_insights)
            }
        
        return {
            "running": self.running,
            "current_character": self.current_character_id,
            "active_teams": len(self.active_tasks),
            "teams": team_status
        }


# Global instance
_autonomous_team_manager: Optional[AutonomousTeamManager] = None


def get_autonomous_team_manager() -> Optional[AutonomousTeamManager]:
    """Get the global autonomous team manager instance"""
    return _autonomous_team_manager


async def initialize_autonomous_team_manager(
    tool_registry,
    scb_client=None,
    vtuber_client=None,
    execution_interval: int = 60
) -> AutonomousTeamManager:
    """Initialize and return the global autonomous team manager"""
    
    global _autonomous_team_manager
    
    if _autonomous_team_manager is None:
        _autonomous_team_manager = AutonomousTeamManager(
            tool_registry=tool_registry,
            scb_client=scb_client,
            vtuber_client=vtuber_client,
            execution_interval=execution_interval
        )
        
        if await _autonomous_team_manager.initialize():
            logging.info("✅ [TEAM_MANAGER] Global autonomous team manager initialized")
        else:
            logging.error("❌ [TEAM_MANAGER] Failed to initialize autonomous team manager")
            _autonomous_team_manager = None
    
    return _autonomous_team_manager