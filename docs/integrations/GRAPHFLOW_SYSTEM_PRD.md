# Product Requirements Document (PRD)
# GraphFlow-Based External Stimuli Handling System

**Document Version:** 1.0  
**Date:** January 2025  
**Author:** System Architect  
**Status:** Draft  

---

## 1. Executive Summary

### 1.1 Project Overview
This PRD outlines the redesign of System2 (AutoGen multi-agent system) to leverage Microsoft AutoGen's GraphFlow functionality for sophisticated external stimuli handling. The new system will implement a gateway agent architecture that intelligently routes external stimuli to appropriate processing paths while maintaining compatibility with existing System1 (immediate speech/avatar functionality).

### 1.2 Strategic Objectives
- **Enhanced Decision Making**: Implement GraphFlow-based routing for more intelligent stimuli processing
- **System Separation**: Maintain clear boundaries between System1 (lightweight/immediate) and System2 (heavy/analytical)
- **Scalable Architecture**: Support future expansion of agent capabilities and stimuli types
- **Production Readiness**: Create enterprise-grade external stimuli handling with monitoring and observability

### 1.3 Success Metrics
- **Response Time**: < 2 seconds for stimuli categorization and routing decisions
- **Accuracy**: > 95% correct classification of stimuli types
- **System Reliability**: 99.9% uptime for GraphFlow gateway agent
- **Integration Success**: Zero breaking changes to existing autogen-agent system

---

## 2. Problem Statement

### 2.1 Current System Limitations
The existing AutoGen system uses a GroupChat-based approach with limited external stimuli handling:

**Current External Stimuli Categories:**
- **Direct Admin Requests**: High priority administrative commands
- **External User Stimuli**: Chat messages, viewer comments, social media mentions
- **External System Information**: Environment changes, new viewers, system notifications
- **Autonomous Events**: Self-generated content based on idle thresholds

**Key Limitations:**
1. **Simple Routing**: Basic event handlers without sophisticated decision logic
2. **Limited Context Awareness**: Insufficient consideration of system state and context
3. **Rigid Processing**: Fixed response patterns without adaptive decision-making
4. **Scalability Constraints**: Difficulty adding new stimuli types or processing logic
5. **Monitoring Gaps**: Limited observability into decision-making processes

### 2.2 Business Impact
- **Suboptimal User Experience**: Inconsistent responses to external stimuli
- **Development Friction**: Difficulty extending stimuli handling capabilities
- **Operational Overhead**: Manual intervention required for edge cases
- **Integration Challenges**: Complex coordination between System1 and System2

---

## 3. Solution Overview

### 3.1 GraphFlow Architecture Design

```
┌─────────────────────────────────────────────────────────────────┐
│                   GraphFlow Gateway Agent                      │
├─────────────────────────────────────────────────────────────────┤
│  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐ │
│  │   Categorizer   │  │   Analyzer      │  │   Router        │ │
│  │     Node        │  │     Node        │  │     Node        │ │
│  └─────────────────┘  └─────────────────┘  └─────────────────┘ │
├─────────────────────────────────────────────────────────────────┤
│                    Decision Execution Layer                    │
├─────────────────────────────────────────────────────────────────┤
│ Option A:         │ Option B:         │ Option C:              │
│ Avatar + Analysis │ Analysis Only     │ No Action              │
│ ┌─────────────┐   │ ┌─────────────┐   │ ┌─────────────┐        │
│ │ Avatar Tools│   │ │ Agent Pool  │   │ │ Log & Store │        │
│ │ + Agent Pool│   │ │ Processing  │   │ │ Only        │        │
│ └─────────────┘   │ └─────────────┘   │ └─────────────┘        │
└─────────────────────────────────────────────────────────────────┘
                               │
                               ▼
┌─────────────────────────────────────────────────────────────────┐
│               Existing System Integration                       │
├─────────────────────────────────────────────────────────────────┤
│ System1: Immediate │     System2: Heavy Analysis               │
│ ┌─────────────────┐ │ ┌─────────────────────────────────────┐   │
│ │ Speech/TTS      │ │ │ Multi-Agent Processing              │   │
│ │ Avatar Control  │ │ │ - cognitive_ai_agent                │   │
│ │ Blend Shapes    │ │ │ - programmer_agent                  │   │
│ │ Lightweight LLM │ │ │ - observer_agent                    │   │
│ └─────────────────┘ │ │ - Evolution Engine                  │   │
│                     │ │ - Cognee Integration                │   │
│                     │ └─────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────┘
```

