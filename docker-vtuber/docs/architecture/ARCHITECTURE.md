# Autonomous VTuber System Architecture

## Overview

The Autonomous VTuber System is a sophisticated dual-layer architecture designed to provide both real-time avatar interactions and intelligent multi-agent processing capabilities. The system operates through two primary subsystems that work in harmony:

- **S1 System**: Character-based conversational AI with real-time avatar visualization
- **S2 System**: AutoGen-powered multi-agent teams for specialized processing

## High-Level Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                     UNIFIED CORE SYSTEM                        │
│                   (Orchestration Layer)                        │
└─────────────────────┬───────────────────────┬───────────────────┘
                      │                       │
┌─────────────────────▼───────────────────────▼───────────────────┐
│                  STIMULI ROUTER                                │
│            (Intelligent Request Routing)                       │
└─────────────────────┬───────────────────────┬───────────────────┘
                      │                       │
           ┌──────────▼──────────┐   ┌────────▼──────────┐
           │    S1 SYSTEM        │   │    S2 SYSTEM      │
           │  (Avatar/Speech)    │   │ (AutoGen Teams)   │
           └─────────────────────┘   └───────────────────┘
                      │                       │
           ┌──────────▼──────────┐   ┌────────▼──────────┐
           │  NeuroSync Bridge   │   │   Redis Queue     │
           │     (SCB)           │   │   Processing      │
           └─────────────────────┘   └───────────────────┘
                      │                       │
           ┌──────────▼──────────┐   ┌────────▼──────────┐
           │   Unreal Engine     │   │    Neo4j Graph    │
           │    Avatar          │   │     Memory        │
           └─────────────────────┘   └───────────────────┘
```

## Core Components

### 1. Unified CORE System
**Location**: `/app/CORE/unified_main.py`

The central orchestration layer that provides:
- Single entry point for all requests
- Unified API endpoints
- Health monitoring and metrics
- Error handling and recovery
- Configuration management

**Key Features**:
- FastAPI-based REST API
- Automatic service discovery
- Circuit breaker patterns
- Comprehensive logging
- Zero-downtime deployment support

### 2. Stimuli Router
**Location**: `/app/CORE/shared/processing/stimuli_processor.py`

Intelligent routing system that determines how to process incoming stimuli:

```python
class ProcessingMode(str, Enum):
    S1_ONLY = "s1_only"      # Direct to avatar/speech
    S2_ONLY = "s2_only"      # Analysis teams only  
    S1_AND_S2 = "s1_and_s2"  # Both systems
    AUTO = "auto"            # Intelligent routing
```

**Routing Logic**:
1. **Character-based routing**: Certain characters (e.g., trader) always go to S2
2. **Content analysis**: Keywords determine appropriate system
3. **Priority-based**: Emergency requests use both systems
4. **Default fallback**: S1_AND_S2 for maximum coverage

### 3. S1 System (Avatar/Speech)
**Location**: `/app/AVATAR/NeuroBridge/NeuroSync_Player/`

Real-time character-based conversational AI system:

**Components**:
- **Character Templates**: JSON-based personality definitions
- **NeuroSync Local API**: Speech synthesis and processing
- **NeuroSync Player**: Avatar animation and visualization
- **SCB Bridge**: Conversation state management
- **Unreal Engine Integration**: Real-time 3D avatar rendering

**Character Types**:
- Teachers (Emma, Professor Smith)
- Traders (Gordon, Marcus)  
- Educators (Sarah, Diana)
- Streamers (Alex, Mike)
- Doctors (Dr. House, Dr. Martinez)
- Specialized roles (Weatherman, Secretary)

### 4. S2 System (AutoGen Teams)
**Location**: `/app/CORE/autogen-agent/`

Multi-agent specialized processing system:

**Team Types**:
1. **Trader Team**: Market analysis, trading strategies, risk assessment
2. **Educator Team**: Curriculum design, lesson planning, educational content
3. **Streamer Team**: Content creation, audience engagement, social media

**Architecture**:
```python
class SimplifiedAutoGenTeam:
    - Coordinator Agent: Task delegation and management
    - Memory Agent: Learning and pattern recognition
    - Specialized Agents: Domain-specific expertise
    - Group Chat Manager: Conversation orchestration
