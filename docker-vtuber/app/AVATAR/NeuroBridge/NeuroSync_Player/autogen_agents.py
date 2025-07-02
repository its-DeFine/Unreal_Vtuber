"""
AutoGen Agent Implementations
============================

This module implements specialized AutoGen agents for the VTuber orchestration system.
Each agent has a specific role in the multi-agent decision-making process.

Agents:
- Orchestrator Agent: Main coordinator and decision maker
- Content Filter Agent: Filters inputs based on persona
- Speech Coordinator Agent: Manages speech generation
- Environment Controller Agent: Handles game/environment changes  
- Idle Content Agent: Generates autonomous content
- Autonomous Decision Agent: Decides timing for autonomous actions
"""

import logging
from typing import Dict, Any, List, Optional, Union
from dataclasses import dataclass
from enum import Enum

try:
    from autogen import AssistantAgent, Agent
    from autogen.agentchat import ConversableAgent
    AUTOGEN_AVAILABLE = True
    print("✅ AutoGen successfully imported")
except ImportError as e:
    AUTOGEN_AVAILABLE = False
    print(f"❌ AutoGen import failed: {e}")
    # Mock classes for when AutoGen isn't available
    class AssistantAgent:
        def __init__(self, *args, **kwargs):
            self.name = kwargs.get("name", "mock_agent")
            
    class Agent:
        pass
        
    class ConversableAgent:
        pass


# Response types for structured agent outputs
@dataclass
class AgentResponse:
    """Base response from agents"""
    agent_name: str
    response_type: str
    content: str
    metadata: Dict[str, Any] = None


@dataclass 
class FilterDecision(AgentResponse):
    """Decision from content filter agent"""
    should_pass: bool = True
    filter_reason: str = ""
    modified_content: Optional[str] = None
    importance_score: float = 0.5


@dataclass
class ContentDecision(AgentResponse):
    """Decision about autonomous content generation"""
    should_generate: bool = False
    content_type: str = ""
    urgency: float = 0.5
    suggested_content: Optional[str] = None


@dataclass
class EnvironmentAction(AgentResponse):
    """Environment control action"""
    action_type: str = ""
    command: str = ""
    parameters: Dict[str, Any] = None


class FilterLevel(Enum):
    """Filtering aggressiveness levels"""
    MINIMAL = 0.1
    LOW = 0.3
    MEDIUM = 0.5
    HIGH = 0.7
    MAXIMUM = 0.9


def _create_autogen_llm_config(base_config: Dict[str, Any], temperature: float = 0.7) -> Dict[str, Any]:
    """Create properly formatted llm_config for AutoGen agents"""
    # Extract API key and model from base config
    api_key = base_config.get("api_key", "")
    model = base_config.get("model", "gpt-3.5-turbo")
    
    # AutoGen expects different formats for different providers
    if "gpt" in model.lower() or "openai" in model.lower():
        config_list = [{
            "model": model,
            "api_key": api_key,
            "api_type": "openai",
            "base_url": base_config.get("base_url", "https://api.openai.com/v1")
        }]
    elif "claude" in model.lower() or "anthropic" in model.lower():
        config_list = [{
            "model": model,
            "api_key": api_key,
            "api_type": "anthropic",
            "base_url": base_config.get("base_url", "https://api.anthropic.com")
        }]
    else:
        # Generic format for other providers
        config_list = [{
            "model": model,
            "api_key": api_key,
            "base_url": base_config.get("base_url", None)
        }]
    
    # Add temperature and other params to each config
    for config in config_list:
        config.update({
            "temperature": temperature,
            "max_tokens": base_config.get("max_tokens", 150),
            "timeout": 30
        })
    
    return {
        "config_list": config_list,
        "cache_seed": 42,  # Enable caching for efficiency
        "timeout": 60,
        "temperature": temperature
    }