### 3.2 Core Components

#### 3.2.1 Gateway Agent (GraphFlow-Based)
**Primary Responsibilities:**
- **Stimuli Categorization**: Classify incoming external stimuli using LLM-powered analysis
- **Context Analysis**: Evaluate system state, user history, and environmental factors
- **Decision Routing**: Determine optimal processing path based on comprehensive analysis
- **Execution Coordination**: Orchestrate avatar tools and agent analysis as determined

#### 3.2.2 Stimuli Categories (Enhanced)
```python
class StimuliCategory(Enum):
    DIRECT_ADMIN = "direct_admin"           # Administrative commands
    USER_INTERACTION = "user_interaction"   # Chat, comments, questions
    SYSTEM_NOTIFICATION = "system_notification"  # Environment, status changes
    SOCIAL_MEDIA = "social_media"          # Tweets, mentions, shares
    AUTONOMOUS_TRIGGER = "autonomous_trigger"  # Self-generated events
    EMERGENCY = "emergency"                # Critical system alerts
    CONTEXTUAL_UPDATE = "contextual_update"  # Background information
```

#### 3.2.3 Decision Matrix
```python
class ProcessingDecision(Enum):
    AVATAR_AND_ANALYSIS = "avatar_and_analysis"  # Option A
    ANALYSIS_ONLY = "analysis_only"              # Option B  
    LOG_ONLY = "log_only"                        # Option C
    EMERGENCY_OVERRIDE = "emergency_override"     # Special handling
```

### 3.3 Processing Flow

#### Phase 1: Stimuli Ingestion
1. **Input Validation**: Validate incoming stimuli format and content
2. **Preprocessing**: Extract metadata, timestamps, source information
3. **Queue Management**: Priority-based queuing with overflow protection

#### Phase 2: GraphFlow Analysis
1. **Categorization Node**: LLM-powered classification of stimuli type
2. **Context Analysis Node**: System state evaluation and user history review
3. **Decision Routing Node**: Determine processing path using decision matrix

#### Phase 3: Execution Coordination
1. **Avatar Tool Execution**: Trigger System1 components when appropriate
2. **Agent Analysis**: Route to System2 multi-agent processing
3. **Response Coordination**: Manage concurrent processing and response merging
4. **Emergency Override** *(conditional)*: Execute predefined emergency actions (character load, mode switch, alert speech) before any further processing.

### 4. Functional Requirements

#### FR-001: GraphFlow Gateway Agent
- **Description**: Implement Microsoft AutoGen GraphFlow-based gateway agent
- **Requirements**:
  - Support for node-based processing with configurable workflows
  - LLM-powered stimuli classification with 95%+ accuracy
  - Context-aware decision making using system state
  - Configurable routing rules and decision matrices
- **Priority**: Critical
- **Success Criteria**: Gateway agent correctly processes 100% of test stimuli types

#### FR-002: Stimuli Categorization System  
- **Description**: Enhanced classification of external stimuli
- **Requirements**:
  - Support for 7 primary stimuli categories
  - Machine learning-based classification with confidence scoring
  - Real-time processing with <500ms categorization time
  - Fallback mechanisms for unknown stimuli types
- **Priority**: Critical  
- **Success Criteria**: >95% classification accuracy on diverse test dataset

#### FR-003: Context-Aware Decision Making
- **Description**: Intelligent routing based on comprehensive context analysis
- **Requirements**:
  - System state evaluation (speaking, idle, busy, etc.)
  - User interaction history and patterns
  - Environmental context (autonomous mode, streaming status)
  - Priority-based decision making with override capabilities
- **Priority**: High
- **Success Criteria**: Context factors demonstrably improve decision quality by 30%

#### FR-004: Multi-Path Processing Support
- **Description**: Support for three distinct processing paths
- **Requirements**:
  - **Option A**: Avatar tools + agent analysis for high-engagement stimuli
  - **Option B**: Agent analysis only for background processing
  - **Option C**: Log and store only for low-priority information
  - Concurrent processing support with resource management
