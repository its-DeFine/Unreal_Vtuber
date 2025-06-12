# Functional Requirements Document (FRD)
# Autonomous Agent Statistics, Evolution & Persistence System

**Version**: 1.0  
**Date**: December 12, 2024  
**PRD Reference**: AUTONOMOUS_STATISTICS_EVOLUTION_PRD.md  
**Status**: Draft

## 1. Introduction

This FRD provides detailed functional specifications for implementing comprehensive statistics tracking, persistent storage, and real evolution capabilities in the AutoGen autonomous agent system. It serves as the implementation guide for developers.

## 2. System Architecture Overview

```
┌─────────────────────────────────────────────────────────────┐
│                    AutoGen Agent System                      │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐       │
│  │   Agent 1   │  │   Agent 2   │  │   Agent 3   │       │
│  └──────┬──────┘  └──────┬──────┘  └──────┬──────┘       │
│         │                 │                 │               │
│         └─────────────────┴─────────────────┘               │
│                           │                                 │
│                    ┌──────▼──────┐                         │
│                    │ Tool Bridge │                         │
│                    └──────┬──────┘                         │
│                           │                                 │
│         ┌─────────────────┴─────────────────┐             │
│         │          Tool Registry            │              │
│         │    (with Usage Tracking)          │              │
│         └─────────────────┬─────────────────┘             │
│                           │                                 │
│  ┌──────────────┐  ┌─────▼──────┐  ┌──────────────┐     │
│  │  Statistics  │  │   Tools    │  │  Evolution   │      │
│  │   Collector  │  │            │  │   Engine     │      │
│  └──────┬───────┘  └────────────┘  └──────┬───────┘     │
│         │                                   │              │
│         └───────────────┬───────────────────┘              │
│                         │                                   │
│                  ┌──────▼──────┐                          │
│                  │ Persistence │                          │
│                  │    Layer    │                          │
│                  └──────┬──────┘                          │
│                         │                                   │
│      ┌──────────────────┴──────────────────┐              │
│      │                                      │              │
│ ┌────▼─────┐                        ┌──────▼──────┐       │
│ │PostgreSQL│                        │   Cognee    │       │
│ │(KPIs)    │                        │(Long-term) │       │
│ └──────────┘                        └─────────────┘       │
└─────────────────────────────────────────────────────────────┘
```

## 3. Detailed Functional Specifications

### 3.1 Statistics Collection & Persistence

#### 3.1.1 Statistics Collector Enhancement

**File**: `app/CORE/autogen-agent/autogen_agent/statistics_collector.py` (NEW)

```python
class StatisticsCollector:
    """
    Centralized statistics collection and persistence
    """
    
    def __init__(self, db_url: str):
        self.db_url = db_url
        self.buffer = []  # Batch writes
        self.buffer_size = 100
        self.flush_interval = 5.0  # seconds
        
    async def collect_cycle_stats(self, cycle_data: Dict):
        """Collect statistics for each decision cycle"""
        stats = {
            "timestamp": datetime.now(),
            "iteration": cycle_data.get("iteration"),
            "cycle_duration": cycle_data.get("duration"),
            "agents_participated": cycle_data.get("agents"),
            "tools_executed": cycle_data.get("tools_executed"),
            "success": cycle_data.get("success"),
            "error_count": cycle_data.get("errors", 0),
            "memory_usage": self._get_memory_usage(),
            "decision_time": cycle_data.get("decision_time")
        }
        
        await self._add_to_buffer(stats)
        
    async def collect_tool_usage(self, tool_data: Dict):
        """Collect tool execution statistics"""
        usage = {
            "timestamp": datetime.now(),
            "tool_name": tool_data.get("tool"),
            "execution_time": tool_data.get("execution_time"),
            "success": tool_data.get("success"),
            "input_context": tool_data.get("context"),
            "output_result": tool_data.get("result"),
            "requesting_agent": tool_data.get("agent"),
            "selection_score": tool_data.get("score"),
            "iteration": tool_data.get("iteration")
        }
        
        await self._persist_tool_usage(usage)
```