```

**Tools Integration**:
- Market data analysis tools
- Educational content generation
- Risk assessment calculators
- Social media analytics

### 5. Integration Layer

#### SCB (Synchronized Communication Bridge)
**Location**: `/app/CORE/autogen-agent/autogen_agent/clients/scb_client.py`

Redis-based communication bridge that:
- Synchronizes state between S1 and S2
- Provides AgentNet activation control
- Enables cross-system message passing
- Stores conversation context

#### Neo4j Semantic Memory
**Location**: `/app/CORE/autogen-agent/autogen_agent/services/neo4j_semantic_storage.py`

Graph database for persistent memory:
- Semantic relationship mapping
- Context-aware knowledge storage
- Agent action chain tracking
- Pattern recognition and learning

## Data Flow Architecture

### Request Processing Flow

1. **Request Ingestion**
   ```
   User Input → Unified CORE API → Stimuli Router
   ```

2. **Routing Decision**
   ```
   Stimuli Router → [S1 Only | S2 Only | Both Systems]
   ```

3. **S1 Processing Path**
   ```
   S1 Strategy → NeuroSync Player → Avatar Rendering → SCB Update
   ```

4. **S2 Processing Path**
   ```
   S2 Strategy → Team Selection → AutoGen Processing → Neo4j Storage
   ```

5. **Response Aggregation**
   ```
   Processing Results → Response Formation → Client Return
   ```

### Memory and State Management

**SCB State Flow**:
```
S1 Conversations → SCB → S2 Context Awareness
S2 Insights → SCB → S1 Character Enhancement
```

**Neo4j Knowledge Flow**:
```
Team Discussions → Semantic Extraction → Graph Storage
Pattern Recognition → Future Team Enhancement
```

## Technology Stack

### Core Technologies
- **Python 3.9+**: Primary programming language
- **FastAPI**: REST API framework
- **AutoGen**: Multi-agent conversation framework
- **Redis**: Message queuing and state management
- **Neo4j**: Graph database for semantic memory
- **Docker**: Containerization platform

### AI/ML Components
- **Ollama**: Local LLM inference
- **LLaMA 3.1**: Language model for agents
- **Nomic Embed**: Text embeddings for semantic search
- **Whisper**: Speech-to-text processing

### Visualization and Media
- **Unreal Engine**: 3D avatar rendering
- **Kokoro TTS**: Text-to-speech synthesis
- **D3.js**: Graph visualization for debugging

### Infrastructure
- **Docker Compose**: Service orchestration
- **Nginx**: Reverse proxy and load balancing
- **RTMP**: Live streaming protocol support

## Configuration Management

### Environment Variables
```bash
# Core System
SYSTEM_MODE=simplified|full_autogen|hybrid
API_HOST=0.0.0.0
API_PORT=8000

# LLM Configuration
USE_OLLAMA=true
OLLAMA_HOST=http://vtuber-ollama:11434
OLLAMA_MODEL=llama3.1:8b

# Database Connections
NEO4J_URI=bolt://neo4j:7687
NEO4J_USER=neo4j
NEO4J_PASSWORD=password123

# SCB Configuration
REDIS_URL=redis://redis:6379
AGENTNET_ENABLED=true

