"""
Character-Team Registry and Configuration
========================================

This module defines the character-paired specialized team architecture.
Each character type has its own specialized AutoGen team with specific:
- Agent configurations
- Tool assignments
- Mission objectives
- Behavioral patterns
"""

import logging
from typing import Dict, Any, List, Optional
from dataclasses import dataclass, field
from enum import Enum


class CharacterType(Enum):
    """Supported character types with specialized teams"""
    TRADER = "trader"
    STREAMER = "streamer"
    TEACHER = "teacher"
    DEFAULT = "default"


@dataclass
class TeamAgentConfig:
    """Configuration for a single agent in a team"""
    name: str
    role: str
    system_message: str
    tools: List[str] = field(default_factory=list)
    max_consecutive_auto_reply: int = 3
    
    
@dataclass 
class CharacterTeamConfig:
    """Complete configuration for a character-specific team"""
    character_type: CharacterType
    team_name: str
    description: str
    mission: str
    agents: List[TeamAgentConfig]
    shared_tools: List[str] = field(default_factory=list)
    scb_channels: List[str] = field(default_factory=list)
    max_rounds: int = 4
    speaker_selection_method: str = "round_robin"


class CharacterTeamRegistry:
    """Registry of character-team configurations"""
    
    def __init__(self):
        self.team_configs: Dict[CharacterType, CharacterTeamConfig] = {}
        self._initialize_team_configs()
        
    def _initialize_team_configs(self):
        """Initialize all character-team configurations"""
        
        # TRADER TEAM CONFIGURATION
        trader_config = CharacterTeamConfig(
            character_type=CharacterType.TRADER,
            team_name="Quantum Trading Intelligence Team",
            description="Specialized team for market analysis, risk management, and trading strategies",
            mission="Analyze markets, manage portfolio risk, and execute optimal trading strategies",
            agents=[
                TeamAgentConfig(
                    name="market_analyst",
                    role="Senior Market Analyst",
                    system_message="""You are a Senior Market Analyst specializing in:
                    - Technical and fundamental analysis
                    - Market trend identification
                    - Economic indicator interpretation
                    - Multi-asset correlation analysis
                    
                    Provide data-driven insights and actionable market intelligence.""",
                    tools=["market_data_tool", "technical_analysis_tool", "news_sentiment_tool"]
                ),
                TeamAgentConfig(
                    name="risk_manager",
                    role="Chief Risk Officer",
                    system_message="""You are a Chief Risk Officer responsible for:
                    - Portfolio risk assessment
                    - Position sizing recommendations
                    - Drawdown prevention strategies
                    - Risk/reward optimization
                    
                    Ensure all trading decisions align with risk management principles.""",
                    tools=["portfolio_tool", "risk_calculator_tool", "var_analysis_tool"]
                ),
                TeamAgentConfig(
                    name="trade_executor",
                    role="Algorithmic Trading Strategist",
                    system_message="""You are an Algorithmic Trading Strategist focused on:
                    - Trade execution optimization
                    - Entry/exit timing
                    - Order type selection
                    - Slippage minimization
                    
                    Execute trades efficiently while minimizing market impact.""",
                    tools=["trading_tool", "order_management_tool", "execution_analytics_tool"]
                )
            ],
            shared_tools=["scb_operations_tool", "goal_management_tools"],
            scb_channels=["market_signals", "risk_alerts", "trade_execution"],
            max_rounds=6  # More rounds for complex market analysis
        )
        
        # STREAMER TEAM CONFIGURATION
        streamer_config = CharacterTeamConfig(
            character_type=CharacterType.STREAMER,
            team_name="Digital Star Management Team",
            description="Specialized team for content strategy, community engagement, and streaming success",
            mission="Maximize streaming impact through strategic content creation and community building",
            agents=[
                TeamAgentConfig(
                    name="content_strategist", 
                    role="Chief Content Strategist",
                    system_message="""You are a Chief Content Strategist specializing in:
                    - Content calendar planning
                    - Trend identification and capitalization
                    - Cross-platform content optimization
                    - Viral content creation strategies
                    
                    Create compelling content strategies that drive engagement.""",
                    tools=["social_media_tool", "trending_topics_tool", "content_calendar_tool"]
                ),
                TeamAgentConfig(
                    name="community_manager",
                    role="Head of Community Engagement", 
                    system_message="""You are a Head of Community Engagement responsible for:
                    - Community growth strategies
                    - Engagement optimization
                    - Moderator coordination
                    - Fan relationship building
                    
                    Foster a thriving, positive community across all platforms.""",
                    tools=["community_tool", "moderation_tool", "engagement_analytics_tool"]
                ),
                TeamAgentConfig(
                    name="analytics_expert",
                    role="Streaming Analytics Director",
                    system_message="""You are a Streaming Analytics Director focused on:
                    - Performance metric analysis
                    - Growth opportunity identification
                    - Revenue optimization strategies
                    - Audience behavior insights
                    
                    Use data to drive strategic decisions and growth.""",
                    tools=["streaming_tool", "analytics_tool", "revenue_tracking_tool"]
                )
            ],
            shared_tools=["scb_operations_tool", "goal_management_tools"],
            scb_channels=["content_updates", "community_insights", "performance_metrics"],
            max_rounds=5
        )
        
        # TEACHER TEAM CONFIGURATION
        teacher_config = CharacterTeamConfig(
            character_type=CharacterType.TEACHER,
            team_name="Adaptive Education Excellence Team",
            description="Specialized team for curriculum design, personalized learning, and educational innovation",
            mission="Transform education through adaptive learning and evidence-based teaching strategies",
            agents=[
                TeamAgentConfig(
                    name="curriculum_designer",
                    role="Chief Learning Architect",
                    system_message="""You are a Chief Learning Architect specializing in:
                    - Adaptive curriculum design
                    - Learning pathway optimization
                    - Cross-disciplinary integration
                    - Competency-based progression
                    
                    Design curricula that maximize learning outcomes for diverse learners.""",
                    tools=["educational_content_tool", "curriculum_tool", "learning_standards_tool"]
                ),
                TeamAgentConfig(
                    name="learning_analyst",
                    role="Educational Data Scientist",
                    system_message="""You are an Educational Data Scientist responsible for:
                    - Learning pattern analysis
                    - Performance prediction modeling
                    - Intervention recommendation
                    - Progress tracking optimization
                    
                    Use data to personalize and improve learning experiences.""",
                    tools=["assessment_tool", "learning_analytics_tool", "progress_tracking_tool"]
                ),
                TeamAgentConfig(
                    name="student_mentor",
                    role="Personalized Learning Coach",
                    system_message="""You are a Personalized Learning Coach focused on:
                    - Individual student support
                    - Motivation and engagement strategies
                    - Learning style adaptation
                    - Goal setting and achievement
                    
                    Provide personalized guidance to help each student succeed.""",
                    tools=["learning_tool", "motivation_tool", "communication_tool"]
                )
            ],
            shared_tools=["scb_operations_tool", "goal_management_tools"],
            scb_channels=["curriculum_updates", "student_progress", "learning_insights"],
            max_rounds=4
        )
        
        # DEFAULT/SELF-IMPROVEMENT TEAM CONFIGURATION
        default_config = CharacterTeamConfig(
            character_type=CharacterType.DEFAULT,
            team_name="Autonomous Self-Improvement Collective",
            description="Meta-team focused on continuous system evolution and optimization",
            mission="Continuously evolve, optimize, and enhance the entire system architecture",
            agents=[
                TeamAgentConfig(
                    name="system_architect",
                    role="Principal Systems Architect",
                    system_message="""You are a Principal Systems Architect responsible for:
                    - System architecture evolution
                    - Integration optimization
                    - Performance bottleneck identification
                    - Scalability planning
                    
                    Design and implement system improvements that enhance overall capability.""",
                    tools=["core_evolution_tool", "system_analysis_tool", "architecture_tool"]
                ),
                TeamAgentConfig(
                    name="performance_optimizer",
                    role="Performance Engineering Lead",
                    system_message="""You are a Performance Engineering Lead focused on:
                    - Resource optimization
                    - Latency reduction strategies
                    - Throughput maximization
                    - Cost-efficiency improvements
                    
                    Optimize system performance across all dimensions.""",
                    tools=["performance_tool", "resource_monitor_tool", "optimization_tool"]
                ),
                TeamAgentConfig(
                    name="knowledge_curator",
                    role="Chief Knowledge Officer",
                    system_message="""You are a Chief Knowledge Officer specializing in:
                    - Knowledge graph curation
                    - Learning consolidation
                    - Pattern recognition
                    - Insight synthesis
                    
                    Curate and synthesize knowledge to enhance system intelligence.""",
                    tools=["knowledge_tool", "pattern_tool", "synthesis_tool"]
                )
            ],
            shared_tools=["scb_operations_tool", "goal_management_tools", "tool_management"],
            scb_channels=["system_updates", "performance_metrics", "knowledge_insights"],
            max_rounds=4
        )
        
        # Register all configurations
        self.team_configs[CharacterType.TRADER] = trader_config
        self.team_configs[CharacterType.STREAMER] = streamer_config
        self.team_configs[CharacterType.TEACHER] = teacher_config
        self.team_configs[CharacterType.DEFAULT] = default_config
        
        logging.info(f"✅ [TEAM_REGISTRY] Initialized {len(self.team_configs)} character team configurations")
    
    def get_team_config(self, character_type: CharacterType) -> Optional[CharacterTeamConfig]:
        """Get team configuration for a character type"""
        return self.team_configs.get(character_type)
    
    def get_team_config_by_character_id(self, character_id: str) -> Optional[CharacterTeamConfig]:
        """Get team configuration based on character ID"""
        
        # Map character IDs to character types
        # Updated to match our actual character files
        character_mapping = {
            # Trader characters (mapped to doctor personas for analytical/diagnostic roles)
            "dr._house_doctor_template": CharacterType.TRADER,
            "dr._martinez_doctor_template": CharacterType.TRADER,
            "doctor": CharacterType.TRADER,
            "dr_house": CharacterType.TRADER,
            "dr_martinez": CharacterType.TRADER,
            
            # Streamer characters (mapped to coach/weatherman for engagement/communication roles)
            "weatherman_template": CharacterType.STREAMER,
            "testbot_coach_template": CharacterType.STREAMER,
            "coach": CharacterType.STREAMER,
            "weatherman": CharacterType.STREAMER,
            "testbot": CharacterType.STREAMER,
            
            # Teacher characters
            "emma_teacher_template": CharacterType.TEACHER,
            "professor_smith_teacher_template": CharacterType.TEACHER,
            "teacher": CharacterType.TEACHER,
            "professor": CharacterType.TEACHER,
            "emma": CharacterType.TEACHER,
            "professor_smith": CharacterType.TEACHER,
            
            # Default/Self-improvement (secretary template)
            "secretary_template": CharacterType.DEFAULT,
            "secretary": CharacterType.DEFAULT,
            "assistant": CharacterType.DEFAULT,
            "default_template": CharacterType.DEFAULT,
            "self_improvement_template": CharacterType.DEFAULT,
            "autonomous_template": CharacterType.DEFAULT
        }
        
        # Get character type from mapping
        character_type = character_mapping.get(character_id, CharacterType.DEFAULT)
        
        return self.get_team_config(character_type)
    
    def get_all_team_names(self) -> List[str]:
        """Get all registered team names"""
        return [config.team_name for config in self.team_configs.values()]
    
    def get_team_tools(self, character_type: CharacterType) -> List[str]:
        """Get all tools (agent-specific and shared) for a team"""
        
        config = self.get_team_config(character_type)
        if not config:
            return []
        
        # Collect all tools
        all_tools = set(config.shared_tools)
        
        for agent in config.agents:
            all_tools.update(agent.tools)
        
        return list(all_tools)
    
    def get_scb_channels(self, character_type: CharacterType) -> List[str]:
        """Get SCB channels for a team"""
        
        config = self.get_team_config(character_type)
        return config.scb_channels if config else []


# Global registry instance
_character_team_registry: Optional[CharacterTeamRegistry] = None


def get_character_team_registry() -> CharacterTeamRegistry:
    """Get the global character team registry"""
    global _character_team_registry
    
    if _character_team_registry is None:
        _character_team_registry = CharacterTeamRegistry()
    
    return _character_team_registry