- **Priority**: Critical
- **Success Criteria**: All three processing paths function correctly under load

#### FR-005: System1 Integration (Avatar Tools)
- **Description**: Seamless integration with existing avatar/speech systems
- **Requirements**:
  - Trigger VTuber speech generation when appropriate
  - Control avatar animations and blend shapes
  - Coordinate with TTS pipeline for immediate responses
  - Maintain existing API compatibility
- **Priority**: Critical
- **Success Criteria**: Zero breaking changes to existing System1 functionality

#### FR-006: System2 Integration (Multi-Agent Analysis)
- **Description**: Enhanced integration with existing AutoGen agents
- **Requirements**:
  - Route stimuli to cognitive_ai_agent, programmer_agent, observer_agent
  - Trigger evolution engine analysis when appropriate
  - Integrate with Cognee memory system
  - Support teachable agent learning from stimuli patterns
- **Priority**: High
- **Success Criteria**: Existing AutoGen agents receive properly formatted stimuli

#### FR-007: External System Integration
- **Description**: Support for external stimuli sources
- **Requirements**:
  - REST API endpoints for external system integration
  - WebSocket support for real-time stimuli streaming
  - SCB (Shared Contextual Bridge) integration
  - MCP server compatibility for Cursor IDE integration
- **Priority**: High
- **Success Criteria**: External systems can successfully submit stimuli via all supported methods

#### FR-008: Response Time Requirements
- **Description**: Performance benchmarks for stimuli processing
- **Requirements**:
  - Stimuli categorization: <500ms
  - Decision routing: <1 second
  - Avatar tool triggering: <2 seconds
  - Agent analysis initiation: <3 seconds
- **Priority**: High
- **Success Criteria**: 95% of requests meet performance targets under normal load

#### FR-009: Scalability Requirements
- **Description**: System capacity and growth support
- **Requirements**:
  - Handle 1000+ stimuli per hour
  - Support concurrent processing of 50+ stimuli
  - Horizontal scaling with container orchestration
  - Resource-based auto-scaling capabilities
- **Priority**: Medium
- **Success Criteria**: System maintains performance under 10x expected load

#### FR-010: Reliability Requirements
- **Description**: System availability and fault tolerance
- **Requirements**:
  - 99.9% uptime for gateway agent
  - Graceful degradation when components unavailable
  - Automatic recovery from transient failures
  - Circuit breaker patterns for external dependencies
- **Priority**: High
- **Success Criteria**: System meets uptime requirements over 30-day period

#### FR-011: Emergency Override Action File
- **Description**: Provide an external Python module that specifies what actions to execute during an emergency override.
- **Requirements**:
  - File path: `config/emergency_override.py`
  - Must expose a `handle_emergency(context: Dict[str, Any]) -> bool` function.
  - Default implementation: 
    1. Call System1 API `POST /character/load` with preset `"emergency_guardian"`.
    2. Call System1 API `POST /mode/set` with `{ "mode": "reactive" }`.
    3. Optionally invoke speech: `POST /speak` with a short alert phrase (configurable).
  - Gateway must import and execute this function when `EMERGENCY_OVERRIDE` decision is returned.
- **Priority**: High
- **Success Criteria**: Emergency override file executed successfully in >99% simulated emergency events without blocking normal processing.

### 4.2 Integration Requirements

#### FR-005: System1 Integration (Avatar Tools)
- **Updates**:
  - System1 **can receive stimuli directly from external sources**. Gateway must forward qualifying stimuli if the decision matrix selects `AVATAR_AND_ANALYSIS` or an emergency override requires direct System1 intervention.
  - Support new endpoints:
    - `POST /character/load` – load a character preset by ID.
    - `POST /mode/set` – switch between `reactive` and `autonomous` modes.

#### FR-006: System2 Integration (Multi-Agent Analysis)
- **Description**: Enhanced integration with existing AutoGen agents
- **Requirements**:
  - Route stimuli to cognitive_ai_agent, programmer_agent, observer_agent
  - Trigger evolution engine analysis when appropriate
  - Integrate with Cognee memory system
  - Support teachable agent learning from stimuli patterns
