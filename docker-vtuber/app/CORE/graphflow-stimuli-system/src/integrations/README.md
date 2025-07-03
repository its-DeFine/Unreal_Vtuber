# System2 Integration Components

This directory contains the integration components for System2 (Multi-Agent) system based on the FRD specifications.

## Components

### 1. **System2Interface** (`system2_interface.py`)
Main interface for System2 integration that coordinates all components:
- Manages AutoGen client and agent coordination
- Handles Cognee memory system queries
- Triggers evolution engine analysis
- Provides comprehensive response aggregation

### 2. **AutoGenClient** (`autogen_client.py`)
HTTP client for AutoGen agent system communication:
- Task submission and management
- Agent status monitoring
- Evolution engine triggers
- Response parsing and error handling
- Batch operations support

### 3. **AgentManager** (`agent_manager.py`)
Agent coordination and load balancing:
- Multiple load balancing strategies (round-robin, least-loaded, best-performance, weighted-random)
- Agent health monitoring and metrics tracking
- Task assignment and completion tracking
- Automatic failover and recovery

### 4. **CogneeClient** (`cognee_client.py`)
Client for Cognee memory system:
- Memory queries with semantic search
- Memory storage and updates
- Context retrieval and enrichment
- Caching for frequently accessed memories
- Batch query support

## Usage Example

```python
from src.config.settings import System2Config
from src.integrations import System2Interface
from src.models.stimuli import AnalyzedStimuli

# Initialize System2 interface
config = System2Config()
system2 = System2Interface(config)
await system2.initialize()

# Submit stimuli for analysis
stimuli = AnalyzedStimuli(...)
task_id = await system2.submit_for_analysis(stimuli)

# Check task status
status = await system2.get_task_status(task_id)

# Query memories
memories = await system2.query_cognee_memory("relevant context")

# Get comprehensive response
response = await system2.get_comprehensive_response(stimuli.id)
```

## Configuration

Configure via environment variables:

```bash
# AutoGen settings
SYSTEM2_AUTOGEN_ENDPOINT=http://autogen-agent:3100
SYSTEM2_MAX_RETRIES=3
SYSTEM2_REQUEST_TIMEOUT=60.0

# Cognee settings
SYSTEM2_COGNEE_ENDPOINT=http://cognee:8000
SYSTEM2_COGNEE_API_KEY=your-api-key

# Load balancing
SYSTEM2_LOAD_BALANCING=best_performance
SYSTEM2_HEALTH_CHECK_INTERVAL=60
SYSTEM2_MAX_TASKS_PER_AGENT=10

# Evolution engine
SYSTEM2_EVOLUTION_ENGINE_ENABLED=true
```

## Available Agents

The system supports three types of agents:
1. **cognitive_ai_agent** - For cognitive analysis and reasoning
2. **programmer_agent** - For code-related analysis
3. **observer_agent** - For observation and monitoring

## Load Balancing Strategies

- **round_robin**: Distributes tasks evenly across agents
- **least_loaded**: Assigns to agent with fewest current tasks
- **best_performance**: Assigns to agent with best health score
- **weighted_random**: Random selection weighted by health scores

## Error Handling

All components implement:
- Retry logic with exponential backoff
- Graceful degradation on failures
- Comprehensive error logging
- Circuit breaker patterns for resilience

## Models

System2-specific models are defined in `src/models/system2_models.py`:
- `AgentStatusInfo` - Agent status information
- `AnalysisResult` - Results from agent analysis
- `MemoryResult` - Results from memory queries
- `EvolutionResult` - Results from evolution analysis
- `System2Response` - Aggregated response