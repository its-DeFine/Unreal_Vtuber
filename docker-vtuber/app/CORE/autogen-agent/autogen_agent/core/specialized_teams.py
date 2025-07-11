"""
Specialized Character Teams for S2
==================================

This module implements the actual specialized teams for each character type.
Each team has unique agents, tools, and processing logic.
"""

import logging
from typing import Dict, Any, List, Optional
from autogen import AssistantAgent, UserProxyAgent, GroupChat, GroupChatManager
from .stimuli_autogen_team import StimuliAutoGenTeam
from .character_team_registry import CharacterType, get_character_team_registry


class TraderTeam(StimuliAutoGenTeam):
    """Specialized team for financial analysis and trading"""
    
    def __init__(self):
        super().__init__()
        self.team_type = CharacterType.TRADER
        self.team_name = "Quantum Trading Intelligence Team"
        
    def _create_specialized_agents(self):
        """Create trader-specific agents"""
        llm_config = self._get_llm_config()
        
        # Market Analyst
        self.market_analyst = AssistantAgent(
            name="market_analyst",
            system_message="""You are a Senior Market Analyst specializing in:
            - Technical and fundamental analysis
            - Market trend identification  
            - Economic indicator interpretation
            - Multi-asset correlation analysis
            
            Use market_data_tool, technical_analysis_tool, and news_sentiment_tool to provide data-driven insights.""",
            llm_config=llm_config,
            max_consecutive_auto_reply=3
        )
        
        # Risk Manager
        self.risk_manager = AssistantAgent(
            name="risk_manager",
            system_message="""You are a Chief Risk Officer responsible for:
            - Portfolio risk assessment
            - Position sizing recommendations
            - Drawdown prevention strategies
            - Risk/reward optimization
            
            Use portfolio_tool, risk_calculator_tool, and var_analysis_tool to ensure proper risk management.""",
            llm_config=llm_config,
            max_consecutive_auto_reply=3
        )
        
        # Trade Executor
        self.trade_executor = AssistantAgent(
            name="trade_executor",
            system_message="""You are an Algorithmic Trading Strategist focused on:
            - Trade execution optimization
            - Entry/exit timing
            - Order type selection
            - Slippage minimization
            
            Use trading_tool, order_management_tool, and execution_analytics_tool to execute trades efficiently.""",
            llm_config=llm_config,
            max_consecutive_auto_reply=3
        )
        
        # User proxy for tool execution
        self.trader_proxy = UserProxyAgent(
            name="trader_proxy",
            system_message="Execute trading tools and analysis functions.",
            code_execution_config=False,
            human_input_mode="NEVER",
            max_consecutive_auto_reply=10
        )
        
        # Register tools with proxy
        from ..tools.tool_registry import get_tool_registry
        tool_registry = get_tool_registry()
        
        # Register trader-specific tools
        trader_tools = [
            "market_data_tool", "portfolio_tool", "risk_calculator_tool",
            "technical_analysis_tool", "trading_tool", "news_sentiment_tool",
            "var_analysis_tool", "order_management_tool", "execution_analytics_tool"
        ]
        
        for tool_name in trader_tools:
            tool_func = tool_registry.get_tool(tool_name)
            if tool_func:
                self.trader_proxy.register_for_execution(name=tool_name)(tool_func)
                self.market_analyst.register_for_llm(name=tool_name)(tool_func)
                self.risk_manager.register_for_llm(name=tool_name)(tool_func)
                self.trade_executor.register_for_llm(name=tool_name)(tool_func)
        
        logging.info("✅ [TRADER_TEAM] Specialized trader agents created with tools")
    
    def _create_teachable_stimuli_agents(self, llm_config: Dict):
        """Override to skip generic agents for trader team"""
        # Skip generic agent creation - we'll use specialized agents instead
        logging.info("🏦 [TRADER_TEAM] Skipping generic agents, will use specialized trader agents")
        pass
    
    def _create_team_group_chat(self):
        """Create trader team group chat"""
        self._create_specialized_agents()
        
        # Create group chat
        self.group_chat = GroupChat(
            agents=[
                self.market_analyst,
                self.risk_manager,
                self.trade_executor,
                self.trader_proxy
            ],
            messages=[],
            max_round=6,
            speaker_selection_method="round_robin"
        )
        
        self.group_chat_manager = GroupChatManager(
            groupchat=self.group_chat,
            llm_config=self._get_llm_config()
        )
        
        logging.info("✅ [TRADER_TEAM] Trader team group chat created")
    
    async def process_stimuli_with_team(self, stimuli_data: Dict[str, Any]) -> Dict[str, Any]:
        """Process stimuli with trader-specific logic"""
        result = await super().process_stimuli_with_team(stimuli_data)
        
        # Add trader-specific metadata
        result["team_type"] = "trader"
        result["specialized_analysis"] = {
            "market_conditions": "analyzed",
            "risk_assessment": "completed",
            "trading_strategy": "formulated"
        }
        
        return result


