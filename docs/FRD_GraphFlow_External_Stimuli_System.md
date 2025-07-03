# Functional Requirements Document (FRD)
# GraphFlow-Based External Stimuli Handling System

**Document Version:** 1.0  
**Date:** January 2025  
**Author:** System Architect  
**Status:** Draft  
**Related Documents:** PRD_GraphFlow_External_Stimuli_System.md

---

## 1. Overview

### 1.1 Purpose
This FRD provides detailed functional specifications for implementing the GraphFlow-based external stimuli handling system. It translates the high-level requirements from the PRD into specific, actionable technical specifications for development teams.

### 1.2 Scope
- **In Scope**: GraphFlow gateway agent, stimuli processing pipeline, System1/System2 integration
- **Out of Scope**: Modifications to existing autogen-agent system, System1 avatar functionality changes
- **Dependencies**: Microsoft AutoGen 0.4+, existing System1/System2 infrastructure

### 1.3 Architecture Overview
```
External Stimuli → GraphFlow Gateway → Decision Matrix → Execution Paths
                      ↓
            [Categorizer] → [Analyzer] → [Router] → [Executor]
                      ↓                              ↓
                [Option A: Avatar + Analysis]  [Option B: Analysis Only]  [Option C: Log Only]
```

---

## 2. System Architecture

### 2.1 Project Structure
```
docker-vtuber/app/CORE/graphflow-stimuli-system/
├── src/
│   ├── gateway/
│   │   ├── __init__.py
│   │   ├── gateway_agent.py          # Main GraphFlow gateway
│   │   ├── nodes/
│   │   │   ├── categorizer_node.py   # Stimuli classification
│   │   │   ├── analyzer_node.py      # Context analysis  
│   │   │   ├── router_node.py        # Decision routing
│   │   │   └── executor_node.py      # Execution coordination
│   │   └── flows/
│   │       ├── stimuli_flow.py       # Main processing flow
│   │       └── decision_flow.py      # Decision logic flow
│   ├── models/
│   │   ├── __init__.py
│   │   ├── stimuli.py               # Data models for stimuli
│   │   ├── context.py               # Context and state models
│   │   └── decisions.py             # Decision and result models
│   ├── integrations/
│   │   ├── __init__.py
│   │   ├── system1_interface.py     # Avatar/speech integration
│   │   ├── system2_interface.py     # Multi-agent integration
│   │   └── external_interface.py    # External API interface
│   ├── config/
│   │   ├── __init__.py
│   │   ├── settings.py              # Configuration management
│   │   └── decision_matrix.py       # Decision rules
│   └── utils/
│       ├── __init__.py
│       ├── logging.py               # Structured logging
│       ├── metrics.py               # Performance metrics
│       └── validation.py            # Input validation
├── tests/
│   ├── unit/
│   ├── integration/
│   └── e2e/
├── docker/
│   ├── Dockerfile
│   ├── docker-compose.yml
│   └── docker-compose.test.yml
├── config/
│   ├── development.env
│   ├── testing.env
│   └── production.env
├── docs/
│   ├── API.md
│   ├── DEPLOYMENT.md
│   └── TROUBLESHOOTING.md
├── requirements.txt
├── setup.py
└── README.md
```

### 2.2 Technology Stack
- **Framework**: Microsoft AutoGen 0.4+ with GraphFlow
- **Language**: Python 3.10+
- **Dependencies**: autogen-agentchat, autogen-core, pydantic, asyncio
- **Database**: Redis for state management, PostgreSQL for persistence
- **Monitoring**: Prometheus metrics, structured logging
- **Testing**: pytest, pytest-asyncio, pytest-mock

---

## 3. Functional Specifications

### 3.1 GraphFlow Gateway Agent

#### 3.1.1 Gateway Agent Class
```python
class GraphFlowGatewayAgent:
    """
    Main gateway agent implementing GraphFlow-based stimuli processing
    
    Responsibilities:
    - Receive and validate external stimuli
    - Orchestrate GraphFlow processing pipeline
    - Coordinate with System1/System2 integrations
    - Provide monitoring and observability
    """
    
    def __init__(self, config: GraphFlowConfig):
        """Initialize gateway agent with configuration"""
        self.config = config
        self.flow_manager = StimuliFlowManager()
        self.system1_interface = System1Interface(config.system1)
        self.system2_interface = System2Interface(config.system2)
        self.metrics_collector = MetricsCollector()
        self.logger = get_structured_logger("gateway_agent")
        
    async def process_stimuli(self, stimuli: ExternalStimuli) -> ProcessingResult:
        """
        Main entry point for stimuli processing
        
        Args:
            stimuli: External stimuli to process
            
        Returns:
            ProcessingResult with decisions and execution results
        """
        
    async def health_check(self) -> Dict[str, Any]:
        """Health check for monitoring"""
        
    async def get_metrics(self) -> Dict[str, Any]:
        """Get performance metrics"""
```

