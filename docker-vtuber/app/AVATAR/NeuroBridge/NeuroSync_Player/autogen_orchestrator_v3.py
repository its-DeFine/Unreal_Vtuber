"""
AutoGen-Based Orchestrator V3 - Production Implementation
========================================================

This module implements a sophisticated multi-agent orchestrator using Microsoft AutoGen
framework for autonomous VTuber content generation and decision-making.

Key Features:
- Multi-agent coordination with specialized roles
- Configurable personas with dynamic filtering
- Continuous autonomous content generation
- External input processing with context awareness
- Environment control integration
- Backward compatible with existing endpoints

Architecture:
- Orchestrator Agent: Main coordinator and decision maker
- Content Filter Agent: Persona-based input filtering
- Speech Coordinator Agent: Speech generation management
- Environment Controller Agent: Game/environment control
- Idle Content Agent: Autonomous content generation
- Autonomous Decision Agent: Timing and strategy decisions
"""

import asyncio
import logging
import os
import time
import hashlib
import json
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional, Union, Tuple
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path

# AutoGen imports
try:
    from autogen import Agent, AssistantAgent, UserProxyAgent, GroupChat, GroupChatManager
    from autogen.agentchat import ConversableAgent
    AUTOGEN_AVAILABLE = True
except ImportError:
    AUTOGEN_AVAILABLE = False
    logging.warning("AutoGen not available - using mock implementation")

# Local imports
from autogen_agents import (
    create_orchestrator_agent,
    create_content_filter_agent,
    create_speech_coordinator_agent,
    create_environment_controller_agent,
    create_idle_content_agent,
    create_autonomous_decision_agent,
    AgentResponse,
    FilterDecision,
    ContentDecision,
    EnvironmentAction
)
from autogen_state_manager import (
    OrchestratorState,
    StateManager,
    ConversationContext,
    EnvironmentState,
    ContentHistory
)
from autogen_content_strategies import (
    ContentStrategyManager,
    ContentType,
    ContentStrategy,
    PersonaConfig,
    IdleBehaviorConfig
)

# Import existing components for compatibility
from autonomous_orchestrator_v2 import (
    ActionType,
    Priority,
    SpeechRequest,
    ActionRequest,
    SystemStateV2,
    BlendshapeMonitor
)

# SCB integration
try:
    from utils.scb.scb_client import OrchestratorSCBClient
    SCB_AVAILABLE = True
except ImportError:
    SCB_AVAILABLE = False
    logging.warning("SCB integration not available")