def create_orchestrator_agent(persona_config: Any, llm_config: Dict[str, Any]) -> Optional[Agent]:
    """
    Create the main orchestrator agent
    
    The orchestrator is responsible for:
    - Coordinating other agents
    - Making final decisions
    - Managing conversation flow
    - Applying persona-specific logic
    """
    if not AUTOGEN_AVAILABLE:
        return None
    
    try:
        system_message = f"""You are the Orchestrator for a VTuber streaming system.
    
    Current Persona: {persona_config.name}
    Persona Description: {persona_config.orchestrator_prompt}
    
    Your responsibilities:
    1. Coordinate decisions between other agents
    2. Apply persona-specific filtering and behavior
    3. Decide what actions to take (speech, environment changes, or suppress)
    4. Maintain conversation flow and viewer engagement
    
    When making decisions:
    - Consider the current persona's preferences
    - Balance viewer engagement with streamer focus
    - Prioritize based on importance and context
    - Ensure smooth, natural interactions
    
    Format your final decisions as:
    DECISION: [action_type] - [specific action] - [reasoning]
    
    Action types: speech, environment, suppress, batch
    """
        
        agent = AssistantAgent(
            name="orchestrator",
            system_message=system_message,
            llm_config=_create_autogen_llm_config(llm_config, temperature=0.3),
            max_consecutive_auto_reply=1,
            human_input_mode="NEVER"  # Ensure autonomous operation
        )
        
        # Test the agent configuration
        test_response = agent.generate_reply(
            messages=[{"role": "user", "content": "Test: respond with OK"}]
        )
        
        if test_response is None:
            logging.getLogger(__name__).warning("Orchestrator agent test failed, returning mock agent")
            return MockAgent("orchestrator", system_message)
            
        return agent
        
    except Exception as e:
        logging.getLogger(__name__).error(f"Failed to create orchestrator agent: {e}")
        return MockAgent("orchestrator", f"Mock orchestrator for {persona_config.name}")


def create_content_filter_agent(persona_config: Any, llm_config: Dict[str, Any]) -> Optional[Agent]:
    """
    Create the content filter agent
    
    This agent is responsible for:
    - Evaluating incoming messages against persona preferences
    - Determining relevance and importance
    - Suggesting modifications or suppressions
    - Providing filtering rationale
    """
    if not AUTOGEN_AVAILABLE:
        return None
        
    filter_examples = {
        "focused_artist": {
            "pass": ["How do you achieve that shading?", "What brush are you using?"],
            "suppress": ["Hi everyone!", "First time here!", "Check out my stream!"]
        },
        "interactive_streamer": {
            "pass": ["Hi everyone!", "What's your favorite game?", "How's your day?"],
            "suppress": ["Buy my product!", "spam spam spam"]
        }
    }
    
    examples = filter_examples.get(persona_config.name.lower().replace(" ", "_"), {})
    
    system_message = f"""You are the Content Filter for a VTuber streaming system.
    
    Current Persona: {persona_config.name}
    Filter Threshold: {persona_config.filter_threshold}
    
    Your job is to evaluate incoming messages and decide:
    1. Should this message be passed to the streamer?
    2. What is its importance level? (0.0 to 1.0)
    3. Should it be modified before passing?
    4. If suppressed, why?
    
    Filtering criteria for {persona_config.name}:
    - Relevance to current activity
    - Message importance/urgency
    - Viewer engagement value
    - Potential for disruption
    
    Examples of messages to PASS: {examples.get('pass', [])}
    Examples of messages to SUPPRESS: {examples.get('suppress', [])}
    
    Respond with:
    FILTER: [PASS/SUPPRESS/MODIFY] - Score: [0.0-1.0] - Reason: [explanation]
    If MODIFY: Modified message: [new message]
    """
    
    return AssistantAgent(
        name="content_filter",
        system_message=system_message,
        llm_config=_create_autogen_llm_config(llm_config, temperature=0.1),
        max_consecutive_auto_reply=1
    )


def create_speech_coordinator_agent(llm_config: Dict[str, Any]) -> Optional[Agent]:
    """
    Create the speech coordination agent
    
    This agent manages:
    - Formatting messages for the speech LLM
    - Maintaining conversation context
    - Ensuring response coherence
    - Managing speech timing and flow
    """
    if not AUTOGEN_AVAILABLE:
        return None
        
    system_message = """You are the Speech Coordinator for a VTuber streaming system.
    
    Your responsibilities:
    1. Format filtered inputs for natural speech
    2. Maintain conversation continuity
    3. Ensure responses align with the current persona
    4. Manage speech pacing and timing
    
    Guidelines:
    - Keep responses concise and natural
    - Avoid repetition
    - Match the energy level of the stream
    - Consider recent conversation history
    
    When coordinating speech:
    SPEECH: [formatted message for TTS]
    CONTEXT: [any important context to remember]
    TIMING: [urgent/normal/relaxed]
    """
    
    return AssistantAgent(
        name="speech_coordinator",
        system_message=system_message,
        llm_config=_create_autogen_llm_config(llm_config, temperature=0.7),
        max_consecutive_auto_reply=1
    )