#### 3.1.2 Configuration Management
```python
@dataclass
class GraphFlowConfig:
    """Configuration for GraphFlow gateway agent"""
    # Core settings
    max_concurrent_stimuli: int = 50
    processing_timeout: float = 30.0
    retry_attempts: int = 3
    
    # LLM settings
    llm_provider: str = "ollama"
    llm_model: str = "llama3.2:3b"
    llm_temperature: float = 0.3
    
    # Decision thresholds
    categorization_confidence_threshold: float = 0.8
    context_analysis_depth: str = "standard"  # minimal, standard, deep
    
    # Integration settings
    system1: System1Config
    system2: System2Config
    external_apis: ExternalAPIConfig
    
    # Monitoring
    metrics_enabled: bool = True
    detailed_logging: bool = True
    performance_tracking: bool = True
```

### 3.2 GraphFlow Nodes

#### 3.2.1 Categorizer Node
```python
class StimuliCategorizerNode:
    """
    GraphFlow node for stimuli categorization
    
    Input: Raw external stimuli
    Output: Categorized stimuli with confidence scores
    """
    
    def __init__(self, llm_client: LLMClient, config: CategorizerConfig):
        self.llm_client = llm_client
        self.config = config
        self.category_classifier = CategoryClassifier()
        
    async def process(self, stimuli: ExternalStimuli) -> CategorizedStimuli:
        """
        Categorize incoming stimuli using LLM analysis. The node also recognises **avatar state notifications** (speaking, idle, busy, character_loaded) as high-salience `SYSTEM_NOTIFICATION` events, guaranteeing that System2 has real-time awareness of System1.
        
        Process:
        1. Extract content features (length, keywords, source)
        2. Apply LLM-based classification
        3. Generate confidence scores
        4. Apply fallback logic for unknown types
        
        Returns:
            CategorizedStimuli with category and confidence
        """
        
    def _extract_features(self, stimuli: ExternalStimuli) -> Dict[str, Any]:
        """Extract features for classification"""
        
    def _apply_llm_classification(self, features: Dict[str, Any]) -> CategoryResult:
        """Use LLM for intelligent categorization"""
        
    def _validate_category(self, category: StimuliCategory, confidence: float) -> bool:
        """Validate categorization result"""
```

#### 3.2.2 Analyzer Node
```python
class ContextAnalyzerNode:
    """
    GraphFlow node for context analysis
    
    Input: Categorized stimuli
    Output: Context-enriched stimuli with analysis metadata
    """
    
    def __init__(self, context_service: ContextService, config: AnalyzerConfig):
        self.context_service = context_service
        self.config = config
        
    async def process(self, categorized_stimuli: CategorizedStimuli) -> AnalyzedStimuli:
        """
        Analyze context for intelligent decision making
        
        Analysis dimensions:
        1. System state (speaking, idle, busy, error)
        2. User interaction history and patterns
        3. Environmental context (autonomous mode, streaming)
        4. Resource availability (CPU, memory, agent status)
        5. Temporal factors (time of day, recent activity)
        
        Returns:
            AnalyzedStimuli with rich context metadata
        """
        
    async def _analyze_system_state(self) -> SystemStateAnalysis:
        """Analyze current system state"""
        
    async def _analyze_user_context(self, stimuli: CategorizedStimuli) -> UserContextAnalysis:
        """Analyze user interaction patterns"""
        
    async def _analyze_environmental_context(self) -> EnvironmentalAnalysis:
        """Analyze environmental factors"""
        
    async def _analyze_resource_availability(self) -> ResourceAnalysis:
        """Check system resource availability"""
```

#### 3.2.3 Router Node
```python
class DecisionRouterNode:
    """
    GraphFlow node for decision routing
    
    Input: Analyzed stimuli with context
    Output: Routing decision with execution plan
    """
    
    def __init__(self, decision_engine: DecisionEngine, config: RouterConfig):
        self.decision_engine = decision_engine
        self.config = config
        
    async def process(self, analyzed_stimuli: AnalyzedStimuli) -> RoutingDecision:
        """
        Make routing decisions based on comprehensive analysis
        
        Decision matrix considerations:
        1. Stimuli category and priority
        2. System state and availability
        3. User engagement patterns
        4. Resource constraints
        5. Business rules and policies
        
        Returns:
            RoutingDecision with execution plan
        """
        
    def _apply_decision_matrix(self, analyzed_stimuli: AnalyzedStimuli) -> ProcessingDecision:
        """Apply decision matrix rules"""
        
    def _generate_execution_plan(self, decision: ProcessingDecision, 
                                analyzed_stimuli: AnalyzedStimuli) -> ExecutionPlan:
        """Generate detailed execution plan"""
        
    def _validate_decision(self, decision: ProcessingDecision, 
                          analyzed_stimuli: AnalyzedStimuli) -> bool:
        """Validate decision against constraints"""
```

