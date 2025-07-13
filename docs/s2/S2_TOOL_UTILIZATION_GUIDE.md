# S2 Tool Utilization Guide

## Overview
This guide provides comprehensive documentation for utilizing all 12 tools across the three specialized teams in the S2 system. Each tool has been tested and validated for production use.

## Tool Architecture

### AutoGen Tool Bridge
The `AutoGenToolBridge` class converts BaseTool instances into AutoGen-compatible functions:

```python
class AutoGenToolBridge:
    def register_tools_with_agents(self, agents: List[ConversableAgent], tools: List[BaseTool])
    def create_tool_wrapper(self, tool: BaseTool) -> Callable
    def generate_tool_schema(self, tool: BaseTool) -> dict
```

### Tool Registration Process
1. **Tool Discovery**: Scan team configurations for available tools
2. **Schema Generation**: Convert BaseTool.get_schema() to AutoGen format
3. **Wrapper Creation**: Create callable functions with parameter validation
4. **Agent Registration**: Register with `register_for_llm()` and `register_for_execution()`

## Team-Specific Tool Documentation

### 🏪 Trader Team Tools

#### 1. market_data
**Purpose**: Retrieve real-time market data and basic technical analysis

**Parameters**:
- `symbol` (required): Stock symbol (e.g., "AAPL", "TSLA")
- `timeframe`: Data timeframe (default: "1d")
- `indicators`: Technical indicators to include

**Example Usage**:
```bash
curl -X POST http://localhost:8200/api/stimuli/receive \
  -H "Content-Type: application/json" \
  -d '{
    "stimuli_id": "market_test",
    "content": "Get current market data for AAPL stock with technical indicators",
    "source": "api_test",
    "priority": "high"
  }'
```

**Expected Tool Invocation**:
```
#assistant to=market_data
***** Suggested tool call: market_data *****
>>>>>>>> EXECUTING FUNCTION market_data...
>>>>>>>> EXECUTED FUNCTION market_data...
```

**Sample Response**:
```json
{
  "symbol": "AAPL",
  "data_points": 30,
  "price_data": [
    {
      "timestamp": "2025-06-13T13:46:14.066281",
      "open": 169.17,
      "high": 172.01,
      "low": 166.08,
      "close": 169.17,
      "volume": 793794
    }
  ]
}
```

#### 2. trading_analysis
**Purpose**: Perform advanced trading analysis and generate strategy recommendations

**Parameters**:
- `symbol` (required): Target stock symbol
- `analysis_type`: Type of analysis ("technical", "fundamental", "sentiment")
- `timeframe`: Analysis timeframe

**Tool Capabilities**:
- Technical pattern recognition
- Support/resistance levels
- Moving average analysis
- Strategy recommendations

#### 3. risk_assessment
**Purpose**: Comprehensive risk assessment for trading positions

**Parameters**:
- `portfolio_value` (required): Total portfolio value
- `position_size` (required): Size of position being evaluated
- `symbol` (required): Asset symbol
- `risk_tolerance`: Risk tolerance level

**Risk Metrics Calculated**:
- Position sizing recommendations
- Value at Risk (VaR)
- Maximum drawdown estimates
- Correlation analysis

#### 4. communication
**Purpose**: Inter-team communication and coordination

**Parameters**:
- `action` (required): Communication action type
- `target_team`: Destination team
- `message`: Message content
- `priority`: Message priority level

#### 5. system_status
**Purpose**: Check system status and health metrics

**Parameters**: None required

**Health Checks**:
- System uptime and performance
- Resource utilization
- Service connectivity
- Queue status

#### 6. utility
**Purpose**: General utility functions and data operations

**Parameters**:
- `utility_type` (required): Type of utility operation
- `data`: Input data for processing
- `options`: Operation-specific options

### 🎓 Educator Team Tools

#### 1. educational_content
**Purpose**: Generate educational content, explanations, and learning materials

**Parameters**:
- `topic` (required): Subject or topic to create content for
- `difficulty_level`: Target difficulty (beginner, intermediate, advanced)
- `content_type`: Type of content (explanation, tutorial, reference)
- `learning_objectives`: Specific learning goals
- `format`: Output format preference

**Content Types**:
- Step-by-step tutorials
- Conceptual explanations
- Interactive examples
- Reference materials

**Example Usage**:
```bash
curl -X POST http://localhost:8200/api/stimuli/receive \
  -H "Content-Type: application/json" \
  -d '{
    "stimuli_id": "education_test",
    "content": "Create comprehensive educational content about machine learning fundamentals for beginners",
    "source": "api_test",
    "priority": "high"
  }'
```

#### 2. assessment_creation
**Purpose**: Create educational assessments, rubrics, and evaluation methods

**Parameters**:
- `topic` (required): Assessment subject
- `assessment_type`: Type of assessment (quiz, project, exam)
- `difficulty_level`: Target difficulty level
- `evaluation_criteria`: Assessment criteria

**Assessment Features**:
- Multiple choice questions
- Open-ended problems
- Practical exercises
- Rubric generation

#### 3. curriculum_planning
**Purpose**: Plan educational curricula and learning sequences

