# AutoGen Orchestrator System Documentation

## Overview

The AutoGen Orchestrator System is a sophisticated multi-agent AI system that powers autonomous VTuber content generation, viewer interaction processing, and environment control. Built on Microsoft's AutoGen framework, it coordinates multiple specialized AI agents to make intelligent decisions about content generation, filtering, and response timing.

## System Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                    AutoGen Orchestrator V3                     │
├─────────────────────────────────────────────────────────────────┤
│  ┌───────────────┐  ┌───────────────┐  ┌───────────────────┐   │
│  │ Orchestrator  │  │ Content Filter│  │  Speech Coordinator │  │
│  │    Agent      │  │    Agent      │  │       Agent       │   │
│  └───────────────┘  └───────────────┘  └───────────────────┘   │
│  ┌───────────────┐  ┌───────────────┐  ┌───────────────────┐   │
│  │ Environment   │  │ Idle Content  │  │ Autonomous Decision│  │
│  │ Controller    │  │    Agent      │  │      Agent        │   │
│  └───────────────┘  └───────────────┘  └───────────────────┘   │
├─────────────────────────────────────────────────────────────────┤
│                    Group Chat Manager                          │
├─────────────────────────────────────────────────────────────────┤
│  State Management  │  Content Strategy  │  Performance Tracking│
├─────────────────────────────────────────────────────────────────┤
│           Speech Pipeline  │  Environment Control              │
└─────────────────────────────────────────────────────────────────┘
```

## Core Components

### 1. AutoGen Agents

#### **Orchestrator Agent**
- **Role**: Main coordinator and final decision maker
- **Responsibilities**:
  - Coordinates between other agents
  - Makes final decisions on actions
  - Applies persona-specific logic
  - Manages conversation flow

#### **Content Filter Agent**
- **Role**: Filters and evaluates incoming inputs
- **Responsibilities**:
  - Evaluates viewer messages against persona preferences
  - Determines relevance and importance (0.0-1.0 scale)
  - Suggests content modifications
  - Provides filtering rationale

#### **Speech Coordinator Agent**
- **Role**: Manages speech generation and formatting
- **Responsibilities**:
  - Formats filtered inputs for natural speech
  - Maintains conversation continuity
  - Ensures responses align with persona
  - Manages speech timing and pacing

#### **Environment Controller Agent**
- **Role**: Handles game/avatar environment changes
- **Responsibilities**:
  - Controls avatar appearance (hair color, outfit, accessories)
  - Manages scene transitions
  - Coordinates visual changes with content
  - Executes environment commands

#### **Idle Content Agent**
- **Role**: Generates autonomous content during quiet periods
- **Responsibilities**:
  - Creates conversation starters
  - Generates ambient commentary
  - Provides engagement prompts
  - Maintains stream activity

#### **Autonomous Decision Agent**
- **Role**: Decides when to take autonomous actions
- **Responsibilities**:
  - Monitors stream state and timing
  - Decides when to generate content
  - Evaluates urgency levels
  - Prevents over-generation

### 2. Content Strategy System

#### **ContentStrategyManager**
Manages different content generation approaches:

- **Contextual Follow-up**: Based on recent conversation topics
- **Interest-based**: Leverages known viewer interests
- **Time-aware**: Considers time of day and stream phase
- **Activity-based**: Relates to current stream activity
- **Viewer Engagement**: Focuses on audience interaction
- **Variety-focused**: Ensures diverse content
- **Energy Matching**: Matches conversation energy level

#### **Content Types**
- **Ambient**: Background thoughts and observations
- **Commentary**: Activity-related commentary
- **Engagement**: Direct viewer interaction
- **Questions**: Prompting viewer responses
- **Reactions**: Responses to events
- **Stories**: Anecdotes and experiences
- **Greetings**: Welcoming new viewers
- **Transitions**: Moving between topics/activities

### 3. State Management

#### **OrchestratorState**
Central state tracking:
- Speech state (speaking, queues, timing)
- Viewer metrics (count, engagement, chat rate)
- Conversation context (topics, energy, keywords)
- Environment state (scene, avatar configuration)
- Content history (generation patterns, variety)

#### **StateManager**
- Updates idle calculations
- Manages stream phases
- Tracks interaction timing
- Calculates engagement scores

## Personas

The system supports different VTuber personalities with custom behavior:

### **Focused Artist**
- **Filter Threshold**: 0.7 (high filtering)
- **Behavior**: Values creative flow, filters general chatter
- **Content**: Art commentary, technique explanations
- **Idle Time**: 15-45 seconds

### **Interactive Streamer**
- **Filter Threshold**: 0.2 (low filtering)
- **Behavior**: Highly responsive to chat
- **Content**: Viewer questions, reactions, topic starters
- **Idle Time**: 8-20 seconds

### **Casual Gamer**
- **Filter Threshold**: 0.5 (medium filtering)
- **Behavior**: Balances gameplay with chat
- **Content**: Game commentary, strategy thoughts
- **Idle Time**: 10-30 seconds

## Workflow Process

### 1. Input Processing

```
External Input → Content Filter Agent → Importance Scoring → Decision Matrix
                      ↓