- **Priority**: High
- **Success Criteria**: Existing AutoGen agents receive properly formatted stimuli

#### FR-007: External System Integration
- **Description**: Support for external stimuli sources
- **Requirements**:
  - REST API endpoints for external system integration
  - WebSocket support for real-time stimuli streaming
  - SCB (Shared Contextual Bridge) integration
  - MCP server compatibility for Cursor IDE integration
- **Priority**: High
- **Success Criteria**: External systems can successfully submit stimuli via all supported methods

### 4.3 Performance Requirements

#### FR-008: Response Time Requirements
- **Description**: Performance benchmarks for stimuli processing
- **Requirements**:
  - Stimuli categorization: <500ms
  - Decision routing: <1 second
  - Avatar tool triggering: <2 seconds
  - Agent analysis initiation: <3 seconds
- **Priority**: High
- **Success Criteria**: 95% of requests meet performance targets under normal load

#### FR-009: Scalability Requirements
- **Description**: System capacity and growth support
- **Requirements**:
  - Handle 1000+ stimuli per hour
  - Support concurrent processing of 50+ stimuli
  - Horizontal scaling with container orchestration
  - Resource-based auto-scaling capabilities
- **Priority**: Medium
- **Success Criteria**: System maintains performance under 10x expected load

#### FR-010: Reliability Requirements
- **Description**: System availability and fault tolerance
- **Requirements**:
  - 99.9% uptime for gateway agent
  - Graceful degradation when components unavailable
  - Automatic recovery from transient failures
  - Circuit breaker patterns for external dependencies
- **Priority**: High
- **Success Criteria**: System meets uptime requirements over 30-day period

---

## 5. Non-Functional Requirements

### 5.1 Architecture Requirements

#### NFR-001: Containerization
- **Description**: Full containerization for deployment flexibility
- **Requirements**:
  - Docker containers for all components
  - Docker Compose configuration for testing
  - Kubernetes deployment manifests
  - Health check endpoints for orchestration
- **Priority**: High

#### NFR-002: Configuration Management
- **Description**: Flexible configuration without code changes
- **Requirements**:
  - Environment-based configuration
  - Runtime configuration updates for non-critical settings
  - Version-controlled configuration templates
  - Validation for configuration changes
- **Priority**: Medium

### 5.2 Security Requirements

#### NFR-003: Authentication & Authorization
- **Description**: Secure access control for external stimuli
- **Requirements**:
  - API key authentication for external systems
  - Role-based access control for different stimuli types
  - Rate limiting and DDoS protection
  - Audit logging for all security-relevant events
- **Priority**: High

#### NFR-004: Data Protection
- **Description**: Secure handling of sensitive stimuli data
- **Requirements**:
  - Encryption in transit for all communications
  - Secure storage for sensitive stimuli content
  - Data retention policies with automatic cleanup
  - PII detection and protection mechanisms
- **Priority**: High

### 5.3 Observability Requirements

#### NFR-005: Monitoring & Metrics
- **Description**: Comprehensive system observability
- **Requirements**:
  - Prometheus metrics for all components
  - Grafana dashboards for operational monitoring
  - Alert manager integration for critical issues
  - Performance tracking for decision quality
- **Priority**: High

#### NFR-006: Logging & Tracing
- **Description**: Detailed logging for debugging and analysis
- **Requirements**:
  - Structured logging with correlation IDs
  - Distributed tracing across components
  - Log aggregation with search capabilities
  - Retention policies for operational logs
- **Priority**: Medium

---

## 6. Technical Architecture

### 6.1 Technology Stack

#### Core Technologies
- **Framework**: Microsoft AutoGen 0.4+ with GraphFlow
- **Language**: Python 3.10+
- **LLM Integration**: Ollama (local), OpenAI (cloud), Azure OpenAI
- **Message Broker**: Redis for inter-component communication
- **Database**: PostgreSQL for persistent storage, pgvector for embeddings
- **Containerization**: Docker with Docker Compose

#### GraphFlow Components
- **Nodes**: Categorizer, Analyzer, Router, Executor
- **Edges**: Decision paths with conditional routing
- **State Management**: In-memory state with Redis persistence
- **Flow Control**: Parallel processing with synchronization points