# S1 System
S1_CHARACTER_SYNC_ENDPOINT=http://neurosync_s1:5001
NEUROSYNC_PLAYER_URL=http://localhost:5001
```

### Character Configuration
Characters are defined in JSON templates with:
- Personality traits and communication style
- Domain expertise and knowledge areas
- Response patterns and behavioral rules
- S2 team mappings and capabilities

## Performance and Scalability

### Performance Characteristics
- **S1 Response Time**: < 2 seconds for speech generation
- **S2 Processing Time**: 5-30 seconds for team analysis
- **Concurrent Users**: Scales horizontally via Docker
- **Memory Usage**: ~2GB base + ~1GB per active team

### Scalability Features
- **Horizontal Scaling**: Docker Compose service replication
- **Queue-based Processing**: Async S2 team processing
- **Redis Clustering**: Distributed state management
- **Neo4j Sharding**: Graph database scaling

### Reliability Features
- **Circuit Breakers**: Automatic failure handling
- **Graceful Degradation**: Fallback processing modes
- **Health Monitoring**: Comprehensive system checks
- **Zero-downtime Deployment**: Rolling update support

## Security Considerations

### Authentication and Authorization
- API key-based authentication
- Role-based access control
- Rate limiting per client
- Input validation and sanitization

### Data Protection
- Redis AUTH for SCB access
- Neo4j authentication required
- Encrypted inter-service communication
- PII scrubbing in logs

### Network Security
- Container isolation via Docker networks
- Firewall rules for external access
- TLS termination at reverse proxy
- CORS policy enforcement

## Monitoring and Observability

### Health Endpoints
- `/health`: System health check
- `/metrics`: Prometheus-compatible metrics
- `/status`: Detailed component status
- `/api/stats`: Processing statistics

### Logging Strategy
- Structured JSON logging
- Component-specific log levels
- Request tracing across services
- Performance metrics collection

### Debugging Tools
- Neo4j browser for graph visualization
- Redis CLI for state inspection
- FastAPI docs for API testing
- Real-time log streaming

## Development and Deployment

### Development Setup
```bash
# Clone repository
git clone <repository-url>
cd docker-vtuber

# Start development environment
docker-compose up -d

# Run tests
python -m pytest tests/

# Access services
curl http://localhost:8000/health
```

### Production Deployment
```bash
# Production configuration
export SYSTEM_MODE=production
export API_PORT=80

# Deploy with scaling
docker-compose -f docker-compose.prod.yml up -d --scale autogen-agent=3

# Monitor deployment
docker-compose logs -f
```

### Continuous Integration
- Automated testing on commit
- Docker image building and versioning
- Performance regression testing
- Security vulnerability scanning

## Future Enhancements

### Planned Features
1. **Multi-language Support**: Character personalities in multiple languages
2. **Advanced Analytics**: Real-time performance dashboards
3. **Plugin Architecture**: Third-party tool integration
4. **Voice Cloning**: Personalized character voices
5. **Blockchain Integration**: NFT character ownership

### Technical Roadmap
1. **Kubernetes Migration**: Enhanced orchestration and scaling
2. **GraphQL API**: More efficient data querying
3. **Streaming Responses**: Real-time conversation updates
4. **Edge Computing**: Distributed processing nodes
5. **AI Model Updates**: Latest LLM and embedding models

## Troubleshooting Guide

### Common Issues

**Issue**: S2 teams not responding
**Solution**: Check AutoGen container logs, verify LLM connectivity

**Issue**: Avatar not rendering
**Solution**: Verify Unreal Engine connection, check NeuroSync Player status

**Issue**: Memory storage failing
**Solution**: Check Neo4j connectivity, verify credentials

**Issue**: High latency responses
**Solution**: Monitor queue depths, check system resources

### Performance Optimization
1. Tune LLM inference parameters
2. Optimize Redis memory usage
3. Index Neo4j queries properly
4. Scale processing containers

### Debugging Steps
1. Check service health endpoints
2. Review container logs for errors
3. Verify network connectivity
4. Test individual components

---

This architecture provides a robust, scalable foundation for autonomous VTuber operations while maintaining clear separation of concerns and enabling independent component scaling and maintenance.