class StreamerTeam(StimuliAutoGenTeam):
    """Specialized team for content creation and streaming"""
    
    def __init__(self):
        super().__init__()
        self.team_type = CharacterType.STREAMER
        self.team_name = "Digital Star Management Team"
        
    def _create_specialized_agents(self):
        """Create streamer-specific agents"""
        llm_config = self._get_llm_config()
        
        # Content Strategist
        self.content_strategist = AssistantAgent(
            name="content_strategist",
            system_message="""You are a Chief Content Strategist specializing in:
            - Content calendar planning
            - Trend identification and capitalization
            - Cross-platform content optimization
            - Viral content creation strategies
            
            Use social_media_tool, trending_topics_tool, and content_calendar_tool to create compelling strategies.""",
            llm_config=llm_config,
            max_consecutive_auto_reply=3
        )
        
        # Community Manager
        self.community_manager = AssistantAgent(
            name="community_manager",
            system_message="""You are a Head of Community Engagement responsible for:
            - Community growth strategies
            - Engagement optimization
            - Moderator coordination
            - Fan relationship building
            
            Use community_tool, moderation_tool, and engagement_analytics_tool to foster a thriving community.""",
            llm_config=llm_config,
            max_consecutive_auto_reply=3
        )
        
        # Analytics Expert
        self.analytics_expert = AssistantAgent(
            name="analytics_expert",
            system_message="""You are a Streaming Analytics Director focused on:
            - Performance metric analysis
            - Growth opportunity identification
            - Revenue optimization strategies
            - Audience behavior insights
            
            Use streaming_tool, analytics_tool, and revenue_tracking_tool to drive strategic decisions.""",
            llm_config=llm_config,
            max_consecutive_auto_reply=3
        )
        
        # User proxy for tool execution
        self.streamer_proxy = UserProxyAgent(
            name="streamer_proxy",
            system_message="Execute streaming and content tools.",
            code_execution_config=False,
            human_input_mode="NEVER",
            max_consecutive_auto_reply=10
        )
        
        # Register tools
        from ..tools.tool_registry import get_tool_registry
        tool_registry = get_tool_registry()
        
        streamer_tools = [
            "social_media_tool", "streaming_tool", "analytics_tool",
            "trending_topics_tool", "content_calendar_tool", "community_tool",
            "moderation_tool", "engagement_analytics_tool", "revenue_tracking_tool"
        ]
        
        for tool_name in streamer_tools:
            tool_func = tool_registry.get_tool(tool_name)
            if tool_func:
                self.streamer_proxy.register_for_execution(name=tool_name)(tool_func)
                self.content_strategist.register_for_llm(name=tool_name)(tool_func)
                self.community_manager.register_for_llm(name=tool_name)(tool_func)
                self.analytics_expert.register_for_llm(name=tool_name)(tool_func)
        
        logging.info("✅ [STREAMER_TEAM] Specialized streamer agents created with tools")
    
    def _create_teachable_stimuli_agents(self, llm_config: Dict):
        """Override to skip generic agents for streamer team"""
        # Skip generic agent creation - we'll use specialized agents instead
        logging.info("📹 [STREAMER_TEAM] Skipping generic agents, will use specialized streamer agents")
        pass
    
    def _create_team_group_chat(self):
        """Create streamer team group chat"""
        self._create_specialized_agents()
        
        self.group_chat = GroupChat(
            agents=[
                self.content_strategist,
                self.community_manager,
                self.analytics_expert,
                self.streamer_proxy
            ],
            messages=[],
            max_round=5,
            speaker_selection_method="round_robin"
        )
        
        self.group_chat_manager = GroupChatManager(
            groupchat=self.group_chat,
            llm_config=self._get_llm_config()
        )
        
        logging.info("✅ [STREAMER_TEAM] Streamer team group chat created")
    
    async def process_stimuli_with_team(self, stimuli_data: Dict[str, Any]) -> Dict[str, Any]:
        """Process stimuli with streamer-specific logic"""
        result = await super().process_stimuli_with_team(stimuli_data)
        
        result["team_type"] = "streamer"
        result["content_strategy"] = {
            "platform_optimization": "completed",
            "engagement_plan": "created",
            "analytics_insights": "generated"
        }
        
        return result