### 6.2 Component Architecture

#### Gateway Agent Structure
```python
class GraphFlowGatewayAgent:
    """
    Main gateway agent implementing GraphFlow-based stimuli processing
    """
    
    def __init__(self, config: GraphFlowConfig):
        self.categorizer = StimuliCategorizerNode()
        self.analyzer = ContextAnalyzerNode() 
        self.router = DecisionRouterNode()
        self.executor = ExecutionCoordinatorNode()
        
    async def process_stimuli(self, stimuli: ExternalStimuli) -> ProcessingResult:
        """Main processing pipeline using GraphFlow"""
        # Flow: Categorizer -> Analyzer -> Router -> Executor
        pass
```

#### Integration Interfaces
```python
class System1Interface:
    """Interface for System1 (avatar/speech) integration"""
    
    async def trigger_avatar_response(self, content: str) -> bool:
        """Trigger avatar speech and animations"""
        pass
        
    async def check_system_availability(self) -> SystemStatus:
        """Check if System1 is available for requests"""
        pass

class System2Interface:
    """Interface for System2 (multi-agent) integration"""
    
    async def submit_for_analysis(self, stimuli: ExternalStimuli) -> str:
        """Submit stimuli to existing AutoGen agents"""
        pass
        
    async def get_agent_status(self) -> Dict[str, AgentStatus]:
        """Get status of all AutoGen agents"""
        pass
```

### 6.3 Data Models

#### Core Data Structures
```python
@dataclass
class ExternalStimuli:
    id: str
    content: str
    source: str
    timestamp: datetime
    metadata: Dict[str, Any]
    priority: Priority
    category: Optional[StimuliCategory] = None
    confidence: Optional[float] = None

@dataclass  
class ProcessingContext:
    system_state: SystemState
    user_history: List[UserInteraction]
    environmental_factors: Dict[str, Any]
    active_conversations: List[ConversationContext]
    resource_availability: ResourceStatus

@dataclass
class ProcessingResult:
    decision: ProcessingDecision
    execution_results: List[ExecutionResult]
    processing_time: float
    confidence_score: float
    metadata: Dict[str, Any]
```

---

## 7. Implementation Strategy

### 7.1 Development Phases

#### Phase 1: Foundation (Weeks 1-2)
**Deliverables:**
- GraphFlow gateway agent skeleton
- Basic stimuli categorization 
- Integration interfaces defined
- Development environment setup

**Key Activities:**
- Create new subfolder structure
- Implement core data models
- Set up GraphFlow node framework
- Create basic categorization logic

#### Phase 2: Core Functionality (Weeks 3-4)
**Deliverables:**
- Complete GraphFlow implementation
- Context-aware decision making
- System1/System2 integration
- Basic testing framework

**Key Activities:**
- Implement all GraphFlow nodes
- Build context analysis capabilities
- Create integration adapters
- Develop unit and integration tests

#### Phase 3: Advanced Features (Weeks 5-6)
**Deliverables:**
- Machine learning-enhanced categorization
- Performance optimization
- Monitoring and observability
- Load testing and tuning

**Key Activities:**
- Implement ML-based classification
- Add comprehensive monitoring
- Performance optimization
- Stress testing and tuning

#### Phase 4: Production Readiness (Weeks 7-8)
**Deliverables:**
- Security hardening
- Production deployment
- Documentation completion
- Performance validation

**Key Activities:**
- Security review and hardening
- Production deployment automation
- User documentation
- Performance benchmarking

### 7.2 Risk Mitigation

#### Technical Risks
- **GraphFlow Learning Curve**: Mitigate with early prototyping and team training
- **Integration Complexity**: Reduce with well-defined interfaces and extensive testing
- **Performance Bottlenecks**: Address with early performance testing and optimization

#### Project Risks
- **Scope Creep**: Control with clear requirements and change management
- **Resource Constraints**: Manage with phased delivery and priority focus
- **Timeline Pressure**: Mitigate with realistic estimation and buffer time

---

## 8. Success Criteria & Validation

### 8.1 Acceptance Criteria