#### 3.2.4 Executor Node
```python
class ExecutionCoordinatorNode:
    """
    GraphFlow node for execution coordination
    
    Input: Routing decision with execution plan
    Output: Execution results and performance metrics
    """
    
    def __init__(self, system1_interface: System1Interface,
                 system2_interface: System2Interface, config: ExecutorConfig):
        self.system1_interface = system1_interface
        self.system2_interface = system2_interface
        self.config = config
        
    async def process(self, routing_decision: RoutingDecision) -> ExecutionResult:
        """
        Execute the routing decision
        
        Execution paths:
        - Option A: Avatar tools + agent analysis (concurrent)
        - Option B: Agent analysis only
        - Option C: Log and store only
        - Emergency: Override with immediate processing
        
        Returns:
            ExecutionResult with success status and metadata
        """
        
    async def _execute_option_a(self, execution_plan: ExecutionPlan) -> List[ExecutionResult]:
        """Execute avatar tools + agent analysis concurrently"""
        
    async def _execute_option_b(self, execution_plan: ExecutionPlan) -> ExecutionResult:
        """Execute agent analysis only"""
        
    async def _execute_option_c(self, execution_plan: ExecutionPlan) -> ExecutionResult:
        """Execute log and store only"""
        
    async def _handle_emergency_override(self, execution_plan: ExecutionPlan) -> ExecutionResult:
        """Handle emergency processing with override"""
        # Load actions dynamically from external file so they can be changed
        try:
            from config.emergency_override import handle_emergency
        except ImportError:
            self.logger.error("Emergency override file not found – skipping override actions")
            return ExecutionResult(
                stimuli_id=execution_plan.stimuli_id,
                execution_plan_id=execution_plan.id,
                success=False,
                results={"error": "Emergency override file missing"},
                execution_time=0.0
            )
        start = time.time()
        success = await handle_emergency({
            "system1_interface": self.system1_interface,
            "execution_plan": execution_plan
        })
        end = time.time()
        return ExecutionResult(
            stimuli_id=execution_plan.stimuli_id,
            execution_plan_id=execution_plan.id,
            success=success,
            results={"override": success},
            execution_time=end - start
        )
```

### 3.3 Data Models

#### 3.3.1 Core Stimuli Models
```python
@dataclass
class ExternalStimuli:
    """Base model for external stimuli"""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    content: str
    source: str
    timestamp: datetime = field(default_factory=datetime.now)
    metadata: Dict[str, Any] = field(default_factory=dict)
    priority: Priority = Priority.MEDIUM
    
    def validate(self) -> bool:
        """Validate stimuli data"""
        
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization"""

@dataclass
class CategorizedStimuli(ExternalStimuli):
    """Stimuli with categorization results"""
    category: StimuliCategory
    confidence: float
    classification_metadata: Dict[str, Any] = field(default_factory=dict)
    
@dataclass
class AnalyzedStimuli(CategorizedStimuli):
    """Stimuli with context analysis"""
    system_state_analysis: SystemStateAnalysis
    user_context_analysis: UserContextAnalysis
    environmental_analysis: EnvironmentalAnalysis
    resource_analysis: ResourceAnalysis
    analysis_timestamp: datetime = field(default_factory=datetime.now)

@dataclass
class RoutingDecision:
    """Decision routing result"""
    stimuli_id: str
    decision: ProcessingDecision
    execution_plan: ExecutionPlan
    confidence_score: float
    reasoning: str
    decision_timestamp: datetime = field(default_factory=datetime.now)
```

#### 3.3.2 Context Analysis Models
```python
@dataclass
class SystemStateAnalysis:
    """Analysis of current system state"""
    is_speaking: bool
    is_idle: bool
    is_busy: bool
    has_errors: bool
    queue_size: int
    resource_utilization: Dict[str, float]
    availability_score: float

@dataclass
class UserContextAnalysis:
    """Analysis of user interaction context"""
    interaction_frequency: float
    engagement_level: str  # low, medium, high
    recent_topics: List[str]
    user_preference_match: float
    historical_response_patterns: Dict[str, Any]

@dataclass
class EnvironmentalAnalysis:
    """Analysis of environmental context"""
    autonomous_mode_active: bool
    streaming_status: str
    time_of_day_factor: float
    recent_activity_level: str
    external_event_context: Dict[str, Any]

@dataclass
class ResourceAnalysis:
    """Analysis of system resource availability"""
    cpu_availability: float
    memory_availability: float
    agent_availability: Dict[str, bool]
    system1_availability: bool
    system2_availability: bool
    estimated_processing_capacity: int
```