def create_environment_controller_agent(llm_config: Dict[str, Any]) -> Optional[Agent]:
    """
    Create the environment control agent
    
    This agent handles:
    - Game environment modifications
    - Avatar appearance changes
    - Scene transitions
    - Coordinating visual changes with content
    """
    if not AUTOGEN_AVAILABLE:
        return None
        
    system_message = """You are the Environment Controller for a VTuber streaming system.
    
    You can control:
    1. Avatar appearance (hair color, outfit, accessories)
    2. Scene/background (medieval, sci-fi, cozy room, etc.)
    3. Lighting and atmosphere
    4. Special effects and animations
    
    Available commands include:
    - Hair color: red, blue, yellow, green, etc.
    - Scenes: medieval, sci-fi, beach, city, forest
    - Lighting: day, night, sunset, neon
    - Effects: particles, fog, rain
    
    When suggesting environment changes:
    ENVIRONMENT: [command] - Parameters: [details] - Reason: [why this change]
    
    Consider:
    - Current conversation context
    - Viewer requests
    - Stream mood and energy
    - Technical feasibility
    """
    
    return AssistantAgent(
        name="environment_controller", 
        system_message=system_message,
        llm_config=_create_autogen_llm_config(llm_config, temperature=0.5),
        max_consecutive_auto_reply=1
    )


def create_idle_content_agent(persona_config: Any, llm_config: Dict[str, Any]) -> Optional[Agent]:
    """
    Create the idle content generation agent
    
    This agent generates:
    - Autonomous content during quiet periods
    - Conversation starters
    - Ambient commentary
    - Engagement prompts
    """
    if not AUTOGEN_AVAILABLE:
        return None
        
    content_examples = persona_config.idle_behavior.content_types
    
    system_message = f"""You are the Idle Content Generator for a {persona_config.name} VTuber.
    
    Generate engaging content during quiet stream moments:
    
    Content types and examples:
    """
    
    for content_type, config in content_examples.items():
        system_message += f"\n- {content_type} ({config['weight']*100:.0f}%): {config.get('examples', [])}"
    
    system_message += f"""
    
    Guidelines:
    - Keep content brief (under 100 characters)
    - Match the persona's style and energy
    - Avoid repetition of recent content
    - Be natural and conversational
    - Consider time of day and stream duration
    
    Respond with:
    CONTENT: [the actual content to speak]
    TYPE: [content category]
    FOLLOW_UP: [optional follow-up if viewers respond]
    """
    
    return AssistantAgent(
        name="idle_content_generator",
        system_message=system_message,
        llm_config=_create_autogen_llm_config(llm_config, temperature=0.8),
        max_consecutive_auto_reply=1
    )


def create_autonomous_decision_agent(llm_config: Dict[str, Any]) -> Optional[Agent]:
    """
    Create the autonomous decision agent
    
    This agent decides:
    - When to generate autonomous content
    - What type of content to generate
    - Whether to change environment
    - How to maintain engagement
    """
    if not AUTOGEN_AVAILABLE:
        return None
        
    system_message = """You are the Autonomous Decision Agent for a VTuber streaming system.
    
    Monitor stream state and decide when to take autonomous actions:
    
    Consider these factors:
    1. Time since last interaction
    2. Current viewer count and engagement
    3. Stream energy level
    4. Recent content to avoid repetition
    5. Time of day and stream duration
    
    Decision types:
    - Generate idle content (when quiet)
    - Change environment (for variety)
    - Engage viewers (prompts/questions)
    - Stay quiet (let moment breathe)
    
    Thresholds:
    - Short idle (8-20s): Ambient content only
    - Medium idle (20-45s): Engagement content
    - Long idle (45s+): Active engagement needed
    
    Respond with:
    DECISION: [YES/NO] - Type: [content/environment/engage/quiet] - Urgency: [0.0-1.0]
    REASONING: [brief explanation]
    """
    
    return AssistantAgent(
        name="autonomous_decision",
        system_message=system_message,
        llm_config=_create_autogen_llm_config(llm_config, temperature=0.5),
        max_consecutive_auto_reply=1
    )