class AutoGenOrchestratorV3:
    """
    Enhanced Autonomous Orchestrator using Microsoft AutoGen multi-agent framework
    
    This orchestrator coordinates multiple specialized agents to make sophisticated
    decisions about content generation, filtering, and environment control.
    """
    
    def __init__(self, config_path: Optional[str] = None):
        """
        Initialize the AutoGen-based orchestrator
        
        Args:
            config_path: Optional path to configuration file
        """
        self.logger = logging.getLogger(__name__)
        self.logger.info("🚀 Initializing AutoGen Orchestrator V3")
        
        # Load configuration
        self.config = self._load_configuration(config_path)
        self.enabled = self.config.get("enabled", True)
        
        # Initialize state management
        self.state_manager = StateManager()
        self.state = self.state_manager.state
        
        # Initialize content strategy manager
        self.content_strategy_manager = ContentStrategyManager(self.config)
        
        # Initialize agents
        self.agents = self._initialize_agents()
        
        # Initialize group chat for multi-agent coordination
        self.group_chat = None
        self.chat_manager = None
        if AUTOGEN_AVAILABLE:
            self._initialize_group_chat()
        
        # SCB integration
        self.scb_client = None
        if SCB_AVAILABLE and self.config.get("scb_integration_enabled", True):
            try:
                self.scb_client = OrchestratorSCBClient()
                self.logger.info("✅ SCB integration enabled")
            except Exception as e:
                self.logger.warning(f"⚠️ SCB integration failed: {e}")
        
        # Blendshape monitor for accurate speech detection
        self.blendshape_monitor = BlendshapeMonitor(self.state, self.logger)
        self.blendshape_monitor.register_callback('on_complete', self._on_speech_complete)
        
        # Action queues
        self.action_queue: List[ActionRequest] = []
        self.speech_queue: List[SpeechRequest] = []
        
        # Autonomous operation control
        self.running = False
        self.decision_task = None
        self.autonomous_task = None
        
        # Performance tracking
        self.metrics = {
            "decisions_made": 0,
            "content_generated": 0,
            "inputs_filtered": 0,
            "environment_changes": 0,
            "start_time": time.time()
        }
        
        self.logger.info(
            f"✅ AutoGen Orchestrator V3 initialized\n"
            f"   Persona: {self.config.get('current_persona', 'default')}\n"
            f"   Agents: {len(self.agents)}\n"
            f"   Autonomous: {self.config.get('autonomous_enabled', True)}"
        )
    
    def _load_configuration(self, config_path: Optional[str] = None) -> Dict[str, Any]:
        """Load orchestrator configuration from file or environment"""
        config = {
            "enabled": os.getenv("AUTOGEN_ORCHESTRATOR_ENABLED", "true").lower() == "true",
            "current_persona": os.getenv("ORCHESTRATOR_PERSONA", "interactive_streamer"),
            "autonomous_enabled": os.getenv("AUTONOMOUS_CONTENT_ENABLED", "true").lower() == "true",
            "scb_integration_enabled": os.getenv("SCB_INTEGRATION_ENABLED", "true").lower() == "true",
            
            # LLM configuration
            "llm_config": {
                "model": os.getenv("AUTOGEN_MODEL", "gpt-3.5-turbo"),
                "temperature": float(os.getenv("AUTOGEN_TEMPERATURE", "0.7")),
                "max_tokens": int(os.getenv("AUTOGEN_MAX_TOKENS", "150")),
                "api_key": os.getenv("OPENAI_API_KEY", "")
            },
            
            # Timing configuration
            "timing": {
                "decision_interval": float(os.getenv("DECISION_INTERVAL", "0.5")),
                "min_idle_time": float(os.getenv("MIN_IDLE_TIME", "8.0")),
                "max_idle_time": float(os.getenv("MAX_IDLE_TIME", "45.0")),
                "min_speech_gap": float(os.getenv("MIN_SPEECH_GAP", "2.5"))
            },
            
            # Group chat configuration
            "group_chat": {
                "max_rounds": int(os.getenv("AUTOGEN_MAX_ROUNDS", "10")),
                "speaker_selection_method": os.getenv("SPEAKER_SELECTION", "auto")
            }
        }
        
        # Load from file if provided
        if config_path and Path(config_path).exists():
            try:
                with open(config_path, 'r') as f:
                    file_config = json.load(f)
                    config.update(file_config)
                self.logger.info(f"📄 Loaded configuration from {config_path}")
            except Exception as e:
                self.logger.error(f"Failed to load config file: {e}")
        
        # Load persona configurations
        config["personas"] = self._load_persona_configs()
        
        return config
    
    def _load_persona_configs(self) -> Dict[str, PersonaConfig]:
        """Load persona configurations"""
        return {
            "focused_artist": PersonaConfig(
                name="Focused Artist",
                orchestrator_prompt="""You are managing a VTuber who is a focused artist creating art.
                They value their creative flow and don't want to be constantly interrupted.
                Filter inputs based on relevance to current art project, importance/urgency,
                and viewer engagement level. Suppress general chatter but respond to art questions.""",
                filter_threshold=0.7,
                idle_behavior=IdleBehaviorConfig(
                    min_idle_time=15,
                    max_idle_time=45,
                    content_types={
                        "art_commentary": {"weight": 0.4, "examples": ["Let me add some shading here..."]},
                        "technique_explanation": {"weight": 0.3, "examples": ["This technique is called..."]},
                        "viewer_engagement": {"weight": 0.2, "examples": ["What do you think about this?"]},
                        "ambient_thoughts": {"weight": 0.1, "examples": ["*humming softly*"]}
                    }
                )
            ),
            "interactive_streamer": PersonaConfig(
                name="Interactive Streamer",
                orchestrator_prompt="""You are managing a highly interactive VTuber who loves engaging with chat.
                Pass through most viewer comments and create engaging responses.
                Prioritize questions, new viewer greetings, and interesting comments.
                Maintain high energy and responsiveness.""",
                filter_threshold=0.2,
                idle_behavior=IdleBehaviorConfig(
                    min_idle_time=8,
                    max_idle_time=20,
                    content_types={
                        "viewer_questions": {"weight": 0.4, "examples": ["So what's everyone up to today?"]},
                        "topic_starters": {"weight": 0.3, "examples": ["Let's talk about..."]},
                        "reactions": {"weight": 0.2, "examples": ["Oh, that's interesting!"]},
                        "games_activities": {"weight": 0.1, "examples": ["Should we play a quick game?"]}
                    }
                )
            ),
            "casual_gamer": PersonaConfig(
                name="Casual Gamer",
                orchestrator_prompt="""You are managing a casual gamer VTuber who balances gameplay with chat.
                Filter based on game relevance and timing - suppress during intense moments.
                Acknowledge important messages but batch responses when appropriate.""",
                filter_threshold=0.5,
                idle_behavior=IdleBehaviorConfig(
                    min_idle_time=10,
                    max_idle_time=30,
                    content_types={
                        "game_commentary": {"weight": 0.4, "examples": ["This level is tricky..."]},
                        "strategy_thoughts": {"weight": 0.3, "examples": ["Maybe I should try..."]},
                        "chat_acknowledgment": {"weight": 0.2, "examples": ["Good suggestion!"]},
                        "reactions": {"weight": 0.1, "examples": ["Whoa, didn't see that coming!"]}
                    }
                )
            )
        }
    
    def _initialize_agents(self) -> Dict[str, Optional[Agent]]:
        """Initialize all AutoGen agents"""
        if not AUTOGEN_AVAILABLE:
            self.logger.warning("AutoGen not available - agents will be mocked")
            return {}
        
        persona_name = self.config.get("current_persona", "interactive_streamer")
        persona_config = self.config["personas"].get(persona_name)
        
        if not persona_config:
            self.logger.warning(f"Unknown persona {persona_name}, using interactive_streamer")
            persona_config = self.config["personas"]["interactive_streamer"]
        
        llm_config = self.config["llm_config"]
        
        agents = {
            "orchestrator": create_orchestrator_agent(persona_config, llm_config),
            "content_filter": create_content_filter_agent(persona_config, llm_config),
            "speech_coordinator": create_speech_coordinator_agent(llm_config),
            "environment_controller": create_environment_controller_agent(llm_config),
            "idle_content": create_idle_content_agent(persona_config, llm_config),
            "autonomous_decision": create_autonomous_decision_agent(llm_config)
        }
        
        self.logger.info(f"🤖 Initialized {len(agents)} AutoGen agents")
        return agents
    
    def _initialize_group_chat(self):
        """Initialize AutoGen group chat for multi-agent coordination"""
        if not self.agents:
            return
        
        # Create group chat with all agents
        agent_list = [agent for agent in self.agents.values() if agent is not None]
        
        self.group_chat = GroupChat(
            agents=agent_list,
            messages=[],
            max_round=self.config["group_chat"]["max_rounds"],
            speaker_selection_method=self.config["group_chat"]["speaker_selection_method"]
        )
        
        # Create group chat manager with proper config
        manager_llm_config = {
            "config_list": [{
                "model": self.config["llm_config"].get("model", "gpt-3.5-turbo"),
                "api_key": self.config["llm_config"].get("api_key", ""),
                "temperature": 0.5,
                "max_tokens": self.config["llm_config"].get("max_tokens", 150)
            }],
            "timeout": 60,
            "cache_seed": None
        }
        
        self.chat_manager = GroupChatManager(
            groupchat=self.group_chat,
            llm_config=manager_llm_config
        )
        
        self.logger.info("🎭 Group chat initialized for multi-agent coordination")
    
    async def start(self):
        """Start the orchestrator and all background tasks"""
        if self.running:
            return
        
        self.running = True
        self.logger.info("🚀 Starting AutoGen Orchestrator V3")
        
        # Start decision loop
        self.decision_task = asyncio.create_task(self._decision_loop())
        
        # Start autonomous content loop if enabled
        if self.config.get("autonomous_enabled", True):
            self.autonomous_task = asyncio.create_task(self._autonomous_operation_loop())
        
        self.logger.info("✅ AutoGen Orchestrator V3 started successfully")
    
    async def stop(self):
        """Stop the orchestrator and cleanup resources"""
        if not self.running:
            return
        
        self.running = False
        self.logger.info("🛑 Stopping AutoGen Orchestrator V3")
        
        # Cancel background tasks
        for task in [self.decision_task, self.autonomous_task]:
            if task:
                task.cancel()
                try:
                    await task
                except asyncio.CancelledError:
                    pass
        
        self.logger.info("✅ AutoGen Orchestrator V3 stopped")
    
    async def _decision_loop(self):
        """Main decision loop for processing queued actions"""
        interval = self.config["timing"]["decision_interval"]
        self.logger.info(f"🧠 Decision loop started (interval: {interval}s)")
        
        while self.running:
            try:
                # Update state
                self.state_manager.update_idle_state()
                
                # Process action queue
                if await self._process_action_queue():
                    self.metrics["decisions_made"] += 1
                
                # Process speech queue (compatibility)
                elif await self._process_speech_queue():
                    self.metrics["decisions_made"] += 1
                
                # Dynamic sleep based on activity
                sleep_duration = self._calculate_dynamic_interval()
                await asyncio.sleep(sleep_duration)
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                self.logger.error(f"Error in decision loop: {e}")
                await asyncio.sleep(interval)
    
    async def _autonomous_operation_loop(self):
        """Background loop for autonomous content generation"""
        self.logger.info("🤖 Autonomous operation loop started")
        
        while self.running:
            try:
                current_time = datetime.now()
                idle_duration = self.state_manager.get_idle_duration()
                
                # Check if we should generate autonomous content
                if await self._should_generate_autonomous_content():
                    await self._generate_autonomous_content()
                    self.metrics["content_generated"] += 1
                
                # Dynamic sleep based on persona and activity
                sleep_duration = self._calculate_autonomous_interval()
                await asyncio.sleep(sleep_duration)
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                self.logger.error(f"Error in autonomous loop: {e}")
                await asyncio.sleep(5.0)
    
    async def process_external_input(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Process external input through AutoGen pipeline
        
        Args:
            input_data: Input data including text, source, metadata
            
        Returns:
            Processing result with decisions made
        """
        self.state_manager.update_interaction_time()
        
        # Create message for AutoGen agents
        message = {
            "role": "user",
            "content": f"External input received: {input_data.get('text', '')}",
            "metadata": input_data
        }
        
        # Run through AutoGen group chat if available
        if self.chat_manager:
            response = await self._run_agent_discussion(message)
            decisions = self._extract_decisions_from_discussion(response)
        else:
            # Fallback to direct processing
            decisions = await self._process_input_directly(input_data)
        
        # Execute decisions
        await self._execute_decisions(decisions)
        
        self.metrics["inputs_filtered"] += 1
        
        return {
            "processed": True,
            "decisions": decisions,
            "autogen_conversation": response if self.chat_manager else None
        }
    
    async def _run_agent_discussion(self, message: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Run multi-agent discussion through AutoGen"""
        if not self.chat_manager:
            return []
        
        try:
            # Get the orchestrator agent as the initial sender
            orchestrator_agent = self.agents.get("orchestrator")
            if not orchestrator_agent:
                self.logger.warning("No orchestrator agent available for discussion")
                return []
            
            # Get another agent as recipient (try content filter first, then idle content)
            recipient_agent = self.agents.get("content_filter") or self.agents.get("idle_content")
            if not recipient_agent:
                self.logger.warning("No recipient agent available for discussion")
                # Just return a simple decision without group chat
                return [{
                    "name": "orchestrator",
                    "content": f"DECISION: {message['content']}",
                    "role": "assistant"
                }]
            
            # Initiate chat between orchestrator and recipient
            orchestrator_agent.initiate_chat(
                recipient=recipient_agent,
                message=message["content"],
                clear_history=False
            )
            
            # Get conversation history from the chat manager or group chat
            if hasattr(self.group_chat, 'messages') and self.group_chat.messages:
                return self.group_chat.messages
            else:
                return []
            
        except Exception as e:
            self.logger.error(f"Error in agent discussion: {e}")
            return []
    
    async def _process_input_directly(self, input_data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Process input directly without AutoGen (fallback)"""
        text = input_data.get("text", "")
        source = input_data.get("source", "unknown")
        
        decisions = []
        
        # Simple filtering logic
        persona_config = self.config["personas"].get(self.config["current_persona"])
        if persona_config and persona_config.filter_threshold > 0.5:
            # High threshold - filter more aggressively
            if any(keyword in text.lower() for keyword in ["spam", "ad", "promo"]):
                decisions.append({
                    "type": "suppress",
                    "reason": "Filtered as spam/promotional content"
                })
                return decisions
        
        # Default: pass through as speech
        decisions.append({
            "type": "speech",
            "action": text,
            "priority": "medium",
            "reasoning": "Passing through to speech system"
        })
        
        return decisions
    
    def _extract_decisions_from_discussion(self, messages: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Extract actionable decisions from agent discussion"""
        decisions = []
        
        for message in messages:
            agent_name = message.get("name", "")
            content = message.get("content", "")
            
            # Extract decisions based on agent roles
            if agent_name == "orchestrator":
                # Orchestrator makes final decisions
                if "DECISION:" in content:
                    decision_text = content.split("DECISION:")[1].strip()
                    decisions.append(self._parse_decision(decision_text))
                    
            elif agent_name == "content_filter":
                # Filter agent recommendations
                if "FILTER:" in content:
                    filter_text = content.split("FILTER:")[1].strip()
                    if "suppress" in filter_text.lower():
                        decisions.append({
                            "type": "suppress",
                            "reason": filter_text
                        })
        
        return decisions
    
    def _parse_decision(self, decision_text: str) -> Dict[str, Any]:
        """Parse decision text into structured format"""
        decision = {
            "type": "unknown",
            "action": decision_text,
            "reasoning": ""
        }
        
        # Parse decision type
        if any(word in decision_text.lower() for word in ["speak", "say", "speech"]):
            decision["type"] = "speech"
        elif any(word in decision_text.lower() for word in ["environment", "scene", "game"]):
            decision["type"] = "environment"
        elif "suppress" in decision_text.lower():
            decision["type"] = "suppress"
        
        return decision
    
    async def _execute_decisions(self, decisions: List[Dict[str, Any]]):
        """Execute decisions made by AutoGen agents"""
        for decision in decisions:
            decision_type = decision.get("type")
            
            if decision_type == "speech":
                await self._queue_speech(
                    content=decision.get("action", ""),
                    priority=Priority.MEDIUM,
                    metadata={"source": "autogen_decision"}
                )
            elif decision_type == "environment":
                await self._queue_environment_change(
                    command=decision.get("action", ""),
                    parameters=decision.get("parameters", {})
                )
            elif decision_type == "suppress":
                self.logger.info(f"Suppressed input: {decision.get('reason', 'No reason')}")
    
    async def _should_generate_autonomous_content(self) -> bool:
        """Determine if autonomous content should be generated"""
        idle_duration = self.state_manager.get_idle_duration()
        timing_config = self.config["timing"]
        
        # Check minimum idle time
        if idle_duration < timing_config["min_idle_time"]:
            return False
        
        # Check speech gap
        speech_gap = time.time() - self.state.last_speech_completed
        if speech_gap < timing_config["min_speech_gap"]:
            return False
        
        # Check queue sizes
        if len(self.action_queue) + len(self.speech_queue) > 2:
            return False
        
        # Use AutoGen decision agent if available
        if self.agents.get("autonomous_decision"):
            return await self._consult_autonomous_decision_agent()
        
        return True
    
    async def _consult_autonomous_decision_agent(self) -> bool:
        """Consult the autonomous decision agent"""
        if not self.agents.get("autonomous_decision"):
            return True
        
        state_context = {
            "idle_duration": self.state_manager.get_idle_duration(),
            "viewer_count": self.state_manager.get_viewer_count(),
            "recent_topics": self.state_manager.get_recent_topics(),
            "current_activity": self.state.conversation_context.current_activity
        }
        
        message = f"""
        Current stream state: {json.dumps(state_context, indent=2)}
        Should we generate autonomous content now? Consider viewer engagement and timing.
        Respond with YES or NO and brief reasoning.
        """
        
        try:
            response = self.agents["autonomous_decision"].generate_reply(
                messages=[{"role": "user", "content": message}]
            )
            
            # Handle None response
            if response is None:
                self.logger.warning(f"Decision agent returned None response, defaulting to True. LLM config: {self.config['llm_config']}")
                return True
            
            # Handle non-string response
            if not isinstance(response, str):
                self.logger.warning(f"Decision agent returned non-string response: {type(response)}, defaulting to True")
                return True
            
            return "yes" in response.lower()
            
        except Exception as e:
            self.logger.error(f"Error consulting decision agent: {e}")
            return True
    
    async def _generate_autonomous_content(self):
        """Generate autonomous content using content strategies"""
        # Get SCB context if available
        scb_context_str = ""
        if self.scb_client:
            try:
                scb_context = self.scb_client.get_context_for_decision()
                if scb_context:
                    scb_context_str = self.scb_client.format_context_for_prompt(scb_context)
                    self.logger.debug(f"SCB Context available: {len(scb_context_str)} chars")
            except Exception as e:
                self.logger.warning(f"Failed to get SCB context: {e}")
        
        # Get content from strategy manager
        content_strategy = self.content_strategy_manager.select_strategy(self.state_manager)
        content = self.content_strategy_manager.generate_content(content_strategy, self.state_manager)
        
        if not content:
            return
        
        # Use idle content agent for enhancement if available
        if self.agents.get("idle_content"):
            content = await self._enhance_content_with_agent(content, content_strategy, scb_context_str)
        elif scb_context_str:
            # If no agent available but SCB context exists, incorporate it directly
            content = f"{content} {scb_context_str[:50]}..." if len(scb_context_str) > 50 else f"{content} {scb_context_str}"
        
        # Queue the content
        await self._queue_speech(
            content=content,
            priority=Priority.LOW,
            metadata={
                "source": "autonomous_content",
                "strategy": content_strategy.value,
                "is_autonomous": True,
                "has_scb_context": bool(scb_context_str)
            }
        )
        
        # Update state
        self.state_manager.update_autonomous_generation_time()
        self.content_strategy_manager.record_content_generation(content_strategy, content)
    
    async def _enhance_content_with_agent(self, content: str, strategy: ContentStrategy, scb_context: str = "") -> str:
        """Enhance content using the idle content agent"""
        if not self.agents.get("idle_content"):
            return content
        
        try:
            context = {
                "strategy": strategy.value,
                "recent_topics": self.state_manager.get_recent_topics(),
                "viewer_interests": self.state.conversation_context.user_interests
            }
            
            # Include SCB context if available
            if scb_context:
                context["scb_memory"] = scb_context
            
            message = f"""
            Enhance this autonomous content for a VTuber stream:
            Original: {content}
            Context: {json.dumps(context, indent=2)}
            {"SCB Memory Context: " + scb_context if scb_context else ""}
            Keep it natural, engaging, and under 100 characters.
            """
            
            response = self.agents["idle_content"].generate_reply(
                messages=[{"role": "user", "content": message}]
            )
            
            # Handle None response
            if response is None:
                self.logger.warning("Content enhancement agent returned None response, using original content")
                return content
            
            # Handle non-string response
            if not isinstance(response, str):
                self.logger.warning(f"Content enhancement agent returned non-string response: {type(response)}, using original")
                return content
            
            enhanced = response.strip()
            return enhanced if enhanced else content
            
        except Exception as e:
            self.logger.error(f"Error enhancing content: {e}")
            return content
    
    async def _queue_speech(self, content: str, priority: Priority, metadata: Dict[str, Any] = None):
        """Queue speech request"""
        speech = SpeechRequest(
            content=content,
            priority=priority,
            is_autonomous=metadata.get("is_autonomous", False) if metadata else False,
            metadata=metadata or {}
        )
        
        self.speech_queue.append(speech)
        self.speech_queue.sort(key=lambda s: (-s.priority.value, s.timestamp))
        
        self.logger.debug(f"Queued speech: {content[:50]}... (priority: {priority.name})")
    
    async def _queue_environment_change(self, command: str, parameters: Dict[str, Any]):
        """Queue environment change request"""
        action = ActionRequest(
            action_type=ActionType.ENVIRONMENT,
            content=command,
            priority=Priority.MEDIUM,
            environment_action=command,
            environment_params=parameters,
            metadata={"source": "autogen_environment"}
        )
        
        self.action_queue.append(action)
        self.action_queue.sort(key=lambda a: (-a.priority.value, a.timestamp))
        
        self.logger.debug(f"Queued environment change: {command}")
        self.metrics["environment_changes"] += 1
    
    async def _process_action_queue(self) -> bool:
        """Process the action queue"""
        if not self.action_queue:
            return False
        
        action = self.action_queue.pop(0)
        
        if action.action_type == ActionType.SPEECH:
            await self._execute_speech_action(action)
        elif action.action_type == ActionType.ENVIRONMENT:
            await self._execute_environment_action(action)
        
        return True
    
    async def _process_speech_queue(self) -> bool:
        """Process the speech queue (compatibility)"""
        if not self.speech_queue:
            return False
        
        speech = self.speech_queue.pop(0)
        
        # Update state
        self.state.is_speaking = True
        self.state.current_speech_id = speech.id
        self.state.speech_start_time = time.time()
        
        # Send to TTS system
        await self._send_speech_to_tts(speech)
        
        return True
    
    async def _execute_speech_action(self, action: ActionRequest):
        """Execute a speech action"""
        speech_content = action.speech_content or action.content
        
        speech = SpeechRequest(
            content=speech_content,
            priority=action.priority,
            is_autonomous=action.metadata.get("is_autonomous", False),
            metadata=action.metadata
        )
        
        self.state.is_speaking = True
        self.state.current_speech_id = speech.id
        self.state.speech_start_time = time.time()
        
        await self._send_speech_to_tts(speech)
    
    async def _execute_environment_action(self, action: ActionRequest):
        """Execute an environment action"""
        self.logger.info(f"🌍 Executing environment action: {action.environment_action}")
        
        # Send to game control system
        try:
            import aiohttp
            async with aiohttp.ClientSession() as session:
                payload = {
                    "prompt": action.environment_action,
                    "autonomous_context": {
                        "source": "autogen_orchestrator",
                        "parameters": action.environment_params
                    }
                }
                
                async with session.post("http://localhost:5001/game_control", json=payload) as response:
                    if response.status == 200:
                        self.logger.info("✅ Environment action executed successfully")
                    else:
                        self.logger.error(f"Failed to execute environment action: {response.status}")
                        
        except Exception as e:
            self.logger.error(f"Error executing environment action: {e}")
    
    async def _send_speech_to_tts(self, speech: SpeechRequest):
        """Send speech to TTS system"""
        try:
            import aiohttp
            async with aiohttp.ClientSession() as session:
                payload = {
                    "text": speech.content,
                    "direct_speech": True,
                    "autonomous_context": {
                        "source": "autogen_orchestrator_v3",
                        "speech_id": speech.id,
                        "priority": speech.priority.value,
                        "is_autonomous": speech.is_autonomous,
                        **speech.metadata
                    }
                }
                
                async with session.post("http://localhost:5001/process_text", json=payload) as response:
                    if response.status == 200:
                        self.logger.info(f"✅ Speech sent to TTS: {speech.id[:8]}")
                    else:
                        self.logger.error(f"Failed to send speech: {response.status}")
                        
        except Exception as e:
            self.logger.error(f"Error sending speech: {e}")
            self.state.is_speaking = False
            self.state.current_speech_id = None
    
    def _calculate_dynamic_interval(self) -> float:
        """Calculate dynamic decision interval based on activity"""
        base_interval = self.config["timing"]["decision_interval"]
        
        # Speed up if user recently interacted
        if self.state_manager.get_idle_duration() < 30:
            return base_interval * 0.7
        
        # Slow down if very idle
        if self.state_manager.get_idle_duration() > 120:
            return base_interval * 1.5
        
        return base_interval
    
    def _calculate_autonomous_interval(self) -> float:
        """Calculate autonomous content generation interval"""
        persona_config = self.config["personas"].get(self.config["current_persona"])
        if not persona_config:
            return 10.0
        
        idle_config = persona_config.idle_behavior
        base_interval = (idle_config.min_idle_time + idle_config.max_idle_time) / 2
        
        # Adjust based on viewer count
        viewer_factor = min(self.state_manager.get_viewer_count() / 100, 2.0)
        
        return base_interval / max(viewer_factor, 0.5)
    
    def _on_speech_complete(self):
        """Callback when speech/blendshape completes"""
        self.state.is_speaking = False
        self.state.blendshape_active = False
        self.state.last_speech_completed = time.time()
        self.state.current_speech_id = None
        
        self.logger.info("Speech completed, state reset")
    
    def notify_speech_complete(self, speech_id: str = None):
        """External notification that speech has completed"""
        self.logger.info(f"🔊 Speech completion notification received: {speech_id[:8] if speech_id else 'unknown'}")
        
        # Verify this is the current speech
        if speech_id and self.state.current_speech_id != speech_id:
            self.logger.warning(f"Speech ID mismatch: expected {self.state.current_speech_id}, got {speech_id}")
        
        # Call the internal completion handler
        self._on_speech_complete()
        
        # Update blendshape monitor if needed
        if hasattr(self, 'blendshape_monitor'):
            self.blendshape_monitor.on_blendshape_complete()
    
    def get_status(self) -> Dict[str, Any]:
        """Get comprehensive orchestrator status"""
        uptime = time.time() - self.metrics["start_time"]
        
        return {
            "running": self.running,
            "enabled": self.enabled,
            "persona": self.config.get("current_persona"),
            "state": {
                "is_speaking": self.state.is_speaking,
                "idle_duration": self.state_manager.get_idle_duration(),
                "speech_queue_size": len(self.speech_queue),
                "action_queue_size": len(self.action_queue)
            },
            "agents": {
                name: agent is not None for name, agent in self.agents.items()
            },
            "metrics": {
                **self.metrics,
                "uptime_seconds": uptime,
                "decisions_per_minute": (self.metrics["decisions_made"] / uptime) * 60 if uptime > 0 else 0
            },
            "configuration": {
                "autogen_enabled": AUTOGEN_AVAILABLE,
                "scb_enabled": self.scb_client is not None,
                "autonomous_enabled": self.config.get("autonomous_enabled", True)
            }
        }
    
    async def update_persona(self, persona_name: str) -> bool:
        """Update the current persona and reinitialize agents"""
        if persona_name not in self.config["personas"]:
            self.logger.error(f"Unknown persona: {persona_name}")
            return False
        
        self.config["current_persona"] = persona_name
        
        # Reinitialize agents with new persona
        self.agents = self._initialize_agents()
        
        # Reinitialize group chat
        if AUTOGEN_AVAILABLE:
            self._initialize_group_chat()
        
        # Update content strategy manager
        self.content_strategy_manager.update_persona(persona_name)
        
        self.logger.info(f"✅ Persona updated to: {persona_name}")
        return True
    
    async def process_external_event(self, event_type: str, payload: Dict[str, Any]):
        """Process external events (viewer joins, donations, etc.)"""
        self.logger.info(f"Processing external event: {event_type}")
        
        # Update state based on event
        if event_type == "new_viewers":
            names = payload.get("names", [])
            self.state_manager.add_viewers(names)
            
            # Generate welcome message
            if names and self.config.get("autonomous_enabled", True):
                welcome_content = f"Welcome to the stream, {', '.join(names[:3])}!"
                if len(names) > 3:
                    welcome_content += f" And welcome to {len(names) - 3} others!"
                
                await self._queue_speech(
                    content=welcome_content,
                    priority=Priority.HIGH,
                    metadata={"source": "viewer_greeting", "event_type": event_type}
                )
        
        elif event_type == "change_subject":
            topic = payload.get("topic", "")
            if topic:
                self.state_manager.update_conversation_topic(topic)
                
                # Generate topic transition
                transition_content = f"Let's talk about {topic}! That's an interesting topic."
                await self._queue_speech(
                    content=transition_content,
                    priority=Priority.URGENT,
                    metadata={"source": "topic_change", "event_type": event_type}
                )
        
        # Store event in SCB if available
        if self.scb_client:
            try:
                event_text = payload.get("text", str(payload))
                self.scb_client.append_event(event_type, event_text)
            except Exception as e:
                self.logger.warning(f"Failed to store event in SCB: {e}")


def create_autogen_orchestrator_v3(**kwargs) -> AutoGenOrchestratorV3:
    """
    Factory function to create an AutoGen Orchestrator V3 instance
    
    Args:
        **kwargs: Configuration overrides
        
    Returns:
        Configured AutoGenOrchestratorV3 instance
    """
    return AutoGenOrchestratorV3(**kwargs)


# Compatibility exports
__all__ = [
    'AutoGenOrchestratorV3',
    'create_autogen_orchestrator_v3',
    'ActionType',
    'Priority'
]