#### 3.3.3 Execution Models
```python
@dataclass
class ExecutionPlan:
    """Detailed execution plan"""
    decision: ProcessingDecision
    target_systems: List[str]  # system1, system2, external
    execution_order: List[str]  # sequential, parallel
    timeout_settings: Dict[str, float]
    retry_policies: Dict[str, RetryPolicy]
    success_criteria: Dict[str, Any]

@dataclass
class ExecutionResult:
    """Result of execution"""
    stimuli_id: str
    execution_plan_id: str
    success: bool
    results: Dict[str, Any]
    execution_time: float
    error_details: Optional[str] = None
    performance_metrics: Dict[str, float] = field(default_factory=dict)
    timestamp: datetime = field(default_factory=datetime.now)
```

### 3.4 Integration Interfaces

#### 3.4.1 System1 Interface (Avatar/Speech)
```python
class System1Interface:
    """Interface for System1 (avatar/speech) integration"""
    
    def __init__(self, config: System1Config):
        self.config = config
        self.vtuber_client = VTuberClient(config.vtuber_endpoint)
        self.tts_client = TTSClient(config.tts_endpoint)
        
    async def trigger_avatar_response(self, content: str, metadata: Dict[str, Any]) -> bool:
        """
        Trigger avatar speech and animations
        
        Args:
            content: Text content for speech
            metadata: Additional context for avatar control
            
        Returns:
            Success status of avatar activation
        """
        
    async def check_system_availability(self) -> SystemStatus:
        """Check if System1 is available for requests"""
        
    async def get_current_status(self) -> Dict[str, Any]:
        """Get current avatar/speech system status"""
        
    async def estimate_processing_time(self, content: str) -> float:
        """Estimate time required for processing content"""

    async def load_character(self, character_id: str) -> bool:
        """Load a character preset by ID"""
        # POST /character/load
        pass
        
    async def set_mode(self, mode: Literal["reactive", "autonomous"]) -> bool:
        """Switch between reactive or autonomous mode"""
        # POST /mode/set
        pass
```

#### 3.4.2 System2 Interface (Multi-Agent)
```python
class System2Interface:
    """Interface for System2 (multi-agent) integration"""
    
    def __init__(self, config: System2Config):
        self.config = config
        self.autogen_client = AutoGenClient(config.autogen_endpoint)
        self.agent_manager = AgentManager(config.agent_config)
        
    async def submit_for_analysis(self, stimuli: AnalyzedStimuli) -> str:
        """
        Submit stimuli to existing AutoGen agents
        
        Args:
            stimuli: Analyzed stimuli for agent processing
            
        Returns:
            Task ID for tracking analysis progress
        """
        
    async def get_agent_status(self) -> Dict[str, AgentStatus]:
        """Get status of all AutoGen agents"""
        
    async def trigger_evolution_analysis(self, stimuli: AnalyzedStimuli) -> bool:
        """Trigger evolution engine analysis if appropriate"""
        
    async def query_cognee_memory(self, query: str) -> List[MemoryResult]:
        """Query Cognee memory system for relevant context"""
```

#### 3.4.3 External API Interface
```python
class ExternalAPIInterface:
    """Interface for external system integration"""
    
    def __init__(self, config: ExternalAPIConfig):
        self.config = config
        self.api_server = FastAPI()
        self.websocket_manager = WebSocketManager()
        self.auth_manager = AuthManager(config.auth_config)
        
    async def setup_routes(self):
        """Setup REST API routes for external integration"""
        
    @app.post("/api/v1/stimuli/submit")
    async def submit_stimuli(self, stimuli_data: Dict[str, Any]) -> Dict[str, Any]:
        """REST endpoint for submitting external stimuli"""
        
    @app.websocket("/ws/stimuli")
    async def websocket_stimuli_stream(self, websocket: WebSocket):
        """WebSocket endpoint for real-time stimuli streaming"""
        
    async def validate_api_key(self, api_key: str) -> bool:
        """Validate API key for authentication"""
```

---

## 4. Decision Matrix Specifications

