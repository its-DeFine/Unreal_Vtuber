#!/bin/bash

# SCB End-to-End Test Runner
# This script runs comprehensive tests for the Shared Contextual Bridge functionality

echo "🚀 SCB End-to-End Test Runner"
echo "============================="
echo ""

# Check if services are running
echo "📋 Checking required services..."

# Function to check if a service is running
check_service() {
    local service_name=$1
    local port=$2
    
    if nc -z localhost $port 2>/dev/null; then
        echo "✅ $service_name is running on port $port"
    else
        echo "❌ $service_name is not running on port $port"
        echo "   Please ensure all services are running with: docker-compose -f docker-compose.all.yml up -d"
        exit 1
    fi
}

# Check all required services
check_service "S1 (NeuroSync)" 5001
check_service "S2 (AutoGen)" 8200
check_service "SCB Gateway" 8300
check_service "Redis" 6379

echo ""
echo "📦 Installing test dependencies..."
pip3 install redis requests pytest --quiet

echo ""
echo "🧪 Running SCB end-to-end tests..."
echo ""

# Run the test
python3 tests/test_scb_e2e.py

# Capture exit code
TEST_EXIT_CODE=$?

echo ""
echo "============================="

if [ $TEST_EXIT_CODE -eq 0 ]; then
    echo "✅ All tests completed successfully!"
else
    echo "❌ Some tests failed. Please check the logs above."
fi

exit $TEST_EXIT_CODE 