#### Primary Success Metrics
1. **Functional Completeness**: 100% of specified functional requirements implemented
2. **Integration Success**: Zero breaking changes to existing autogen-agent system
3. **Performance Targets**: All performance requirements met under specified load
4. **Quality Standards**: >95% test coverage with automated testing pipeline

#### Secondary Success Metrics
1. **User Experience**: Improved response relevance as measured by user feedback
2. **System Efficiency**: Reduced processing overhead compared to current system
3. **Maintainability**: Clear code structure with comprehensive documentation
4. **Extensibility**: Easy addition of new stimuli types and processing logic

### 8.2 Testing Strategy

#### Test Categories
1. **Unit Tests**: Individual component functionality
2. **Integration Tests**: System boundary interactions
3. **End-to-End Tests**: Complete stimuli processing workflows
4. **Performance Tests**: Load, stress, and scalability validation
5. **Security Tests**: Vulnerability assessment and penetration testing

#### Test Environments
1. **Development**: Local development with mocked dependencies
2. **Testing**: Isolated environment for automated testing
3. **Staging**: Production-like environment for final validation
4. **Production**: Live environment with monitoring and rollback capabilities

---

## 9. Assumptions & Dependencies

### 9.1 Technical Assumptions
- Microsoft AutoGen GraphFlow functionality is stable and well-documented
- Existing System1 and System2 components remain architecturally stable
- Current hardware resources are sufficient for additional processing load
- LLM services (Ollama, OpenAI) maintain current availability and performance

### 9.2 Business Assumptions
- User requirements remain stable during development period
- Development team has sufficient AutoGen and GraphFlow expertise
- Testing resources and environments are available as needed
- Stakeholders are available for requirements clarification and validation

### 9.3 External Dependencies
- **Microsoft AutoGen**: Framework stability and feature availability
- **LLM Providers**: Service availability and API compatibility
- **Container Infrastructure**: Docker and orchestration platform availability
- **Monitoring Stack**: Prometheus, Grafana, and alerting infrastructure

---

## 10. Appendices

### Appendix A: Current System Analysis
**Existing AutoGen System Components:**
- `cognitive_ai_agent`: Context-aware decision maker with memory integration
- `programmer_agent`: Code generation and technical implementation  
- `observer_agent`: System monitoring and evaluation
- `GroupChat Manager`: Orchestrates agent collaboration
- Evolution Engine: Self-improvement capabilities with Darwin-Gödel Machine
- Cognee Integration: Knowledge graph and memory management

**Current External Stimuli Processing:**
- Event-based processing with priority queues
- Simple categorization (email, calendar, task, chat, system, autonomous)
- Basic routing to appropriate handlers
- Limited context awareness and decision logic

### Appendix B: GraphFlow Benefits Analysis
**Advantages of GraphFlow Approach:**
1. **Sophisticated Routing**: Graph-based decision trees vs. simple conditionals
2. **Visual Workflow**: Clear representation of processing flows
3. **Parallel Processing**: Concurrent node execution with synchronization
4. **Extensibility**: Easy addition of new nodes and processing paths
5. **Debugging**: Clear visibility into decision-making processes
6. **State Management**: Sophisticated state handling across workflow steps

### Appendix C: Risk Assessment Matrix

| Risk Category | Probability | Impact | Mitigation Strategy |
|---------------|-------------|---------|-------------------|
| GraphFlow Integration | Medium | High | Early prototyping, expert consultation |
| Performance Issues | Low | Medium | Load testing, optimization planning |
| Integration Breakage | Low | High | Comprehensive testing, rollback plans |
| Timeline Delays | Medium | Medium | Phased delivery, buffer time |
| Resource Constraints | Low | Medium | Clear prioritization, scope management |

---

**Document Approval:**

| Role | Name | Date | Signature |
|------|------|------|-----------|
| Product Owner | [TBD] | [TBD] | [TBD] |
| Technical Lead | [TBD] | [TBD] | [TBD] |
| Architecture Review | [TBD] | [TBD] | [TBD] |

**Next Steps:**
1. Stakeholder review and approval of PRD
2. Creation of detailed Functional Requirements Document (FRD)
3. Technical architecture deep-dive and design sessions
4. Implementation planning and resource allocation 