Orchestrator Agent ← Speech Coordinator ← Filter Decision
                      ↓
Final Decision: [speech|environment|suppress|batch]
```

### 2. Autonomous Content Generation

```
Idle Detection → Autonomous Decision Agent → Strategy Selection
                      ↓
Content Strategy Manager → Idle Content Agent → Speech Generation
                      ↓
Quality Check → Variety Validation → TTS Pipeline
```

### 3. Speech Pipeline

The speech processing flow works as follows:

1. **Content Extraction**: 
   - Raw orchestrator output: `"CONTENT: Hello everyone! TYPE: greeting"`
   - Cleaned content: `"Hello everyone!"`

2. **Direct Speech Mode**:
   - Bypasses LLM for orchestrator-generated content
   - Processes through TTS pipeline immediately
   - Maintains timing and quality

3. **TTS Processing**:
   - Splits content into tokens
   - Uses SentenceBuilder for proper timing
   - Generates audio and blendshape data

## Configuration

### Environment Variables

```bash
# Core Settings
AUTOGEN_ORCHESTRATOR_ENABLED=true
ORCHESTRATOR_PERSONA=interactive_streamer
AUTONOMOUS_CONTENT_ENABLED=true

# AI Configuration
AUTOGEN_MODEL=gpt-3.5-turbo
AUTOGEN_TEMPERATURE=0.7
AUTOGEN_MAX_TOKENS=150

# Timing
DECISION_INTERVAL=0.5
MIN_IDLE_TIME=8.0
MAX_IDLE_TIME=45.0
MIN_SPEECH_GAP=2.5
```

### Persona Configuration

Personas are defined in `autogen_orchestrator_v3.py` with:
- Name and description
- Filter threshold (0.0-1.0)
- Idle behavior configuration
- Preferred content strategies
- Content type weights

## API Endpoints

### Core Endpoints

- `POST /orchestrator/v3/process` - Process external input
- `GET /orchestrator/v3/health` - Health check
- `GET /orchestrator/v3/status` - Comprehensive status

### Persona Management

- `GET /orchestrator/v3/persona` - Get current persona
- `PUT /orchestrator/v3/persona` - Update persona

### Control Endpoints

- `POST /orchestrator/v3/autonomous/control` - Control autonomous behavior
- `POST /orchestrator/v3/event` - Handle external events
- `POST /orchestrator/v3/activity` - Update stream activity

## Performance Monitoring

### Metrics Tracked

- **Decision Latency**: Time to make orchestration decisions
- **Content Generation Rate**: Autonomous content per minute
- **Filter Accuracy**: Input filtering effectiveness
- **Variety Score**: Content diversity measurement
- **Engagement Score**: Overall viewer engagement

### Debugging

- **Debug Endpoint**: `/orchestrator/v3/debug`
- **Metrics Export**: `/orchestrator/v3/metrics` (Prometheus format)
- **Performance Traces**: Detailed operation timing

## Integration Points

### TTS System Integration

The orchestrator integrates with the TTS system via:
- Direct speech mode for immediate processing
- Proper content extraction and cleaning
- Queue management and timing

### Environment Control

Connected to Unreal Engine for:
- Avatar appearance changes
- Scene transitions
- Special effects
- Environment commands

### SCB (Shared Contextual Bridge)

Stores conversation history and context for:
- Memory persistence
- Pattern recognition
- Cross-session learning

## Troubleshooting

### Common Issues

1. **No speech output**: Check `AUTOGEN_ORCHESTRATOR_ENABLED` and API keys
2. **Content includes TYPE labels**: Verify content extraction in `clean_speech_text()`
3. **Agent discussion errors**: Check AutoGen dependencies and model configuration
4. **Performance issues**: Monitor decision latency and queue sizes

### Debug Steps

1. Check health endpoint for component status
2. Review debug endpoint for configuration issues
3. Monitor logs for agent communication
4. Verify environment variable configuration

## Development Notes

### File Structure

- `autogen_orchestrator_v3.py` - Main orchestrator implementation
- `autogen_agents.py` - Individual agent definitions
- `autogen_state_manager.py` - State management
- `autogen_content_strategies.py` - Content generation strategies
- `orchestrator_integration_v3.py` - Integration wrapper

### Adding New Personas

1. Define persona in `_load_persona_configs()`
2. Set filter threshold and content preferences
3. Configure idle behavior patterns
4. Test with different content strategies

### Extending Functionality

1. **New Agent Types**: Add to `autogen_agents.py`
2. **Content Strategies**: Extend `ContentStrategy` enum
3. **Event Handlers**: Add to `process_external_event()`
4. **Metrics**: Extend performance tracking

## Future Enhancements

- Advanced conversation memory
- Multi-modal input processing
- Dynamic persona adaptation
- Enhanced environment integration
- Real-time performance optimization 