# S2 Specialized Teams - Technical Implementation Guide

## Quick Start

### 1. Verify Environment
```bash
# Check required environment variables
echo "USE_AUTOGEN_LLM=$USE_AUTOGEN_LLM"
echo "NEO4J_URI=$NEO4J_URI"
echo "AGENTNET_ENABLED=$AGENTNET_ENABLED"

# Ensure services are running
docker-compose ps
```

### 2. Initialize Characters
```bash
# Run character cleanup scripts
chmod +x /tmp/cleanup_s1_characters.sh
chmod +x /tmp/cleanup_s2_characters.sh

# Execute cleanup (requires appropriate permissions)
./tmp/cleanup_s1_characters.sh
./tmp/cleanup_s2_characters.sh
```

### 3. Start S2 System
```bash
# Start S2 with specialized teams enabled
cd /home/geo/directories/autonomy/docker-vtuber
docker-compose up -d autogen_s2
```

## Architecture Details

### Component Interactions

```
┌─────────────────┐     ┌──────────────────┐     ┌─────────────────┐
│                 │     │                  │     │                 │
│  GraphFlow      │────►│  Consolidation   │────►│  Queue File     │
│  Stimuli        │     │  System          │     │  (.json)        │
│                 │     │                  │     │                 │
└─────────────────┘     └──────────────────┘     └────────┬────────┘
                                                           │
                                                           ▼
┌─────────────────┐     ┌──────────────────┐     ┌─────────────────┐
│                 │     │                  │     │                 │
│  Queue Consumer │◄────│  Character Team  │────►│  Specialized    │
│  Service        │     │  Registry        │     │  AutoGen Team   │
│                 │     │                  │     │                 │
└─────────────────┘     └──────────────────┘     └────────┬────────┘
                                                           │
                                                           ▼
┌─────────────────┐     ┌──────────────────┐     ┌─────────────────┐
│                 │     │                  │     │                 │
│  SCB Publisher  │────►│  Neo4j Storage   │◄────│  Team Insight   │
│                 │     │                  │     │  Consolidator   │
│                 │     │                  │     │                 │
└─────────────────┘     └──────────────────┘     └─────────────────┘
```

### File Structure

```
docker-vtuber/app/CORE/autogen-agent/autogen_agent/
├── core/
│   ├── queue_consumer_service.py      # Polls and processes queue
│   ├── character_team_registry.py     # Team configurations
│   ├── autonomous_team_manager.py     # Background execution
│   └── stimuli_autogen_team.py       # Team implementation
├── tools/
│   ├── common/                        # Shared tools
│   ├── trader/                        # Trader-specific tools
│   ├── streamer/                      # Streamer-specific tools
│   ├── teacher/                       # Teacher-specific tools
│   └── system/                        # System tools
├── utils/
│   └── scb_utils.py                   # SCB communication
└── services/
    ├── team_insight_consolidator.py   # Team-specific consolidation
    └── graph_consolidation_service.py # General consolidation
```

## Implementation Patterns

### 1. Creating a New Specialized Team

```python
# In character_team_registry.py

# Define new character type
class CharacterType(Enum):
    TRADER = "trader"
    STREAMER = "streamer"
    TEACHER = "teacher"
    RESEARCHER = "researcher"  # New type
    DEFAULT = "default"

# Add team configuration
TEAM_CONFIGS = {
    CharacterType.RESEARCHER: TeamConfig(
        character_type=CharacterType.RESEARCHER,
        team_name="Research Innovation Team",
        agents=[
            AgentConfig(
                name="research_lead",
                role="Research Director",
                system_message="You lead research initiatives...",
                tools=["literature_review_tool", "hypothesis_tool"]
            ),
            # Add more agents...
        ],
        shared_tools=["goal_management_tools", "scb_operations_tool"],
        scb_channels=["researcher_insights", "research_discoveries"],
        max_rounds=15
    ),
    # ... other teams
}
```

### 2. Creating Specialized Tools

```python
# In tools/researcher/literature_review_tool.py

import logging
from typing import Dict, Any

logger = logging.getLogger(__name__)

async def run(context: Dict[str, Any]) -> Dict[str, Any]:
    """
    Literature Review Tool for Research Team
    
    Args:
        context: Contains query, scope, filters
    
    Returns:
        Review results and citations
    """
    try:
        query = context.get("query", "")
        scope = context.get("scope", "recent")
        
        # Tool implementation
        results = await perform_literature_search(query, scope)
        
        return {
            "success": True,
            "tool": "literature_review_tool",
            "query": query,
            "results": results,
            "citations": extract_citations(results)
        }
        
    except Exception as e:
        logger.error(f"Literature review failed: {e}")
        return {"success": False, "error": str(e)}
```

### 3. Implementing Team-Specific Logic

```python
# In autonomous_team_manager.py - Custom prompt generation

def _generate_autonomous_prompt(self, context: TeamExecutionContext) -> str:
    """Generate appropriate autonomous prompt based on character type"""
    
    if context.character_type == CharacterType.RESEARCHER:
        prompts = [
            "Review latest research papers in the field",
            "Analyze research trends and identify gaps",
            "Formulate new research hypotheses",
            "Plan experimental methodology"
        ]
        # Select based on iteration
        return prompts[context.iteration_count % len(prompts)]
```

### 4. SCB Communication Patterns

