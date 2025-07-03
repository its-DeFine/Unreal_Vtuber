# GraphFlow External Stimuli System - Developer Guide

## Table of Contents

1. [Setup Instructions](#setup-instructions)
2. [Development Workflow](#development-workflow)
3. [Testing Guide](#testing-guide)
4. [Debugging Tips](#debugging-tips)
5. [Code Structure](#code-structure)
6. [Contributing Guidelines](#contributing-guidelines)

## Setup Instructions

### Prerequisites

- Python 3.10 or higher
- Docker and Docker Compose
- Redis (for caching and state management)
- PostgreSQL (for persistent storage)
- Ollama (for local LLM support)

### Local Development Setup

1. **Clone the Repository**
   ```bash
   cd docker-vtuber/app/CORE/graphflow-stimuli-system
   ```

2. **Create Virtual Environment**
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install Dependencies**
   ```bash
   pip install -r requirements.txt
   pip install -e .  # Install package in development mode
   ```

4. **Configure Environment**
   ```bash
   cp config/development.env.example config/development.env
   cp config/api_keys.json.example config/api_keys.json
   ```

5. **Start Infrastructure Services**
   ```bash
   # Start Redis and PostgreSQL
   docker-compose up -d redis postgres
   
   # Start Ollama (if using local LLM)
   docker-compose up -d ollama
   ```

6. **Initialize Database**
   ```bash
   docker exec -i graphflow-postgres psql -U postgres < docker/init-db.sql
   ```

7. **Run the System**
   ```bash
   python -m src.main
   ```

### Docker Development Setup

1. **Build Development Image**
   ```bash
   docker-compose -f docker/docker-compose.dev.yml build
   ```

2. **Start All Services**
   ```bash
   docker-compose -f docker/docker-compose.dev.yml up
   ```

3. **View Logs**
   ```bash
   docker-compose -f docker/docker-compose.dev.yml logs -f graphflow-gateway
   ```

## Development Workflow

### Project Structure Overview

```
src/
├── gateway/              # Core GraphFlow implementation
│   ├── gateway_agent.py  # Main orchestrator
│   ├── nodes/           # Processing nodes
│   │   ├── categorizer_node.py
│   │   ├── analyzer_node.py
│   │   ├── router_node.py
│   │   └── executor_node.py
│   └── flows/           # Flow managers
├── models/              # Data models
├── integrations/        # External system interfaces
├── config/             # Configuration management
├── services/           # Business logic services
└── utils/              # Utilities and helpers
```

### Adding New Features

#### 1. Creating a New Node

```python
# src/gateway/nodes/my_custom_node.py
from typing import Any, Dict
from ...utils.logging import get_structured_logger

class MyCustomNode:
    """Custom processing node for GraphFlow pipeline."""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.logger = get_structured_logger("my_custom_node")
        self.is_initialized = False
    
    async def initialize(self) -> None:
        """Initialize the node resources."""
        try:
            # Initialize resources
            self.logger.info("Initializing custom node")
            self.is_initialized = True
        except Exception as e:
            self.logger.error(f"Failed to initialize: {e}")
            raise
    
    async def process(self, input_data: Any) -> Any:
        """Process input through the node."""
        if not self.is_initialized:
            raise RuntimeError("Node not initialized")
        
        # Implement processing logic
        result = await self._do_processing(input_data)
        
        self.logger.info(
            "Processing completed",
            input_type=type(input_data).__name__,
            success=True
        )
        
        return result
    
    async def _do_processing(self, data: Any) -> Any:
        """Actual processing implementation."""
        # Your logic here
        pass
    
    async def shutdown(self) -> None:
        """Cleanup node resources."""
        self.logger.info("Shutting down custom node")
        self.is_initialized = False
```

#### 2. Adding a New Integration

```python
# src/integrations/my_system_interface.py
from typing import Dict, Any, Optional
import aiohttp
from ..utils.logging import get_structured_logger

class MySystemInterface:
    """Interface for integrating with external system."""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.endpoint = config.get("endpoint", "http://localhost:8000")
        self.logger = get_structured_logger("my_system_interface")
        self.session: Optional[aiohttp.ClientSession] = None
    
    async def initialize(self) -> None:
        """Initialize connection to external system."""
        self.session = aiohttp.ClientSession(
            timeout=aiohttp.ClientTimeout(total=30)
        )
        
        # Test connection
        try:
            async with self.session.get(f"{self.endpoint}/health") as resp:
                if resp.status != 200:
                    raise RuntimeError(f"System unhealthy: {resp.status}")
        except Exception as e:
            self.logger.error(f"Failed to connect: {e}")
            raise
    
    async def send_data(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Send data to external system."""
        if not self.session:
            raise RuntimeError("Interface not initialized")
        
        try:
            async with self.session.post(
                f"{self.endpoint}/api/process",
                json=data
            ) as resp:
                resp.raise_for_status()
                return await resp.json()
        except Exception as e:
            self.logger.error(f"Failed to send data: {e}")
            raise
    
    async def shutdown(self) -> None:
        """Close connections."""
        if self.session:
            await self.session.close()
```

#### 3. Extending the Decision Matrix

```python
# config/custom_rules.json
{
  "custom_rules": [
    {
      "name": "high_priority_user_interaction",
      "conditions": {
        "category": "USER_INTERACTION",
        "priority": "high",
        "metadata.vip_user": true
      },
      "decision": "AVATAR_AND_ANALYSIS",
      "confidence_boost": 0.2,
      "description": "VIP users get immediate avatar response"
    },
    {
      "name": "maintenance_mode",
      "conditions": {
        "system_state.maintenance_mode": true
      },
      "decision": "LOG_ONLY",
      "override": true,
      "description": "All stimuli logged during maintenance"
    }
  ]
}
```

### Code Style Guidelines

1. **Type Hints**: Always use type hints for function parameters and returns
2. **Docstrings**: Follow Google style docstrings
3. **Async/Await**: Use async/await for all I/O operations
4. **Error Handling**: Use structured logging for all errors
5. **Testing**: Maintain >90% test coverage

## Testing Guide

### Running Tests

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=src --cov-report=html

# Run specific test file
pytest tests/unit/test_categorizer_node.py

# Run with verbose output
pytest -v

# Run only unit tests
pytest tests/unit/

# Run only integration tests
pytest tests/integration/

# Run with specific markers
pytest -m "not slow"
```

### Test Structure

```
tests/
├── unit/              # Fast, isolated unit tests
├── integration/       # Tests with external dependencies
├── e2e/              # End-to-end system tests
├── fixtures/         # Shared test data
└── conftest.py       # Pytest configuration
```

### Writing Tests

#### Unit Test Example

```python
# tests/unit/test_categorizer_node.py
import pytest
from unittest.mock import Mock, AsyncMock
from src.gateway.nodes.categorizer_node import StimuliCategorizerNode
from src.models.stimuli import ExternalStimuli, Priority

@pytest.fixture
def categorizer_config():
    return {
        "use_llm": False,
        "confidence_threshold": 0.7,
        "fallback_category": "CONTEXTUAL_UPDATE",
        "cache_enabled": True
    }

@pytest.fixture
def categorizer_node(categorizer_config):
    return StimuliCategorizerNode(
        config=categorizer_config,
        llm_config={}
    )

@pytest.mark.asyncio
async def test_categorize_user_interaction(categorizer_node):
    """Test categorization of user interaction stimuli."""
    # Arrange
    stimuli = ExternalStimuli(
        content="Hello, how are you?",
        source="chat",
        priority=Priority.MEDIUM
    )
    
    # Act
    await categorizer_node.initialize()
    result = await categorizer_node.process(stimuli)
    
    # Assert
    assert result.category.value == "USER_INTERACTION"
    assert result.confidence >= 0.7
    assert result.classification_metadata["method"] == "keyword_matching"
```

#### Integration Test Example

```python
# tests/integration/test_gateway_integration.py
import pytest
from src.gateway.gateway_agent import create_gateway
from src.models.stimuli import ExternalStimuli, Priority

@pytest.mark.integration
@pytest.mark.asyncio
async def test_full_processing_pipeline():
    """Test complete stimuli processing pipeline."""
    # Create gateway
    gateway = await create_gateway()
    
    try:
        # Submit stimuli
        stimuli = ExternalStimuli(
            content="Important system alert",
            source="monitoring",
            priority=Priority.HIGH
        )
        
        result = await gateway.process_stimuli(stimuli)
        
        # Verify processing
        assert result.success
        assert result.decision is not None
        assert result.processing_time < 2.0
        assert len(result.execution_results) > 0
        
    finally:
        await gateway.stop()
```

### Test Fixtures

```python
# tests/conftest.py
import pytest
import asyncio
from typing import AsyncGenerator

@pytest.fixture
def event_loop():
    """Create event loop for async tests."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()

@pytest.fixture
async def redis_client():
    """Provide test Redis client."""
    import aioredis
    redis = await aioredis.create_redis_pool('redis://localhost:6379')
    yield redis
    redis.close()
    await redis.wait_closed()

@pytest.fixture
def mock_system1_interface():
    """Mock System1 interface for testing."""
    from unittest.mock import AsyncMock
    mock = AsyncMock()
    mock.trigger_avatar_response.return_value = {
        "success": True,
        "speech_id": "test-123"
    }
    return mock
```

## Debugging Tips

### Enable Debug Logging

```bash
# Set environment variable
export GRAPHFLOW_LOG_LEVEL=DEBUG
export GRAPHFLOW_DETAILED_LOGGING=true

# Or in development.env
GRAPHFLOW_LOG_LEVEL=DEBUG
GRAPHFLOW_DETAILED_LOGGING=true
```

### Using the Debug Mode

```python
# In your code
from src.utils.logging import get_structured_logger

logger = get_structured_logger("my_module")

# Debug level logging
logger.debug(
    "Processing started",
    stimuli_id=stimuli.id,
    metadata=stimuli.metadata
)

# Use structured logging for better debugging
logger.info(
    "Decision made",
    decision=decision.value,
    confidence=confidence,
    reasoning=reasoning,
    processing_time=elapsed_time
)
```

### Common Debugging Scenarios

#### 1. Stimuli Not Being Categorized Correctly

```python
# Enable categorizer debug mode
export GRAPHFLOW_CATEGORIZER_DEBUG=true

# Check categorizer logs
docker-compose logs -f graphflow-gateway | grep categorizer_node
```

#### 2. Integration Connection Issues

```python
# Test connections directly
curl http://neurosync:5001/health
curl http://autogen-agent:3100/health

# Check integration logs
docker-compose logs -f graphflow-gateway | grep interface
```

#### 3. Performance Issues

```python
# Enable performance profiling
export GRAPHFLOW_ENABLE_PROFILING=true

# Check metrics
curl http://localhost:8080/metrics | grep processing_time
```

### Using the Test Client

```bash
# Run interactive test client
python examples/test_analyzer_with_context_service.py

# Submit test stimuli
python -c "
import asyncio
from src.gateway.gateway_agent import create_gateway
from src.models.stimuli import ExternalStimuli, Priority

async def test():
    gateway = await create_gateway()
    stimuli = ExternalStimuli(
        content='Test message',
        source='debug',
        priority=Priority.HIGH
    )
    result = await gateway.process_stimuli(stimuli)
    print(f'Result: {result}')
    await gateway.stop()

asyncio.run(test())
"
```

### Monitoring Tools

1. **Grafana Dashboard**: http://localhost:3000
2. **Prometheus Metrics**: http://localhost:9090
3. **Redis Commander**: http://localhost:8081

## Code Structure

### Core Components

#### Gateway Agent
- **Location**: `src/gateway/gateway_agent.py`
- **Purpose**: Main orchestrator for the entire system
- **Key Methods**:
  - `process_stimuli()`: Main entry point
  - `health_check()`: System health monitoring
  - `get_metrics()`: Performance metrics

#### Processing Nodes

1. **Categorizer Node** (`src/gateway/nodes/categorizer_node.py`)
   - Classifies stimuli into predefined categories
   - Uses LLM and keyword matching
   - Implements caching for performance

2. **Analyzer Node** (`src/gateway/nodes/analyzer_node.py`)
   - Deep contextual analysis
   - Extracts entities and intent
   - Enriches with historical context

3. **Router Node** (`src/gateway/nodes/router_node.py`)
   - Applies decision matrix rules
   - Evaluates routing conditions
   - Generates execution decisions

4. **Executor Node** (`src/gateway/nodes/executor_node.py`)
   - Coordinates with external systems
   - Manages concurrent execution
   - Handles retry logic

### Data Models

```python
# Key models in src/models/

# stimuli.py
ExternalStimuli      # Input stimuli
CategorizedStimuli   # After categorization
AnalyzedStimuli      # After analysis
ProcessingResult     # Final result

# decisions.py
ProcessingDecision   # Decision enum
RoutingDecision     # Routing details
ExecutionResult     # Execution outcome
```

### Configuration System

```python
# src/config/settings.py
GraphFlowConfig      # Main configuration
CategorizerConfig    # Categorizer settings
RouterConfig         # Router settings
ExecutorConfig       # Executor settings

# Loading configuration
from src.config.settings import load_config
config = load_config()  # Loads from environment
```

## Contributing Guidelines

### Pull Request Process

1. **Fork and Branch**
   ```bash
   git checkout -b feature/your-feature-name
   ```

2. **Write Tests First**
   - Add unit tests for new functionality
   - Ensure integration tests pass
   - Maintain >90% coverage

3. **Update Documentation**
   - Update relevant .md files
   - Add docstrings to new functions
   - Update API documentation if needed

4. **Run Quality Checks**
   ```bash
   # Format code
   black src/ tests/
   
   # Sort imports
   isort src/ tests/
   
   # Type checking
   mypy src/
   
   # Linting
   flake8 src/ tests/
   
   # Run all tests
   pytest
   ```

5. **Submit PR**
   - Clear description of changes
   - Link to related issues
   - Include test results

### Code Review Checklist

- [ ] Tests pass and coverage maintained
- [ ] Documentation updated
- [ ] Type hints added
- [ ] Error handling implemented
- [ ] Logging added for debugging
- [ ] Performance impact considered
- [ ] Security implications reviewed
- [ ] Backwards compatibility maintained