#### 3.1.2 Database Persistence Layer

**Updates to**: `app/CORE/autogen-agent/autogen_agent/main.py`

```python
# Add after analytics_data initialization
statistics_collector = None

async def initialize_statistics_collector():
    """Initialize statistics collector with database connection"""
    global statistics_collector
    db_url = os.getenv("DATABASE_URL")
    statistics_collector = StatisticsCollector(db_url)
    await statistics_collector.initialize()
    logging.info("📊 [STATISTICS] Collector initialized with persistence")

# Update run_autogen_decision_cycle to persist stats
async def run_autogen_decision_cycle(iteration: int, scb: SCBClient, vtuber: VTuberClient):
    # ... existing code ...
    
    # After tool execution
    if tool_executions and statistics_collector:
        await statistics_collector.collect_cycle_stats({
            "iteration": iteration,
            "duration": time.time() - start_time,
            "agents": list(agent_responses.keys()),
            "tools_executed": tool_executions.get('total_executions', 0),
            "success": tool_executions.get('successful_executions', 0) > 0,
            "decision_time": decision_time
        })
```

### 3.2 Tool Usage Tracking

#### 3.2.1 Enhanced Tool Registry

**Updates to**: `app/CORE/autogen-agent/autogen_agent/tool_registry.py`

```python
# Add to execute_tool_async method
async def execute_tool_async(self, tool_name: str, context: dict) -> Optional[dict]:
    """Execute a tool asynchronously with full tracking"""
    tool = self.get_tool_by_name(tool_name)
    if not tool:
        return None
        
    # Track execution start
    execution_id = f"exec_{datetime.now().strftime('%Y%m%d_%H%M%S_%f')}"
    start_time = time.time()
    
    try:
        # Execute tool
        result = await tool(context) if inspect.iscoroutinefunction(tool) else tool(context)
        
        execution_time = time.time() - start_time
        success = result.get('success', True) if isinstance(result, dict) else True
        
        # Persist tool usage
        if statistics_collector:
            await statistics_collector.collect_tool_usage({
                "execution_id": execution_id,
                "tool": tool_name,
                "execution_time": execution_time,
                "success": success,
                "context": context,
                "result": result,
                "agent": context.get('requested_by_agent', 'system'),
                "score": self._get_last_selection_score(tool_name),
                "iteration": context.get('iteration', 0)
            })
        
        # Update performance metrics
        self.update_tool_performance(tool_name, success, execution_time)
        
        return result
```

### 3.3 Conversation Storage

#### 3.3.1 Conversation Persistence Service

**File**: `app/CORE/autogen-agent/autogen_agent/services/conversation_storage_service.py` (NEW)

```python
class ConversationStorageService:
    """
    Store and retrieve agent conversations
    """
    
    def __init__(self, db_url: str, cognee_service=None):
        self.db_url = db_url
        self.cognee_service = cognee_service
        
    async def store_conversation(self, conversation_data: Dict):
        """Store complete conversation thread"""
        conversation = {
            "id": f"conv_{datetime.now().strftime('%Y%m%d_%H%M%S_%f')}",
            "iteration": conversation_data.get("iteration"),
            "timestamp": datetime.now(),
            "agents": conversation_data.get("agents"),
            "messages": conversation_data.get("messages"),
            "outcome": conversation_data.get("outcome"),
            "tools_triggered": conversation_data.get("tools_triggered"),
            "duration": conversation_data.get("duration")
        }
        
        # Store in PostgreSQL
        await self._persist_to_postgres(conversation)
        
        # Store summary in Cognee for semantic search
        if self.cognee_service:
            summary = self._generate_conversation_summary(conversation)
            await self.cognee_service.add_data([summary])
```

#### 3.3.2 Integration with Decision Cycle

**Updates to**: `app/CORE/autogen-agent/autogen_agent/main.py`

