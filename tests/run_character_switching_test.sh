#!/bin/bash
# Character Switching Test Runner
# Created: 2025-07-14

echo "🧪 Running Character Switching Tests"
echo "===================================="

# Colors for output
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Function to check service
check_service() {
    local service_name=$1
    local url=$2
    
    echo -n -e "${YELLOW}Checking ${service_name}...${NC} "
    
    if curl -s -f "$url" > /dev/null; then
        echo -e "${GREEN}✓ Running${NC}"
        return 0
    else
        echo -e "${RED}✗ Not accessible${NC}"
        return 1
    fi
}

# Check required services
echo -e "\n${BLUE}Pre-flight Checks:${NC}"
check_service "Orchestrator" "http://localhost:8082/health" || exit 1
check_service "System 1 (NeuroSync)" "http://localhost:5001/health" || exit 1

# Show current character
echo -e "\n${BLUE}Current S1 Character:${NC}"
current_char=$(curl -s http://localhost:5001/character/current | jq -r '.character.name // "Unknown"')
echo -e "Currently active: ${GREEN}${current_char}${NC}"

# Install test dependencies if needed
if ! python3 -c "import pytest" 2>/dev/null; then
    echo -e "\n${YELLOW}Installing test dependencies...${NC}"
    pip install pytest pytest-asyncio httpx
fi

# Run the tests
echo -e "\n${BLUE}Running Character Switching Tests:${NC}"
echo "This will test:"
echo "  - Character endpoints availability"
echo "  - Trader persona → Sophia Trader"
echo "  - Streamer persona → Luna Streamer"
echo "  - Educator persona → Diana Code"
echo "  - Rapid character switching"
echo "  - Character persistence"
echo ""

cd /home/geo/directories/autonomy/tests
python3 -m pytest test_orchestrator_character_switching.py -v -s

# Show final character state
echo -e "\n${BLUE}Final S1 Character State:${NC}"
final_char=$(curl -s http://localhost:5001/character/current | jq -r '.character.name // "Unknown"')
echo -e "Final character: ${GREEN}${final_char}${NC}"

echo -e "\n${GREEN}Test run complete!${NC}"