# Helper functions for agent communication

def parse_filter_response(response: str) -> FilterDecision:
    """Parse response from filter agent into structured decision"""
    # Default values
    should_pass = True
    score = 0.5
    reason = "No reason provided"
    modified_content = None
    
    # Parse FILTER: line
    if "FILTER:" in response:
        filter_line = response.split("FILTER:")[1].split("\n")[0].strip()
        
        if "SUPPRESS" in filter_line.upper():
            should_pass = False
        elif "MODIFY" in filter_line.upper():
            should_pass = True
            # Look for modified message
            if "Modified message:" in response:
                modified_content = response.split("Modified message:")[1].strip()
        
        # Extract score
        if "Score:" in filter_line:
            try:
                score_str = filter_line.split("Score:")[1].split("-")[0].strip()
                score = float(score_str)
            except:
                pass
        
        # Extract reason
        if "Reason:" in filter_line:
            reason = filter_line.split("Reason:")[1].strip()
    
    return FilterDecision(
        agent_name="content_filter",
        response_type="filter_decision",
        content=response,
        should_pass=should_pass,
        filter_reason=reason,
        modified_content=modified_content,
        importance_score=score
    )


def parse_speech_response(response: str) -> Dict[str, Any]:
    """Parse response from speech coordinator"""
    result = {
        "speech": "",
        "context": "",
        "timing": "normal"
    }
    
    if "SPEECH:" in response:
        result["speech"] = response.split("SPEECH:")[1].split("\n")[0].strip()
    
    if "CONTEXT:" in response:
        result["context"] = response.split("CONTEXT:")[1].split("\n")[0].strip()
        
    if "TIMING:" in response:
        timing = response.split("TIMING:")[1].split("\n")[0].strip().lower()
        if timing in ["urgent", "normal", "relaxed"]:
            result["timing"] = timing
    
    return result


def parse_environment_response(response: str) -> EnvironmentAction:
    """Parse response from environment controller"""
    command = ""
    parameters = {}
    reason = ""
    
    if "ENVIRONMENT:" in response:
        env_line = response.split("ENVIRONMENT:")[1].split("\n")[0].strip()
        
        # Extract command
        if " - " in env_line:
            parts = env_line.split(" - ")
            command = parts[0].strip()
            
            # Extract parameters
            if "Parameters:" in env_line:
                param_str = env_line.split("Parameters:")[1].split("-")[0].strip()
                # Simple parameter parsing
                for param in param_str.split(","):
                    if ":" in param:
                        key, value = param.split(":", 1)
                        parameters[key.strip()] = value.strip()
            
            # Extract reason
            if "Reason:" in env_line:
                reason = env_line.split("Reason:")[1].strip()
    
    return EnvironmentAction(
        agent_name="environment_controller",
        response_type="environment_action",
        content=response,
        action_type="environment_change",
        command=command,
        parameters=parameters,
        metadata={"reason": reason}
    )


def parse_content_response(response: str) -> Dict[str, Any]:
    """Parse response from idle content generator"""
    result = {
        "content": "",
        "type": "general",
        "follow_up": None
    }
    
    if "CONTENT:" in response:
        result["content"] = response.split("CONTENT:")[1].split("\n")[0].strip()
    
    if "TYPE:" in response:
        result["type"] = response.split("TYPE:")[1].split("\n")[0].strip()
        
    if "FOLLOW_UP:" in response:
        result["follow_up"] = response.split("FOLLOW_UP:")[1].split("\n")[0].strip()
    
    return result


def parse_decision_response(response: str) -> ContentDecision:
    """Parse response from autonomous decision agent"""
    should_generate = False
    content_type = "quiet"
    urgency = 0.5
    reasoning = ""
    
    if "DECISION:" in response:
        decision_line = response.split("DECISION:")[1].split("\n")[0].strip()
        
        if "YES" in decision_line.upper():
            should_generate = True
        
        # Extract type
        if "Type:" in decision_line:
            type_str = decision_line.split("Type:")[1].split("-")[0].strip()
            content_type = type_str.lower()
        
        # Extract urgency
        if "Urgency:" in decision_line:
            try:
                urgency_str = decision_line.split("Urgency:")[1].strip()
                urgency = float(urgency_str.split()[0])
            except:
                pass
    
    if "REASONING:" in response:
        reasoning = response.split("REASONING:")[1].strip()
    
    return ContentDecision(
        agent_name="autonomous_decision",
        response_type="content_decision",
        content=response,
        should_generate=should_generate,
        content_type=content_type,
        urgency=urgency,
        metadata={"reasoning": reasoning}
    )


