# Product Requirements Document: AutoGen-Based Orchestrator for Autonomous VTuber System

## Executive Summary

This PRD outlines the implementation of a Microsoft AutoGen-based orchestrator to replace the current autonomous orchestrator in the VTuber system. The new orchestrator will leverage AutoGen's multi-agent capabilities to create a more sophisticated decision-making system that can handle external inputs, filter them based on configurable prompts, and coordinate speech generation and game environment changes.

## Current System Analysis

### Existing Architecture
- **Current Orchestrator**: `/autonomous_orchestrator_v2.py` - A custom Python-based orchestrator with:
  - State management for speech and idle tracking
  - Content generation with contextual awareness
  - Priority-based action queuing
  - SCB (System Context Buffer) integration
  - External event handling via HTTP endpoints

- **Integration Point**: `/llm_to_face.py` - The main application that:
  - Handles HTTP requests on port 5001
  - Processes text and game control commands
  - Integrates with the orchestrator for autonomous decisions
  - Manages TTS (Text-to-Speech) and game control systems

## Proposed AutoGen Architecture

### Core Components

#### 1. Orchestrator Agent (Primary)
The main coordinator agent responsible for:
- Receiving and processing external inputs (viewer comments, tweets, system events)
- Applying configurable filtering logic based on the streamer's persona
- Deciding whether to pass information to the Speech LLM
- Managing conversation flow and priorities

#### 2. Content Filter Agent
A specialized agent for:
- Evaluating incoming messages against the current persona/prompt
- Determining relevance and importance of external inputs
- Providing reasoning for filtering decisions

#### 3. Speech Generation Agent
Manages communication with the existing Speech LLM:
- Formats filtered inputs for the LLM
- Maintains conversation context
- Ensures responses align with the configured persona

#### 4. Environment Control Agent
Handles game environment modifications:
- Processes environmental change requests
- Coordinates with the game control system
- Maintains environmental state consistency

### AutoGen Integration Approach

```python
# Proposed AutoGen agent structure
from autogen import Agent, AssistantAgent, UserProxyAgent, GroupChat, GroupChatManager
import asyncio
from datetime import datetime, timedelta

class AutoGenOrchestrator:
    def __init__(self, config):
        # Orchestrator Agent - Main coordinator
        self.orchestrator = AssistantAgent(
            name="orchestrator",
            system_message=config.orchestrator_prompt,
            llm_config={"model": "gpt-4", "temperature": 0.3}
        )
        
        # Content Filter Agent
        self.content_filter = AssistantAgent(
            name="content_filter",
            system_message=config.filter_prompt,
            llm_config={"model": "gpt-3.5-turbo", "temperature": 0.1}
        )
        
        # Speech Generation Coordinator
        self.speech_coordinator = AssistantAgent(
            name="speech_coordinator",
            system_message="Coordinate speech generation based on filtered inputs",
            llm_config={"model": "gpt-3.5-turbo", "temperature": 0.7}
        )
        
        # Environment Controller
        self.env_controller = AssistantAgent(
            name="environment_controller",
            system_message="Manage game environment changes",
            llm_config={"model": "gpt-3.5-turbo", "temperature": 0.5}
        )
        
        # Autonomous Content Generator
        self.idle_content_agent = AssistantAgent(
            name="idle_content_generator",
            system_message=config.idle_content_prompt,
            llm_config={"model": "gpt-3.5-turbo", "temperature": 0.8}
        )
        
        # Autonomous Decision Maker
        self.autonomous_decision_agent = AssistantAgent(
            name="autonomous_decision",
            system_message=config.autonomous_decision_prompt,
            llm_config={"model": "gpt-3.5-turbo", "temperature": 0.5}
        )
        
        # Group chat for multi-agent coordination
        self.group_chat = GroupChat(
            agents=[self.orchestrator, self.content_filter, 
                   self.speech_coordinator, self.env_controller,
                   self.idle_content_agent, self.autonomous_decision_agent],
            messages=[],
            max_round=10
        )
        
        self.manager = GroupChatManager(groupchat=self.group_chat)
        
        # State tracking for autonomous operation
        self.state = {
            "last_interaction": datetime.now(),
            "last_autonomous_content": datetime.now(),
            "content_history": [],
            "viewer_count": 0,
            "current_activity": None
        }
        
        # Start continuous operation loop
        self.autonomous_task = None
```

