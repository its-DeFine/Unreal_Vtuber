# AutoGen System - API Reference & Troubleshooting

## Table of Contents

1. [MCP API Reference](#mcp-api-reference)
2. [Data Structures](#data-structures)
3. [Tool API Reference](#tool-api-reference)
4. [Internal APIs](#internal-apis)
5. [Error Codes & Messages](#error-codes--messages)
6. [Troubleshooting Guide](#troubleshooting-guide)
7. [Performance Metrics](#performance-metrics)
8. [Integration Examples](#integration-examples)

---

## MCP API Reference

### Available MCP Tools

The Model Context Protocol (MCP) server provides the following tools for external integration:

#### `get_cognitive_status`
**Purpose:** Get comprehensive system status
**Parameters:** None
**Returns:** System status dictionary
**Example:**
```json
{
  "success": true,
  "data": {
    "system_health": "healthy",
    "iteration_count": 1543,
    "uptime_seconds": 86400,
    "active_agents": 3,
    "memory_entries": 2847,
    "evolution_cycles": 12,
    "last_evolution": "2024-01-15T10:30:00Z",
    "performance_metrics": {
      "avg_decision_time": 2.3,
      "success_rate": 0.94,
      "tools_executed": 1205
    }
  }
}
```

#### `trigger_cognitive_decision`
**Purpose:** Manually trigger a decision cycle
**Parameters:**
- `context` (Dict): Custom context for decision making
- `force_tool_selection` (Optional[str]): Force specific tool selection
**Returns:** Decision cycle result
**Example:**
```json
{
  "context": {
    "priority": "high",
    "domain": "performance_optimization",
    "custom_data": {"target_metric": "response_time"}
  },
  "force_tool_selection": "core_evolution_tool"
}
```

#### `query_cognitive_memory`
**Purpose:** Search system memory for relevant information
**Parameters:**
- `query` (str): Search query
- `limit` (Optional[int]): Maximum results (default: 10)
- `include_metadata` (Optional[bool]): Include metadata (default: true)
**Returns:** Memory search results
**Example:**
```json
{
  "query": "performance optimization techniques",
  "limit": 5,
  "include_metadata": true
}
```

#### `trigger_code_evolution`
**Purpose:** Manually trigger Darwin-Gödel evolution cycle
**Parameters:**
- `target_files` (Optional[List[str]]): Specific files to analyze
- `performance_context` (Dict): Current performance metrics
- `safety_mode` (Optional[bool]): Enable safety restrictions (default: true)
**Returns:** Evolution cycle result
**Example:**
```json
{
  "target_files": ["autogen_agent/tool_registry.py"],
  "performance_context": {
    "avg_tool_selection_time": 0.45,
    "tool_success_rate": 0.89,
    "memory_usage": "1.2GB"
  },
  "safety_mode": true
}
```

#### `analyze_code_performance`
**Purpose:** Analyze code performance without modifications
**Parameters:**
- `target_file` (str): File to analyze
- `analysis_depth` (Optional[str]): "shallow" or "deep" (default: "shallow")
**Returns:** Code analysis results
**Example:**
```json
{
  "target_file": "autogen_agent/main.py",
  "analysis_depth": "deep"
}
```

---

## Data Structures

### Core Data Types

#### `EvolutionResult`
```python
{
  "cycle_id": str,
  "success": bool,
  "improvements_made": int,
  "performance_impact": float,  # -1.0 to 1.0
  "modifications": List[Dict],
  "safety_checks": Dict,
  "timestamp": str,
  "duration_seconds": float
}
```

#### `MemoryEntry`
```python
{
  "id": str,
  "timestamp": str,
  "context": Dict,
  "action": str,
  "result": Dict,
  "success": bool,
  "relevance_score": float,  # 0.0 to 1.0
  "metadata": {
    "iteration": int,
    "tool_used": str,
    "execution_time": float
  }
}
```

#### `ToolExecutionResult`
```python
{
  "success": bool,
  "message": str,
  "data": Dict,  # Tool-specific data
  "execution_time": float,
  "timestamp": str,
  "tool_name": str,
  "context_hash": str,
  "error": Optional[str]
}
```

#### `PerformanceMetrics`
```python
{
  "iteration": int,
  "timestamp": str,
  "decision_time": float,
  "tool_execution_time": float,
  "success_rate": float,
  "agents_participated": List[str],
  "collaboration_score": int,
  "response_quality": float,
  "memory_usage": str,
  "cpu_usage": float,
  "gpu_usage": Optional[Dict]
}
```

### Agent Data Structures

#### `AgentResponse`
```python
{
  "agent_name": str,
  "response_content": str,
  "confidence": float,  # 0.0 to 1.0
  "reasoning": str,
  "suggested_actions": List[str],
  "metadata": {
    "response_time": float,
    "token_usage": int,
    "model_used": str
  }
}
```

#### `CollaborationMetrics`
```python
{
  "total_agents": int,
  "active_agents": int,
  "consensus_score": float,  # 0.0 to 1.0
  "decision_quality": float,
  "coordination_time": float,
  "conflict_resolution": Dict
}
```

---

## Tool API Reference

### Tool Interface Contract

All tools must implement the following interface:

#### `run(context: Dict) -> Dict[str, Any]`
**Purpose:** Main tool execution entry point
**Parameters:**
- `context` (Dict): Execution context with tool-specific parameters
**Returns:** Standardized result dictionary
**Required Response Format:**
```python
{
  "success": bool,           # Execution success status
  "message": str,           # Human-readable message
  "data": Dict,            # Tool-specific result data
  "execution_time": float, # Optional: execution duration
  "metadata": Dict         # Optional: additional metadata
}
```

### Tool-Specific APIs

#### Goal Management Tool
**Context Parameters:**
```python
{
  "action": str,  # "define_goal", "get_goals", "update_progress", "generate_report"
  "goal_text": Optional[str],
  "goal_id": Optional[str],
  "priority": Optional[str],  # "low", "medium", "high"
  "progress_data": Optional[Dict],
  "timeframe_hours": Optional[int]
}
```

#### Evolution Tool
**Context Parameters:**
```python
{
  "action": str,  # "analyze_performance", "trigger_evolution", "get_status"
  "target_files": Optional[List[str]],
  "performance_context": Optional[Dict],
  "safety_mode": Optional[bool]
}
```

#### VTuber Control Tool
**Context Parameters:**
```python
{
  "action": str,  # "speak", "create_instance", "control_instance"
  "message": Optional[str],
  "instance_id": Optional[str],
  "avatar_config": Optional[Dict],
  "control_parameters": Optional[Dict]
}
```

---

## Internal APIs

### SCB (Shared Cognitive Blackboard) API

#### `publish_state(data: Dict, force_publish: bool = False)`
**Data Structure:**
```python
{
  "agent_id": "autogen_agent",
  "timestamp": float,
  "iteration": int,
  "event_type": str,  # "decision_cycle", "tool_execution", "evolution_cycle"
  "success": bool,
  "data": Dict,
  "metadata": {
    "system_health": str,
    "performance_metrics": Dict
  }
}
```

### VTuber Client API

#### `post_message(message: str, force_send: bool = False)`
**Request Format:**
```python
{
  "text": str,
  "autonomous_context": bool,
  "priority": Optional[str],  # "low", "normal", "high"
  "metadata": Optional[Dict]
}
```

### Cognee Integration API

#### `add_data(data: Union[str, Dict, List])`
**Data Formats:**
```python
# Text data
"This is important information about system performance"

# Structured data
{
  "type": "performance_data",
  "content": "System achieved 94% success rate",
  "metrics": {"success_rate": 0.94, "response_time": 2.3},
  "timestamp": "2024-01-15T10:30:00Z"
}

# Batch data
[
  {"content": "First piece of information"},
  {"content": "Second piece of information"}
]
```

---

## Error Codes & Messages

### System Error Codes

#### `SYS_001` - Database Connection Error
**Message:** "Failed to connect to database"
**Cause:** PostgreSQL connection issues
**Resolution:** Check DATABASE_URL and database availability

#### `SYS_002` - Redis Connection Error
**Message:** "Failed to connect to Redis"
**Cause:** Redis server unavailable or incorrect configuration
**Resolution:** Verify REDIS_URL and Redis server status

#### `SYS_003` - Ollama Model Error
**Message:** "Ollama model not available"
**Cause:** Specified model not loaded or Ollama server down
**Resolution:** Pull model with `ollama pull MODEL_NAME`

#### `SYS_004` - Configuration Error
**Message:** "Invalid configuration parameter"
**Cause:** Missing or invalid environment variables
**Resolution:** Check configuration guide and verify environment setup

### Tool Error Codes

#### `TOOL_001` - Tool Execution Timeout
**Message:** "Tool execution exceeded timeout limit"
**Cause:** Tool taking too long to execute
**Resolution:** Increase TOOL_EXECUTION_TIMEOUT or optimize tool logic

#### `TOOL_002` - Tool Not Found
**Message:** "Requested tool not available"
**Cause:** Tool not loaded or doesn't exist
**Resolution:** Verify tool exists in tools directory and is properly loaded

#### `TOOL_003` - Invalid Tool Context
**Message:** "Tool context validation failed"
**Cause:** Missing required parameters in context
**Resolution:** Check tool documentation for required parameters

### Evolution Error Codes

#### `EVO_001` - Evolution Safety Violation
**Message:** "Evolution blocked by safety checks"
**Cause:** Proposed modifications failed safety validation
**Resolution:** Review safety settings or approve manually if safe

#### `EVO_002` - Code Analysis Error
**Message:** "Failed to analyze code structure"
**Cause:** Malformed code or analysis tool error
**Resolution:** Check code syntax and analysis tool configuration

#### `EVO_003` - Sandbox Execution Error
**Message:** "Sandbox execution failed"
**Cause:** Code modifications caused runtime errors
**Resolution:** Review proposed modifications and test manually

---

## Troubleshooting Guide

### Common Issues

#### System Won't Start

**Symptoms:**
- Application exits immediately
- Import errors in logs
- Database connection failures

**Diagnosis:**
```bash
# Check Python environment
python -c "import autogen_agent; print('OK')"

# Verify database connection
python -c "import psycopg2; psycopg2.connect('$DATABASE_URL')"

# Check Ollama availability
curl -s http://localhost:11434/api/tags | jq .
```

**Solutions:**
1. Install missing dependencies: `pip install -r requirements.txt`
2. Verify database setup and credentials
3. Ensure Ollama is running and models are available

#### Tool Selection Issues

**Symptoms:**
- Same tool selected repeatedly
- Tools not executing
- Low tool diversity

**Diagnosis:**
```bash
# Check tool loading
grep "Tool loaded" /path/to/logs/autogen.log

# Monitor tool selection
grep "Tool selected" /path/to/logs/autogen.log | tail -20

# Check tool performance
grep "Tool execution" /path/to/logs/autogen.log | grep -v "success"
```

**Solutions:**
1. Adjust tool selection weights in configuration
2. Clear tool performance cache
3. Verify all tools are properly loaded

#### Memory Issues

**Symptoms:**
- High memory usage
- Out of memory errors
- Slow performance

**Diagnosis:**
```bash
# Monitor memory usage
ps aux | grep python | grep autogen

# Check database connections
netstat -an | grep :5432

# Monitor GPU memory (if applicable)
nvidia-smi
```

**Solutions:**
1. Reduce batch sizes and concurrent operations
2. Optimize database connection pool settings
3. Consider using smaller LLM models

#### Evolution Not Working

**Symptoms:**
- No evolution cycles triggered
- Evolution cycles fail immediately
- No code improvements

**Diagnosis:**
```bash
# Check evolution status
grep "Evolution" /path/to/logs/autogen.log

# Verify safety settings
echo $DARWIN_GODEL_REAL_MODIFICATIONS
echo $DARWIN_GODEL_REQUIRE_APPROVAL

# Check sandbox directory
ls -la $SANDBOX_DIR
```

**Solutions:**
1. Enable real modifications if desired: `DARWIN_GODEL_REAL_MODIFICATIONS=true`
2. Verify sandbox directory permissions
3. Check that performance metrics trigger evolution thresholds

### Performance Optimization

#### Slow Decision Cycles

**Diagnosis:**
```sql
-- Check average decision times
SELECT AVG(decision_time) as avg_decision_time,
       AVG(tool_execution_time) as avg_tool_time
FROM cycle_statistics 
WHERE timestamp > NOW() - INTERVAL '1 hour';
```

**Optimizations:**
1. Increase `MAX_WORKER_THREADS`
2. Optimize tool selection algorithm weights
3. Use faster LLM models for development

#### Database Performance Issues

**Diagnosis:**
```sql
-- Find slow queries
SELECT query, calls, total_time, mean_time 
FROM pg_stat_statements 
ORDER BY total_time DESC 
LIMIT 10;

-- Check database size
SELECT pg_size_pretty(pg_database_size('autogen_db'));
```

**Optimizations:**
1. Add database indexes for frequently queried columns
2. Increase database connection pool size
3. Implement query result caching

---

## Performance Metrics

### Key Performance Indicators

#### System Health Metrics
- **Uptime:** System availability percentage
- **Success Rate:** Percentage of successful decision cycles
- **Average Decision Time:** Mean time per decision cycle
- **Memory Usage:** Current memory consumption
- **CPU Utilization:** Processor usage

#### Tool Performance Metrics
- **Tool Selection Diversity:** Distribution of tool usage
- **Tool Success Rate:** Success percentage per tool
- **Tool Execution Time:** Average execution duration
- **Tool Cache Hit Rate:** Performance cache effectiveness

#### Evolution Metrics
- **Evolution Frequency:** Cycles per time period
- **Improvement Rate:** Successful improvements per cycle
- **Code Quality:** Static analysis metrics
- **Performance Impact:** Measured improvement from changes

### Monitoring Endpoints

#### Health Check
```bash
curl http://localhost:8080/health
```

#### Metrics Export
```bash
curl http://localhost:8080/metrics
```

#### Status Dashboard
```bash
curl http://localhost:8080/status | jq .
```

---

## Integration Examples

### MCP Client Integration

```python
import asyncio
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

async def use_autogen_mcp():
    server_params = StdioServerParameters(
        command="python", 
        args=["-m", "autogen_agent.mcp_server"]
    )
    
    async with stdio_client(server_params) as (read, write):
        async with ClientSession(read, write) as session:
            # Initialize
            await session.initialize()
            
            # Get system status
            result = await session.call_tool("get_cognitive_status", {})
            print(f"System status: {result}")
            
            # Trigger decision
            result = await session.call_tool("trigger_cognitive_decision", {
                "context": {"priority": "high"}
            })
            print(f"Decision result: {result}")

# Run the example
asyncio.run(use_autogen_mcp())
```

### REST API Integration

```python
import requests
import json

class AutoGenAPIClient:
    def __init__(self, base_url="http://localhost:8080"):
        self.base_url = base_url
    
    def get_status(self):
        response = requests.get(f"{self.base_url}/api/status")
        return response.json()
    
    def trigger_decision(self, context):
        response = requests.post(
            f"{self.base_url}/api/decision",
            json={"context": context}
        )
        return response.json()
    
    def query_memory(self, query, limit=10):
        response = requests.post(
            f"{self.base_url}/api/memory/search",
            json={"query": query, "limit": limit}
        )
        return response.json()

# Usage example
client = AutoGenAPIClient()
status = client.get_status()
print(f"System health: {status['system_health']}")
```

### WebSocket Integration

```python
import asyncio
import websockets
import json

async def monitor_autogen_events():
    uri = "ws://localhost:8080/ws/events"
    
    async with websockets.connect(uri) as websocket:
        # Subscribe to events
        await websocket.send(json.dumps({
            "action": "subscribe",
            "event_types": ["decision_cycle", "evolution_cycle"]
        }))
        
        # Listen for events
        async for message in websocket:
            event = json.loads(message)
            print(f"Event: {event['event_type']}")
            print(f"Data: {event['data']}")

# Run the monitor
asyncio.run(monitor_autogen_events())
```

---

## Version Information

- **API Version:** 1.0.0
- **Protocol Version:** MCP 1.0
- **Last Updated:** Current Date
- **Maintainer:** AutoGen Documentation System

---

*This API reference is maintained alongside the codebase. Please update when adding new endpoints or modifying data structures.*