# 🧠 **Implement Intelligent Tool Selection System**

## **OBJECTIVE**
Replace the naive round-robin tool selection in `app/CORE/autogen-agent/autogen_agent/tool_registry.py` with an intelligent, context-aware selection system that maximizes tool utilization effectiveness.

## **CURRENT PROBLEM**
The existing tool selection is naive and wasteful:
```python
# Current naive implementation (Lines 66-77 in tool_registry.py)
def select_tool(self, context: dict) -> Optional[Callable]:
    # Simple round-robin selection for now
    iteration = context.get("iteration", 0)
    tool_names = list(self.tools.keys())
    selected_name = tool_names[iteration % len(tool_names)]  # ❌ RANDOM!
```

**Impact:** Sophisticated tools like `goal_management_tools`, `core_evolution_tool`, and `advanced_vtuber_control` are randomly selected instead of being chosen when contextually relevant.

## **SOLUTION REQUIREMENTS**

### **1. Replace `select_tool()` Method**
Replace the naive round-robin selection with intelligent scoring based on:
- **Context Relevance (40%)** - Match tool to context keywords/patterns
- **Historical Performance (30%)** - Success rate and execution time
- **Recent Success Rate (20%)** - Performance in last 10 uses
- **Diversity Bonus (10%)** - Avoid overusing same tools

### **2. Add Context-Tool Mapping**
```python
self.context_tool_mapping = {
    # Goal-related contexts
    "goal": ["goal_management_tools"],
    "progress": ["goal_management_tools"],
    "achievement": ["goal_management_tools"],
    "target": ["goal_management_tools"],
    "smart": ["goal_management_tools"],
    
    # Evolution/Performance contexts
    "performance": ["core_evolution_tool"],
    "optimization": ["core_evolution_tool"],
    "improvement": ["core_evolution_tool"],
    "evolution": ["core_evolution_tool"],
    "error": ["core_evolution_tool"],
    "speed": ["core_evolution_tool"],
    
    # VTuber-related contexts
    "vtuber": ["advanced_vtuber_control"],
    "avatar": ["advanced_vtuber_control"],
    "stream": ["advanced_vtuber_control"],
    "audience": ["advanced_vtuber_control"],
    "activate": ["advanced_vtuber_control"],
    
    # Dynamic/Variable contexts
    "dynamic": ["variable_tool_calls"],
    "adaptive": ["variable_tool_calls"],
    "context": ["variable_tool_calls"]
}
```

### **3. Add Performance Tracking**
```python
self.tool_performance = {
    'tool_name': {
        'total_uses': 0,
        'successes': 0,
        'avg_execution_time': 0.0,
        'context_relevance_scores': [],
        'last_used': 0
    }
}
self.tool_usage_history = []  # Track recent usage for diversity
```

### **4. Implement Scoring Algorithm**
```python
def _calculate_tool_score(self, tool_name: str, context: dict, context_text: str) -> float:
    score = 0.0
    
    # Context Relevance (40%)
    context_relevance = self._calculate_context_relevance(tool_name, context_text)
    score += context_relevance * 0.4
    
    # Historical Performance (30%)
    historical_performance = self._get_historical_performance(tool_name)
    score += historical_performance * 0.3
    
    # Recent Success Rate (20%)
    recent_success = self._get_recent_success_rate(tool_name)
    score += recent_success * 0.2
    
    # Diversity Bonus (10%)
    diversity_bonus = self._calculate_diversity_bonus(tool_name)
    score += diversity_bonus * 0.1
    
    return min(score, 1.0)
```

### **5. Special Context Handling**
- **Iteration-based patterns**: `core_evolution_tool` gets bonus every 5 iterations
- **Autonomous mode bonus**: Sophisticated tools get +0.2 score in autonomous mode
- **Performance triggers**: `core_evolution_tool` gets high score when errors > 3 or decision_time > 3.0

### **6. Update Tool Execution Methods**
Modify `execute_tool_sync()` and `execute_tool_async()` to:
- Track execution time
- Record success/failure
- Update performance metrics
- Log intelligent selection decisions

## **IMPLEMENTATION DETAILS**

### **Key Methods to Implement:**
1. `_calculate_context_relevance(tool_name, context_text)` - Match keywords to tools
2. `_get_historical_performance(tool_name)` - Calculate success rate × speed factor
3. `_get_recent_success_rate(tool_name, lookback=10)` - Recent performance
4. `_calculate_diversity_bonus(tool_name)` - Prevent overuse
5. `_extract_context_text(context)` - Extract searchable text from context
6. `_update_tool_usage(tool_name, context)` - Track usage patterns
7. `update_tool_performance(tool_name, success, execution_time)` - Update metrics