```python
# Add conversation storage
conversation_storage = None

# In run_autogen_decision_cycle, after group chat completes:
if group_chat_result and conversation_storage:
    await conversation_storage.store_conversation({
        "iteration": iteration,
        "agents": list(agent_responses.keys()),
        "messages": group_chat_result.chat_history,
        "outcome": {
            "tools_executed": tool_executions,
            "final_response": final_response
        },
        "duration": time.time() - cycle_start_time
    })
```

### 3.4 Evolution System Activation

#### 3.4.1 Evolution Configuration

**Updates to**: `docker-compose.autogen-ollama.yml`

```yaml
environment:
  # Enable real evolution
  - DARWIN_GODEL_REAL_MODIFICATIONS=true
  - DARWIN_GODEL_REQUIRE_APPROVAL=false
  - DARWIN_GODEL_PERFORMANCE_THRESHOLD=10
  - DARWIN_GODEL_BACKUP_RETENTION_DAYS=30
  - DARWIN_GODEL_MAX_MODIFICATIONS_PER_CYCLE=3
  
  # Enable statistics persistence
  - STATISTICS_PERSISTENCE_ENABLED=true
  - STATISTICS_RETENTION_DAYS=90
  - CONVERSATION_STORAGE_ENABLED=true
```

#### 3.4.2 Evolution Tracking

**Updates to**: `app/CORE/autogen-agent/autogen_agent/evolution/darwin_godel_engine.py`

```python
async def _deploy_single_modification(self, improvement: Dict) -> Dict:
    """Deploy modification with full tracking"""
    
    # ... existing safety checks ...
    
    # Track modification in database
    modification_record = {
        "id": improvement['id'],
        "timestamp": datetime.now(),
        "target_file": improvement['target_file'],
        "modification_type": improvement.get('type', 'optimization'),
        "expected_improvement": improvement.get('expected_improvement'),
        "risk_level": improvement.get('risk_level'),
        "backup_path": backup_path,
        "status": "pending"
    }
    
    if statistics_collector:
        await statistics_collector.collect_evolution_action(modification_record)
    
    # Apply modification
    if self.real_modifications_enabled:
        success = await self._apply_real_modification(improvement)
        
        # Measure actual impact
        actual_impact = await self._measure_actual_impact(improvement)
        
        # Update record
        modification_record.update({
            "status": "applied" if success else "failed",
            "actual_improvement": actual_impact.get('improvement', 0),
            "performance_impact": actual_impact
        })
        
        if statistics_collector:
            await statistics_collector.update_evolution_result(modification_record)
```

### 3.5 Cognee Long-term Storage

#### 3.5.1 Pattern Storage Service

**File**: `app/CORE/autogen-agent/autogen_agent/services/pattern_storage_service.py` (NEW)

```python
class PatternStorageService:
    """
    Store successful patterns and improvements in Cognee
    """
    
    def __init__(self, cognee_service):
        self.cognee_service = cognee_service
        
    async def store_successful_pattern(self, pattern_data: Dict):
        """Store successful decision/improvement patterns"""
        pattern_doc = f"""
Pattern ID: {pattern_data['id']}
Type: {pattern_data['type']}
Success Rate: {pattern_data['success_rate']}
Context: {pattern_data['context']}
Actions: {pattern_data['actions']}
Outcomes: {pattern_data['outcomes']}
Performance Impact: {pattern_data['performance_impact']}
        """
        
        await self.cognee_service.add_data([pattern_doc])
        
    async def retrieve_similar_patterns(self, context: Dict) -> List[Dict]:
        """Retrieve patterns similar to current context"""
        query = self._build_context_query(context)
        results = await self.cognee_service.search(query, limit=5)
        return self._parse_pattern_results(results)
```

### 3.6 Reporting API Endpoints

#### 3.6.1 Enhanced Statistics API

**Updates to**: `app/CORE/autogen-agent/autogen_agent/main.py`