## Functional Requirements

### 1. Autonomous Content Generation

#### Continuous Operation Mode
The orchestrator must maintain engaging content even without external stimuli. This is critical for maintaining viewer engagement during quiet periods.

#### Idle Content Generation Strategy
```python
class IdleContentAgent(AssistantAgent):
    """Agent responsible for generating autonomous content during idle periods"""
    
    def __init__(self, persona_config):
        super().__init__(
            name="idle_content_generator",
            system_message=f"""
            You are responsible for keeping the stream engaging during quiet periods.
            Based on the persona '{persona_config.name}', generate appropriate content:
            - Commentary about current activity
            - Thoughts and observations
            - Interactive prompts for viewers
            - Story-telling or experiences
            
            Persona context: {persona_config.idle_behavior}
            """,
            llm_config={"model": "gpt-3.5-turbo", "temperature": 0.8}
        )
```

#### Idle Behavior Configuration
```yaml
persona_configs:
  focused_artist:
    idle_behavior:
      min_idle_time: 15  # seconds before autonomous content
      max_idle_time: 45  # max seconds between autonomous content
      content_types:
        - art_commentary: 
            weight: 0.4
            examples: ["Let me add some shading here...", "I think this color works better..."]
        - technique_explanation:
            weight: 0.3
            examples: ["This technique is called...", "The reason I'm using this brush..."]
        - viewer_engagement:
            weight: 0.2
            examples: ["What do you think about this composition?", "Should I add more detail here?"]
        - ambient_thoughts:
            weight: 0.1
            examples: ["*humming softly*", "This reminds me of..."]
      
  interactive_streamer:
    idle_behavior:
      min_idle_time: 8   # Quick to fill silence
      max_idle_time: 20  # Frequent engagement
      content_types:
        - viewer_questions:
            weight: 0.4
            examples: ["So what's everyone up to today?", "Anyone have fun weekend plans?"]
        - topic_starters:
            weight: 0.3
            examples: ["Let's talk about...", "I've been thinking about..."]
        - reactions:
            weight: 0.2
            examples: ["Oh, that's interesting!", "Wait, I just realized..."]
        - games_activities:
            weight: 0.1
            examples: ["Should we play a quick game?", "Let's do a poll!"]
```

#### Autonomous Decision Loop
```python
class AutonomousDecisionAgent(AssistantAgent):
    """Makes decisions about when and what autonomous content to generate"""
    
    def __init__(self):
        super().__init__(
            name="autonomous_decision",
            system_message="""
            Monitor the stream state and decide when to generate autonomous content.
            Consider:
            - Time since last interaction
            - Current activity/context
            - Viewer count and engagement level
            - Previous content to avoid repetition
            
            Make decisions about:
            - When to speak autonomously
            - What type of content to generate
            - Whether to change the environment/scene
            - How to maintain engagement
            """
        )
```

#### Continuous Content Strategies

##### 1. Activity-Based Content
```python
activity_content_mapping = {
    "drawing": {
        "commentary": ["Describing technique", "Sharing inspiration", "Progress updates"],
        "engagement": ["Asking for color suggestions", "Polling composition choices"],
        "stories": ["Related art experiences", "Artist inspirations"]
    },
    "gaming": {
        "commentary": ["Strategy explanation", "Reaction to events", "Goal setting"],
        "engagement": ["Asking for tips", "Challenge suggestions"],
        "stories": ["Previous gaming experiences", "Favorite moments"]
    },
    "chatting": {
        "commentary": ["Topic deep dives", "Personal thoughts", "Current events"],
        "engagement": ["Question rounds", "Would you rather", "Story prompts"],
        "stories": ["Personal anecdotes", "Funny experiences"]
    }
}
```