### **Context Relevance Implementation**
```python
def _calculate_context_relevance(self, tool_name: str, context_text: str) -> float:
    relevance_score = 0.0
    context_lower = context_text.lower()
    
    # Check direct context mapping
    for keyword, relevant_tools in self.context_tool_mapping.items():
        if keyword in context_lower and tool_name in relevant_tools:
            relevance_score += 0.8  # High relevance for direct matches
            
    # Check for specific tool indicators
    tool_indicators = {
        "goal_management_tools": ["goal", "progress", "achievement", "target", "smart", "objective"],
        "core_evolution_tool": ["performance", "optimization", "improvement", "evolution", "error", "speed"],
        "advanced_vtuber_control": ["vtuber", "avatar", "stream", "audience", "activate", "control"],
        "variable_tool_calls": ["dynamic", "adaptive", "context", "variable", "selection"]
    }
    
    if tool_name in tool_indicators:
        indicators = tool_indicators[tool_name]
        matches = sum(1 for indicator in indicators if indicator in context_lower)
        relevance_score += (matches / len(indicators)) * 0.6
    
    # Iteration-based relevance for core evolution
    if tool_name == "core_evolution_tool":
        iteration = context.get("iteration", 0)
        # Higher relevance for evolution tool every 5 iterations
        if iteration % 5 == 0:
            relevance_score += 0.3
            
    # Autonomous mode bonus for sophisticated tools
    if context.get("autonomous", False):
        sophisticated_tools = ["goal_management_tools", "core_evolution_tool", "variable_tool_calls"]
        if tool_name in sophisticated_tools:
            relevance_score += 0.2
    
    return min(relevance_score, 1.0)
```

### **Performance Tracking Implementation**
```python
def _get_historical_performance(self, tool_name: str) -> float:
    if tool_name not in self.tool_performance:
        return 0.5  # Default neutral score for new tools
    
    metrics = self.tool_performance[tool_name]
    total_uses = metrics.get('total_uses', 0)
    
    if total_uses == 0:
        return 0.5  # No history, neutral score
    
    success_rate = metrics.get('successes', 0) / total_uses
    avg_execution_time = metrics.get('avg_execution_time', 5.0)
    
    # Combine success rate and speed (penalize slow tools)
    time_factor = max(0.1, 1.0 - (avg_execution_time / 10.0))
    return success_rate * time_factor

def update_tool_performance(self, tool_name: str, success: bool, execution_time: float):
    if tool_name not in self.tool_performance:
        return
    
    metrics = self.tool_performance[tool_name]
    metrics['total_uses'] += 1
    
    if success:
        metrics['successes'] += 1
    
    # Update average execution time
    current_avg = metrics['avg_execution_time']
    total_uses = metrics['total_uses']
    metrics['avg_execution_time'] = ((current_avg * (total_uses - 1)) + execution_time) / total_uses
```

### **Diversity Bonus Implementation**
```python
def _calculate_diversity_bonus(self, tool_name: str) -> float:
    if not self.tool_usage_history:
        return 0.5
    
    # Check last 5 tool uses
    recent_tools = [entry.get('tool') for entry in self.tool_usage_history[-5:]]
    tool_count = recent_tools.count(tool_name)
    
    # More recent use = lower diversity bonus
    if tool_count == 0:
        return 1.0  # Not used recently, high bonus
    elif tool_count == 1:
        return 0.7  # Used once, moderate bonus
    elif tool_count == 2:
        return 0.4  # Used twice, low bonus
    else:
        return 0.1  # Used frequently, very low bonus
```

### **Context Text Extraction**
```python
def _extract_context_text(self, context: dict) -> str:
    text_parts = []
    
    # Extract common text fields
    for key in ['message', 'action', 'request', 'description', 'goal', 'task']:
        if key in context and isinstance(context[key], str):
            text_parts.append(context[key])
    
    # Add iteration info for pattern matching
    if 'iteration' in context:
        text_parts.append(f"iteration {context['iteration']}")
        
    # Add autonomous indicator
    if context.get('autonomous', False):
        text_parts.append("autonomous mode")
    
    return " ".join(text_parts).lower()
```