```python
@app.get("/api/statistics/detailed")
async def get_detailed_statistics(
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    include_tools: bool = True,
    include_agents: bool = True
):
    """Get comprehensive statistics with filtering"""
    stats = await statistics_collector.get_statistics(
        start_date=start_date,
        end_date=end_date
    )
    
    return {
        "summary": {
            "total_cycles": stats['total_cycles'],
            "success_rate": stats['success_rate'],
            "avg_decision_time": stats['avg_decision_time'],
            "total_tools_executed": stats['total_tools_executed']
        },
        "tools": stats['tool_statistics'] if include_tools else None,
        "agents": stats['agent_statistics'] if include_agents else None,
        "performance_trend": stats['performance_trend'],
        "evolution_impact": stats['evolution_statistics']
    }

@app.get("/api/tools/usage")
async def get_tool_usage_report(
    tool_name: Optional[str] = None,
    limit: int = 100
):
    """Get detailed tool usage analytics"""
    usage = await statistics_collector.get_tool_usage(
        tool_name=tool_name,
        limit=limit
    )
    
    return {
        "tool_usage": usage,
        "most_used": usage[:10],
        "success_rates": {t['tool']: t['success_rate'] for t in usage},
        "avg_execution_times": {t['tool']: t['avg_time'] for t in usage}
    }

@app.get("/api/conversations")
async def get_conversations(
    iteration: Optional[int] = None,
    limit: int = 50
):
    """Retrieve stored conversations"""
    conversations = await conversation_storage.get_conversations(
        iteration=iteration,
        limit=limit
    )
    
    return {
        "conversations": conversations,
        "total": len(conversations)
    }

@app.get("/api/evolution/history")
async def get_evolution_history():
    """Get history of all evolution changes"""
    history = await statistics_collector.get_evolution_history()
    
    return {
        "modifications": history,
        "total_improvements": len([h for h in history if h['status'] == 'applied']),
        "avg_improvement": sum(h.get('actual_improvement', 0) for h in history) / max(len(history), 1),
        "risk_breakdown": {
            "low": len([h for h in history if h['risk_level'] == 'low']),
            "medium": len([h for h in history if h['risk_level'] == 'medium']),
            "high": len([h for h in history if h['risk_level'] == 'high'])
        }
    }

@app.post("/api/reports/generate")
async def generate_custom_report(request: Dict):
    """Generate custom analytics report"""
    report_type = request.get("type", "comprehensive")
    timeframe = request.get("timeframe", "24h")
    
    report = await statistics_collector.generate_report(
        report_type=report_type,
        timeframe=timeframe,
        filters=request.get("filters", {})
    )
    
    return report
```

### 3.7 Database Schema Implementation

#### 3.7.1 SQL Migration Script

**File**: `migrations/enable_full_statistics.sql`

```sql
-- Ensure all analytics tables exist and are optimized

-- Add indexes for performance
CREATE INDEX idx_tool_usage_timestamp ON tool_usage(timestamp);
CREATE INDEX idx_tool_usage_tool_name ON tool_usage(tool_name);
CREATE INDEX idx_tool_usage_agent ON tool_usage(agent_id);

CREATE INDEX idx_decision_patterns_effectiveness ON decision_patterns(effectiveness_score DESC);
CREATE INDEX idx_decision_patterns_frequency ON decision_patterns(usage_frequency DESC);

-- Add conversation storage table
CREATE TABLE IF NOT EXISTS conversations (
    id VARCHAR(255) PRIMARY KEY,
    iteration INTEGER NOT NULL,
    timestamp TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    agents JSONB,
    messages JSONB,
    outcome JSONB,
    tools_triggered JSONB,
    duration FLOAT,
    search_vector tsvector
);

CREATE INDEX idx_conversations_iteration ON conversations(iteration);
CREATE INDEX idx_conversations_timestamp ON conversations(timestamp);
CREATE INDEX idx_conversations_search ON conversations USING GIN(search_vector);

-- Add evolution tracking table
CREATE TABLE IF NOT EXISTS evolution_history (
    id VARCHAR(255) PRIMARY KEY,
    timestamp TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    target_file TEXT,
    modification_type VARCHAR(50),
    expected_improvement FLOAT,
    actual_improvement FLOAT,
    risk_level VARCHAR(20),
    backup_path TEXT,
    status VARCHAR(50),
    performance_impact JSONB,
    rollback_performed BOOLEAN DEFAULT FALSE
);

CREATE INDEX idx_evolution_history_timestamp ON evolution_history(timestamp);
CREATE INDEX idx_evolution_history_status ON evolution_history(status);

-- Add statistics summary table for fast queries
CREATE TABLE IF NOT EXISTS statistics_summary (
    date DATE PRIMARY KEY,
    total_cycles INTEGER DEFAULT 0,
    successful_cycles INTEGER DEFAULT 0,
    total_tools_executed INTEGER DEFAULT 0,
    avg_decision_time FLOAT,
    avg_memory_usage FLOAT,
    total_errors INTEGER DEFAULT 0,
    performance_score FLOAT,
    evolution_changes INTEGER DEFAULT 0,
    updated_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
);

-- Create view for tool effectiveness
CREATE OR REPLACE VIEW tool_effectiveness AS
SELECT 
    tool_name,
    COUNT(*) as total_uses,
    AVG(CASE WHEN success THEN 1 ELSE 0 END) as success_rate,
    AVG(execution_time) as avg_execution_time,
    COUNT(DISTINCT agent_id) as unique_agents
FROM tool_usage
GROUP BY tool_name;
```