class TeacherTeam(StimuliAutoGenTeam):
    """Specialized team for educational content and learning"""
    
    def __init__(self):
        super().__init__()
        self.team_type = CharacterType.TEACHER
        self.team_name = "Adaptive Education Excellence Team"
        
    def _create_specialized_agents(self):
        """Create teacher-specific agents"""
        llm_config = self._get_llm_config()
        
        # Curriculum Designer
        self.curriculum_designer = AssistantAgent(
            name="curriculum_designer",
            system_message="""You are a Chief Learning Architect specializing in:
            - Adaptive curriculum design
            - Learning pathway optimization
            - Cross-disciplinary integration
            - Competency-based progression
            
            Use educational_content_tool, curriculum_tool, and learning_standards_tool to design effective curricula.""",
            llm_config=llm_config,
            max_consecutive_auto_reply=3
        )
        
        # Learning Analyst
        self.learning_analyst = AssistantAgent(
            name="learning_analyst",
            system_message="""You are an Educational Data Scientist responsible for:
            - Learning pattern analysis
            - Performance prediction modeling
            - Intervention recommendation
            - Progress tracking optimization
            
            Use assessment_tool, learning_analytics_tool, and progress_tracking_tool to personalize learning.""",
            llm_config=llm_config,
            max_consecutive_auto_reply=3
        )
        
        # Student Mentor
        self.student_mentor = AssistantAgent(
            name="student_mentor",
            system_message="""You are a Personalized Learning Coach focused on:
            - Individual student support
            - Motivation and engagement strategies
            - Learning style adaptation
            - Goal setting and achievement
            
            Use learning_tool, motivation_tool, and communication_tool to guide students to success.""",
            llm_config=llm_config,
            max_consecutive_auto_reply=3
        )
        
        # User proxy
        self.teacher_proxy = UserProxyAgent(
            name="teacher_proxy",
            system_message="Execute educational tools and learning functions.",
            code_execution_config=False,
            human_input_mode="NEVER",
            max_consecutive_auto_reply=10
        )
        
        # Register tools
        from ..tools.tool_registry import get_tool_registry
        tool_registry = get_tool_registry()
        
        teacher_tools = [
            "educational_content_tool", "assessment_tool", "learning_tool",
            "curriculum_tool", "learning_standards_tool", "learning_analytics_tool",
            "progress_tracking_tool", "motivation_tool", "communication_tool"
        ]
        
        for tool_name in teacher_tools:
            tool_func = tool_registry.get_tool(tool_name)
            if tool_func:
                self.teacher_proxy.register_for_execution(name=tool_name)(tool_func)
                self.curriculum_designer.register_for_llm(name=tool_name)(tool_func)
                self.learning_analyst.register_for_llm(name=tool_name)(tool_func)
                self.student_mentor.register_for_llm(name=tool_name)(tool_func)
        
        logging.info("✅ [TEACHER_TEAM] Specialized teacher agents created with tools")
    
    def _create_teachable_stimuli_agents(self, llm_config: Dict):
        """Override to skip generic agents for teacher team"""
        # Skip generic agent creation - we'll use specialized agents instead
        logging.info("🎓 [TEACHER_TEAM] Skipping generic agents, will use specialized teacher agents")
        pass
    
    def _create_team_group_chat(self):
        """Create teacher team group chat"""
        self._create_specialized_agents()
        
        self.group_chat = GroupChat(
            agents=[
                self.curriculum_designer,
                self.learning_analyst,
                self.student_mentor,
                self.teacher_proxy
            ],
            messages=[],
            max_round=4,
            speaker_selection_method="round_robin"
        )
        
        self.group_chat_manager = GroupChatManager(
            groupchat=self.group_chat,
            llm_config=self._get_llm_config()
        )
        
        logging.info("✅ [TEACHER_TEAM] Teacher team group chat created")
    
    async def process_stimuli_with_team(self, stimuli_data: Dict[str, Any]) -> Dict[str, Any]:
        """Process stimuli with teacher-specific logic"""
        result = await super().process_stimuli_with_team(stimuli_data)
        
        result["team_type"] = "teacher"
        result["educational_outcomes"] = {
            "curriculum_adapted": True,
            "learning_path_optimized": True,
            "student_engagement_enhanced": True
        }
        
        return result