##### 2. Dynamic Content Pacing
```python
def calculate_content_timing(self, state):
    """Dynamically adjust content generation timing"""
    base_interval = self.persona_config["idle_behavior"]["min_idle_time"]
    
    # Factors that affect timing
    viewer_factor = min(state["viewer_count"] / 100, 2.0)  # More viewers = more content
    engagement_factor = state.get("chat_activity", 0.5)  # Active chat = less autonomous
    time_factor = self._get_time_of_day_factor()  # Peak hours = more content
    
    # Calculate adjusted interval
    adjusted_interval = base_interval * (1 / viewer_factor) * (2 - engagement_factor)
    
    return max(5, min(adjusted_interval, 60))  # Clamp between 5-60 seconds
```

##### 3. Content Variety System
```python
class ContentVarietyTracker:
    """Ensures diverse autonomous content generation"""
    
    def __init__(self):
        self.recent_types = []  # Track last N content types
        self.topic_cooldowns = {}  # Prevent topic repetition
        self.max_history = 20
        
    def get_next_content_type(self, available_types):
        """Select next content type ensuring variety"""
        weights = {}
        
        for content_type, config in available_types.items():
            base_weight = config["weight"]
            
            # Reduce weight if recently used
            recency_penalty = self.recent_types.count(content_type) * 0.2
            
            # Check cooldown
            if content_type in self.topic_cooldowns:
                if time.time() < self.topic_cooldowns[content_type]:
                    recency_penalty += 0.5
                    
            weights[content_type] = max(0.1, base_weight - recency_penalty)
            
        # Weighted random selection
        return self._weighted_choice(weights)
```

### 2. External Input Processing

#### Input Types
- **Viewer Comments**: Real-time chat messages from streaming platforms
- **Social Media**: Tweets, mentions, and other social interactions
- **System Events**: New viewers, follows, subscriptions, donations
- **Game Events**: In-game triggers and state changes

#### Processing Flow
1. External input received via HTTP endpoint
2. Orchestrator Agent evaluates input importance
3. Content Filter Agent applies persona-based filtering
4. Decision made whether to:
   - Pass to Speech LLM with full context
   - Pass to Speech LLM with modified context
   - Suppress the input entirely
   - Trigger environment changes

### 2. Configurable Prompts and Personas

#### Persona Configuration
```yaml
persona_configs:
  focused_artist:
    name: "Focused Artist"
    orchestrator_prompt: |
      You are managing a VTuber who is a focused artist creating art.
      They value their creative flow and don't want to be constantly interrupted.
      Filter inputs based on:
      - Relevance to current art project
      - Importance/urgency of the message
      - Viewer engagement level
    filter_rules:
      - suppress_general_chatter: true
      - respond_to_art_questions: true
      - acknowledge_donations: true
      - batch_responses: true
      
  interactive_streamer:
    name: "Interactive Streamer"
    orchestrator_prompt: |
      You are managing a highly interactive VTuber who loves engaging with chat.
      Pass through most viewer comments and create engaging responses.
      Prioritize:
      - Direct questions
      - New viewer greetings
      - Interesting comments
    filter_rules:
      - suppress_general_chatter: false
      - immediate_response: true
      - encourage_interaction: true
```

### 3. Speech Generation Integration

#### Communication with Speech LLM
- Maintain existing `/process_text` endpoint compatibility
- Add AutoGen context to requests
- Support for:
  - Direct speech (bypass LLM)
  - Contextual speech (with filtered context)
  - Autonomous speech (generated by orchestrator)

#### Context Management
```python
class SpeechContext:
    def __init__(self):
        self.conversation_history = []
        self.filtered_inputs = []
        self.persona_context = {}
        self.current_activity = None
        
    def prepare_llm_context(self, filtered_input):
        """Prepare context for Speech LLM based on filtered input"""
        return {
            "user_input": filtered_input.content,
            "context": {
                "activity": self.current_activity,
                "recent_topics": self.get_recent_topics(),
                "viewer_context": filtered_input.metadata,
                "persona_hints": self.persona_context
            }
        }
```

### 4. Environment Control

