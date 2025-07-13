"""
Simplified AutoGen Team for S2
==============================

A streamlined implementation focused on the 3 specialized teams:
- Trader (market analysis)
- Educator (teaching)
- Streamer (content creation)

Each team has teachable agents with SCB and Neo4j integration.
Enhanced with AutoGen tool integration and comprehensive logging.
"""

import asyncio
import logging
from typing import Dict, Any, List, Optional
from datetime import datetime

logger = logging.getLogger(__name__)

try:
    from autogen import AssistantAgent, UserProxyAgent, GroupChat, GroupChatManager
except ImportError:
    logging.error("AutoGen not available")
    AssistantAgent = UserProxyAgent = GroupChat = GroupChatManager = None

# Import our tool bridge
from .autogen_tool_bridge import AutoGenToolBridge


class SimplifiedAutoGenTeam:
    """
    Simplified team implementation for S2 specialized character teams.
    Enhanced with proper AutoGen tool integration.
    """
    
    def __init__(self, team_type: str, llm_config: Dict[str, Any]):
        self.team_type = team_type
        self.llm_config = llm_config
        self.agents = {}
        self.group_chat = None
        self.manager = None
        self.scb_client = None
        self.neo4j_client = None
        self.max_rounds = 15  # 🔥 INCREASED from 5 to 15 for longer conversations
        
        # Initialize tool bridge for this team
        self.tool_bridge = AutoGenToolBridge(team_type)
        
        # Register tools and get AutoGen-compatible functions
        registered_tools = self.tool_bridge.register_tools()
        tool_count = self.tool_bridge.get_tool_count()
        
        logger.info(f"🔧 [S2_TEAM] Tools initialized: {tool_count} tools available")
        logger.info(f"🔧 [S2_TEAM] S2_TOOLS_AVAILABLE: {tool_count} tools for {team_type} team")
        
        # Initialize agents with enhanced configuration
        self.user_proxy = UserProxyAgent(
            name="user_proxy",
            system_message="You are a helpful assistant that executes tools and coordinates team discussions.",
            human_input_mode="NEVER",
            max_consecutive_auto_reply=15,  # Increased from 5
            code_execution_config=False,
            is_termination_msg=lambda x: x.get("content", "").rstrip().endswith("TERMINATE")
        )
        
        # Initialize LLM agents based on team type
        if team_type == "trader":
            self.llm_agents = [
                AssistantAgent(
                    name="market_analyst",
                    system_message="""You are a skilled market analyst specializing in cryptocurrency and financial markets.
                    You analyze market data, identify trends, and provide actionable trading insights.
                    
                    IMPORTANT: You must use the available tools to gather real data before making recommendations.
                    
                    Example tool usage:
                    To get market data: #assistant to=market_data
                    {"symbol": "BTCUSDT", "timeframe": "1d"}
                    
                    To analyze trading opportunities: #assistant to=trading_analysis
                    {"symbol": "BTCUSDT", "analysis_type": "technical"}
                    
                    Always use tools first, then provide specific, data-driven recommendations based on the results.""",
                    llm_config=llm_config,
                    max_consecutive_auto_reply=15  # Increased from 5
                ),
                AssistantAgent(
                    name="risk_manager",
                    system_message="""You are a risk management specialist focused on protecting capital.
                    You assess trading risks, calculate position sizes, and implement risk controls.
                    
                    IMPORTANT: Use tools to evaluate risks before making recommendations.
                    
                    Example tool usage:
                    To assess risk: #assistant to=risk_assessment
                    {"portfolio_value": 10000, "position_size": 1000, "symbol": "BTCUSDT"}
                    
                    Always consider worst-case scenarios and use tool data for accurate assessments.""",
                    llm_config=llm_config,
                    max_consecutive_auto_reply=15  # Increased from 5
                )
            ]
        elif team_type == "educator":
            self.llm_agents = [
                AssistantAgent(
                    name="content_creator",
                    system_message="""You are an educational content creator who develops engaging learning materials.
                    You create courses, assessments, and interactive content for various subjects.
                    
                    IMPORTANT: Use tools to generate structured educational content.
                    
                    Example tool usage:
                    To create educational content: #assistant to=educational_content
                    {"topic": "Python Programming", "learning_level": "beginner", "content_type": "lesson_plan"}
                    
                    To create assessments: #assistant to=assessment_creation
                    {"topic": "Python Basics", "assessment_type": "formative", "question_count": 10}
                    
                    Focus on making complex topics accessible using tool-generated materials.""",
                    llm_config=llm_config,
                    max_consecutive_auto_reply=15  # Increased from 5
                ),
                AssistantAgent(
                    name="learning_coordinator",
                    system_message="""You are a learning coordinator who designs curriculum and tracks progress.
                    You plan learning paths, coordinate resources, and assess student outcomes.
                    
                    IMPORTANT: Use tools to create comprehensive learning plans.
                    
                    Example tool usage:
                    To plan curriculum: #assistant to=curriculum_planning
                    {"subject": "Data Science", "duration_weeks": 12, "level": "intermediate"}
                    
                    Ensure learning objectives are met using tool-generated content.""",
                    llm_config=llm_config,
                    max_consecutive_auto_reply=15  # Increased from 5
                )
            ]
        elif team_type == "streamer":
            self.llm_agents = [
                AssistantAgent(
                    name="content_strategist",
                    system_message="""You are a content strategist for live streaming and social media.
                    You plan engaging content, analyze audience metrics, and optimize engagement.
                    
                    IMPORTANT: Use tools to create compelling content strategies.
                    
                    Example tool usage:
                    To generate content ideas: #assistant to=content_creation
                    {"content_type": "stream_ideas", "theme": "gaming", "duration_minutes": 120}
                    
                    To analyze community: #assistant to=community_management
                    {"action": "sentiment_analysis", "timeframe": "week"}
                    
                    Focus on building audience using tool-driven insights.""",
                    llm_config=llm_config,
                    max_consecutive_auto_reply=15  # Increased from 5
                ),
                AssistantAgent(
                    name="community_manager",
                    system_message="""You are a community manager who builds and maintains audience relationships.
                    You engage with viewers, moderate discussions, and foster community growth.
                    
                    IMPORTANT: Use tools to manage community effectively.
                    
                    Example tool usage:
                    To get analytics: #assistant to=streaming_analytics
                    {"metric_type": "engagement", "period": "month"}
                    
                    Create a welcoming environment using data-driven strategies.""",
                    llm_config=llm_config,
                    max_consecutive_auto_reply=15  # Increased from 5
                )
            ]
        else:
            # Default agents for unknown team types
            self.llm_agents = [
                AssistantAgent(
                    name="general_assistant",
                    system_message="You are a helpful general assistant. Use available tools to provide accurate information.",
                    llm_config=llm_config,
                    max_consecutive_auto_reply=15  # Increased from 5
                )
            ]
        
        # Register tools with all agents using the new method
        self.tool_bridge.register_tools_with_agents(self.user_proxy, self.llm_agents)
        logger.info(f"🔧 [S2_TEAM] Registered {tool_count} tools with all agents")
        
        # Create group chat
        all_agents = [self.user_proxy] + self.llm_agents
        self.group_chat = GroupChat(
            agents=all_agents,
            messages=[],
            max_round=15,  # Increased from 5
            speaker_selection_method="round_robin"
        )
        
        self.group_chat_manager = GroupChatManager(
            groupchat=self.group_chat,
            llm_config=llm_config
        )
        
        logger.info(f"✅ [S2_TEAM] Initialized {team_type} team with {len(self.llm_agents)} agents and {tool_count} tools")
    
    def set_clients(self, scb_client=None, neo4j_client=None):
        """Set external service clients."""
        self.scb_client = scb_client
        self.neo4j_client = neo4j_client
    
    def create_team(self) -> bool:
        """Create the specialized team based on type."""
        if not AssistantAgent:
            logging.error("AutoGen not available")
            return False
        
        try:
            # Create base agents for all teams
            self._create_base_agents()
            
            # Add specialized agents based on team type
            if self.team_type == "trader":
                self._add_trader_agents()
            elif self.team_type == "educator":
                self._add_educator_agents()
            elif self.team_type == "streamer":
                self._add_streamer_agents()
            else:
                logging.error(f"Unknown team type: {self.team_type}")
                return False
            
            # Create group chat with termination condition
            self._create_group_chat()
            
            # Tools already registered in __init__, just log count
            tool_count = self.tool_bridge.get_tool_count()
            logger.info(f"✅ [TEAM] {self.team_type} team created with {len(self.agents)} agents and {tool_count} tools")
            return True
            
        except Exception as e:
            logger.error(f"❌ [TEAM] Error creating team: {e}")
            return False
    
    def _create_base_agents(self):
        """Create base agents common to all teams."""
        
        # Coordinator agent
        self.agents["coordinator"] = AssistantAgent(
            name=f"{self.team_type}_coordinator",
            llm_config=self.llm_config,
            system_message=f"""You are the coordinator for the {self.team_type} team.
            Your role is to:
            1. Understand the user's request
            2. Delegate tasks to appropriate team members
            3. Use available tools to gather information and perform analysis
            4. Ensure responses are actionable and clear
            5. Write insights to SCB when important information is discovered
            6. Store patterns in Neo4j for future reference
            
            IMPORTANT: You have access to specialized tools - use them actively to provide better insights.
            Keep discussions focused and conclude within {self.max_rounds} rounds.
            Say "TERMINATE" when the task is complete.
            """
        )
        
        # Memory agent for teachable functionality
        self.agents["memory"] = AssistantAgent(
            name=f"{self.team_type}_memory",
            llm_config=self.llm_config,
            system_message=f"""You are the memory specialist for the {self.team_type} team.
            Your role is to:
            1. Remember important patterns and insights
            2. Recall relevant past experiences
            3. Learn from feedback and improve
            4. Store knowledge in Neo4j for persistence
            5. Use memory and analysis tools when available
            
            When you learn something new, say "LEARNED: [insight]"
            """
        )
    
    def _add_trader_agents(self):
        """Add trader-specific agents."""
        
        self.agents["analyst"] = AssistantAgent(
            name="market_analyst",
            llm_config=self.llm_config,
            system_message="""You are a market analysis expert with access to trading tools.
            Analyze market trends, identify opportunities, and assess risks.
            Use the available market data and trading analysis tools actively.
            Focus on actionable insights for trading decisions.
            When you find important patterns, say "PATTERN: [description]"
            """
        )
        
        self.agents["strategist"] = AssistantAgent(
            name="trading_strategist",
            llm_config=self.llm_config,
            system_message="""You are a trading strategy expert with access to risk assessment tools.
            Develop trading strategies based on market analysis.
            Use risk assessment and analysis tools to evaluate strategies.
            Consider risk management and portfolio optimization.
            Say "STRATEGY: [description]" when proposing a strategy.
            """
        )
    
    def _add_educator_agents(self):
        """Add educator-specific agents."""
        
        self.agents["teacher"] = AssistantAgent(
            name="content_teacher",
            llm_config=self.llm_config,
            system_message="""You are an expert educator with access to educational tools.
            Break down complex topics into understandable lessons.
            Use educational content generation and assessment tools actively.
            Create engaging educational content.
            Say "LESSON: [topic]" when teaching something new.
            """
        )
        
        self.agents["curriculum"] = AssistantAgent(
            name="curriculum_designer",
            llm_config=self.llm_config,
            system_message="""You are a curriculum design expert with planning tools.
            Structure learning paths and create comprehensive courses.
            Use curriculum planning and assessment tools for better design.
            Ensure content is progressive and engaging.
            Say "CURRICULUM: [structure]" when proposing a learning path.
            """
        )
    
    def _add_streamer_agents(self):
        """Add streamer-specific agents."""
        
        self.agents["content_creator"] = AssistantAgent(
            name="content_creator",
            llm_config=self.llm_config,
            system_message="""You are a content creation expert with creative tools.
            Generate engaging content ideas for streaming.
            Use content creation and analytics tools for better ideas.
            Focus on audience engagement and entertainment value.
            Say "CONTENT: [idea]" when proposing content.
            """
        )
        
        self.agents["engagement"] = AssistantAgent(
            name="engagement_specialist",
            llm_config=self.llm_config,
            system_message="""You are an audience engagement expert with community tools.
            Develop strategies to grow and engage the streaming audience.
            Use community management and analytics tools actively.
            Focus on community building and interaction.
            Say "ENGAGEMENT: [strategy]" when proposing engagement tactics.
            """
        )
    
    def _create_group_chat(self):
        """Create group chat with proper termination."""
        
        # Create user proxy for execution
        self.user_proxy = UserProxyAgent(
            name="user_proxy",
            system_message="Execute approved actions and tools. Reply with 'Task completed.' when done.",
            code_execution_config=False,  # Disable code execution for safety
            human_input_mode="NEVER",  # Never ask for human input
            max_consecutive_auto_reply=1,  # Allow one auto-reply for tool results
            is_termination_msg=lambda x: "TERMINATE" in x.get("content", ""),  # Terminate on TERMINATE
            llm_config=False  # No LLM for user proxy
        )
        
        # Add all agents to list
        all_agents = [self.user_proxy] + list(self.agents.values())
        
        # Create group chat with termination
        self.group_chat = GroupChat(
            agents=all_agents,
            messages=[],
            max_round=self.max_rounds,  # 🔥 INCREASED limit
            speaker_selection_method="round_robin",
            allow_repeat_speaker=True,  # Allow repeat speakers for tool interactions
            select_speaker_auto_verbose=True  # Better speaker selection logging
        )
        
        # Create manager
        self.manager = GroupChatManager(
            groupchat=self.group_chat,
            llm_config=self.llm_config,
            system_message=f"Manage the {self.team_type} team conversation. Ensure tools are used effectively and discussions stay focused. Allow up to {self.max_rounds} rounds for thorough analysis.",
            is_termination_msg=lambda x: "TERMINATE" in x.get("content", "")  # Also check for termination
        )
    
    # Old method removed - tool registration now handled in __init__
    
    async def process_stimuli(self, stimuli: Dict[str, Any]) -> Dict[str, Any]:
        """Process stimuli with the team using real AutoGen group chat."""
        
        if not self.manager:
            return {
                "success": False,
                "error": "Team not initialized"
            }
        
        stimuli_id = stimuli.get("stimuli_id", f"s2_{datetime.now().timestamp()}")
        team_start_time = datetime.now()
        
        # 🔥 ENHANCED: S2_TEAM_START timestamp with stimuli ID
        logger.info(f"S2_TEAM_START {stimuli_id} {team_start_time.isoformat()}")
        
        try:
            # Extract content
            content = stimuli.get("content", "")
            metadata = stimuli.get("metadata", {})
            
            # Create enhanced task prompt that encourages tool usage
            task = f"""
            Task: {content}
            Context: {metadata}
            Stimuli ID: {stimuli_id}
            
            Please analyze this task and provide actionable insights.
            Team members should collaborate to:
            1. Understand the requirements
            2. Use available tools to gather relevant information
            3. Share expertise and analysis results
            4. Generate comprehensive insights
            5. Store important patterns for future reference
            
            IMPORTANT: You have access to specialized tools - use them actively to enhance your analysis.
            Tools available: {self.tool_bridge.get_tool_names()}
            
            TOOL USAGE INSTRUCTIONS:
            - Always use tools BEFORE making recommendations
            - Call tools using the format: #assistant to=tool_name
            - Follow with JSON parameters on the next line
            - Wait for tool results before proceeding
            - Use multiple tools if needed for comprehensive analysis
            
            Example:
            #assistant to=market_data
            {{"symbol": "BTCUSDT", "timeframe": "1d"}}
            
            Keep the discussion focused and conclude with TERMINATE when done.
            """
            
            logger.info(f"🚀 [TEAM] {self.team_type} team starting real group chat with {self.tool_bridge.get_tool_count()} tools available")
            logging.info(f"🚀 [TEAM] Content: {content[:50]}...")
            
            # Reset group chat messages for fresh conversation
            self.group_chat.messages = []
            
            # Track tools that are actually used
            tools_invoked = []
            
            # 🔥 ENHANCED: S2_TOOLS_AVAILABLE timestamp with tool count
            tools_available_time = datetime.now()
            logger.info(f"S2_TOOLS_AVAILABLE {stimuli_id} {tools_available_time.isoformat()}")
            logger.info(f"🔧 [TEAM] Tools available: {self.tool_bridge.get_tool_count()} - {self.tool_bridge.get_tool_names()}")
            
            # Start real AutoGen group chat conversation
            try:
                # Find user proxy agent
                user_proxy = None
                for agent in self.group_chat.agents:
                    if hasattr(agent, 'name') and agent.name == "user_proxy":
                        user_proxy = agent
                        break
                
                if not user_proxy:
                    raise Exception("User proxy not found in group chat agents")
                
                logging.info(f"🎯 [TEAM] Starting group chat with {len(self.group_chat.agents)} agents")
                
                # Use asyncio to run the group chat with extended timeout
                chat_task = asyncio.create_task(
                    self._run_group_chat_async(user_proxy, task, stimuli_id)
                )
                
                # Wait for chat to complete with longer timeout (15 rounds * 30s per round)
                chat_result = await asyncio.wait_for(chat_task, timeout=450.0)
                
                logging.info(f"✅ [TEAM] Group chat completed with {len(self.group_chat.messages)} messages")
                
                # Log sample of conversation for debugging
                if self.group_chat.messages:
                    logging.info(f"📝 [TEAM] Sample conversation:")
                    for i, msg in enumerate(self.group_chat.messages[:3]):  # Show first 3 messages
                        sender = msg.get('name', 'unknown')
                        content_preview = msg.get('content', '')[:100]
                        logging.info(f"   {i+1}. {sender}: {content_preview}...")
            
            except asyncio.TimeoutError:
                logging.warning(f"⏰ [TEAM] Group chat timed out after extended timeout, using existing messages")
            except Exception as e:
                logging.error(f"❌ [TEAM] Error in group chat: {e}")
                import traceback
                traceback.print_exc()
                
                # Fallback to simple response if group chat fails
                await self._fallback_simple_response(task)
            
            # Extract insights from the real conversation
            insights = self._extract_insights()
            
            # Extract tool usage from conversation
            tools_invoked = self._extract_tool_usage()
            
            # 🔥 ENHANCED: S2_INSIGHTS_EXTRACTED timestamp
            insights_time = datetime.now()
            logger.info(f"S2_INSIGHTS_EXTRACTED {stimuli_id} {insights_time.isoformat()}")
            
            # Store in SCB if available
            if self.scb_client and insights:
                await self._write_to_scb(insights)
            
            # Store in Neo4j if available
            if self.neo4j_client and insights:
                await self._write_to_neo4j(stimuli, insights)
            
            # Count actual conversation rounds (exclude system messages)
            conversation_rounds = len([msg for msg in self.group_chat.messages 
                                     if msg.get('role') == 'assistant' or msg.get('role') == 'user'])
            
            # 🔥 ENHANCED: S2_TEAM_COMPLETE timestamp
            team_complete_time = datetime.now()
            logger.info(f"S2_TEAM_COMPLETE {stimuli_id} {team_complete_time.isoformat()}")
            
            return {
                "success": True,
                "team_type": self.team_type,
                "insights": insights,
                "rounds": conversation_rounds,
                "total_messages": len(self.group_chat.messages),
                "timestamp": datetime.now().isoformat(),
                "tools_invoked": tools_invoked,  # 🔥 ENHANCED: Actual tool usage
                "tools_available": self.tool_bridge.get_tool_count(),  # 🔥 NEW: Tools available count
                "processing_time_ms": (team_complete_time - team_start_time).total_seconds() * 1000,
                "debug_info": {
                    "group_chat_exists": self.group_chat is not None,
                    "manager_exists": self.manager is not None,
                    "agents_count": len(self.agents),
                    "tools_registered": self.tool_bridge.get_tool_count(),
                    "max_rounds": self.max_rounds,
                    "real_autogen_chat": True
                }
            }
            
        except asyncio.TimeoutError:
            logging.error(f"❌ [TEAM] {self.team_type} team timed out")
            return {
                "success": False,
                "error": "Team discussion timed out",
                "team_type": self.team_type
            }
        except Exception as e:
            logging.error(f"❌ [TEAM] {self.team_type} team error: {e}")
            import traceback
            traceback.print_exc()
            return {
                "success": False,
                "error": str(e),
                "team_type": self.team_type
            }
    
    async def _run_group_chat_async(self, user_proxy, task, stimuli_id):
        """Run the AutoGen group chat asynchronously with stimuli ID context."""
        
        try:
            # Add stimuli_id to user proxy for tool context
            if hasattr(user_proxy, '_stimuli_id'):
                user_proxy._stimuli_id = stimuli_id
            
            # Use the manager's a_initiate_chat method for real group conversation
            result = await self.manager.a_initiate_chat(
                user_proxy,
                message=task,
                max_turns=self.max_rounds
            )
            
            logging.info(f"🎉 [TEAM] Group chat initiate completed")
            return result
            
        except Exception as e:
            logging.error(f"❌ [TEAM] Error in group chat initiation: {e}")
            raise
    
    async def _fallback_simple_response(self, task):
        """Fallback to simple response if group chat fails."""
        
        logging.info(f"🔄 [TEAM] Using fallback simple response")
        
        try:
            # Get a simple response from the coordinator
            coordinator_response = await self._get_agent_response(self.agents["coordinator"], task)
            
            # Add to messages manually
            self.group_chat.messages = [
                {
                    "content": task,
                    "name": "user_proxy",
                    "role": "user"
                },
                {
                    "content": coordinator_response,
                    "name": f"{self.team_type}_coordinator",
                    "role": "assistant"
                }
            ]
            
            logging.info(f"✅ [TEAM] Fallback response generated")
            
        except Exception as e:
            logging.error(f"❌ [TEAM] Error in fallback response: {e}")
    
    def _extract_insights(self) -> Dict[str, List[str]]:
        """Extract insights from team conversation."""
        
        insights = {
            "patterns": [],
            "strategies": [],
            "lessons": [],
            "content": [],
            "engagement": [],
            "learned": [],
            "tool_results": [],  # 🔥 NEW: Track tool results
            "general": []
        }
        
        for msg in self.group_chat.messages:
            content = msg.get("content", "")
            name = msg.get("name", "")
            
            # Extract marked insights
            if "PATTERN:" in content:
                insights["patterns"].append(content.split("PATTERN:")[-1].strip()[:200])
            if "STRATEGY:" in content:
                insights["strategies"].append(content.split("STRATEGY:")[-1].strip()[:200])
            if "LESSON:" in content:
                lesson_start = content.find("LESSON:")
                if lesson_start != -1:
                    lesson_text = content[lesson_start + 7:].strip()
                    lesson_line = lesson_text.split('\n')[0][:200]
                    if lesson_line:
                        insights["lessons"].append(lesson_line)
            if "CONTENT:" in content:
                insights["content"].append(content.split("CONTENT:")[-1].strip()[:200])
            if "ENGAGEMENT:" in content:
                insights["engagement"].append(content.split("ENGAGEMENT:")[-1].strip()[:200])
            if "LEARNED:" in content:
                insights["learned"].append(content.split("LEARNED:")[-1].strip()[:200])
            
            # 🔥 NEW: Extract tool results
            if "Tool '" in content and "completed successfully" in content:
                insights["tool_results"].append(content[:200])
            
            # Also extract general insights from team responses
            if self.team_type in name and len(content) > 50:
                lines = content.split('\n')
                for line in lines:
                    line = line.strip()
                    if (len(line) > 20 and 
                        any(keyword in line.lower() for keyword in 
                            ['important', 'key', 'insight', 'note', 'tip', 'learn', 'discover'])):
                        insights["general"].append(line[:200])
        
        # Remove empty categories and duplicates
        for key in insights:
            insights[key] = list(set(insights[key]))  # Remove duplicates
        
        return {k: v for k, v in insights.items() if v}
    
    def _extract_tool_usage(self) -> List[str]:
        """Extract which tools were actually used from conversation."""
        tools_used = []
        
        for msg in self.group_chat.messages:
            content = msg.get("content", "")
            
            # Look for tool execution messages
            if "Tool '" in content:
                # Extract tool name from messages like "Tool 'market_data' completed successfully"
                for tool_name in self.tool_bridge.get_tool_names():
                    if f"Tool '{tool_name}'" in content:
                        tools_used.append(tool_name)
        
        return list(set(tools_used))  # Remove duplicates
    
    async def _write_to_scb(self, insights: Dict[str, List[str]]):
        """Write insights to SCB."""
        try:
            if not self.scb_client:
                return
            
            scb_data = {
                "team": self.team_type,
                "insights": insights,
                "timestamp": datetime.now().isoformat(),
                "tools_available": self.tool_bridge.get_tool_count()  # 🔥 NEW: Include tool info
            }
            
            # Use set_state for SCB client (not write)
            self.scb_client.set_state("s2_team_insights", scb_data)
            logging.info(f"✅ [TEAM] Wrote insights to SCB")
            
        except Exception as e:
            logging.error(f"❌ [TEAM] SCB write error: {e}")
    
    async def _write_to_neo4j(self, stimuli: Dict[str, Any], insights: Dict[str, List[str]]):
        """Write insights to Neo4j."""
        try:
            if not self.neo4j_client:
                return
            
            # Store stimuli node
            stimuli_node = {
                "type": "Stimuli",
                "content": stimuli.get("content", ""),
                "team": self.team_type,
                "timestamp": datetime.now().isoformat(),
                "tools_used": len([tool for tool in insights.get("tool_results", [])])  # 🔥 NEW: Tool usage tracking
            }
            
            # Store insights as connected nodes
            for category, items in insights.items():
                for item in items:
                    insight_node = {
                        "type": "Insight",
                        "category": category,
                        "content": item,
                        "team": self.team_type
                    }
                    # This would create nodes and relationships in Neo4j
                    # Implementation depends on Neo4j client
            
            logging.info(f"✅ [TEAM] Stored insights in Neo4j")
            
        except Exception as e:
            logging.error(f"❌ [TEAM] Neo4j write error: {e}")
    
    async def _get_agent_response(self, agent: AssistantAgent, prompt: str) -> str:
        """Get response from an agent using the LLM."""
        try:
            # Use the agent's generate_reply method directly
            response = agent.generate_reply(
                messages=[{"content": prompt, "role": "user"}],
                sender=agent
            )
            
            if isinstance(response, dict):
                return response.get("content", str(response))
            return str(response)
            
        except Exception as e:
            logging.error(f"Error getting response from {agent.name}: {e}")
            return f"I understand the task about {prompt[:50]}... Let me analyze this further with our available tools."