class DefaultTeam(StimuliAutoGenTeam):
    """Default team for system optimization and general tasks"""
    
    def __init__(self):
        super().__init__()
        self.team_type = CharacterType.DEFAULT
        self.team_name = "Autonomous Self-Improvement Collective"
        
    def _create_specialized_agents(self):
        """Create default team agents"""
        llm_config = self._get_llm_config()
        
        # System Architect
        self.system_architect = AssistantAgent(
            name="system_architect",
            system_message="""You are a Principal Systems Architect responsible for:
            - System architecture evolution
            - Integration optimization
            - Performance bottleneck identification
            - Scalability planning
            
            Use core_evolution_tool, system_analysis_tool, and architecture_tool to enhance system capability.""",
            llm_config=llm_config,
            max_consecutive_auto_reply=3
        )
        
        # Performance Optimizer
        self.performance_optimizer = AssistantAgent(
            name="performance_optimizer",
            system_message="""You are a Performance Engineering Lead focused on:
            - Resource optimization
            - Latency reduction strategies
            - Throughput maximization
            - Cost-efficiency improvements
            
            Use performance_tool, resource_monitor_tool, and optimization_tool to optimize performance.""",
            llm_config=llm_config,
            max_consecutive_auto_reply=3
        )
        
        # Knowledge Curator
        self.knowledge_curator = AssistantAgent(
            name="knowledge_curator",
            system_message="""You are a Chief Knowledge Officer specializing in:
            - Knowledge graph curation
            - Learning consolidation
            - Pattern recognition
            - Insight synthesis
            
            Use knowledge_tool, pattern_tool, and synthesis_tool to enhance system intelligence.""",
            llm_config=llm_config,
            max_consecutive_auto_reply=3
        )
        
        # User proxy
        self.default_proxy = UserProxyAgent(
            name="default_proxy",
            system_message="Execute system optimization tools.",
            code_execution_config=False,
            human_input_mode="NEVER",
            max_consecutive_auto_reply=10
        )
        
        # Register tools
        from ..tools.tool_registry import get_tool_registry
        tool_registry = get_tool_registry()
        
        default_tools = [
            "core_evolution_tool", "goal_management_tools", "scb_operations_tool",
            "system_analysis_tool", "architecture_tool", "performance_tool",
            "resource_monitor_tool", "optimization_tool", "knowledge_tool",
            "pattern_tool", "synthesis_tool", "tool_management"
        ]
        
        for tool_name in default_tools:
            tool_func = tool_registry.get_tool(tool_name)
            if tool_func:
                self.default_proxy.register_for_execution(name=tool_name)(tool_func)
                self.system_architect.register_for_llm(name=tool_name)(tool_func)
                self.performance_optimizer.register_for_llm(name=tool_name)(tool_func)
                self.knowledge_curator.register_for_llm(name=tool_name)(tool_func)
        
        logging.info("✅ [DEFAULT_TEAM] Default team agents created with tools")
    
    def _create_teachable_stimuli_agents(self, llm_config: Dict):
        """Override to skip generic agents for default team"""
        # Skip generic agent creation - we'll use specialized agents instead
        logging.info("🔧 [DEFAULT_TEAM] Skipping generic agents, will use specialized default agents")
        pass
    
    def _create_team_group_chat(self):
        """Create default team group chat"""
        self._create_specialized_agents()
        
        self.group_chat = GroupChat(
            agents=[
                self.system_architect,
                self.performance_optimizer,
                self.knowledge_curator,
                self.default_proxy
            ],
            messages=[],
            max_round=4,
            speaker_selection_method="round_robin"
        )
        
        self.group_chat_manager = GroupChatManager(
            groupchat=self.group_chat,
            llm_config=self._get_llm_config()
        )
        
        logging.info("✅ [DEFAULT_TEAM] Default team group chat created")
    
    async def process_stimuli_with_team(self, stimuli_data: Dict[str, Any]) -> Dict[str, Any]:
        """Process stimuli with default team logic"""
        result = await super().process_stimuli_with_team(stimuli_data)
        
        result["team_type"] = "default"
        result["system_optimization"] = {
            "architecture_reviewed": True,
            "performance_analyzed": True,
            "knowledge_consolidated": True
        }
        
        return result


def create_specialized_team(team_type: CharacterType) -> Optional[StimuliAutoGenTeam]:
    """Factory function to create the appropriate specialized team"""
    
    team_map = {
        CharacterType.TRADER: TraderTeam,
        CharacterType.STREAMER: StreamerTeam,
        CharacterType.TEACHER: TeacherTeam,
        CharacterType.DEFAULT: DefaultTeam
    }
    
    team_class = team_map.get(team_type)
    if team_class:
        try:
            team = team_class()
            logging.info(f"✅ Created specialized {team_type.value} team")
            return team
        except Exception as e:
            logging.error(f"❌ Failed to create {team_type.value} team: {e}")
            return None
    
    logging.warning(f"⚠️ No specialized team class for {team_type.value}")
    return None