#### Game Control Integration
- Maintain existing `/game_control` endpoint
- AutoGen agents can trigger environment changes based on:
  - Viewer requests (if persona allows)
  - Autonomous decisions
  - Mood/activity changes

#### Coordination Rules
- Environment changes should align with current activity
- Avoid disruptive changes during focused activities
- Support preset scenes for different streaming modes

## Technical Implementation

### 1. AutoGen Agent Initialization

```python
class AutoGenOrchestratorV3:
    def __init__(self):
        self.config = self._load_config()
        self.agents = self._initialize_agents()
        self.state = OrchestratorState()
        self.scb_client = SCBClient()  # Maintain SCB integration
        
    def _initialize_agents(self):
        """Initialize AutoGen agents based on configuration"""
        # Load persona-specific prompts
        persona = self.config.current_persona
        
        return {
            "orchestrator": self._create_orchestrator_agent(persona),
            "filter": self._create_filter_agent(persona),
            "speech": self._create_speech_agent(persona),
            "environment": self._create_environment_agent(persona)
        }
```

### 2. Continuous Operation Loop

```python
async def start_autonomous_loop(self):
    """Main loop for continuous autonomous operation"""
    self.autonomous_task = asyncio.create_task(self._autonomous_operation_loop())
    
async def _autonomous_operation_loop(self):
    """Background loop that ensures continuous content generation"""
    while True:
        try:
            current_time = datetime.now()
            idle_duration = (current_time - self.state["last_interaction"]).total_seconds()
            auto_gap = (current_time - self.state["last_autonomous_content"]).total_seconds()
            
            # Check if we should generate autonomous content
            persona_config = self.config.get_current_persona_config()
            min_idle = persona_config["idle_behavior"]["min_idle_time"]
            max_idle = persona_config["idle_behavior"]["max_idle_time"]
            
            should_generate = (
                idle_duration >= min_idle and 
                auto_gap >= min_idle and
                (idle_duration >= max_idle or self._should_generate_content())
            )
            
            if should_generate:
                await self._generate_autonomous_content()
                
            # Dynamic sleep based on activity
            sleep_duration = self._calculate_sleep_duration(idle_duration)
            await asyncio.sleep(sleep_duration)
            
        except Exception as e:
            self.logger.error(f"Error in autonomous loop: {e}")
            await asyncio.sleep(5)  # Error recovery delay

async def _generate_autonomous_content(self):
    """Generate autonomous content through AutoGen agents"""
    
    # Create context message for autonomous decision
    context_message = {
        "role": "system",
        "content": f"""
        Current stream state:
        - Time since last interaction: {idle_duration}s
        - Viewer count: {self.state['viewer_count']}
        - Current activity: {self.state['current_activity']}
        - Recent topics: {self.state['content_history'][-5:]}
        
        Decide what autonomous content to generate.
        """
    }
    
    # Get decision from autonomous agents
    decision_response = await self.manager.a_send(
        message=context_message,
        recipient=self.autonomous_decision_agent,
        request_reply=True
    )
    
    # Generate content based on decision
    if decision_response.get("generate_speech"):
        content_response = await self.manager.a_send(
            message={"role": "user", "content": "Generate engaging idle content"},
            recipient=self.idle_content_agent,
            request_reply=True
        )
        
        # Queue the generated content
        await self._queue_autonomous_speech(content_response["content"])
        
    # Update state
    self.state["last_autonomous_content"] = datetime.now()
```

### 3. Message Processing Pipeline

```python
async def process_external_input(self, input_data):
    """Process external input through AutoGen pipeline"""
    
    # Update interaction timestamp
    self.state["last_interaction"] = datetime.now()
    
    # 1. Create initial message for orchestrator
    initial_message = {
        "role": "user",
        "content": f"External input received: {input_data}",
        "metadata": {
            "source": input_data.source,
            "timestamp": input_data.timestamp,
            "viewer_info": input_data.viewer_info
        }
    }
    
    # 2. Run through AutoGen group chat
    response = await self.manager.a_send(
        message=initial_message,
        recipient=self.orchestrator,
        request_reply=True
    )
    
    # 3. Process agent decisions
    decisions = self._extract_decisions(response)
    
    # 4. Execute decisions
    await self._execute_decisions(decisions)
```