### 4.1 Decision Rules Engine
```python
class DecisionRulesEngine:
    """Engine for applying decision rules to stimuli"""
    
    def __init__(self, rules_config: DecisionRulesConfig):
        self.rules = self._load_decision_rules(rules_config)
        
    def apply_rules(self, analyzed_stimuli: AnalyzedStimuli) -> ProcessingDecision:
        """
        Apply decision rules to determine processing path
        
        Rule evaluation order:
        1. Emergency rules (highest priority)
        2. System state rules
        3. Category-specific rules
        4. Resource availability rules
        5. Default rules (lowest priority)
        
        Returns:
            ProcessingDecision based on rule evaluation
        """
        
    def _evaluate_emergency_rules(self, stimuli: AnalyzedStimuli) -> Optional[ProcessingDecision]:
        """Evaluate emergency override rules"""
        
    def _evaluate_system_state_rules(self, stimuli: AnalyzedStimuli) -> Optional[ProcessingDecision]:
        """Evaluate system state-based rules"""
        
    def _evaluate_category_rules(self, stimuli: AnalyzedStimuli) -> Optional[ProcessingDecision]:
        """Evaluate category-specific rules"""
```

### 4.2 Decision Matrix Configuration
```python
# Decision matrix configuration example
DECISION_MATRIX = {
    "emergency_rules": [
        {
            "condition": "category == EMERGENCY",
            "decision": "EMERGENCY_OVERRIDE",
            "priority": 100
        }
    ],
    "system_state_rules": [
        {
            "condition": "system_state.is_speaking == True",
            "decision": "ANALYSIS_ONLY",
            "priority": 90
        },
        {
            "condition": "system_state.is_idle == True AND category == USER_INTERACTION",
            "decision": "AVATAR_AND_ANALYSIS",
            "priority": 80
        }
    ],
    "category_rules": [
        {
            "condition": "category == DIRECT_ADMIN",
            "decision": "AVATAR_AND_ANALYSIS",
            "priority": 70
        },
        {
            "condition": "category == CONTEXTUAL_UPDATE",
            "decision": "LOG_ONLY",
            "priority": 30
        }
    ],
    "resource_rules": [
        {
            "condition": "resource_analysis.cpu_availability < 0.3",
            "decision": "LOG_ONLY",
            "priority": 60
        }
    ],
    "default_rules": [
        {
            "condition": "True",
            "decision": "ANALYSIS_ONLY",
            "priority": 10
        }
    ]
}
```

---

## 5. API Specifications

### 5.1 REST API Endpoints

#### 5.1.1 Stimuli Submission
```
POST /api/v1/stimuli/submit
Content-Type: application/json
Authorization: Bearer <api_key>

Request Body:
{
    "content": "string",           # Required: Stimuli content
    "source": "string",           # Required: Source identifier
    "priority": "high|medium|low", # Optional: Priority level
    "metadata": {                 # Optional: Additional metadata
        "user_id": "string",
        "platform": "string",
        "context": "object"
    },
    "processing_options": {       # Optional: Processing preferences
        "force_avatar": boolean,
        "bypass_analysis": boolean,
        "timeout": number
    }
}

Response:
{
    "success": boolean,
    "stimuli_id": "string",
    "processing_status": "queued|processing|completed|failed",
    "estimated_processing_time": number,
    "message": "string"
}
```

#### 5.1.2 Status and Monitoring
```
GET /api/v1/status
Response:
{
    "system_status": "healthy|degraded|down",
    "gateway_agent_status": "active|inactive|error",
    "processing_queue_size": number,
    "average_processing_time": number,
    "system_load": {
        "cpu": number,
        "memory": number,
        "active_requests": number
    }
}

GET /api/v1/stimuli/{stimuli_id}/status
Response:
{
    "stimuli_id": "string",
    "status": "queued|processing|completed|failed",
    "processing_decision": "string",
    "execution_results": "object",
    "processing_time": number,
    "created_at": "timestamp",
    "completed_at": "timestamp"
}
```

### 5.2 WebSocket API

#### 5.2.1 Real-time Stimuli Streaming
```javascript
// WebSocket connection
ws://localhost:8080/ws/stimuli

// Message format for submitting stimuli
{
    "type": "submit_stimuli",
    "data": {
        "content": "string",
        "source": "string",
        "priority": "string",
        "metadata": "object"
    }
}

// Response format
{
    "type": "stimuli_response",
    "stimuli_id": "string",
    "status": "string",
    "data": "object"
}

// Status updates
{
    "type": "status_update",
    "stimuli_id": "string",
    "status": "string",
    "processing_stage": "string",
    "timestamp": "string"
}
```

---

## 6. Performance Requirements

### 6.1 Response Time Targets
- **Stimuli Ingestion**: < 100ms
- **Categorization**: < 500ms
- **Context Analysis**: < 800ms
- **Decision Routing**: < 200ms
- **Execution Initiation**: < 1000ms
- **End-to-End Processing**: < 2000ms (95th percentile)

### 6.2 Throughput Targets
- **Peak Load**: 1000 stimuli per hour
- **Concurrent Processing**: 50 stimuli simultaneously
- **Queue Capacity**: 10000 pending stimuli
- **Sustained Load**: 500 stimuli per hour over 24 hours

