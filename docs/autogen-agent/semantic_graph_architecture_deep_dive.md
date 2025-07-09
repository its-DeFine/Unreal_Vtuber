# Semantic Graph Architecture Deep Dive

## 1. Stimuli as Root Connections

### Implementation
We've implemented a non-blocking stimuli connection system:

```python
# When a stimuli arrives:
1. Create stimuli node as root
2. Register it with StimuliGraphConnector
3. All subsequent nodes get connected via TRIGGERED_BY relationship
4. Connections are queued and processed asynchronously
```

### Non-Blocking Design
- **Async Queue**: Connections are queued, not created immediately
- **Batch Processing**: Processes up to 10 connections per batch
- **Background Task**: Runs continuously without blocking main flow
- **1-Hour Cleanup**: Automatically cleans up old stimuli tracking

### Graph Structure
```
[Stimuli Node] ──TRIGGERED_BY──> [Tool Execution]
       │                              │
       └──TRIGGERED_BY──> [S2 Analysis]
                                      │
                              [Trading Decision]
```

## 2. Data Storage Architecture

### Current Storage Layers

#### Redis (SCB)
- **Purpose**: Real-time state management
- **Data**: Current system state, active stimuli, agent communications
- **Retention**: Short-term (until consumed)
- **Access**: All agents can write, S1 can ONLY interact here

#### Neo4j (Semantic Graph)
- **Purpose**: Historical knowledge graph
- **Data**: All transformed SCB states (except S1 writes)
- **Retention**: Long-term with daily consolidation
- **Access**: S2 and character agents only

#### PostgreSQL
- **Current Usage**:
  - Cognitive memory storage (memories table)
  - Conversation history (conversation_metadata table)
  - System statistics and metrics
  - User preferences and settings
- **NOT used for**: SCB states or graph data

### Data Flow
```
User Input → SCB (Redis) → Transform → Neo4j Graph
                ↓                         ↓
            S1 Reads                  S2 Queries
                                         ↓
                                    Intelligence
```

## 3. Testing Status

### What Has Been Tested
✅ Access control blocking (S1 restrictions)
✅ Agent tracking in nodes
✅ Node immutability
✅ Consolidation logic
✅ Query tool access control

### What Needs Testing with Live System
⚠️ Stimuli connection performance under load
⚠️ Daily consolidation with real data volumes
⚠️ Query performance on large graphs
⚠️ PostgreSQL integration with new system

### Test Coverage Gaps
- Integration tests with live Neo4j
- Performance benchmarks
- Concurrent stimuli handling
- Graph size limits

## 4. Agent Query Patterns

### Query Scope Options

#### Full Graph Queries
```python
# Search across entire graph
result = await query_semantic_graph(
    query_type="search",
    query="Bitcoin",
    # No context filter = full graph
)
```

#### Context-Filtered Queries
```python
# Search only in specific context
result = await query_semantic_graph(
    query_type="search",
    query="Bitcoin",
    context="trading_finance"  # Limits to one context
)
```

#### Time-Bounded Queries
```python
# Search recent data only
result = await query_semantic_graph(
    query_type="temporal",
    query="trades",
    time_range={"hours": 24}  # Last 24 hours only
)
```

#### Relationship-Specific Queries
```python
# Follow specific relationships
result = await query_semantic_graph(
    query_type="pattern",
    query="stimuli:* -> tool:*"  # Specific pattern
)
```

### Performance Optimization Strategies

1. **Default Limits**: All queries limited to 10-1000 results
2. **Index Usage**: Full-text indexes on content field
3. **Context Filtering**: Reduces search space dramatically
4. **Time Windows**: Recent data queries are faster
5. **Summary Nodes**: Historical queries use consolidated summaries

### Recommended Query Patterns by Agent Type

#### S2 Analyst
- Query last 24 hours of trading_finance context
- Pattern match for successful trade sequences
- Use summaries for historical trend analysis

#### S2 Trader
- Real-time queries on recent market data
- Relationship queries from signals to outcomes
- Context-specific to trading_finance

#### Character Agents
- Query their specific context + general
- Time-bounded to recent interactions
- Pattern match for user preferences

## 5. System Recommendations

### Production Readiness Checklist
1. ✅ Add monitoring for graph size growth
2. ✅ Implement connection pooling for Neo4j
3. ⚠️ Add circuit breakers for query timeouts
4. ⚠️ Create backup/restore procedures
5. ⚠️ Set up performance alerting

### Scaling Considerations
- **Graph Partitioning**: May need sharding at 10M+ nodes
- **Read Replicas**: For heavy query loads
- **Caching Layer**: For frequent queries
- **Archival Strategy**: Move old summaries to cold storage

### Missing Components
1. **Query Cache**: Reduce repeated graph traversals
2. **Graph Analytics**: PageRank, community detection
3. **ML Integration**: Embedding-based similarity search
4. **Audit Logging**: Track all access attempts

## 6. Current Limitations

### Known Issues
1. No automatic PostgreSQL → Neo4j migration
2. Stimuli connections may lag under heavy load
3. No query result caching
4. Limited to single Neo4j instance

### Future Enhancements
1. **Multi-Graph Support**: Separate graphs per team
2. **Real-time Subscriptions**: Live query updates
3. **Advanced Analytics**: Graph algorithms
4. **Federation**: Cross-graph queries

## 7. Monitoring & Operations

### Key Metrics to Track
- Graph size (nodes and relationships)
- Query response times by type
- Stimuli connection queue depth
- Consolidation duration
- S1 access denial rate

### Operational Tasks
- Daily: Check consolidation status
- Weekly: Review graph growth metrics
- Monthly: Analyze query patterns
- Quarterly: Capacity planning

## Summary

The system now provides:
1. ✅ Non-blocking stimuli tracking with root connections
2. ✅ Clear separation of storage responsibilities
3. ✅ Flexible query patterns for different needs
4. ⚠️ Some testing gaps that need addressing
5. ✅ Foundation for scalable knowledge management