### 3. Decision Execution

```python
async def _execute_decisions(self, decisions):
    """Execute decisions made by AutoGen agents"""
    
    for decision in decisions:
        if decision.type == "speech":
            await self._queue_speech(
                content=decision.content,
                priority=decision.priority,
                context=decision.context
            )
        elif decision.type == "environment":
            await self._trigger_environment_change(
                command=decision.command,
                parameters=decision.parameters
            )
        elif decision.type == "suppress":
            self.logger.info(f"Suppressed input: {decision.reason}")
```

## API Specifications

### New Endpoints

#### 1. `/orchestrator/v3/process`
```json
POST /orchestrator/v3/process
{
  "input_type": "viewer_comment|tweet|system_event",
  "content": "string",
  "metadata": {
    "viewer_name": "string",
    "viewer_id": "string",
    "platform": "twitch|youtube|twitter",
    "importance": "low|medium|high",
    "timestamp": "ISO8601"
  }
}

Response:
{
  "processed": true,
  "decisions": [
    {
      "type": "speech|environment|suppress",
      "action": "string",
      "reasoning": "string"
    }
  ],
  "autogen_conversation": [...] // Optional debug info
}
```

#### 2. `/orchestrator/v3/persona`
```json
GET /orchestrator/v3/persona
Response:
{
  "current_persona": "focused_artist",
  "available_personas": ["focused_artist", "interactive_streamer", "casual_gamer"],
  "config": {...}
}

PUT /orchestrator/v3/persona
{
  "persona": "interactive_streamer",
  "custom_overrides": {
    "filter_aggressiveness": 0.3
  }
}
```

#### 3. `/orchestrator/v3/agents/status`
```json
GET /orchestrator/v3/agents/status
Response:
{
  "agents": {
    "orchestrator": {
      "status": "active",
      "last_activity": "ISO8601",
      "decisions_made": 42
    },
    "filter": {...},
    "speech": {...},
    "environment": {...}
  },
  "group_chat_status": {
    "total_messages": 150,
    "active_conversation": false
  }
}
```

#### 4. `/orchestrator/v3/autonomous/control`
```json
POST /orchestrator/v3/autonomous/control
{
  "action": "pause|resume|configure",
  "settings": {
    "min_idle_time": 15,
    "max_idle_time": 45,
    "content_variety": "high|medium|low",
    "activity_override": "drawing|gaming|chatting"
  }
}

Response:
{
  "status": "success",
  "autonomous_state": {
    "active": true,
    "current_settings": {...},
    "last_content_generated": "ISO8601",
    "content_queue_size": 2
  }
}
```

#### 5. `/orchestrator/v3/autonomous/stats`
```json
GET /orchestrator/v3/autonomous/stats
Response:
{
  "autonomous_metrics": {
    "total_content_generated": 145,
    "content_by_type": {
      "commentary": 45,
      "engagement": 38,
      "stories": 32,
      "reactions": 30
    },
    "average_idle_before_content": 22.5,
    "viewer_retention_during_idle": 0.85,
    "most_successful_content_types": ["engagement", "stories"]
  },
  "time_period": "last_24_hours"
}
```

### Modified Existing Endpoints

#### `/process_text` Enhancement
- Add `autogen_context` field for AutoGen-processed inputs
- Support for batched responses when orchestrator decides to group multiple inputs
- Include `autonomous_priority` field to indicate if content is viewer-triggered or autonomous

#### `/orchestrator/event` Enhancement
- Route through AutoGen pipeline instead of direct processing
- Return AutoGen reasoning in response
- Support for activity state changes that affect autonomous behavior

## Migration Strategy

### Phase 1: Parallel Implementation
1. Implement AutoGen orchestrator alongside existing V2
2. Add feature flag to switch between orchestrators
3. Route subset of traffic through AutoGen for testing