### 6.3 Resource Constraints
- **Memory Usage**: < 2GB per instance
- **CPU Utilization**: < 80% under normal load
- **Disk I/O**: < 100MB/s
- **Network Bandwidth**: < 50Mbps

---

## 7. Testing Specifications

### 7.1 Unit Testing
```python
# Example unit test structure
class TestStimuliCategorizerNode:
    """Unit tests for stimuli categorizer node"""
    
    @pytest.fixture
    def categorizer_node(self):
        """Create categorizer node for testing"""
        config = CategorizerConfig(
            confidence_threshold=0.8,
            fallback_category="CONTEXTUAL_UPDATE"
        )
        return StimuliCategorizerNode(mock_llm_client, config)
    
    @pytest.mark.asyncio
    async def test_categorize_direct_admin(self, categorizer_node):
        """Test categorization of direct admin requests"""
        stimuli = ExternalStimuli(
            content="Set avatar hair color to blue",
            source="admin_console"
        )
        result = await categorizer_node.process(stimuli)
        assert result.category == StimuliCategory.DIRECT_ADMIN
        assert result.confidence > 0.8
    
    @pytest.mark.asyncio
    async def test_categorize_unknown_fallback(self, categorizer_node):
        """Test fallback for unknown stimuli types"""
        stimuli = ExternalStimuli(
            content="Random gibberish text",
            source="unknown"
        )
        result = await categorizer_node.process(stimuli)
        assert result.category == StimuliCategory.CONTEXTUAL_UPDATE
        assert result.confidence < 0.5
```

### 7.2 Integration Testing
```python
class TestGraphFlowIntegration:
    """Integration tests for GraphFlow pipeline"""
    
    @pytest.mark.asyncio
    async def test_end_to_end_processing(self):
        """Test complete stimuli processing pipeline"""
        gateway = GraphFlowGatewayAgent(test_config)
        
        stimuli = ExternalStimuli(
            content="Hello, how are you today?",
            source="user_chat"
        )
        
        result = await gateway.process_stimuli(stimuli)
        
        assert result.success == True
        assert result.processing_time < 2.0
        assert result.decision in [
            ProcessingDecision.AVATAR_AND_ANALYSIS,
            ProcessingDecision.ANALYSIS_ONLY
        ]
```

### 7.3 Load Testing
```python
class TestPerformanceLoad:
    """Load testing for performance validation"""
    
    @pytest.mark.asyncio
    async def test_concurrent_processing(self):
        """Test handling of concurrent stimuli"""
        gateway = GraphFlowGatewayAgent(production_config)
        
        # Generate 50 concurrent stimuli
        stimuli_batch = [
            ExternalStimuli(
                content=f"Test stimuli {i}",
                source="load_test"
            ) for i in range(50)
        ]
        
        start_time = time.time()
        results = await asyncio.gather(*[
            gateway.process_stimuli(stimuli) 
            for stimuli in stimuli_batch
        ])
        end_time = time.time()
        
        # Validate performance requirements
        assert len(results) == 50
        assert all(result.success for result in results)
        assert (end_time - start_time) < 10.0  # 50 stimuli in < 10 seconds
```

---

## 8. Deployment Specifications

### 8.1 Docker Configuration
```dockerfile
# Dockerfile
FROM python:3.10-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY src/ ./src/
COPY config/ ./config/

# Create non-root user
RUN useradd -m -u 1000 graphflow && chown -R graphflow:graphflow /app
USER graphflow

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8080/health || exit 1

# Run application
CMD ["python", "-m", "src.main"]
```

### 8.2 Docker Compose Configuration
```yaml
# docker-compose.yml
version: '3.8'

services:
  graphflow-gateway:
    build: .
    ports:
      - "8080:8080"
    environment:
      - GRAPHFLOW_CONFIG_PATH=/app/config/production.env
      - REDIS_URL=redis://redis:6379
      - POSTGRES_URL=postgresql://postgres:password@postgres:5432/graphflow
    depends_on:
      - redis
      - postgres
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8080/health"]
      interval: 30s
      timeout: 10s
      retries: 3
    restart: unless-stopped
    
  redis:
    image: redis:7-alpine
    ports:
      - "6379:6379"
    volumes:
      - redis_data:/data
    restart: unless-stopped
    
  postgres:
    image: postgres:15-alpine
    environment:
      POSTGRES_DB: graphflow
      POSTGRES_USER: postgres
      POSTGRES_PASSWORD: password
    volumes:
      - postgres_data:/var/lib/postgresql/data
    ports:
      - "5432:5432"
    restart: unless-stopped
    
  prometheus:
    image: prom/prometheus:latest
    ports:
      - "9090:9090"
    volumes:
      - ./monitoring/prometheus.yml:/etc/prometheus/prometheus.yml
    restart: unless-stopped

volumes:
  redis_data:
  postgres_data:
```