**Parameters**:
- `subject` (required): Subject area
- `duration`: Course duration
- `prerequisites`: Required knowledge

**Planning Capabilities**:
- Learning path optimization
- Prerequisite mapping
- Resource allocation
- Progress milestones

### 🎮 Streamer Team Tools

#### 1. content_creation
**Purpose**: Generate streaming content ideas, interactive segments, and community activities

**Parameters**: None required (content generation is context-aware)

**Content Categories**:
- Viral content ideas
- Interactive stream segments
- Community challenges
- Engagement activities

**Example Usage**:
```bash
curl -X POST http://localhost:8200/api/stimuli/receive \
  -H "Content-Type: application/json" \
  -d '{
    "stimuli_id": "streamer_test",
    "content": "Generate creative streaming content ideas for a tech channel with interactive segments",
    "source": "api_test",
    "priority": "high"
  }'
```

#### 2. community_management
**Purpose**: Manage community engagement, moderation, and relationship building

**Parameters**: None required

**Management Features**:
- Engagement strategies
- Moderation guidelines
- Community building activities
- Relationship management

#### 3. streaming_analytics
**Purpose**: Analyze streaming performance and provide data-driven insights

**Parameters**: None required

**Analytics Provided**:
- Viewer engagement metrics
- Content performance analysis
- Growth opportunities
- Optimization recommendations

## Testing Procedures

### Individual Tool Testing

#### 1. Single Tool Test
```bash
# Test specific tool functionality
curl -X POST http://localhost:8200/api/stimuli/receive \
  -H "Content-Type: application/json" \
  -d '{
    "stimuli_id": "single_tool_test",
    "content": "Use market_data tool to get AAPL stock information",
    "source": "test",
    "priority": "high"
  }'
```

#### 2. Multi-Tool Test
```bash
# Test multiple tools in sequence
curl -X POST http://localhost:8200/api/stimuli/receive \
  -H "Content-Type: application/json" \
  -d '{
    "stimuli_id": "multi_tool_test",
    "content": "Get AAPL market data, perform trading analysis, and assess risk for $10000 position",
    "source": "test",
    "priority": "high"
  }'
```

#### 3. Cross-Team Tool Test
```bash
# Test tools across different teams
curl -X POST http://localhost:8200/api/stimuli/receive \
  -H "Content-Type: application/json" \
  -d '{
    "stimuli_id": "cross_team_test",
    "content": "Create educational content about trading, then check system status and generate streaming content about the topic",
    "source": "test",
    "priority": "high"
  }'
```

### Performance Monitoring

#### Log Analysis
```bash
# Monitor tool executions
docker logs autogen_agent | grep -E "(EXECUTING FUNCTION|EXECUTED FUNCTION)"

# Check S2 events
docker logs autogen_agent | grep "S2_"

# Performance timing
docker logs autogen_agent | grep "completed slowly"
```

#### Tool Usage Statistics
```bash
# Get tool execution counts
docker logs autogen_agent | grep "EXECUTING FUNCTION" | \
  sed 's/.*EXECUTING FUNCTION \([^.]*\)\.\.\./\1/' | \
  sort | uniq -c | sort -nr
```

### Validation Checklist

#### ✅ Tool Registration Validation
- [ ] All 12 tools registered successfully
- [ ] No registration errors in logs
- [ ] Tool schemas properly generated
- [ ] AutoGen function overrides working

#### ✅ Tool Execution Validation
- [ ] Each tool executes without errors
- [ ] Proper parameter handling
- [ ] Expected output format
- [ ] Timeout handling functional

#### ✅ Team Integration Validation
- [ ] Tools available to correct teams
- [ ] Cross-team communication working
- [ ] Shared tools accessible by multiple teams
- [ ] No tool conflicts or overwrites

## Troubleshooting

### Common Issues

#### 1. Tool Not Executing
**Symptoms**: Tool suggested but not executed
**Causes**: 
- Missing required parameters
- Tool registration failed
- LLM API key issues

**Solutions**:
```bash
# Check tool registration
curl -s http://localhost:8200/api/stimuli/tools | jq '.tool_details'

# Restart queue processing
curl -X POST http://localhost:8200/api/queue/restart
```

#### 2. Event Loop Errors
**Symptoms**: "Cannot run the event loop while another loop is running"
**Cause**: AsyncIO conflict in tool bridge
**Solution**: Tool bridge handles this automatically with proper async/await patterns

#### 3. Tool Override Warnings
**Symptoms**: "Function 'tool_name' is being overridden"
**Cause**: Multiple tool registrations (expected behavior)
**Solution**: Warnings are normal - tools register with each agent in the team

### Performance Optimization

#### Tool Caching
Future implementation for frequently used tools:
```python
# Planned feature
class ToolCache:
    def get_cached_result(self, tool_name: str, params: dict) -> Optional[dict]
    def cache_result(self, tool_name: str, params: dict, result: dict)
```

#### Parallel Execution
Current: Sequential tool execution
Future: Parallel execution for independent tools

#### Resource Monitoring
Monitor tool execution times and resource usage for optimization opportunities. 