### Phase 2: Feature Parity
1. Ensure all V2 features work in AutoGen version
2. Implement comprehensive logging and monitoring
3. A/B test with different personas

### Phase 3: Deprecation
1. Gradually increase AutoGen traffic percentage
2. Monitor performance and user feedback
3. Deprecate V2 once stability confirmed

## Configuration Examples

### Example 1: Focused Artist Configuration
```python
FOCUSED_ARTIST_CONFIG = {
    "orchestrator_prompt": """
    You are the orchestrator for a VTuber who is focused on creating art.
    Your role is to:
    1. Filter out distracting comments
    2. Only pass through art-related questions or important messages
    3. Batch non-urgent comments for periodic acknowledgment
    4. Maintain a calm, focused streaming environment
    
    When you receive a viewer comment, evaluate:
    - Is it about the current art project? (High priority)
    - Is it a new viewer greeting? (Medium priority, acknowledge later)
    - Is it general chatter? (Low priority, mostly suppress)
    """,
    
    "filter_threshold": 0.7,  # High threshold = more filtering
    "batch_responses": True,
    "batch_interval": 300,  # 5 minutes
    "auto_acknowledge": ["donations", "subscriptions"]
}
```

### Example 2: Interactive Streamer Configuration
```python
INTERACTIVE_STREAMER_CONFIG = {
    "orchestrator_prompt": """
    You are the orchestrator for a highly interactive VTuber who loves chat.
    Your role is to:
    1. Pass through most viewer comments
    2. Prioritize questions and interesting observations
    3. Create opportunities for viewer engagement
    4. Maintain high energy and responsiveness
    
    When you receive a viewer comment, evaluate:
    - Is it a question? (Immediate response)
    - Is it funny or interesting? (Quick response)
    - Is it spam or offensive? (Suppress)
    """,
    
    "filter_threshold": 0.2,  # Low threshold = less filtering
    "batch_responses": False,
    "immediate_response": True,
    "engagement_prompts": True
}
```

## Performance Considerations

### 1. Latency Requirements
- Input processing: < 100ms for filtering decision
- Speech generation initiation: < 200ms
- Total end-to-end: < 500ms for high-priority inputs

### 2. Scalability
- AutoGen agents should be stateless where possible
- Use connection pooling for LLM providers
- Implement caching for repeated decisions

### 3. Resource Management
- Limit AutoGen conversation rounds to prevent runaway processing
- Implement timeouts for agent decisions
- Monitor token usage across all agents

## Success Metrics

### 1. Engagement Metrics
- Viewer retention during different persona modes
- Chat interaction rates
- Streamer focus time (for focused personas)

### 2. Technical Metrics
- Decision latency percentiles (p50, p95, p99)
- Filter accuracy (manual review sampling)
- System resource utilization

### 3. Content Quality
- Coherence of filtered responses
- Appropriateness of suppression decisions
- Persona consistency score

## Security and Privacy

### 1. Input Sanitization
- Validate all external inputs
- Implement rate limiting per viewer
- Filter potentially harmful content

### 2. Data Privacy
- Don't log sensitive viewer information
- Implement data retention policies
- Allow viewers to opt-out of processing

### 3. Prompt Injection Protection
- Sanitize inputs before passing to AutoGen
- Implement prompt validation
- Monitor for unusual agent behaviors

## Future Enhancements

### 1. Advanced Personas
- Mood-based persona switching
- Time-of-day persona adjustments
- Game-specific personas

### 2. Learning Capabilities
- Fine-tune filtering based on streamer feedback
- Adapt to viewer preferences over time
- Optimize response timing

### 3. Multi-Modal Integration
- Process viewer emotes and reactions
- Integrate with visual scene analysis
- Coordinate with background music/effects

## Conclusion

The AutoGen-based orchestrator will provide a more sophisticated and flexible system for managing autonomous VTuber interactions. By leveraging multi-agent coordination, we can create nuanced filtering and response strategies that adapt to different streaming contexts while maintaining engaging viewer experiences.

The implementation will be backwards-compatible with existing systems while providing new capabilities for persona-based content filtering and intelligent response generation.