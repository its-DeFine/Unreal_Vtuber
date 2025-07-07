import os
import logging
import asyncio
from typing import Dict, List, Optional, Any
from datetime import datetime

# Import AutoGen for stimuli-specific multi-agent conversations
try:
    import autogen
    from autogen import AssistantAgent, UserProxyAgent, GroupChat, GroupChatManager
    AUTOGEN_AVAILABLE = True
    logging.info("✅ [STIMULI_TEAM] Microsoft AutoGen framework imported successfully")
except ImportError:
    AUTOGEN_AVAILABLE = False
    logging.warning("⚠️ [STIMULI_TEAM] Microsoft AutoGen not available - stimuli team disabled")

from .teachable_agents import create_teachable_agents, get_learning_summary


class StimuliAutoGenTeam:
    """Dedicated AutoGen team for stimuli analysis and decision-making"""
    
    def __init__(self):
        self.stimuli_analyzer = None
        self.decision_strategist = None
        self.action_coordinator = None
        self.stimuli_manager = None
        self.stimuli_group_chat = None
        self.teachable_wrappers = {}
        self.team_initialized = False
        
        # Team analytics
        self.team_analytics = {
            "stimuli_processed": 0,
            "decisions_made": 0,
            "actions_executed": 0,
            "team_interactions": {},
            "decision_times": []
        }
        
        logging.info("🎯 [STIMULI_TEAM] Stimuli AutoGen team initialized")
    
    def initialize_team(self) -> bool:
        """Initialize the stimuli-specific AutoGen team"""
        if not AUTOGEN_AVAILABLE:
            logging.warning("⚠️ [STIMULI_TEAM] AutoGen not available - cannot initialize stimuli team")
            return False
        
        try:
            # Get LLM configuration
            llm_config = self._get_llm_config()
            if not llm_config:
                logging.error("❌ [STIMULI_TEAM] Failed to get LLM configuration")
                return False
            
            # Check if we should use teachable agents
            use_teachable = os.getenv("USE_TEACHABLE_AGENTS", "true").lower() == "true"
            
            if use_teachable:
                logging.info("🎓 [STIMULI_TEAM] Creating teachable stimuli agents with learning capabilities...")
                self._create_teachable_stimuli_agents(llm_config)
            else:
                logging.info("🤖 [STIMULI_TEAM] Creating standard stimuli agents...")
                self._create_standard_stimuli_agents(llm_config)
            
            # Initialize group chat
            self._initialize_group_chat()
            
            self.team_initialized = True
            logging.info("✅ [STIMULI_TEAM] Stimuli AutoGen team initialized successfully")
            return True
            
        except Exception as e:
            logging.error(f"❌ [STIMULI_TEAM] Failed to initialize stimuli team: {e}")
            return False
    
    def _get_llm_config(self) -> Optional[Dict]:
        """Get LLM configuration for stimuli team"""
        use_ollama = os.getenv("USE_OLLAMA", "false").lower() == "true"
        ollama_host = os.getenv("OLLAMA_HOST", "http://localhost:11434")
        ollama_model = os.getenv("OLLAMA_MODEL", "llama3.2:3b")
        
        try:
            if use_ollama:
                logging.info(f"🦙 [STIMULI_TEAM] Using Ollama at {ollama_host} with model {ollama_model}")
                return {
                    "config_list": [
                        {
                            "api_type": "ollama",
                            "model": ollama_model,
                            "client_host": ollama_host,
                        }
                    ],
                    "temperature": 0.7,  # Slightly more focused for stimuli analysis
                }
            else:
                # Fall back to OpenAI
                openai_api_key = os.getenv("OPENAI_API_KEY")
                if not openai_api_key:
                    logging.warning("⚠️ [STIMULI_TEAM] Neither Ollama nor OpenAI API key configured")
                    return None
                
                return {
                    "config_list": [
                        {
                            "model": os.getenv("OPENAI_MODEL", "gpt-4o-mini"),
                            "api_key": openai_api_key,
                            "api_type": "openai"
                        }
                    ],
                    "temperature": 0.7,
                }
        except Exception as e:
            logging.error(f"❌ [STIMULI_TEAM] Error getting LLM config: {e}")
            return None
    
    def _create_teachable_stimuli_agents(self, llm_config: Dict):
        """Create teachable stimuli agents with learning capabilities"""
        try:
            # Create teachable agents specifically for stimuli processing
            teachable_agents = create_teachable_agents(llm_config)
            
            # Assign stimuli-specific roles
            self.stimuli_analyzer = teachable_agents["cognitive"]
            self.decision_strategist = teachable_agents["programmer"]  # Strategic thinking
            self.action_coordinator = teachable_agents["observer"]    # Action coordination
            
            # Update system messages for stimuli-specific roles
            # self._update_system_messages_for_stimuli()  # Disabled due to read-only system_message property
            
            # Store teachable wrappers
            self.teachable_wrappers = {
                "analyzer": teachable_agents["cognitive_wrapper"],
                "strategist": teachable_agents["programmer_wrapper"],
                "coordinator": teachable_agents.get("executor_wrapper")  # Use executor_wrapper since no observer_wrapper
            }
            
            logging.info("🎓 [STIMULI_TEAM] Teachable stimuli agents created successfully")
            
        except Exception as e:
            logging.error(f"❌ [STIMULI_TEAM] Error creating teachable stimuli agents: {e}")
            raise
    
    def _create_standard_stimuli_agents(self, llm_config: Dict):
        """Create standard stimuli agents"""
        try:
            # Stimuli Analyzer Agent
            self.stimuli_analyzer = AssistantAgent(
                name="stimuli_analyzer_agent",
                system_message="""You are a specialized stimuli analyzer agent focused on understanding and categorizing external stimuli.
                Your responsibilities include:
                1. Analyzing incoming stimuli content, context, and metadata
                2. Identifying stimuli category, urgency, and complexity level
                3. Extracting key information and actionable insights
                4. Determining potential impact on system objectives
                5. Providing structured analysis for decision-making
                
                When analyzing stimuli, focus on:
                - Content relevance and significance
                - Urgency and priority assessment
                - Required response type (objective update, knowledge storage, or action)
                - Potential system impact and considerations
                
                Keep analysis concise but comprehensive. Use structured format for clarity.""",
                llm_config=llm_config,
                max_consecutive_auto_reply=2,
            )
            
            # Decision Strategist Agent
            self.decision_strategist = AssistantAgent(
                name="decision_strategist_agent",
                system_message="""You are a decision strategist agent specializing in stimuli response planning.
                Your responsibilities include:
                1. Evaluating stimuli analysis and determining optimal response strategy
                2. Deciding between objective updates, knowledge storage, or placeholder actions
                3. Defining specific parameters and configurations for chosen actions
                4. Considering system goals and long-term strategic implications
                5. Providing clear rationale for strategic decisions
                
                Decision criteria:
                - For system improvements: Recommend objective updates for main team
                - For knowledge/insights: Recommend knowledge push to Cognee
                - For actionable tasks: Recommend placeholder actions with specific parameters
                
                Always provide clear reasoning and specific action parameters.""",
                llm_config=llm_config,
                max_consecutive_auto_reply=2,
            )
            
            # Action Coordinator Agent
            self.action_coordinator = AssistantAgent(
                name="action_coordinator_agent",
                system_message="""You are an action coordinator agent responsible for finalizing stimuli responses.
                Your responsibilities include:
                1. Coordinating final decisions from team analysis and strategy
                2. Formatting parameters for the stimuli action executor tool
                3. Ensuring all required parameters are properly specified
                4. Validating action feasibility and completeness
                5. Providing final execution summary and rationale
                
                Your output should specify:
                - action_type: ["objective_update", "knowledge_push", "placeholder_action"]
                - Specific parameters based on action type
                - agent_reasoning: Complete team decision rationale
                - priority: Execution priority level
                
                Always end with: "EXECUTE_TOOL: stimuli_action_executor" when ready to execute.""",
                llm_config=llm_config,
                max_consecutive_auto_reply=1,
            )
            
            logging.info("🤖 [STIMULI_TEAM] Standard stimuli agents created successfully")
            
        except Exception as e:
            logging.error(f"❌ [STIMULI_TEAM] Error creating standard stimuli agents: {e}")
            raise
    
    def _update_system_messages_for_stimuli(self):
        """Update system messages for teachable agents to focus on stimuli processing"""
        try:
            if hasattr(self.stimuli_analyzer, 'system_message'):
                self.stimuli_analyzer.system_message = """You are a specialized stimuli analyzer agent with learning capabilities.
                Analyze incoming stimuli for content, context, urgency, and system impact.
                Learn from previous stimuli patterns to improve analysis accuracy."""
            
            if hasattr(self.decision_strategist, 'system_message'):
                self.decision_strategist.system_message = """You are a decision strategist agent with strategic learning capabilities.
                Determine optimal response strategies for stimuli based on analysis.
                Learn from previous decisions to improve strategic planning."""
            
            if hasattr(self.action_coordinator, 'system_message'):
                self.action_coordinator.system_message = """You are an action coordinator agent with execution learning capabilities.
                Coordinate final stimuli responses and format execution parameters.
                Learn from previous executions to improve coordination effectiveness."""
                
            logging.info("🎯 [STIMULI_TEAM] System messages updated for stimuli focus")
            
        except Exception as e:
            logging.error(f"❌ [STIMULI_TEAM] Error updating system messages: {e}")
    
    def _initialize_group_chat(self):
        """Initialize group chat for stimuli team"""
        try:
            if not all([self.stimuli_analyzer, self.decision_strategist, self.action_coordinator]):
                raise ValueError("Not all stimuli agents are initialized")
            
            # Create group chat with stimuli agents
            self.stimuli_group_chat = GroupChat(
                agents=[self.stimuli_analyzer, self.decision_strategist, self.action_coordinator],
                messages=[],
                max_round=5  # Allow thorough stimuli analysis
            )
            
            # Create group chat manager
            self.stimuli_manager = GroupChatManager(
                groupchat=self.stimuli_group_chat,
                llm_config=self._get_llm_config(),
                system_message="""You are managing a specialized stimuli analysis team with three agents:
                - stimuli_analyzer_agent: Analyzes stimuli content and context
                - decision_strategist_agent: Determines optimal response strategy
                - action_coordinator_agent: Coordinates final actions and parameters
                
                Guide the team through thorough stimuli analysis leading to actionable decisions.
                Ensure all agents contribute their expertise before finalizing actions."""
            )
            
            logging.info("🎪 [STIMULI_TEAM] Group chat initialized for stimuli team")
            
        except Exception as e:
            logging.error(f"❌ [STIMULI_TEAM] Error initializing group chat: {e}")
            raise
    
    async def process_stimuli_with_team(self, stimuli_data: Dict[str, Any]) -> Dict[str, Any]:
        """Process stimuli using the full AutoGen team collaboration"""
        if not self.team_initialized:
            logging.error("❌ [STIMULI_TEAM] Team not initialized - cannot process stimuli")
            return {"error": "Stimuli team not initialized"}
        
        start_time = datetime.now()
        
        try:
            # Create enhanced prompt for stimuli analysis
            stimuli_prompt = self._create_stimuli_prompt(stimuli_data)
            
            # Create user proxy for stimuli processing
            user_proxy = UserProxyAgent(
                name="stimuli_orchestrator",
                human_input_mode="NEVER",
                max_consecutive_auto_reply=1,
                code_execution_config=False,
                system_message="You orchestrate stimuli analysis and decision-making for the autonomous system."
            )
            
            # Clear previous messages
            if self.stimuli_group_chat:
                self.stimuli_group_chat.messages = []
            
            # Reset agents
            for agent in [self.stimuli_analyzer, self.decision_strategist, self.action_coordinator]:
                if hasattr(agent, 'reset'):
                    agent.reset()
            
            # Initiate stimuli team group chat
            logging.info("🎯 [STIMULI_TEAM] Starting stimuli analysis team collaboration")
            
            group_chat_result = user_proxy.initiate_chat(
                self.stimuli_manager,
                message=stimuli_prompt,
                max_turns=5,  # Allow thorough analysis
                silent=False
            )
            
            # Process team responses
            team_response = self._process_team_responses(group_chat_result)
            
            # Update analytics
            self._update_team_analytics(start_time, team_response)
            
            logging.info("✅ [STIMULI_TEAM] Stimuli analysis completed successfully")
            return team_response
            
        except Exception as e:
            logging.error(f"❌ [STIMULI_TEAM] Error processing stimuli with team: {e}")
            return {"error": str(e), "action_type": "knowledge_push", "knowledge_data": {"error": str(e)}}
    
    def _create_stimuli_prompt(self, stimuli_data: Dict[str, Any]) -> str:
        """Create enhanced prompt for stimuli analysis"""
        prompt = f"""
        🎯 STIMULI ANALYSIS REQUEST
        
        Stimuli Information:
        - Content: {stimuli_data.get('content', 'No content provided')}
        - Category: {stimuli_data.get('category', 'uncategorized')}
        - Priority: {stimuli_data.get('priority', 'medium')}
        - Source: {stimuli_data.get('source', 'unknown')}
        - Timestamp: {stimuli_data.get('timestamp', datetime.now().isoformat())}
        
        Additional Context:
        - Metadata: {stimuli_data.get('metadata', {})}
        - Required Response: {stimuli_data.get('response_required', True)}
        
        Team Objective:
        Analyze this stimuli and determine the optimal response. Consider:
        1. Should we update main team objectives?
        2. Should we store knowledge in Cognee?
        3. Should we execute a placeholder action?
        
        End with specific action parameters for the stimuli_action_executor tool.
        """
        
        return prompt
    
    def _process_team_responses(self, group_chat_result) -> Dict[str, Any]:
        """Process and extract decisions from team responses"""
        try:
            agent_responses = {}
            final_decision = {}
            
            # Extract agent responses
            if group_chat_result and hasattr(group_chat_result, 'chat_history'):
                for message in group_chat_result.chat_history:
                    if message.get('role') == 'assistant' and message.get('name'):
                        agent_name = message['name']
                        content = message.get('content', '')
                        agent_responses[agent_name] = content
                        
                        # Look for action coordinator final decision
                        if agent_name == "action_coordinator_agent":
                            final_decision = self._extract_action_parameters(content)
            
            # Default response if no clear decision
            if not final_decision:
                final_decision = {
                    "action_type": "knowledge_push",
                    "knowledge_data": {
                        "stimuli_analysis": agent_responses,
                        "timestamp": datetime.now().isoformat(),
                        "status": "processed_without_specific_action"
                    },
                    "agent_reasoning": "Team analysis completed but no specific action determined",
                    "priority": "medium"
                }
            
            # Add team responses to final decision
            final_decision["team_responses"] = agent_responses
            final_decision["total_agents"] = len(agent_responses)
            
            return final_decision
            
        except Exception as e:
            logging.error(f"❌ [STIMULI_TEAM] Error processing team responses: {e}")
            return {
                "action_type": "knowledge_push",
                "knowledge_data": {"error": str(e)},
                "agent_reasoning": f"Error processing team responses: {e}",
                "priority": "low"
            }
    
    def _extract_action_parameters(self, content: str) -> Dict[str, Any]:
        """Extract action parameters from action coordinator response"""
        try:
            # Look for structured action parameters in the response
            # This is a simplified extraction - could be enhanced with more sophisticated parsing
            
            if "objective_update" in content.lower():
                return {
                    "action_type": "objective_update",
                    "objective_updates": self._extract_objectives(content),
                    "agent_reasoning": content,
                    "priority": "high"
                }
            elif "knowledge_push" in content.lower():
                return {
                    "action_type": "knowledge_push",
                    "knowledge_data": self._extract_knowledge_data(content),
                    "agent_reasoning": content,
                    "priority": "medium"
                }
            elif "placeholder_action" in content.lower():
                return {
                    "action_type": "placeholder_action",
                    "placeholder_action": self._extract_placeholder_action(content),
                    "agent_reasoning": content,
                    "priority": "high"
                }
            else:
                # Default to knowledge push
                return {
                    "action_type": "knowledge_push",
                    "knowledge_data": {"analysis": content, "timestamp": datetime.now().isoformat()},
                    "agent_reasoning": content,
                    "priority": "medium"
                }
                
        except Exception as e:
            logging.error(f"❌ [STIMULI_TEAM] Error extracting action parameters: {e}")
            return {
                "action_type": "knowledge_push",
                "knowledge_data": {"error": str(e), "content": content},
                "agent_reasoning": f"Error extracting parameters: {e}",
                "priority": "low"
            }
    
    def _extract_objectives(self, content: str) -> Dict[str, Any]:
        """Extract objective updates from content"""
        # Simplified extraction - enhance based on actual response patterns
        return {
            "new_objectives": [content],
            "timestamp": datetime.now().isoformat(),
            "source": "stimuli_team_analysis"
        }
    
    def _extract_knowledge_data(self, content: str) -> Dict[str, Any]:
        """Extract knowledge data from content"""
        return {
            "knowledge": content,
            "timestamp": datetime.now().isoformat(),
            "source": "stimuli_team_analysis",
            "type": "stimuli_insight"
        }
    
    def _extract_placeholder_action(self, content: str) -> Dict[str, Any]:
        """Extract placeholder action from content"""
        return {
            "action_description": content,
            "timestamp": datetime.now().isoformat(),
            "source": "stimuli_team_decision",
            "parameters": {}  # Could be enhanced to extract specific parameters
        }
    
    def _update_team_analytics(self, start_time: datetime, team_response: Dict[str, Any]):
        """Update team analytics"""
        try:
            duration = (datetime.now() - start_time).total_seconds()
            
            self.team_analytics["stimuli_processed"] += 1
            self.team_analytics["decisions_made"] += 1
            self.team_analytics["decision_times"].append(duration)
            
            # Track agent participation
            if "team_responses" in team_response:
                for agent_name in team_response["team_responses"].keys():
                    self.team_analytics["team_interactions"][agent_name] = \
                        self.team_analytics["team_interactions"].get(agent_name, 0) + 1
            
            # Keep only last 100 decision times
            if len(self.team_analytics["decision_times"]) > 100:
                self.team_analytics["decision_times"] = self.team_analytics["decision_times"][-100:]
            
            logging.info(f"📊 [STIMULI_TEAM] Analytics updated - Duration: {duration:.2f}s")
            
        except Exception as e:
            logging.error(f"❌ [STIMULI_TEAM] Error updating analytics: {e}")
    
    def get_team_status(self) -> Dict[str, Any]:
        """Get current team status and analytics"""
        return {
            "team_initialized": self.team_initialized,
            "autogen_available": AUTOGEN_AVAILABLE,
            "analytics": self.team_analytics,
            "agents": {
                "stimuli_analyzer": bool(self.stimuli_analyzer),
                "decision_strategist": bool(self.decision_strategist),
                "action_coordinator": bool(self.action_coordinator),
                "stimuli_manager": bool(self.stimuli_manager)
            },
            "teachable_mode": bool(self.teachable_wrappers)
        }
    
    def get_learning_summary(self) -> Dict[str, Any]:
        """Get learning summary for teachable agents"""
        if not self.teachable_wrappers:
            return {"status": "not_enabled", "message": "Teachable agents not enabled"}
        
        try:
            return get_learning_summary(self.teachable_wrappers)
        except Exception as e:
            logging.error(f"❌ [STIMULI_TEAM] Error getting learning summary: {e}")
            return {"error": str(e)}