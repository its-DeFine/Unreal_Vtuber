#!/bin/bash

# 🔍 Autonomous Database Diagnostic Script
# Checks database connectivity, tables, and system readiness

set -e

echo "🔍 Autonomous Database Diagnostic Report"
echo "========================================"
echo ""

# Colors
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# Function to check status
check_status() {
    local service=$1
    local command=$2
    local expected=$3
    
    echo -n "🔍 Checking $service... "
    
    if eval "$command" >/dev/null 2>&1; then
        echo -e "${GREEN}✅ OK${NC}"
        return 0
    else
        echo -e "${RED}❌ FAILED${NC}"
        return 1
    fi
}

# Function to get info
get_info() {
    local label=$1
    local command=$2
    
    echo -n "📊 $label: "
    local result=$(eval "$command" 2>/dev/null || echo "N/A")
    echo -e "${BLUE}$result${NC}"
}

echo "## 🐳 Container Status"
echo "----------------------"

# Check containers
check_status "PostgreSQL Container" "docker ps --filter name=autonomous_postgres_bridge --format '{{.Status}}' | grep -q 'Up'"
check_status "Redis Container" "docker ps --filter name=redis_scb --format '{{.Status}}' | grep -q 'Up'"
check_status "NeuroSync Container" "docker ps --filter name=neurosync_byoc --format '{{.Status}}' | grep -q 'Up'"

echo ""
echo "## 🗄️ Database Connectivity"
echo "---------------------------"

# Check database connection
check_status "Database Connection" "docker exec autonomous_postgres_bridge psql -U postgres -d autonomous_agent -c 'SELECT 1;'"

if docker exec autonomous_postgres_bridge psql -U postgres -d autonomous_agent -c 'SELECT 1;' >/dev/null 2>&1; then
    echo ""
    echo "## 📊 Database Statistics"
    echo "-------------------------"
    
    get_info "Total Tables" "docker exec autonomous_postgres_bridge psql -U postgres -d autonomous_agent -t -c \"SELECT COUNT(*) FROM information_schema.tables WHERE table_schema='public';\""
    get_info "Total Memories" "docker exec autonomous_postgres_bridge psql -U postgres -d autonomous_agent -t -c \"SELECT COUNT(*) FROM memories;\""
    get_info "Total Archived" "docker exec autonomous_postgres_bridge psql -U postgres -d autonomous_agent -t -c \"SELECT COUNT(*) FROM context_archive;\""
    get_info "Total Agents" "docker exec autonomous_postgres_bridge psql -U postgres -d autonomous_agent -t -c \"SELECT COUNT(*) FROM agents;\""
    
    echo ""
    echo "## 📋 Analytics Tables"
    echo "----------------------"
    
    # Check analytics tables
    check_status "tool_usage table" "docker exec autonomous_postgres_bridge psql -U postgres -d autonomous_agent -c \"SELECT COUNT(*) FROM tool_usage;\""
    check_status "decision_patterns table" "docker exec autonomous_postgres_bridge psql -U postgres -d autonomous_agent -c \"SELECT COUNT(*) FROM decision_patterns;\""
    check_status "memory_lifecycle table" "docker exec autonomous_postgres_bridge psql -U postgres -d autonomous_agent -c \"SELECT COUNT(*) FROM memory_lifecycle;\""
    
    echo ""
    echo "## 🔧 System Configuration"
    echo "--------------------------"
    
    get_info "Database URL" "echo 'postgresql://postgres:postgres@localhost:5433/autonomous_agent'"
    get_info "VTuber Endpoint" "echo 'http://neurosync:5001/process_text'"
    get_info "SCB Redis" "echo 'redis://redis_scb:6379'"
    
else
    echo -e "${RED}❌ Cannot connect to database - skipping detailed checks${NC}"
fi

echo ""
echo "## 🌐 Network Connectivity"
echo "--------------------------"

# Check network connectivity
check_status "NeuroSync API" "curl -s http://localhost:5001/health"
check_status "SCB Redis" "docker exec redis_scb redis-cli ping"

echo ""
echo "## 🚀 Autonomous Agent Readiness"
echo "--------------------------------"

# Check if autonomous agent can start
if docker ps --filter name=autonomous_starter_s3 --format '{{.Status}}' | grep -q 'Up'; then
    echo -e "🤖 Autonomous Agent: ${GREEN}✅ RUNNING${NC}"
    get_info "Agent Status" "docker ps --filter name=autonomous_starter_s3 --format '{{.Status}}'"
else
    echo -e "🤖 Autonomous Agent: ${YELLOW}⚠️  NOT RUNNING${NC}"
    echo "   To start: docker-compose up autonomous_starter_s3 -d"
fi

echo ""
echo "## 📝 Recommendations"
echo "---------------------"

# Provide recommendations
if docker exec autonomous_postgres_bridge psql -U postgres -d autonomous_agent -c 'SELECT 1;' >/dev/null 2>&1; then
    echo -e "${GREEN}✅ Database is ready for autonomous agent operations${NC}"
    echo -e "${BLUE}💡 You can now run: ./monitor_autonomous_system_enhanced.sh${NC}"
else
    echo -e "${RED}❌ Database issues detected${NC}"
    echo -e "${YELLOW}💡 Try: docker-compose restart autonomous_postgres_bridge${NC}"
fi

# Check if monitoring can work
if command -v jq >/dev/null 2>&1; then
    echo -e "${GREEN}✅ jq is available for log parsing${NC}"
else
    echo -e "${YELLOW}⚠️  jq not found - install with: sudo apt-get install jq${NC}"
fi

echo ""
echo "## 🔍 Quick Memory Test"
echo "-----------------------"

if docker exec autonomous_postgres_bridge psql -U postgres -d autonomous_agent -c 'SELECT 1;' >/dev/null 2>&1; then
    echo "Recent memories:"
    docker exec autonomous_postgres_bridge psql -U postgres -d autonomous_agent -c "
        SELECT 
            LEFT(content->>'text', 50) as memory_text,
            type,
            \"createdAt\"
        FROM memories 
        ORDER BY \"createdAt\" DESC 
        LIMIT 3;
    " 2>/dev/null || echo "No memories found"
else
    echo "Cannot access memories - database connection failed"
fi

echo ""
echo "🎯 Diagnostic Complete!"
echo "=======================" 