```python
# Publishing team insights
await publish_team_insight(
    scb_client=self.scb_client,
    team_name="researcher",
    insight="Discovered correlation between X and Y",
    data={
        "confidence": 0.85,
        "evidence": ["paper1", "paper2"],
        "implications": "This suggests..."
    },
    priority=MessagePriority.HIGH
)

# Requesting collaboration
request_id = await request_team_collaboration(
    scb_client=self.scb_client,
    from_team="researcher",
    to_team="teacher",
    collaboration_type="knowledge_transfer",
    context={
        "discovery": "New learning method",
        "application": "Student engagement"
    }
)
```

### 5. Neo4j Semantic Storage

```python
# Storing team insights in Neo4j
await self.semantic_storage.add_semantic_node(
    content="Research breakthrough in quantum computing",
    context=SemanticContext.RESEARCH,
    node_type="research_discovery",
    metadata={
        "team": "researcher",
        "confidence": 0.9,
        "impact": "high",
        "citations": ["arxiv:2024.1234"]
    },
    initiating_agent="research_team",
    agent_category="specialized_team",
    agent_team="researcher"
)

# Creating relationships
await session.run("""
    MATCH (d:SemanticNode {node_type: 'research_discovery'})
    MATCH (t:SemanticNode {node_type: 'teaching_material'})
    WHERE d.content CONTAINS t.topic
    CREATE (d)-[:INFORMS {timestamp: $timestamp}]->(t)
""", timestamp=datetime.now().timestamp())
```

## Monitoring and Debugging

### 1. Check Queue Status
```python
# Read queue file
import json

with open('/tmp/s2_processing_queue.json', 'r') as f:
    queue = json.load(f)
    print(f"Queue has {len(queue)} batches")
    for batch in queue[:5]:  # First 5
        print(f"- Batch {batch['batch_id']}: {batch['stimuli_count']} stimuli")
```

### 2. Monitor Team Activity
```bash
# Check logs for team activity
docker logs autogen_s2 2>&1 | grep "TEAM_MANAGER"

# Check specific team
docker logs autogen_s2 2>&1 | grep "trader_team"
```

### 3. Query Neo4j for Insights
```cypher
// Get recent team insights
MATCH (n:SemanticNode {node_type: 'team_insight'})
WHERE n.timestamp > timestamp() - 86400
RETURN n.team_type, count(n) as insights_count, 
       avg(toFloat(n.metadata.confidence)) as avg_confidence
ORDER BY insights_count DESC

// Find collaborations
MATCH (n1:SemanticNode)-[r:COLLABORATED_WITH]->(n2:SemanticNode)
RETURN n1.agent_team as from_team, n2.agent_team as to_team, count(r) as collaborations
ORDER BY collaborations DESC
```

### 4. SCB Channel Monitoring
```python
# Check SCB channels
from autogen_agent.utils.scb_utils import SCBReader

reader = SCBReader(scb_client)
insights = await reader.get_latest_insights("trader_insights", limit=10)
for insight in insights:
    print(f"{insight['timestamp']}: {insight['content'][:50]}...")
```

## Performance Optimization

### 1. Queue Processing
- Adjust `QUEUE_POLL_INTERVAL` for responsiveness
- Increase `BATCH_SIZE` for throughput
- Use `PROCESSING_TIMEOUT` to prevent stuck batches

### 2. Team Execution
- Configure `AUTONOMOUS_EXECUTION_INTERVAL` based on needs
- Set `MAX_ITERATIONS_PER_SESSION` to prevent runaway execution
- Use team-specific `max_rounds` for conversation depth

### 3. Storage Optimization
- Enable daily consolidation to manage graph size
- Use appropriate TTLs for SCB data
- Archive old nodes with `Archived` label

## Troubleshooting

### Common Issues

1. **Queue not processing**
   - Check if queue consumer service is running
   - Verify queue file permissions
   - Check for JSON parsing errors

2. **Teams not activating**
   - Verify character state synchronization
   - Check team registry configuration
   - Ensure AutoGen agents initialized

3. **No insights generated**
   - Check team autonomous prompts
   - Verify tool availability
   - Check SCB connectivity

4. **Neo4j connection issues**
   - Verify Neo4j service is running
   - Check credentials and URI
   - Test connection with bolt driver

### Debug Commands

```bash
# Test queue consumer
docker exec -it autogen_s2 python -c "
from autogen_agent.core.queue_consumer_service import get_queue_consumer_service
service = get_queue_consumer_service()
print(service.get_status())
"

# Test team manager
docker exec -it autogen_s2 python -c "
from autogen_agent.core.autonomous_team_manager import get_autonomous_team_manager
manager = get_autonomous_team_manager()
print(manager.get_status() if manager else 'Not initialized')
"

# Test Neo4j connection
docker exec -it autogen_s2 python -c "
from autogen_agent.services.neo4j_semantic_storage import get_neo4j_storage
storage = get_neo4j_storage()
print('Connected' if storage.driver else 'Not connected')
"
```

## Best Practices

1. **Team Design**
   - Keep teams focused on specific domains
   - Limit team size to 3-5 agents
   - Define clear agent roles and responsibilities

2. **Tool Development**
   - Make tools atomic and reusable
   - Include proper error handling
   - Return structured responses

3. **Communication**
   - Use appropriate SCB channels
   - Set message priorities correctly
   - Include metadata for traceability

4. **Storage**
   - Use semantic contexts appropriately
   - Include rich metadata in nodes
   - Create meaningful relationships

5. **Monitoring**
   - Log key events at appropriate levels
   - Track performance metrics
   - Set up alerts for failures

## Conclusion

The S2 Specialized Teams system provides a powerful framework for character-driven autonomous AI operations. By following these implementation patterns and best practices, you can extend the system with new teams, tools, and capabilities while maintaining system stability and performance.