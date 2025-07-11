# S2 AutoGen Specialized Teams System - Product Requirements Document (PRD)

## Executive Summary

This document describes the architecture and implementation of the S2 AutoGen Specialized Teams System, a sophisticated multi-agent AI system that enables character-driven autonomous teams with specialized capabilities. The system implements a character-paired architecture where each character (trader, streamer, teacher, default) has its own specialized AutoGen team that operates autonomously, processes stimuli, and collaborates through a shared context blackboard (SCB).

## System Overview

### Core Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                         S2 AUTOGEN SYSTEM                         │
├─────────────────────────────────────────────────────────────────┤
│                                                                   │
│  ┌─────────────────┐        ┌──────────────────┐                │
│  │ Stimuli Input   │───────►│ Consolidation    │                │
│  │ (from GraphFlow)│        │ System           │                │
│  └─────────────────┘        └────────┬─────────┘                │
│                                      │                           │
│                                      ▼                           │
│                          ┌───────────────────────┐               │
│                          │ Queue Consumer Service│               │
│                          └───────────┬───────────┘               │
│                                      │                           │
│                    ┌─────────────────┴──────────────────┐        │
│                    ▼                                    ▼        │
│         ┌──────────────────┐                ┌──────────────────┐│
│         │ Character Team   │                │ Autonomous Team  ││
│         │ Registry         │                │ Manager          ││
│         └──────────────────┘                └──────────────────┘│
│                    │                                    │        │
│      ┌─────────────┴────────────┬──────────────────────┴───┐    │
│      ▼                          ▼                          ▼    │
│ ┌─────────┐              ┌─────────┐                ┌─────────┐ │
│ │ Trader  │              │Streamer │                │ Teacher │ │
│ │ Team    │              │ Team    │                │  Team   │ │
│ └─────────┘              └─────────┘                └─────────┘ │
│      │                          │                          │     │
│      └──────────────────────────┴──────────────────────────┘    │
│                                 │                                │
│                                 ▼                                │
│                      ┌──────────────────┐                       │
│                      │  SCB & Neo4j     │                       │
│                      │  Integration     │                       │
│                      └──────────────────┘                       │
└─────────────────────────────────────────────────────────────────┘
```

### Key Components

1. **Queue Consumer Service** (`queue_consumer_service.py`)
   - Polls `/tmp/s2_processing_queue.json` for consolidated stimuli batches
   - Routes stimuli to appropriate character teams
   - Manages batch processing with configurable intervals

2. **Character Team Registry** (`character_team_registry.py`)
   - Maps characters to specialized teams
   - Defines team configurations and tool assignments
   - Manages SCB channels for team communications

3. **Autonomous Team Manager** (`autonomous_team_manager.py`)
   - Runs character-specific teams in background
   - Handles character switching and team activation
   - Manages autonomous execution cycles

4. **Specialized Tools** (per team in `/tools/` subdirectories)
   - Trader: Market data, portfolio optimization, risk assessment
   - Streamer: Content strategy, analytics, community management
   - Teacher: Curriculum design, assessment, knowledge management
   - Common: Goal management, evolution, SCB operations

5. **SCB Communication Utilities** (`scb_utils.py`)
   - Enables cross-team communication
   - Publishes insights and events
   - Manages collaboration requests

6. **Neo4j Integration** (`team_insight_consolidator.py`)
   - Stores team insights in semantic graph
   - Consolidates daily team activities
   - Analyzes collaboration patterns

## Character-Team Mappings

### 1. Trader Team
- **Character**: trader_character
- **Focus**: Financial markets and portfolio management
- **Specialized Tools**:
  - `market_data_tool`: Real-time market analysis
  - `portfolio_optimization_tool`: Asset allocation optimization
  - `risk_assessment_tool`: Risk analysis and management
  - `trading_strategy_tool`: Strategy development and backtesting

### 2. Streamer Team
- **Character**: streamer_character
- **Focus**: Content creation and audience engagement
- **Specialized Tools**:
  - `content_strategy_tool`: Content planning and optimization
  - `analytics_tool`: Performance metrics and insights
  - `community_tool`: Audience interaction management
  - `monetization_tool`: Revenue optimization

### 3. Teacher Team
- **Character**: teacher_character
- **Focus**: Educational content and learning optimization
- **Specialized Tools**:
  - `curriculum_design_tool`: Course and module creation
  - `assessment_tool`: Student evaluation and progress tracking
  - `knowledge_management_tool`: Knowledge graph maintenance
  - `learning_analytics_tool`: Learning pattern analysis

### 4. Default Team
- **Character**: default_character
- **Focus**: System self-improvement and evolution
- **Common Tools Only**: Uses standard tools for autonomous enhancement

## System Workflows

### 1. Stimuli Processing Flow

```
1. GraphFlow → Stimuli → Consolidation System
2. Consolidation System → Queue File (/tmp/s2_processing_queue.json)
3. Queue Consumer Service → Polls Queue
4. Queue Consumer → Identifies Active Character
5. Character Team Registry → Returns Team Configuration
6. Specialized Team → Processes Stimuli
7. Team → Generates Response & Insights
8. Response → SCB & Neo4j Storage
```

### 2. Autonomous Execution Flow

```
1. Autonomous Team Manager → Monitors Character State
2. Character Change → Activate Corresponding Team
3. Team → Runs Autonomous Cycles (60s intervals)
4. Team → Generates Autonomous Prompts
5. Team → Executes Tools & Generates Insights
6. Insights → Published to SCB Channels
7. Insights → Stored in Neo4j Graph
```

### 3. Cross-Team Collaboration Flow

```
1. Team A → Detects Collaboration Trigger
2. Team A → Publishes to COLLABORATION_REQUESTS channel
3. SCB Coordinator → Routes to Target Teams
4. Team B → Receives Collaboration Request
5. Teams → Share Insights via SCB Channels
6. Collaboration → Recorded in Neo4j
```

## Data Storage Architecture

### 1. File-Based Queue
- **Location**: `/tmp/s2_processing_queue.json`
- **Format**: JSON array of stimuli batches
- **Purpose**: Decouples stimuli reception from processing

### 2. SCB (Redis)
- **Channels**: Team-specific and cross-team channels
- **Purpose**: Real-time state sharing and communication
- **Retention**: Configurable TTL (default 1 hour)

### 3. Neo4j Semantic Graph
- **Node Types**: 
  - `team_insight`: Individual team insights
  - `team_daily_summary`: Consolidated daily summaries
  - `collaboration_request`: Cross-team collaborations
  - `team_pattern_analysis`: Performance patterns
- **Relationships**:
  - `TEAM_SUMMARIZED_BY`: Links insights to summaries
  - `COLLABORATED_WITH`: Links team interactions
- **Consolidation**: Daily at 2 AM

## API Endpoints

### Stimuli Processing
- `POST /api/stimuli/submit` - Submit stimuli for processing
- `GET /api/stimuli/status/{stimuli_id}` - Check processing status
- `GET /api/stimuli/health` - System health check

### Team Management
- `GET /api/teams/status` - Get all team statuses
- `POST /api/teams/{team_id}/pause` - Pause team execution
- `POST /api/teams/{team_id}/resume` - Resume team execution

### Insights & Analytics
- `GET /api/insights/latest` - Get recent team insights
- `GET /api/analytics/team-performance` - Team performance metrics
- `GET /api/collaborations` - Cross-team collaboration summary

## Configuration

### Environment Variables
```bash
# Core Settings
USE_AUTOGEN_LLM=true
LOOP_INTERVAL=20

