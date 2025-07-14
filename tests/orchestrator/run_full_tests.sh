#!/bin/bash
# Full Orchestrator Execution Test Runner

echo "🧪 Running Full Orchestrator Execution Tests"
echo "==========================================="

# Colors for output
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Function to check service health
check_service() {
    local service_name=$1
    local url=$2
    local expected_response=$3
    
    echo -n -e "${YELLOW}Checking ${service_name}...${NC} "
    
    if curl -s -f "$url" > /dev/null; then
        echo -e "${GREEN}✓ Running${NC}"
        return 0
    else
        echo -e "${RED}✗ Not accessible${NC}"
        return 1
    fi
}

# Check all required services
echo -e "\n${BLUE}=== Service Health Checks ===${NC}"
check_service "Orchestrator" "http://localhost:8082/health" || exit 1
check_service "System 1 (NeuroSync)" "http://localhost:5001/health" || true
check_service "System 2 (AutoGen)" "http://localhost:8200/health" || true

# Check if services are properly connected
echo -e "\n${BLUE}=== Connectivity Check ===${NC}"
echo -e "${YELLOW}Checking orchestrator's view of services...${NC}"
curl -s http://localhost:8082/health | python3 -m json.tool

# Install test dependencies if needed
if ! python3 -c "import pytest" 2>/dev/null; then
    echo -e "\n${YELLOW}Installing test dependencies...${NC}"
    pip install pytest pytest-asyncio httpx
fi

# Run the full execution tests
echo -e "\n${BLUE}=== Running Full Execution Tests ===${NC}"
echo -e "${YELLOW}These tests will actually send stimuli through the orchestrator to both systems${NC}\n"

# Run system health tests first
echo -e "${YELLOW}1. System Health Tests${NC}"
python3 -m pytest test_full_execution.py::TestFullExecution::test_system_health_before_execution -v -s

# Run individual system execution tests
echo -e "\n${YELLOW}2. S1 Execution Tests${NC}"
python3 -m pytest test_full_execution.py::TestFullExecution::test_s1_full_execution -v -s

echo -e "\n${YELLOW}3. S2 Execution Tests${NC}"
python3 -m pytest test_full_execution.py::TestFullExecution::test_s2_full_execution -v -s

# Run hybrid execution tests
echo -e "\n${YELLOW}4. Hybrid Execution Tests${NC}"
python3 -m pytest test_full_execution.py::TestFullExecution::test_hybrid_execution -v -s

# Run routing-specific tests
echo -e "\n${YELLOW}5. Routing Logic Tests${NC}"
python3 -m pytest test_full_execution.py::TestSystemSpecificRouting -v -s

# Run performance tests
echo -e "\n${YELLOW}6. Performance Tests${NC}"
python3 -m pytest test_full_execution.py::TestFullExecution::test_execution_latency -v -s
python3 -m pytest test_full_execution.py::TestFullExecution::test_concurrent_executions -v -s

# Run error handling tests
echo -e "\n${YELLOW}7. Error Handling Tests${NC}"
python3 -m pytest test_full_execution.py::TestErrorRecovery -v -s

# Summary
echo -e "\n${BLUE}=== Test Summary ===${NC}"
echo -e "${GREEN}✓ Full execution tests completed${NC}"
echo -e "${YELLOW}Note: Check the output above for any failures or issues${NC}"

# Optional: Run all tests at once
read -p "Run all tests together? (y/n) " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    echo -e "\n${YELLOW}Running all tests...${NC}"
    python3 -m pytest test_full_execution.py -v --tb=short
fi

echo -e "\n${GREEN}Test run complete!${NC}"