### 8.3 Environment Configuration
```bash
# config/production.env
# Core settings
GRAPHFLOW_LOG_LEVEL=INFO
GRAPHFLOW_MAX_CONCURRENT_STIMULI=50
GRAPHFLOW_PROCESSING_TIMEOUT=30.0

# LLM settings
GRAPHFLOW_LLM_PROVIDER=ollama
GRAPHFLOW_LLM_MODEL=llama3.2:3b
GRAPHFLOW_LLM_ENDPOINT=http://ollama:11434

# Integration endpoints
SYSTEM1_VTUBER_ENDPOINT=http://neurosync:5001
SYSTEM2_AUTOGEN_ENDPOINT=http://autogen-agent:3100

# Database settings
REDIS_URL=redis://redis:6379
POSTGRES_URL=postgresql://postgres:password@postgres:5432/graphflow

# Monitoring
METRICS_ENABLED=true
PROMETHEUS_PORT=9090
DETAILED_LOGGING=true
```

---

## 9. Monitoring and Observability

### 9.1 Metrics Collection
```python
class MetricsCollector:
    """Collect and expose performance metrics"""
    
    def __init__(self):
        # Processing metrics
        self.stimuli_processed = Counter('stimuli_processed_total')
        self.processing_time = Histogram('stimuli_processing_seconds')
        self.categorization_accuracy = Gauge('categorization_accuracy_ratio')
        
        # System metrics
        self.active_requests = Gauge('active_requests_current')
        self.queue_size = Gauge('processing_queue_size')
        self.system_health = Gauge('system_health_status')
        
        # Decision metrics
        self.decision_distribution = Counter('decisions_made_total', ['decision_type'])
        self.execution_success_rate = Gauge('execution_success_rate')
        
    def record_processing_time(self, duration: float):
        """Record processing time for a stimuli"""
        self.processing_time.observe(duration)
        
    def increment_stimuli_processed(self, category: str, decision: str):
        """Increment processed stimuli counter"""
        self.stimuli_processed.labels(category=category, decision=decision).inc()
```

### 9.2 Structured Logging
```python
import structlog

def get_structured_logger(name: str) -> structlog.Logger:
    """Get structured logger with consistent configuration"""
    return structlog.get_logger(name).bind(
        service="graphflow-gateway",
        version="1.0.0"
    )

# Example log messages
logger.info(
    "Stimuli processed successfully",
    stimuli_id=stimuli.id,
    category=result.category,
    decision=result.decision,
    processing_time=result.processing_time,
    confidence=result.confidence
)

logger.error(
    "Failed to process stimuli",
    stimuli_id=stimuli.id,
    error=str(exception),
    processing_stage="categorization",
    retry_count=retry_count
)
```

---

## 10. Security Specifications

### 10.1 Authentication and Authorization
```python
class SecurityManager:
    """Handle authentication and authorization"""
    
    def __init__(self, config: SecurityConfig):
        self.api_keys = self._load_api_keys(config.api_keys_file)
        self.rate_limiter = RateLimiter(config.rate_limits)
        
    async def authenticate_request(self, api_key: str) -> AuthResult:
        """Authenticate API request"""
        if api_key not in self.api_keys:
            return AuthResult(success=False, reason="Invalid API key")
            
        return AuthResult(success=True, permissions=self.api_keys[api_key])
        
    async def authorize_stimuli_submission(self, auth_result: AuthResult,
                                         stimuli: ExternalStimuli) -> bool:
        """Authorize stimuli submission based on permissions"""
        required_permission = f"submit:{stimuli.source}"
        return required_permission in auth_result.permissions
        
    async def check_rate_limit(self, api_key: str) -> bool:
        """Check if request is within rate limits"""
        return await self.rate_limiter.check_limit(api_key)
```

### 10.2 Input Validation and Sanitization
```python
class InputValidator:
    """Validate and sanitize input data"""
    
    MAX_CONTENT_LENGTH = 10000
    ALLOWED_SOURCES = ["user_chat", "admin_console", "social_media", "system"]
    
    def validate_stimuli(self, stimuli_data: Dict[str, Any]) -> ValidationResult:
        """Comprehensive input validation"""
        errors = []
        
        # Content validation
        if not stimuli_data.get("content"):
            errors.append("Content is required")
        elif len(stimuli_data["content"]) > self.MAX_CONTENT_LENGTH:
            errors.append(f"Content exceeds maximum length of {self.MAX_CONTENT_LENGTH}")
            
        # Source validation
        if stimuli_data.get("source") not in self.ALLOWED_SOURCES:
            errors.append(f"Invalid source: {stimuli_data.get('source')}")
            
        # Sanitize content
        sanitized_content = self._sanitize_content(stimuli_data.get("content", ""))
        
        return ValidationResult(
            valid=len(errors) == 0,
            errors=errors,
            sanitized_data={
                **stimuli_data,
                "content": sanitized_content
            }
        )
        
    def _sanitize_content(self, content: str) -> str:
        """Sanitize input content"""
        # Remove potentially dangerous content
        sanitized = html.escape(content)
        # Additional sanitization rules...
        return sanitized
```

