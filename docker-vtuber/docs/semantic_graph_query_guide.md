# Semantic Graph Query Tool Guide

## Overview

The Semantic Graph Query Tool enables agents to intelligently query the Neo4j knowledge graph for historical patterns, relationships, and insights. This tool transforms the flat SCB (Shared Context Blackboard) state into a rich, queryable semantic graph.

## Architecture

### System Components

1. **SCB (Shared Context Blackboard)**: Flat state storage in Redis
2. **Neo4j Semantic Storage**: Graph database for structured knowledge
3. **SCB-Neo4j Bridge**: Transforms flat states into semantic nodes
4. **Query Tool**: Enables agents to search and analyze the graph

### Data Flow

```
SCB State → Bridge → Neo4j Nodes → Relationships → Query Results → Agent Decisions
```

## Semantic Contexts

The system organizes information into 8 semantic contexts:

1. **general_context**: General system information
2. **s2_to_s1_messages**: S2 agent communications to S1
3. **s1_to_s2_feedback**: S1 feedback to S2 agents
4. **tool_executions**: Tool execution history
5. **stimuli_context**: User inputs and routing
6. **agent_state**: Agent collaboration and consensus
7. **trading_finance**: Trading and portfolio data
8. **system_events**: Errors and system health

## Query Types

### 1. Full-Text Search
Search for content containing specific text within a context.

```python
result = await query_semantic_graph(
    query_type="search",
    query="Bitcoin",
    context="trading_finance",  # optional
    limit=10
)
```

### 2. Pattern Matching
Find relationships matching specific patterns.

```python
result = await query_semantic_graph(
    query_type="pattern",
    query="tool:* -> communication",
    limit=5
)
```

Pattern Syntax:
- `tool:*` → Any tool execution
- `s2:*` → Any S2 agent node
- `s1:*` → Any S1 agent node
- `error` → Error nodes
- `*` → Any node
- `->` → Relationship direction

### 3. Temporal Queries
Find nodes within a specific time range.

```python
result = await query_semantic_graph(
    query_type="temporal",
    query="trade",
    time_range={"hours": 24, "days": 0},
    context="trading_finance",
    limit=10
)
```

### 4. Context Analysis
Analyze patterns within a specific semantic context.

```python
result = await query_semantic_graph(
    query_type="context",
    context="s2_to_s1_messages",
    limit=10
)
```

### 5. Relationship Exploration
Explore all relationships for a specific node.

```python
result = await query_semantic_graph(
    query_type="relationships",
    query="node_id_here",
    limit=10
)
```

## API Endpoints

### Query Endpoint
```
POST /api/semantic-map/query
```

Request body:
```json
{
    "query_type": "search",
    "query": "Bitcoin",
    "context": "trading_finance",
    "limit": 5
}
```

### Examples Endpoint
```
GET /api/semantic-map/query/examples
```

Returns example queries and pattern syntax documentation.

## Agent Integration

### AutoGen Configuration

```python
from autogen_agent.tools import query_semantic_graph

# Register tool with agent
tools = [
    {
        "name": "query_semantic_graph",
        "description": "Query the semantic knowledge graph",
        "function": query_semantic_graph
    }
]

# Agent usage
result = await agent.call_tool(
    "query_semantic_graph",
    query_type="search",
    query="recent trading signals"
)
```

### Use Cases by Agent Type

#### S2 Analyst Agent
- Query: "What market patterns led to successful trades?"
- Use: Pattern match "analysis -> trade" with success metadata

#### S2 Trader Agent  
- Query: "Show portfolio changes in last 24 hours"
- Use: Temporal query in trading_finance context

#### S1 Avatar Agent
- Query: "What messages should I communicate to the user?"
- Use: Search s2_to_s1_messages context

#### S2 Programmer Agent
- Query: "Which tools are failing frequently?"
- Use: Pattern match "tool:* -> error"

## Relationship Types

The system automatically creates these relationship types:

- **FOLLOWED_BY**: Sequential temporal relationships
- **PRODUCED**: Tool executions producing results
- **TRIGGERS**: Events triggering other events
- **CAUSES**: Causal relationships
- **EXECUTES**: Command executions
- **UPDATES**: State updates
- **ROUTES_TO**: Stimuli routing
- **ACTIVATES**: Agent activation
- **REACHES**: Consensus/decision reaching
- **MONITORED_BY**: System monitoring

## Query Chaining Strategy

1. **Discovery Phase**: Search for relevant concepts
2. **Exploration Phase**: Query relationships for discovered nodes
3. **Analysis Phase**: Identify patterns in the results
4. **Decision Phase**: Make informed decisions based on historical data

Example workflow:
```python
# 1. Find recent errors
errors = await query_semantic_graph(
    query_type="search",
    query="error",
    time_range={"hours": 1}
)

# 2. Explore what caused them
for error in errors["results"]:
    relationships = await query_semantic_graph(
        query_type="relationships",
        query=error["id"]
    )
    
# 3. Find patterns
patterns = await query_semantic_graph(
    query_type="pattern",
    query="* -> error"
)

# 4. Make decision to avoid similar errors
```

## Performance Considerations

1. **Deduplication**: Content hashes prevent duplicate nodes
2. **Indexing**: Full-text search indexes on content field
3. **Time Windows**: 5-second window for automatic relationships
4. **Embeddings**: Semantic similarity search capability
5. **Context Filtering**: Query specific contexts for faster results

## Advanced Patterns

### Multi-Context Queries
Search across multiple contexts by omitting the context parameter.

### Relationship Strength
Relationships include confidence scores and timestamps.

### Semantic Similarity
Nodes include embeddings for similarity-based queries.

### Graph Metrics
Access graph statistics through the metrics endpoint.

## Troubleshooting

### Empty Results
- Check if data exists in the specified context
- Verify time range includes relevant data
- Ensure query syntax is correct

### Performance Issues
- Limit results appropriately
- Use context filtering when possible
- Consider temporal constraints

### Pattern Matching
- Verify pattern syntax
- Check relationship types exist
- Use wildcards appropriately

## Future Enhancements

1. **Similarity Search**: Query by semantic similarity
2. **Graph Algorithms**: PageRank, community detection
3. **Predictive Queries**: ML-based pattern prediction
4. **Real-time Subscriptions**: Live query updates
5. **Query Optimization**: Automatic query planning