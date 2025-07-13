#!/bin/bash
# Orchestrator Integration Test Runner

echo "🧪 Running Orchestrator Integration Tests"
echo "========================================"

# Colors for output
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Check if orchestrator is running
echo -e "${YELLOW}Checking if orchestrator is accessible...${NC}"
if curl -s -f http://localhost:8082/health > /dev/null; then
    echo -e "${GREEN}✓ Orchestrator is running${NC}"
else
    echo -e "${RED}✗ Orchestrator is not accessible on port 8082${NC}"
    echo "Please ensure the orchestrator container is running:"
    echo "  docker-compose -f docker-compose.all.yml up orchestrator"
    exit 1
fi

# Install test dependencies if needed
if ! python -c "import pytest" 2>/dev/null; then
    echo -e "${YELLOW}Installing pytest...${NC}"
    pip install pytest pytest-asyncio httpx
fi

# Run different test suites
echo -e "\n${YELLOW}Running health checks...${NC}"
pytest test_orchestrator_integration.py::TestOrchestratorHealth -v

echo -e "\n${YELLOW}Running routing decision tests...${NC}"
pytest test_orchestrator_integration.py::TestRoutingDecisions -v

echo -e "\n${YELLOW}Running latency tests...${NC}"
pytest test_orchestrator_integration.py::TestLatencyRequirements -v

echo -e "\n${YELLOW}Running error handling tests...${NC}"
pytest test_orchestrator_integration.py::TestErrorHandling -v

echo -e "\n${YELLOW}Running metrics tests...${NC}"
pytest test_orchestrator_integration.py::TestMetrics -v

# Optional: Run performance tests
read -p "Run performance tests? (y/n) " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    echo -e "\n${YELLOW}Running performance tests...${NC}"
    pytest test_orchestrator_integration.py::TestPerformance -v -m performance
fi

echo -e "\n${GREEN}Test run complete!${NC}"