# Character Settings
S1_CHARACTER_SYNC_ENDPOINT=http://neurosync_s1:5001
DEFAULT_CHARACTER_ID=default_character

# Queue Settings
QUEUE_POLL_INTERVAL=5
BATCH_SIZE=10
PROCESSING_TIMEOUT=300

# Team Settings
AUTONOMOUS_EXECUTION_INTERVAL=60
MAX_ITERATIONS_PER_SESSION=100

# Storage Settings
NEO4J_URI=bolt://neo4j:7687
NEO4J_USER=neo4j
NEO4J_PASSWORD=password
CONSOLIDATION_HOUR=2
```

### Character Configuration Files
Each character requires:
1. `metadata.json` - Character definition with `specialized_team` field
2. Team mapping in `character_team_registry.py`
3. Tool permissions in team configuration

## Monitoring & Observability

### Key Metrics
1. **Queue Metrics**
   - Queue size and processing rate
   - Batch processing times
   - Failed processing attempts

2. **Team Metrics**
   - Iterations per team
   - Tool execution success rates
   - Insight generation frequency

3. **Collaboration Metrics**
   - Cross-team interaction frequency
   - Collaboration request fulfillment
   - Communication channel activity

### Health Checks
- Queue consumer status
- Active team status
- Character synchronization
- Neo4j connectivity
- SCB availability

## Security Considerations

1. **Access Control**
   - Tool execution restricted by team
   - Character-based isolation
   - SCB channel permissions

2. **Data Protection**
   - Sensitive data filtering in insights
   - Secure storage in Neo4j
   - TTL-based data expiration

3. **Resource Limits**
   - Max iterations per session
   - Processing timeouts
   - Queue size limits

## Future Enhancements

1. **Advanced Team Dynamics**
   - Multi-team consensus mechanisms
   - Hierarchical team structures
   - Dynamic team composition

2. **Enhanced Analytics**
   - ML-based pattern recognition
   - Predictive team performance
   - Anomaly detection

3. **Extended Integrations**
   - External API connections
   - Webhook notifications
   - Custom tool plugins

## Conclusion

The S2 AutoGen Specialized Teams System represents a significant advancement in autonomous AI systems, enabling character-driven specialization with sophisticated multi-agent collaboration. The architecture supports scalable, maintainable, and observable autonomous operations while maintaining clear separation of concerns and robust error handling.

This system demonstrates how modern AI architectures can combine specialized domain knowledge with autonomous operation, creating a foundation for increasingly sophisticated AI applications.