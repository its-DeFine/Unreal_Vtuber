# Container Launch and Testing Guide

This guide explains how to launch the GraphFlow External Stimuli System container and run tests both manually and automatically.

## Table of Contents
- [Prerequisites](#prerequisites)
- [Container Launch](#container-launch)
- [Manual Testing](#manual-testing)
- [Automated Testing](#automated-testing)
- [CI/CD Integration](#cicd-integration)
- [Troubleshooting](#troubleshooting)

## Prerequisites

1. **Docker** (version 20.10 or higher)
2. **Docker Compose** (version 2.0 or higher)
3. **Python 3.10+** (for local development)
4. **Make** (optional, for convenience commands)

## Container Launch

### Quick Start

```bash
# From the project root directory
cd /path/to/graphflow-stimuli-system

# Launch in development mode (with auto-reload)
docker-compose -f docker-compose.yml -f docker/docker-compose.dev.yml up

# Launch in production mode
docker-compose up -d

# View logs
docker-compose logs -f graphflow-gateway
```

### Different Launch Modes

#### 1. Development Mode (with hot-reload)
```bash
# Uses mounted volumes for code changes
docker-compose -f docker-compose.yml -f docker/docker-compose.dev.yml up

# Or use the run script
./run.py docker-dev
```

#### 2. Production Mode
```bash
# Build and run production containers
docker-compose up -d --build

# Or use the run script
./run.py docker
```

#### 3. Test Mode
```bash
# Run with test configuration
docker-compose -f docker-compose.yml -f docker/docker-compose.test.yml up

# Or use the run script
./run.py docker-test
```

### Environment Configuration

Create a `.env` file in the project root:

```bash
# Copy from example
cp config/development.env.example .env

# Edit with your settings
vim .env
```

Key environment variables:
```bash
# Service Configuration
GRAPHFLOW_ENV=development
GRAPHFLOW_LOG_LEVEL=INFO
GRAPHFLOW_MAX_CONCURRENT_STIMULI=50

# LLM Configuration
GRAPHFLOW_LLM_PROVIDER=ollama
GRAPHFLOW_LLM_MODEL=llama3.2:3b
GRAPHFLOW_LLM_ENDPOINT=http://ollama:11434

# Integration Endpoints
SYSTEM1_VTUBER_ENDPOINT=http://neurosync:5001
SYSTEM2_AUTOGEN_ENDPOINT=http://autogen-agent:3100

# Database Configuration
REDIS_URL=redis://redis:6379
POSTGRES_URL=postgresql://postgres:password@postgres:5432/graphflow
```

## Manual Testing

### 1. Access Container Shell

```bash
# Get container ID
docker ps | grep graphflow-gateway

# Access container shell
docker exec -it <container_id> /bin/bash

# Or use container name
docker exec -it graphflow-gateway /bin/bash
```

### 2. Run Tests Inside Container

Once inside the container:

```bash
# Run all tests
python -m pytest

# Run specific test categories
python -m pytest tests/unit/
python -m pytest tests/integration/
python -m pytest tests/e2e/

# Run tests for specific node
python -m pytest tests/unit/test_categorizer_node.py

# Run with coverage
python -m pytest --cov=src --cov-report=html

# Run with verbose output
python -m pytest -v -s

# Run specific test function
python -m pytest tests/unit/test_router_node.py::test_decision_routing -v
```

### 3. Test API Endpoints Manually

From inside the container:

```bash
# Test health endpoint
curl http://localhost:8080/health

# Submit test stimuli
curl -X POST http://localhost:8080/api/v1/stimuli/submit \
  -H "Authorization: Bearer dev-key-123" \
  -H "Content-Type: application/json" \
  -d '{
    "content": "Hello, how are you?",
    "source": "user_chat",
    "priority": "medium"
  }'

# Check status
curl http://localhost:8080/api/v1/status \
  -H "Authorization: Bearer dev-key-123"

# Test WebSocket connection
python -c "
import asyncio
import websockets
import json

async def test():
    uri = 'ws://localhost:8080/ws/stimuli?token=dev-key-123'
    async with websockets.connect(uri) as ws:
        # Send test message
        await ws.send(json.dumps({
            'type': 'submit_stimuli',
            'data': {
                'content': 'Test WebSocket message',
                'source': 'test_client'
            }
        }))
        # Receive response
        response = await ws.recv()
        print(f'Received: {response}')

asyncio.run(test())
"
```

### 4. Performance Testing

```bash
# Inside container
# Install locust for load testing
pip install locust

# Create locustfile.py
cat > locustfile.py << 'EOF'
from locust import HttpUser, task, between

class StimuliUser(HttpUser):
    wait_time = between(1, 3)
    
    def on_start(self):
        self.headers = {
            "Authorization": "Bearer dev-key-123",
            "Content-Type": "application/json"
        }
    
    @task
    def submit_stimuli(self):
        self.client.post(
            "/api/v1/stimuli/submit",
            json={
                "content": "Test stimuli from load test",
                "source": "load_test",
                "priority": "medium"
            },
            headers=self.headers
        )
    
    @task
    def check_status(self):
        self.client.get("/api/v1/status", headers=self.headers)
EOF

# Run load test
locust -H http://localhost:8080 --headless -u 10 -r 2 -t 30s
```

## Automated Testing

### 1. Using Docker Compose Test Configuration

```bash
# Run automated tests in container
docker-compose -f docker-compose.yml -f docker/docker-compose.test.yml run --rm test

# This will:
# - Build test container
# - Run all tests
# - Generate coverage report
# - Exit with appropriate code
```

### 2. Using the Test Runner Script

From outside the container:

```bash
# Run all tests
./run_tests.py test

# Run specific test types
./run_tests.py test --type unit
./run_tests.py test --type integration
./run_tests.py test --type e2e

# Run tests for specific node
./run_tests.py node --node categorizer

# Run all checks (tests, linting, type checking)
./run_tests.py all

# Run tests in parallel
./run_tests.py test --parallel
```

### 3. Continuous Testing with Watch Mode

```bash
# Inside container
# Install pytest-watch
pip install pytest-watch

# Run tests in watch mode
ptw -- -x tests/unit/

# Or use nodemon for broader file watching
npm install -g nodemon
nodemon --exec "python -m pytest tests/unit/" --ext py
```

### 4. Test Report Generation

```bash
# Inside container
# Generate HTML coverage report
python -m pytest --cov=src --cov-report=html

# Generate XML report for CI
python -m pytest --cov=src --cov-report=xml --junitxml=test-results.xml

# Generate multiple formats
python -m pytest --cov=src --cov-report=html --cov-report=xml --cov-report=term
```

## CI/CD Integration

### GitHub Actions Example

Create `.github/workflows/test.yml`:

```yaml
name: Test GraphFlow System

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    
    steps:
    - uses: actions/checkout@v3
    
    - name: Build test container
      run: |
        docker-compose -f docker-compose.yml \
          -f docker/docker-compose.test.yml \
          build test
    
    - name: Run tests
      run: |
        docker-compose -f docker-compose.yml \
          -f docker/docker-compose.test.yml \
          run --rm test
    
    - name: Upload coverage
      uses: actions/upload-artifact@v3
      with:
        name: coverage-report
        path: htmlcov/
```

### GitLab CI Example

Create `.gitlab-ci.yml`:

```yaml
stages:
  - test
  - build
  - deploy

test:
  stage: test
  image: docker/compose:latest
  services:
    - docker:dind
  script:
    - docker-compose -f docker-compose.yml -f docker/docker-compose.test.yml build test
    - docker-compose -f docker-compose.yml -f docker/docker-compose.test.yml run --rm test
  artifacts:
    reports:
      junit: test-results.xml
      coverage_report:
        coverage_format: cobertura
        path: coverage.xml
```

### Jenkins Pipeline Example

Create `Jenkinsfile`:

```groovy
pipeline {
    agent any
    
    stages {
        stage('Build') {
            steps {
                sh 'docker-compose build'
            }
        }
        
        stage('Test') {
            steps {
                sh '''
                    docker-compose -f docker-compose.yml \
                      -f docker/docker-compose.test.yml \
                      run --rm test
                '''
            }
            post {
                always {
                    junit 'test-results.xml'
                    publishHTML([
                        allowMissing: false,
                        alwaysLinkToLastBuild: true,
                        keepAll: true,
                        reportDir: 'htmlcov',
                        reportFiles: 'index.html',
                        reportName: 'Coverage Report'
                    ])
                }
            }
        }
    }
}
```

## Testing Best Practices

### 1. Test Data Management

```bash
# Create test fixtures
mkdir -p tests/fixtures

# Create sample stimuli
cat > tests/fixtures/sample_stimuli.json << 'EOF'
[
  {
    "content": "Set avatar hair color to blue",
    "source": "admin_console",
    "priority": "high"
  },
  {
    "content": "Hello, how are you?",
    "source": "user_chat",
    "priority": "medium"
  }
]
EOF
```

### 2. Mock External Services

```python
# tests/conftest.py
import pytest
from unittest.mock import Mock, AsyncMock

@pytest.fixture
def mock_system1():
    """Mock System1 interface for testing."""
    mock = Mock()
    mock.trigger_avatar_response = AsyncMock(return_value=True)
    mock.check_system_availability = AsyncMock(return_value={"available": True})
    return mock

@pytest.fixture
def mock_system2():
    """Mock System2 interface for testing."""
    mock = Mock()
    mock.submit_for_analysis = AsyncMock(return_value="task-123")
    mock.get_agent_status = AsyncMock(return_value={})
    return mock
```

### 3. Integration Test Setup

```bash
# Start only required services for integration tests
docker-compose up -d redis postgres

# Run integration tests
docker-compose run --rm graphflow-gateway python -m pytest tests/integration/

# Cleanup
docker-compose down
```

## Troubleshooting

### Common Issues and Solutions

#### 1. Container Won't Start
```bash
# Check logs
docker-compose logs graphflow-gateway

# Check if ports are in use
lsof -i :8080

# Reset everything
docker-compose down -v
docker-compose up --build
```

#### 2. Tests Failing Due to Missing Dependencies
```bash
# Inside container
pip install -r requirements.txt
pip install -e .
```

#### 3. Database Connection Issues
```bash
# Check if database is running
docker-compose ps postgres

# Check database logs
docker-compose logs postgres

# Reset database
docker-compose down -v
docker-compose up -d postgres
docker-compose run --rm graphflow-gateway python -c "
from src.services.context_service import ContextService
service = ContextService()
service.initialize_database()
"
```

#### 4. Memory Issues During Testing
```bash
# Increase Docker memory limit
# Edit Docker Desktop settings or:
docker run --memory="4g" --memory-swap="4g" ...

# Run tests in smaller batches
python -m pytest tests/unit/ -k "not integration"
python -m pytest tests/integration/ --maxfail=1
```

### Debug Mode

```bash
# Run container with debug logging
docker-compose run -e GRAPHFLOW_LOG_LEVEL=DEBUG graphflow-gateway

# Attach debugger
docker-compose run --service-ports graphflow-gateway python -m pdb src/main.py

# Use VS Code remote debugging
# Add to launch.json:
{
    "name": "Docker: Python",
    "type": "python",
    "request": "attach",
    "port": 5678,
    "host": "localhost",
    "pathMappings": [
        {
            "localRoot": "${workspaceFolder}",
            "remoteRoot": "/app"
        }
    ]
}
```

## Performance Monitoring During Tests

```bash
# Monitor container resources
docker stats graphflow-gateway

# Profile specific tests
python -m cProfile -o profile.stats -m pytest tests/unit/test_gateway_agent.py

# Analyze profile
python -c "
import pstats
stats = pstats.Stats('profile.stats')
stats.sort_stats('cumulative')
stats.print_stats(20)
"
```

## Summary

This guide covers:
- ✅ Multiple ways to launch containers (dev, prod, test)
- ✅ Manual testing inside containers
- ✅ Automated testing with various tools
- ✅ CI/CD integration examples
- ✅ Debugging and troubleshooting
- ✅ Performance testing approaches

The GraphFlow system is designed to be easily testable in containerized environments with comprehensive test coverage and multiple testing strategies.