### **Enhanced Tool Status**
```python
def get_tool_status(self) -> Dict[str, Any]:
    # Calculate performance summary
    performance_summary = {}
    for tool_name, metrics in self.tool_performance.items():
        if metrics['total_uses'] > 0:
            success_rate = metrics['successes'] / metrics['total_uses']
            performance_summary[tool_name] = {
                'success_rate': success_rate,
                'avg_execution_time': metrics['avg_execution_time'],
                'total_uses': metrics['total_uses']
            }
            
    return {
        "total_tools": len(self.tools),
        "available_tools": list(self.tools.keys()),
        "intelligent_selection_enabled": True,
        "performance_summary": performance_summary,
        "usage_history_length": len(self.tool_usage_history),
        "context_mappings": len(self.context_tool_mapping)
    }
```

## **INTEGRATION POINTS**

### **Initialize in Constructor**
```python
def __init__(self, package: str = "autogen_agent.tools"):
    # ... existing code ...
    
    # 🧠 INTELLIGENT TOOL SELECTION - Track performance metrics
    self.tool_performance = {}
    self.tool_usage_history = []
    self.context_tool_mapping = {
        # ... mapping as defined above ...
    }
```

### **Initialize Performance Tracking in load_tools()**
```python
def load_tools(self) -> None:
    # ... existing loading code ...
    
    # Initialize performance tracking for each loaded tool
    if hasattr(module, 'run'):
        self.tools[tool_name] = module.run
        
        # Initialize performance tracking
        self.tool_performance[tool_name] = {
            'total_uses': 0,
            'successes': 0,
            'avg_execution_time': 0.0,
            'context_relevance_scores': [],
            'last_used': 0
        }
```

### **Update Execution Methods**
```python
async def execute_tool_async(self, tool_name: str, context: dict) -> Optional[dict]:
    # ... existing code ...
    
    try:
        import time
        start_time = time.time()
        
        # Execute tool
        if inspect.iscoroutinefunction(tool):
            result = await tool(context)
        else:
            result = tool(context)
        
        execution_time = time.time() - start_time
        success = result.get('success', True) if isinstance(result, dict) else True
        
        # Update performance metrics
        self.update_tool_performance(tool_name, success, execution_time)
        
        return result
    except Exception as e:
        # Update performance with failure
        self.update_tool_performance(tool_name, False, 0.0)
        raise e
```

## **EXPECTED OUTCOMES**

### **Before (Current State):**
- ❌ `goal_management_tools` used 20% of time (random)
- ❌ `core_evolution_tool` used 20% of time (random)  
- ❌ Tools selected regardless of context relevance
- ❌ No learning from tool effectiveness

### **After (Intelligent Selection):**
- ✅ `goal_management_tools` used 80%+ when goal contexts detected
- ✅ `core_evolution_tool` used 90%+ when performance issues detected
- ✅ Context-aware selection based on keywords and patterns
- ✅ Learning from historical tool performance
- ✅ **3-5x improvement in tool utilization effectiveness**

## **VALIDATION CRITERIA**

After implementation, verify:

1. **Intelligent Selection Logging**:
   ```
   🧠 [TOOL_REGISTRY] INTELLIGENT selection: goal_management_tools (score: 0.847)
   🎯 [TOOL_REGISTRY] Tool goal_management_tools: score 0.847
   ```

2. **Context-Appropriate Selection**:
   - Goal-related contexts → `goal_management_tools`
   - Performance issues → `core_evolution_tool`
   - VTuber contexts → `advanced_vtuber_control`

3. **Performance Learning**:
   - Tools with higher success rates get selected more often
   - Slow tools get penalized in scoring
   - Recent failures reduce tool selection probability

4. **Diversity Maintenance**:
   - No single tool dominates selection
   - Recently used tools get lower diversity bonus
   - All tools get opportunities based on context

## **FILES TO MODIFY**
- **Primary**: `app/CORE/autogen-agent/autogen_agent/tool_registry.py`
- **Test**: Verify integration with `cognitive_decision_engine.py` and `main.py`

## **TESTING APPROACH**

1. **Unit Tests**: Test scoring algorithms with known contexts
2. **Integration Tests**: Verify tool selection in autonomous cycles
3. **Performance Tests**: Measure improvement in tool utilization
4. **Logging Analysis**: Review selection decisions and scores

**Transform the tool selection from random to intelligent, context-aware, and performance-driven!** 🚀 