## 4. Implementation Plan

### Phase 1: Database & Core Infrastructure (Week 1)
1. Run database migrations
2. Implement StatisticsCollector class
3. Update main.py with persistence hooks
4. Test data integrity

### Phase 2: Tool Usage Tracking (Week 1-2)
1. Enhance ToolRegistry with tracking
2. Implement tool usage persistence
3. Update statistics API
4. Verify performance impact

### Phase 3: Conversation Storage (Week 2)
1. Implement ConversationStorageService
2. Integrate with decision cycle
3. Add search functionality
4. Test retrieval performance

### Phase 4: Evolution Activation (Week 2-3)
1. Update environment configuration
2. Add evolution tracking
3. Implement safety monitoring
4. Measure first improvements

### Phase 5: Cognee Integration (Week 3)
1. Implement PatternStorageService
2. Configure long-term storage
3. Enable pattern learning
4. Test semantic retrieval

### Phase 6: API & Reporting (Week 3-4)
1. Implement all API endpoints
2. Create report generation logic
3. Add data export functionality
4. Performance optimization

## 5. Testing Requirements

### 5.1 Unit Tests
- Statistics collection accuracy
- Tool usage tracking completeness
- Conversation storage integrity
- Evolution safety mechanisms

### 5.2 Integration Tests
- End-to-end statistics flow
- Database performance under load
- API response times
- Cognee integration reliability

### 5.3 Performance Tests
- Statistics write latency < 100ms
- Query response time < 500ms
- No impact on decision cycles
- Support for 1M+ records

## 6. Monitoring & Alerts

### 6.1 Key Metrics to Monitor
- Statistics write success rate
- Database query performance
- Evolution modification success rate
- Storage growth rate
- API response times

### 6.2 Alert Conditions
- Statistics write failures > 1%
- Query response time > 1s
- Evolution rollback triggered
- Storage usage > 80%
- Error rate > 5%

## 7. Success Validation

### Week 1 Checkpoint
- [ ] Statistics persisting to database
- [ ] Tool usage being tracked
- [ ] Basic queries working

### Week 2 Checkpoint
- [ ] Conversations stored and searchable
- [ ] Evolution making real changes
- [ ] Performance metrics improving

### Week 3 Checkpoint
- [ ] Cognee storing patterns
- [ ] All APIs functional
- [ ] Reports generating correctly

### Final Validation
- [ ] 30 days of historical data available
- [ ] Performance improved by >10%
- [ ] Zero data loss incidents
- [ ] Developer satisfaction survey positive

---

**Next Steps**: 
1. Review and approve FRD
2. Create development tickets
3. Assign implementation tasks
4. Begin Phase 1 implementation