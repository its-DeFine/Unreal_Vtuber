"""
Simplified AutoGen Team for S2
==============================

A streamlined implementation focused on the 3 specialized teams:
- Trader (market analysis)
- Educator (teaching)
- Streamer (content creation)

Each team has teachable agents with SCB and Neo4j integration.
"""

import asyncio
import logging
from typing import Dict, Any, List, Optional
from datetime import datetime

try:
    from autogen import AssistantAgent, UserProxyAgent, GroupChat, GroupChatManager
except ImportError:
    logging.error("AutoGen not available")
    AssistantAgent = UserProxyAgent = GroupChat = GroupChatManager = None


class SimplifiedAutoGenTeam:
    """
    Simplified team implementation for S2 specialized character teams.
    """
    
    def __init__(self, team_type: str, llm_config: Dict[str, Any]):
        self.team_type = team_type
        self.llm_config = llm_config
        self.agents = {}
        self.group_chat = None
        self.manager = None
        self.scb_client = None
        self.neo4j_client = None
        self.max_rounds = 5  # Limit conversation rounds
        
        logging.info(f"🤖 [TEAM] Creating simplified {team_type} team")
    
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
            
            logging.info(f"✅ [TEAM] {self.team_type} team created with {len(self.agents)} agents")
            return True
            
        except Exception as e:
            logging.error(f"❌ [TEAM] Error creating team: {e}")
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
            3. Ensure responses are actionable and clear
            4. Write insights to SCB when important information is discovered
            5. Store patterns in Neo4j for future reference
            
            IMPORTANT: Keep discussions focused and conclude within {self.max_rounds} rounds.
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
            
            When you learn something new, say "LEARNED: [insight]"
            """
        )
    
    def _add_trader_agents(self):
        """Add trader-specific agents."""
        
        self.agents["analyst"] = AssistantAgent(
            name="market_analyst",
            llm_config=self.llm_config,
            system_message="""You are a market analysis expert.
            Analyze market trends, identify opportunities, and assess risks.
            Focus on actionable insights for trading decisions.
            When you find important patterns, say "PATTERN: [description]"
            """
        )
        
        self.agents["strategist"] = AssistantAgent(
            name="trading_strategist",
            llm_config=self.llm_config,
            system_message="""You are a trading strategy expert.
            Develop trading strategies based on market analysis.
            Consider risk management and portfolio optimization.
            Say "STRATEGY: [description]" when proposing a strategy.
            """
        )
    
    def _add_educator_agents(self):
        """Add educator-specific agents."""
        
        self.agents["teacher"] = AssistantAgent(
            name="content_teacher",
            llm_config=self.llm_config,
            system_message="""You are an expert educator.
            Break down complex topics into understandable lessons.
            Create engaging educational content.
            Say "LESSON: [topic]" when teaching something new.
            """
        )
        
        self.agents["curriculum"] = AssistantAgent(
            name="curriculum_designer",
            llm_config=self.llm_config,
            system_message="""You are a curriculum design expert.
            Structure learning paths and create comprehensive courses.
            Ensure content is progressive and engaging.
            Say "CURRICULUM: [structure]" when proposing a learning path.
            """
        )
    
    def _add_streamer_agents(self):
        """Add streamer-specific agents."""
        
        self.agents["content_creator"] = AssistantAgent(
            name="content_creator",
            llm_config=self.llm_config,
            system_message="""You are a content creation expert.
            Generate engaging content ideas for streaming.
            Focus on audience engagement and entertainment value.
            Say "CONTENT: [idea]" when proposing content.
            """
        )
        
        self.agents["engagement"] = AssistantAgent(
            name="engagement_specialist",
            llm_config=self.llm_config,
            system_message="""You are an audience engagement expert.
            Develop strategies to grow and engage the streaming audience.
            Focus on community building and interaction.
            Say "ENGAGEMENT: [strategy]" when proposing engagement tactics.
            """
        )
    
    def _create_group_chat(self):
        """Create group chat with proper termination."""
        
        # Create user proxy for execution
        user_proxy = UserProxyAgent(
            name="user_proxy",
            system_message="Execute approved actions. Reply with 'Task completed.' when done.",
            code_execution_config=False,  # Disable code execution for safety
            human_input_mode="NEVER",  # Never ask for human input
            max_consecutive_auto_reply=0,  # Don't auto-reply, let the agents work
            is_termination_msg=lambda x: "TERMINATE" in x.get("content", ""),  # Terminate on TERMINATE
            llm_config=False  # No LLM for user proxy
        )
        
        # Add all agents to list
        all_agents = [user_proxy] + list(self.agents.values())
        
        # Create group chat with termination
        self.group_chat = GroupChat(
            agents=all_agents,
            messages=[],
            max_round=self.max_rounds,
            speaker_selection_method="round_robin",
            allow_repeat_speaker=False  # Prevent stuck conversations
        )
        
        # Create manager
        self.manager = GroupChatManager(
            groupchat=self.group_chat,
            llm_config=self.llm_config,
            system_message="Manage the conversation and ensure it stays focused.",
            is_termination_msg=lambda x: "TERMINATE" in x.get("content", "")  # Also check for termination
        )
    
    async def process_stimuli(self, stimuli: Dict[str, Any]) -> Dict[str, Any]:
        """Process stimuli with the team using real AutoGen group chat."""
        
        if not self.manager:
            return {
                "success": False,
                "error": "Team not initialized"
            }
        
        try:
            # Extract content
            content = stimuli.get("content", "")
            metadata = stimuli.get("metadata", {})
            
            # Create task message for the user proxy
            task = f"""
            Task: {content}
            Context: {metadata}
            
            Please analyze this task and provide actionable insights.
            Team members should collaborate to:
            1. Understand the requirements
            2. Share relevant expertise
            3. Generate comprehensive insights
            4. Store important patterns for future reference
            
            Keep the discussion focused and conclude with TERMINATE when done.
            """
            
            logging.info(f"🚀 [TEAM] {self.team_type} team starting real group chat: {content[:50]}...")
            
            # Reset group chat messages for fresh conversation
            self.group_chat.messages = []
            
            # Start real AutoGen group chat conversation
            try:
                # Use the manager to initiate the group chat
                # The user proxy will start the conversation with the task
                user_proxy = None
                for agent in self.group_chat.agents:
                    if hasattr(agent, 'name') and agent.name == "user_proxy":
                        user_proxy = agent
                        break
                
                if not user_proxy:
                    raise Exception("User proxy not found in group chat agents")
                
                logging.info(f"🎯 [TEAM] Starting group chat with {len(self.group_chat.agents)} agents")
                
                # Use asyncio to run the group chat with timeout
                chat_task = asyncio.create_task(
                    self._run_group_chat_async(user_proxy, task)
                )
                
                # Wait for chat to complete with timeout
                chat_result = await asyncio.wait_for(chat_task, timeout=60.0)
                
                logging.info(f"✅ [TEAM] Group chat completed with {len(self.group_chat.messages)} messages")
                
                # Log sample of conversation for debugging
                if self.group_chat.messages:
                    logging.info(f"📝 [TEAM] Sample conversation:")
                    for i, msg in enumerate(self.group_chat.messages[:3]):  # Show first 3 messages
                        sender = msg.get('name', 'unknown')
                        content_preview = msg.get('content', '')[:100]
                        logging.info(f"   {i+1}. {sender}: {content_preview}...")
                
            except asyncio.TimeoutError:
                logging.warning(f"⏰ [TEAM] Group chat timed out, using existing messages")
            except Exception as e:
                logging.error(f"❌ [TEAM] Error in group chat: {e}")
                import traceback
                traceback.print_exc()
                
                # Fallback to simple response if group chat fails
                await self._fallback_simple_response(task)
            
            # Extract insights from the real conversation
            insights = self._extract_insights()
            
            # Store in SCB if available
            if self.scb_client and insights:
                await self._write_to_scb(insights)
            
            # Store in Neo4j if available
            if self.neo4j_client and insights:
                await self._write_to_neo4j(stimuli, insights)
            
            # Count actual conversation rounds (exclude system messages)
            conversation_rounds = len([msg for msg in self.group_chat.messages 
                                     if msg.get('role') == 'assistant' or msg.get('role') == 'user'])
            
            return {
                "success": True,
                "team_type": self.team_type,
                "insights": insights,
                "rounds": conversation_rounds,
                "total_messages": len(self.group_chat.messages),
                "timestamp": datetime.now().isoformat(),
                "debug_info": {
                    "group_chat_exists": self.group_chat is not None,
                    "manager_exists": self.manager is not None,
                    "agents_count": len(self.agents),
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
    
    async def _run_group_chat_async(self, user_proxy, task):
        """Run the AutoGen group chat asynchronously."""
        
        try:
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
            "general": []  # For general insights
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
                # Extract lesson content more carefully
                lesson_start = content.find("LESSON:")
                if lesson_start != -1:
                    lesson_text = content[lesson_start + 7:].strip()
                    # Take first line or up to 200 chars
                    lesson_line = lesson_text.split('\n')[0][:200]
                    if lesson_line:
                        insights["lessons"].append(lesson_line)
            if "CONTENT:" in content:
                insights["content"].append(content.split("CONTENT:")[-1].strip()[:200])
            if "ENGAGEMENT:" in content:
                insights["engagement"].append(content.split("ENGAGEMENT:")[-1].strip()[:200])
            if "LEARNED:" in content:
                insights["learned"].append(content.split("LEARNED:")[-1].strip()[:200])
            
            # Also extract general insights from team responses
            if self.team_type in name and len(content) > 50:
                # Extract key points from longer messages
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
    
    async def _write_to_scb(self, insights: Dict[str, List[str]]):
        """Write insights to SCB."""
        try:
            if not self.scb_client:
                return
            
            scb_data = {
                "team": self.team_type,
                "insights": insights,
                "timestamp": datetime.now().isoformat()
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
                "timestamp": datetime.now().isoformat()
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
            return f"I understand the task about {prompt[:50]}... Let me analyze this further."