---

## 11. Error Handling and Recovery

### 11.1 Error Handling Strategy
```python
class ErrorHandler:
    """Handle errors and implement recovery strategies"""
    
    def __init__(self, config: ErrorHandlingConfig):
        self.config = config
        self.circuit_breaker = CircuitBreaker(config.circuit_breaker)
        
    async def handle_processing_error(self, error: Exception, 
                                    stimuli: ExternalStimuli) -> ErrorResponse:
        """Handle errors during stimuli processing"""
        if isinstance(error, ValidationError):
            return ErrorResponse(
                error_type="validation_error",
                message=str(error),
                recoverable=False,
                retry_recommended=False
            )
        elif isinstance(error, LLMTimeoutError):
            return ErrorResponse(
                error_type="llm_timeout",
                message="LLM processing timeout",
                recoverable=True,
                retry_recommended=True,
                retry_delay=5.0
            )
        elif isinstance(error, SystemOverloadError):
            return ErrorResponse(
                error_type="system_overload",
                message="System overloaded, try again later",
                recoverable=True,
                retry_recommended=True,
                retry_delay=10.0
            )
        
        # Default error handling
        return ErrorResponse(
            error_type="unknown_error",
            message=str(error),
            recoverable=False,
            retry_recommended=False
        )
```

### 11.2 Graceful Degradation
```python
class GracefulDegradationManager:
    """Manage system degradation and fallback strategies"""
    
    async def handle_system1_unavailable(self, stimuli: AnalyzedStimuli) -> ProcessingDecision:
        """Handle System1 (avatar) unavailability"""
        logger.warning("System1 unavailable, falling back to analysis only",
                      stimuli_id=stimuli.id)
        return ProcessingDecision.ANALYSIS_ONLY
        
    async def handle_system2_unavailable(self, stimuli: AnalyzedStimuli) -> ProcessingDecision:
        """Handle System2 (agents) unavailability"""
        if stimuli.category == StimuliCategory.DIRECT_ADMIN:
            logger.warning("System2 unavailable for admin request, logging only",
                          stimuli_id=stimuli.id)
            return ProcessingDecision.LOG_ONLY
        else:
            # Try to use System1 if available
            return ProcessingDecision.AVATAR_AND_ANALYSIS
            
    async def handle_llm_unavailable(self, stimuli: ExternalStimuli) -> CategorizedStimuli:
        """Handle LLM unavailability with rule-based fallback"""
        # Use simple keyword-based categorization as fallback
        fallback_category = self._categorize_by_keywords(stimuli.content)
        return CategorizedStimuli(
            **stimuli.__dict__,
            category=fallback_category,
            confidence=0.5,  # Lower confidence for fallback
            classification_metadata={"method": "keyword_fallback"}
        )
```

---

## 12. Conclusion

This FRD provides comprehensive functional specifications for implementing the GraphFlow-based external stimuli handling system. The specifications cover:

1. **Detailed Architecture**: Complete component structure and data flow
2. **Implementation Specifications**: Specific classes, methods, and interfaces
3. **Integration Requirements**: Clear interfaces for System1/System2 integration
4. **Performance Targets**: Quantifiable requirements for response time and throughput
5. **Security Specifications**: Authentication, authorization, and input validation
6. **Testing Strategy**: Unit, integration, and load testing approaches
7. **Deployment Configuration**: Docker, environment, and monitoring setup
8. **Error Handling**: Comprehensive error recovery and graceful degradation

The next steps involve:
1. **Technical Architecture Review**: Review specifications with development team
2. **Implementation Planning**: Break down into development sprints
3. **Environment Setup**: Prepare development and testing environments
4. **Prototype Development**: Create initial GraphFlow gateway prototype

This FRD serves as the definitive technical specification for development teams implementing the GraphFlow-based external stimuli handling system.

---

**Document Approval:**

| Role | Name | Date | Signature |
|------|------|------|-----------|
| Technical Lead | [TBD] | [TBD] | [TBD] |
| Senior Developer | [TBD] | [TBD] | [TBD] |
| DevOps Engineer | [TBD] | [TBD] | [TBD] |
| QA Lead | [TBD] | [TBD] | [TBD] | 