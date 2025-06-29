# AutoGen System - Functions Reference

## Table of Contents

1. [Main Application Functions](#main-application-functions)
2. [Client Functions](#client-functions)
3. [Tool Registry Functions](#tool-registry-functions)
4. [Memory System Functions](#memory-system-functions)
5. [Evolution System Functions](#evolution-system-functions)
6. [Service Functions](#service-functions)
7. [Tool Functions](#tool-functions)
8. [Statistics Functions](#statistics-functions)
9. [Monitoring Functions](#monitoring-functions)

---

## Main Application Functions

### `main.py`

#### `main() -> None`
**Purpose:** Application entry point with mode selection
**Parameters:** None (uses command line arguments)
**Returns:** None
**Side Effects:** Starts application in selected mode
**Example:**
```bash
python main.py --mode autonomous  # Starts autonomous loop
python main.py --mode mcp        # Starts MCP server
python main.py --mode test       # Runs test mode
```

#### `initialize_autogen_agents(llm_config: Dict) -> Dict[str, Any]`
**Purpose:** Creates and configures AutoGen agent instances
**Parameters:**
- `llm_config` (Dict): LLM configuration with provider settings
**Returns:** Dictionary with agent instances and metadata
**Structure:**
```python
{
    "user_proxy": UserProxyAgent,
    "cognitive_agent": TeachableCognitiveAgent,
    "code_executor": CodeExecutionAgent,
    "total_agents": int,
    "llm_config": Dict
}
```
**Example:**
```python
llm_config = {"model": "llama3.2:3b", "api_key": None}
agents = initialize_autogen_agents(llm_config)
```

#### `run_autogen_decision_cycle(iteration: int, agents: Dict, tool_bridge: AgentToolBridge, scb_client: SCBClient, vtuber_client: VTuberClient) -> Tuple[Dict, Dict, Dict]`
**Purpose:** Execute one complete decision cycle with multi-agent collaboration
**Parameters:**
- `iteration` (int): Current iteration number
- `agents` (Dict): Initialized AutoGen agents
- `tool_bridge` (AgentToolBridge): Tool execution bridge
- `scb_client` (SCBClient): Shared Cognitive Blackboard client  
- `vtuber_client` (VTuberClient): VTuber communication client
**Returns:** Tuple of (agent_responses, tool_executions, performance_metrics)
**Example:**
```python
responses, tools, metrics = run_autogen_decision_cycle(
    iteration=1,
    agents=agents,
    tool_bridge=bridge,
    scb_client=scb,
    vtuber_client=vtuber
)
```

#### `enhanced_autonomous_loop(agents: Dict, tool_bridge: AgentToolBridge, scb_client: SCBClient, vtuber_client: VTuberClient) -> None`
**Purpose:** Main autonomous operation loop with continuous evolution
**Parameters:**
- `agents` (Dict): Initialized AutoGen agents
- `tool_bridge` (AgentToolBridge): Tool execution bridge
- `scb_client` (SCBClient): SCB client for state publishing
- `vtuber_client` (VTuberClient): VTuber client for output
**Returns:** None (runs indefinitely)
**Side Effects:** Logs all operations, updates statistics, triggers evolution

---

## Client Functions

### `scb_client.py`

#### `SCBClient.__init__(self, redis_client_url: str) -> None`
**Purpose:** Initialize SCB client with Redis connection
**Parameters:**
- `redis_client_url` (str): Redis connection URL or None to disable
**Returns:** None
**Side Effects:** Sets up Redis connection if URL provided

#### `SCBClient.enable_agentnet(self) -> None`
**Purpose:** Enable SCB state publishing
**Parameters:** None
**Returns:** None
**Side Effects:** Sets `agentnet_enabled = True`
**Example:**
```python
scb = SCBClient("redis://localhost:6379")
scb.enable_agentnet()
```

#### `SCBClient.publish_state(self, data: Dict[str, Any], force_publish: bool = False) -> None`
**Purpose:** Publish state data to shared cognitive blackboard
**Parameters:**
- `data` (Dict): State data to publish
- `force_publish` (bool): Override enabled check
**Returns:** None
**Side Effects:** Publishes to Redis channel "cognitive_agent_events"
**Data Structure:**
```python
{
    "iteration": int,
    "tool_used": str,
    "success": bool,
    "timestamp": float,
    "llm_enhanced": bool,
    "evolution_enhanced": bool,
    "agents_participated": List[str],
    "collaboration_score": int,
    "response_quality": float,
    "decision_time": float,
    "tools_executed": int
}
```

### `vtuber_client.py`

#### `VTuberClient.__init__(self, endpoint_url: str) -> None`
**Purpose:** Initialize VTuber client with endpoint
**Parameters:**
- `endpoint_url` (str): VTuber API endpoint URL or None to disable
**Returns:** None

#### `VTuberClient.post_message(self, message: str, force_send: bool = False) -> None`
**Purpose:** Send message to VTuber system for speech synthesis
**Parameters:**
- `message` (str): Text message to speak
- `force_send` (bool): Override activation check
**Returns:** None
**Side Effects:** HTTP POST to `/process_text` endpoint
**Request Body:**
```python
{
    "text": message,
    "autonomous_context": True
}
```

---

## Tool Registry Functions

### `tool_registry.py`

#### `ToolRegistry.load_tools(self) -> None`
**Purpose:** Dynamically load all tools from tools package
**Parameters:** None
**Returns:** None
**Side Effects:** Populates `self.tools` dictionary with tool instances
**Discovery:** Scans `autogen_agent.tools` package for modules with `run()` function

#### `ToolRegistry.select_tool(self, context: Dict[str, Any]) -> Optional[Callable]`
**Purpose:** Intelligent tool selection based on context scoring
**Parameters:**
- `context` (Dict): Current execution context
**Returns:** Tool function or None if no suitable tool
**Algorithm:**
1. Extract context text from all values
2. Calculate score for each tool (0.0-1.0)
3. Apply diversity bonus to prevent overuse
4. Return highest scoring tool

#### `ToolRegistry._calculate_tool_score(self, tool_name: str, context: Dict, context_text: str) -> float`
**Purpose:** Calculate relevance score for a tool given context
**Parameters:**
- `tool_name` (str): Name of tool to score
- `context` (Dict): Execution context
- `context_text` (str): Concatenated context text
**Returns:** Score between 0.0-1.0
**Components:**
- **Context Relevance (40%):** Keyword matching + semantic analysis
- **Historical Performance (30%):** Success rate + execution speed
- **Recent Success Rate (20%):** Last 10 executions performance
- **Diversity Bonus (10%):** Prevents tool overuse

#### `ToolRegistry.execute_tool_async(self, tool_name: str, context: Dict) -> Optional[Dict]`
**Purpose:** Execute tool asynchronously with error handling
**Parameters:**
- `tool_name` (str): Name of tool to execute
- `context` (Dict): Execution context
**Returns:** Tool result dictionary or None on error
**Error Handling:** Logs exceptions, returns None on failure

---

## Memory System Functions

### `cognitive_memory.py`

#### `CognitiveMemoryManager.__init__(self, db_url: str, cognee_url: str, cognee_api_key: str) -> None`
**Purpose:** Initialize memory manager with database and Cognee connections
**Parameters:**
- `db_url` (str): PostgreSQL connection URL
- `cognee_url` (str): Cognee API URL
- `cognee_api_key` (str): Cognee authentication token
**Returns:** None

#### `CognitiveMemoryManager.store_interaction(self, context: Dict, action: str, result: Dict) -> str`
**Purpose:** Store interaction in both PostgreSQL and Cognee
**Parameters:**
- `context` (Dict): Execution context
- `action` (str): Action performed
- `result` (Dict): Action result
**Returns:** Memory entry ID (string)
**Storage Process:**
1. Generate memory summary using LLM
2. Store in PostgreSQL with metadata
3. Store in Cognee for semantic search
4. Trigger knowledge graph processing

#### `CognitiveMemoryManager.retrieve_relevant_context(self, query: str, max_results: int = 5) -> List[MemoryEntry]`
**Purpose:** Semantic search for relevant memories
**Parameters:**
- `query` (str): Search query
- `max_results` (int): Maximum results to return
**Returns:** List of MemoryEntry objects
**Search Process:**
1. Query Cognee for semantic matches
2. Enhance with PostgreSQL metadata
3. Rank by relevance and recency
4. Return top results

---

## Evolution System Functions

### `cognitive_evolution_engine.py`  

#### `CognitiveEvolutionEngine.analyze_and_evolve(self, performance_context: Dict) -> Optional[EvolutionResult]`
**Purpose:** Main evolution cycle with Cognee integration
**Parameters:**
- `performance_context` (Dict): Current system performance data
**Returns:** EvolutionResult object or None if no improvements made
**Process:**
1. Store performance context in Cognee
2. Identify improvement opportunities
3. Query historical insights
4. Generate modification plan
5. Execute safely with rollback capability

#### `CognitiveEvolutionEngine._store_performance_context(self, context: Dict, cycle_id: str) -> None`
**Purpose:** Store rich performance context in Cognee for pattern learning
**Parameters:**
- `context` (Dict): Performance metrics and context
- `cycle_id` (str): Unique evolution cycle identifier
**Returns:** None
**Data Structure:**
```python
{
    "evolution_cycle_id": str,
    "performance_metrics": Dict,
    "system_state": Dict,
    "improvement_opportunities": List[str],
    "timestamp": float,
    "context_metadata": Dict
}
```

### `darwin_godel_engine.py`

#### `DarwinGodelEngine.analyze_code_performance(self, target_file: str) -> List[CodeAnalysisResult]`
**Purpose:** Analyze code file for performance bottlenecks and improvement opportunities
**Parameters:**
- `target_file` (str): Path to Python file to analyze
**Returns:** List of CodeAnalysisResult objects
**Analysis Types:**
- Cyclomatic complexity calculation
- AST-based bottleneck detection
- Import dependency analysis
- Function call frequency analysis

#### `DarwinGodelEngine.generate_code_improvements(self, analysis_results: List[CodeAnalysisResult], historical_context: Dict) -> List[Dict]`
**Purpose:** Generate code improvements using LLM with historical context
**Parameters:**
- `analysis_results` (List): Code analysis results
- `historical_context` (Dict): Previous improvement patterns
**Returns:** List of improvement dictionaries
**Improvement Structure:**
```python
{
    "target_file": str,
    "improvement_type": str,
    "original_code": str,
    "improved_code": str,
    "rationale": str,
    "confidence_score": float
}
```

#### `DarwinGodelEngine.test_modifications_safely(self, improvements: List[Dict]) -> List[SafetyTestResult]`
**Purpose:** Test code modifications in sandbox environment
**Parameters:**
- `improvements` (List): Code improvements to test
**Returns:** List of SafetyTestResult objects
**Safety Checks:**
- Syntax validation
- Import resolution
- Performance regression testing
- Basic functionality verification

---

## Service Functions

### `cognee_direct_service.py`

#### `CogneeDirectService.add_data(self, data: Union[str, Dict, List]) -> Dict`
**Purpose:** Add data to Cognee knowledge graph
**Parameters:**
- `data` (Union[str, Dict, List]): Data to add to knowledge graph
**Returns:** Operation result dictionary
**Process:**
1. Convert data to appropriate format
2. Add to Cognee dataset
3. Return success/failure status

#### `CogneeDirectService.search(self, query: str, limit: int = 10) -> List[Dict]`
**Purpose:** Semantic search in Cognee knowledge graph
**Parameters:**
- `query` (str): Search query
- `limit` (int): Maximum results to return
**Returns:** List of search result dictionaries
**Result Structure:**
```python
{
    "content": str,
    "score": float,
    "metadata": Dict,
    "timestamp": str
}
```

### `goal_management_service.py`

#### `GoalManagementService.define_goal(self, natural_language_goal: str, priority: str = "medium") -> Goal`
**Purpose:** Create SMART goal from natural language input
**Parameters:**
- `natural_language_goal` (str): Goal description in natural language
- `priority` (str): Goal priority ("low", "medium", "high")
**Returns:** Goal object with SMART criteria
**AI Enhancement Process:**
1. Parse natural language using LLM
2. Generate SMART criteria (Specific, Measurable, Achievable, Relevant, Time-bound)
3. Store in database with tracking metadata
4. Return structured Goal object

#### `GoalManagementService.generate_performance_metrics(self, timeframe_hours: int = 24) -> Dict`
**Purpose:** Generate goal performance correlation metrics
**Parameters:**
- `timeframe_hours` (int): Time window for analysis
**Returns:** Performance metrics dictionary
**Metrics Include:**
- Goal completion rate
- Average time to completion
- Performance correlation with system metrics
- Trend analysis

---

## Tool Functions

### `goal_management_tools.py`

#### `run(context: Dict) -> Dict[str, Any]`
**Purpose:** Main entry point for goal management tool
**Parameters:**
- `context` (Dict): Execution context with action and parameters
**Returns:** Standardized tool result dictionary
**Actions Supported:**
- `define_goal` - Create new goal
- `get_goals` - Retrieve active goals
- `update_progress` - Update goal progress
- `generate_report` - Create performance report
- `query_memory` - Search goal history

### `core_evolution_tool.py`

#### `run(context: Dict) -> Dict[str, Any]`
**Purpose:** Trigger Darwin-Gödel Machine evolution process
**Parameters:**
- `context` (Dict): Current system context and performance metrics
**Returns:** Evolution result dictionary
**Evolution Actions:**
- `analyze_performance` - Analyze current system performance
- `identify_opportunities` - Find improvement opportunities
- `trigger_evolution` - Execute evolution cycle
- `get_status` - Return evolution system status

### `advanced_vtuber_control.py`

#### `run(context: Dict) -> Dict[str, Any]`
**Purpose:** Control VTuber system with advanced features
**Parameters:**
- `context` (Dict): VTuber control context
**Returns:** VTuber control result
**Control Actions:**
- `speak` - Send text for speech synthesis
- `create_instance` - Create new VTuber instance
- `control_instance` - Control existing instance
- `shutdown_instance` - Terminate VTuber instance

---

## Statistics Functions

### `statistics_collector.py`

#### `StatisticsCollector.collect_cycle_stats(self, cycle_data: Dict) -> None`
**Purpose:** Collect performance statistics for each decision cycle
**Parameters:**
- `cycle_data` (Dict): Cycle performance data
**Returns:** None
**Side Effects:** Stores statistics in database
**Data Collected:**
- Iteration number and timestamp
- Decision time and tool execution time
- Success/failure rates
- Agent collaboration metrics

#### `StatisticsCollector.generate_report(self, report_type: str, timeframe: str, filters: Dict = None) -> Dict`
**Purpose:** Generate comprehensive analytics report
**Parameters:**
- `report_type` (str): Type of report ("performance", "tools", "evolution")
- `timeframe` (str): Time window ("1h", "24h", "7d", "30d")
- `filters` (Dict): Optional filters for data
**Returns:** Formatted report dictionary
**Report Types:**
- **Performance Report:** System performance metrics over time
- **Tool Usage Report:** Tool selection and success rates
- **Evolution Report:** Evolution cycle outcomes and improvements

---

## Monitoring Functions

### `gpu_monitor.py`

#### `GPUMonitor.get_gpu_status(self) -> Dict`
**Purpose:** Get comprehensive GPU status information
**Parameters:** None
**Returns:** GPU status dictionary
**Information Included:**
```python
{
    "gpu_available": bool,
    "gpu_count": int,
    "devices": List[Dict],
    "memory": Dict,
    "utilization": Dict,
    "temperature": Dict,
    "cycle_count": int
}
```

#### `GPUMonitor.get_summary(self) -> Dict`
**Purpose:** Get quick GPU health summary
**Parameters:** None
**Returns:** Summary dictionary with key metrics
**Use Case:** Health checks and monitoring dashboards

### `ollama_monitor.py`

#### `OllamaMonitor.get_running_models(self) -> Dict`
**Purpose:** Get information about currently running Ollama models
**Parameters:** None
**Returns:** Running models information
**Information Structure:**
```python
{
    "models": List[Dict],
    "total_models": int,
    "estimated_vram_usage": str,
    "status": str
}
```

---

## Usage Examples

### Complete Function Call Chain

```python
# Initialize system
scb_client = SCBClient(redis_url)
vtuber_client = VTuberClient(vtuber_endpoint)
tool_registry = ToolRegistry()
tool_registry.load_tools()

# Create agent bridge
tool_bridge = AgentToolBridge(tool_registry, scb_client, vtuber_client)

# Initialize agents
agents = initialize_autogen_agents(llm_config)

# Run decision cycle
responses, tools, metrics = run_autogen_decision_cycle(
    iteration=1,
    agents=agents,
    tool_bridge=tool_bridge,
    scb_client=scb_client,
    vtuber_client=vtuber_client
)

# Publish results
scb_client.publish_state({
    "iteration": 1,
    "success": True,
    "metrics": metrics
})
```

### Tool Execution Example

```python
# Tool selection and execution
context = {
    "action": "define_goal",
    "goal_text": "Improve system response time by 20%",
    "priority": "high"
}

# Select appropriate tool
tool = tool_registry.select_tool(context)

# Execute tool
result = await tool_registry.execute_tool_async(tool.__name__, context)

# Process result
if result and result.get("success"):
    print(f"Goal created: {result['data']['goal_id']}")
```

---

## Error Handling Patterns

All functions follow consistent error handling:

```python
def function_template(param: Type) -> ReturnType:
    try:
        # Validate parameters
        if not param:
            raise ValueError("Parameter required")
        
        # Main logic
        result = perform_operation(param)
        
        # Return success
        return result
        
    except Exception as e:
        # Log error with context
        logger.error(f"Function failed: {e}", extra={
            "function": "function_template",
            "param": param,
            "error_type": type(e).__name__
        })
        
        # Return appropriate default/error value
        return None  # or appropriate error structure
```

---

## Version Information

- **Documentation Version:** 1.0.0
- **Last Updated:** Current Date
- **Maintainer:** AutoGen Documentation System