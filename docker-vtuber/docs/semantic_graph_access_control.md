# Semantic Graph Access Control & Consolidation

## Overview

The semantic graph system now implements strict access controls and daily consolidation to ensure data integrity, proper agent boundaries, and long-term performance.

## Access Control Rules

### 1. S1 Agent Restrictions
- **Cannot write to graph** - Only allowed to write to SCB
- **Cannot query graph** - Must use SCB for all state management
- **Rationale**: S1 is the presentation layer and should not have direct knowledge graph access

### 2. S2 Agent Permissions
- **Full write access** to semantic graph
- **Full query access** for analysis and decision-making
- **Agent types**: s2_analyst, s2_trader, s2_programmer

### 3. Character Agent Permissions
- **Full write access** with character context tracking
- **Full query access** for character-specific knowledge
- **Agent types**: weatherman, chef, fitness_coach, medical_advisor, librarian

### 4. System Agent Permissions
- **Full access** for maintenance and consolidation
- **Special permissions** for admin operations

## Agent Tracking

Every node now includes:

```python
{
    "initiating_agent": "s2_analyst",      # Who created this
    "agent_category": "s2_team",           # Category of agent
    "agent_team": "main_autonomous",       # Specific team
    "action_chain": ["user", "s2_analyst"] # Chain of actions
}
```

### Agent Categories
- `s1_agent` - Avatar/presentation agents (blocked)
- `s2_team` - Analysis and decision agents
- `character_agent` - Persona-specific agents
- `system` - Maintenance and admin agents

## Node Immutability

### Design Principles
1. **No Updates** - Nodes cannot be modified after creation
2. **No Deletes** - Nodes cannot be removed (only archived)
3. **Append-Only** - New information creates new nodes
4. **Deduplication** - Content hashes prevent exact duplicates

### Benefits
- Complete audit trail
- No data loss
- Temporal integrity
- Simplified conflict resolution

## Daily Consolidation

### Schedule
- **Default**: 2:00 AM daily
- **Configurable**: Can be set to any hour
- **Manual Trigger**: Available via API for admin agents

### Consolidation Process

1. **Context Grouping**
   - Groups nodes by semantic context
   - Processes each context separately
   
2. **Summary Creation**
   - Creates daily summary nodes per context
   - Includes statistics and agent activity
   - Links original nodes to summaries

3. **Master Summary**
   - Overall system summary across all contexts
   - Total node counts and distributions
   - Agent activity metrics

4. **Node Archival**
   - Adds `Archived` label to processed nodes
   - Maintains all relationships
   - Allows historical queries

### Summary Node Example

```
Daily Summary for trading_finance - 2025-01-09
Total Events: 45
Trades Executed: 12

Agent Activity:
  - s2_trader: 25 actions
  - s2_analyst: 15 actions
  - character_weatherman: 5 actions
```

## API Endpoints

### Query with Access Control
```
POST /api/semantic-map/query
{
    "query_type": "search",
    "query": "Bitcoin",
    "requesting_agent": "s2_analyst"  // Required for access control
}
```

### Consolidation Status
```
GET /api/semantic-map/consolidation/status

Response:
{
    "is_running": true,
    "last_consolidation": "2025-01-09T02:00:00",
    "next_consolidation": "2025-01-10T02:00:00",
    "summaries": {
        "daily_summary": 30,
        "master_daily_summary": 30
    },
    "archived_nodes": 15000
}
```

### Manual Consolidation (Admin Only)
```
POST /api/semantic-map/consolidation/trigger
{
    "requesting_agent": "admin",
    "date": "2025-01-08"  // Optional, defaults to yesterday
}
```

## Implementation Details

### Access Check in Bridge
```python
# In scb_neo4j_bridge.py
if agent_info["agent_category"] == "s1_agent":
    logger.info("🚫 S1 agent detected - skipping graph write")
    return []
```

### Access Check in Query Tool
```python
# In semantic_graph_query_tool.py
if "s1" in requesting_agent or requesting_agent == "avatar":
    return {
        "success": False,
        "error": "S1 agents do not have access to the semantic graph"
    }
```

### Consolidation Relationships
- `SUMMARIZED_BY` - Links nodes to their daily summary
- Preserves full graph structure while improving query performance

## Best Practices

1. **Agent Identification**
   - Always pass `requesting_agent` in API calls
   - Use consistent agent naming conventions
   
2. **Query Optimization**
   - Query recent data directly
   - Use summaries for historical analysis
   - Filter by context when possible

3. **Monitoring**
   - Check consolidation status regularly
   - Monitor graph size growth
   - Track agent activity patterns

## Migration Notes

### For Existing Systems
1. S1 agents must be updated to only use SCB
2. Add `requesting_agent` to all query calls
3. Schedule consolidation service startup
4. Monitor first consolidation run

### Performance Considerations
- Consolidation reduces active node count
- Summaries improve historical queries
- Archival maintains full audit trail
- Daily schedule prevents performance degradation