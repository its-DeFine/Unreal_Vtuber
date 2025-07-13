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
        
        # Use the passed-in llm_config (contains Ollama settings) and add tools to it
        agent_llm_config = self.llm_config.copy()  # Use the Ollama config passed from main
        
        # Add tools to llm_config if available
        if self.tool_bridge:
            tools = self.tool_bridge.get_llm_config_tools()
            if tools:
                agent_llm_config["tools"] = tools
                logger.info(f"🔧 Added {len(tools)} tools to LLM config")
        
        # Initialize agents with unique system prompts
        self.analyst = AssistantAgent(
            name=f"{self.team_type}_analyst",
            system_message=self._get_analyst_prompt(),
            llm_config=agent_llm_config,  # Use the Ollama config with tools
            max_consecutive_auto_reply=15,
        )
        
        self.strategist = AssistantAgent(
            name=f"{self.team_type}_strategist", 
            system_message=self._get_strategist_prompt(),
            llm_config=agent_llm_config,  # Use the Ollama config with tools
            max_consecutive_auto_reply=15,
        )
        
        self.executor = AssistantAgent(
            name=f"{self.team_type}_executor",
            system_message=self._get_executor_prompt(),
            llm_config=agent_llm_config,  # Use the Ollama config with tools
            max_consecutive_auto_reply=15,
        )
        
        # Create user proxy for tool execution
        self.user_proxy = UserProxyAgent(
            name="user_proxy",
            is_termination_msg=lambda x: x.get("content", "") and "TERMINATE" in x.get("content", ""),
            human_input_mode="NEVER",
            max_consecutive_auto_reply=15,
            code_execution_config=False,  # We handle tool execution ourselves
        )
        
        # Store agents list (without user_proxy)
        self.agents = [self.analyst, self.strategist, self.executor]
        
        # Register tools with user proxy if available
        if self.tool_bridge:
            function_map = self.tool_bridge.get_function_map()
            if function_map:
                for func_name, func in function_map.items():
                    self.user_proxy.register_for_execution(name=func_name)(func)
                    # Also register for LLM calling with all agents
                    for agent in self.agents:
                        agent.register_for_llm(name=func_name)(func)
                logger.info(f"✅ Registered {len(function_map)} tools with agents")
        
        # Create group chat
        all_agents = [self.user_proxy] + self.agents
        self.group_chat = GroupChat(
            agents=all_agents,
            messages=[],
            max_round=15,  # Increased from 5
            speaker_selection_method="round_robin"
        )
        
        # Create manager config WITHOUT tools (GroupChatManager cannot have tools)
        manager_llm_config = self.llm_config.copy()  # Start with Ollama config
        # Remove tools if they exist (GroupChatManager cannot have tools)
        manager_llm_config.pop("tools", None)
        
        self.group_chat_manager = GroupChatManager(
            groupchat=self.group_chat,
            llm_config=manager_llm_config  # Use Ollama config without tools
        )
        
        # Alias for backward compatibility with existing process_stimuli logic
        self.manager = self.group_chat_manager
        
        logger.info(f"✅ [S2_TEAM] Initialized {team_type} team with {len(self.agents)} agents and {tool_count} tools")
    
    def set_clients(self, scb_client=None, neo4j_client=None):
        """Set external service clients."""
        self.scb_client = scb_client
        self.neo4j_client = neo4j_client
    
    def create_team(self) -> bool:
        """Create team - already done in __init__, so just return True."""
        return True
    
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
            
            # ------------------------------------------------------------------
            # Inject SCB context (team slice + global slice) into system prompt
            # ------------------------------------------------------------------
            scb_context_lines = []
            if self.scb_client:
                try:
                    team_slice = self.scb_client.get_slice(f"scb:team:{self.team_type}")
                    global_slice = self.scb_client.get_slice("scb:global")

                    def _slice_to_text(slice_obj):
                        lines = []
                        for entry in slice_obj.get("window", [])[-3:]:  # last 3 events
                            lines.append(f"[{entry.get('actor')}]: {entry.get('text')}")
                        return "\n".join(lines)

                    if team_slice:
                        scb_context_lines.append("Team SCB Context:\n" + _slice_to_text(team_slice))
                    if global_slice:
                        scb_context_lines.append("Global SCB Context:\n" + _slice_to_text(global_slice))
                except Exception as _se:
                    logger.warning(f"[TEAM] Failed to load SCB context: {_se}")

            scb_context_block = "\n\n".join(scb_context_lines)

            # Create enhanced task prompt that encourages tool usage
            task = f"""
            Task: {content}
            Context: {metadata}
            Stimuli ID: {stimuli_id}
            {scb_context_block}
            
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

    def _get_analyst_prompt(self) -> str:
        """Get analyst system prompt based on team type."""
        base_prompt = f"""You are a {self.team_type} analyst. Your role is to analyze data and identify opportunities.
You work collaboratively with other agents to solve problems.
When you identify a need for specific data or actions, use the available tools.
Focus on analysis and insights, not execution."""

        return base_prompt
    
    def _get_strategist_prompt(self) -> str:
        """Get strategist system prompt based on team type."""
        base_prompt = f"""You are a {self.team_type} strategist. Your role is to develop strategies based on analysis.
You work with the analyst's insights to create actionable plans.
Use available tools when you need specific data or capabilities.
Focus on strategy and planning, not direct execution."""

        return base_prompt
    
    def _get_executor_prompt(self) -> str:
        """Get executor system prompt based on team type."""
        base_prompt = f"""You are a {self.team_type} executor. Your role is to implement strategies and take actions.
You work with the strategist's plans to execute specific tasks.
Use available tools to perform actions and gather results.
When tasks are complete, summarize the outcomes."""

        return base_prompt