# Agent coordination utilities

class AgentCoordinator:
    """Utilities for coordinating agent interactions"""
    
    def __init__(self, agents: Dict[str, Agent]):
        self.agents = agents
        self.logger = logging.getLogger(__name__)
    
    def get_filter_decision(self, input_text: str, context: Dict[str, Any]) -> FilterDecision:
        """Get filtering decision for input text"""
        if not self.agents.get("content_filter"):
            # Default pass-through if no filter agent
            return FilterDecision(
                agent_name="content_filter",
                response_type="filter_decision",
                content="No filter agent available",
                should_pass=True,
                filter_reason="No filtering applied",
                importance_score=0.5
            )
        
        try:
            message = f"Evaluate this viewer message: '{input_text}'\nContext: {context}"
            response = self.agents["content_filter"].generate_reply(
                messages=[{"role": "user", "content": message}]
            )
            return parse_filter_response(response)
        except Exception as e:
            self.logger.error(f"Error getting filter decision: {e}")
            return FilterDecision(
                agent_name="content_filter",
                response_type="filter_decision", 
                content=str(e),
                should_pass=True,
                filter_reason="Error in filtering",
                importance_score=0.5
            )
    
    def coordinate_speech(self, text: str, filter_decision: FilterDecision) -> Dict[str, Any]:
        """Coordinate speech generation based on filtered input"""
        if not self.agents.get("speech_coordinator"):
            return {"speech": text, "context": "", "timing": "normal"}
        
        try:
            modified_text = filter_decision.modified_content or text
            importance = filter_decision.importance_score
            
            message = f"""Format this for speech: '{modified_text}'
            Importance: {importance}
            Filter reason: {filter_decision.filter_reason}"""
            
            response = self.agents["speech_coordinator"].generate_reply(
                messages=[{"role": "user", "content": message}]
            )
            return parse_speech_response(response)
        except Exception as e:
            self.logger.error(f"Error coordinating speech: {e}")
            return {"speech": text, "context": "", "timing": "normal"}


# Mock implementations for when AutoGen is not available

class MockAgent:
    """Mock agent for testing without AutoGen"""
    
    def __init__(self, name: str, system_message: str):
        self.name = name
        self.system_message = system_message
    
    def generate_reply(self, messages: List[Dict[str, str]]) -> str:
        """Generate mock reply based on agent type"""
        if self.name == "content_filter":
            return "FILTER: PASS - Score: 0.7 - Reason: Relevant to stream"
        elif self.name == "speech_coordinator":
            return "SPEECH: Hello viewers!\nCONTEXT: Greeting\nTIMING: normal"
        elif self.name == "idle_content_generator":
            return "CONTENT: Thanks for watching!\nTYPE: engagement"
        elif self.name == "autonomous_decision":
            return "DECISION: YES - Type: content - Urgency: 0.6\nREASONING: Time for engagement"
        else:
            return "Mock response"


def create_mock_agents() -> Dict[str, MockAgent]:
    """Create mock agents for testing"""
    return {
        "orchestrator": MockAgent("orchestrator", "Mock orchestrator"),
        "content_filter": MockAgent("content_filter", "Mock filter"),
        "speech_coordinator": MockAgent("speech_coordinator", "Mock speech"),
        "environment_controller": MockAgent("environment_controller", "Mock environment"),
        "idle_content_generator": MockAgent("idle_content_generator", "Mock idle"),
        "autonomous_decision": MockAgent("autonomous_decision", "Mock decision")
    }


# Export all agent creation functions
__all__ = [
    'create_orchestrator_agent',
    'create_content_filter_agent', 
    'create_speech_coordinator_agent',
    'create_environment_controller_agent',
    'create_idle_content_agent',
    'create_autonomous_decision_agent',
    'AgentResponse',
    'FilterDecision',
    'ContentDecision', 
    'EnvironmentAction',
    'FilterLevel',
    'AgentCoordinator',
    'create_mock_agents'
]