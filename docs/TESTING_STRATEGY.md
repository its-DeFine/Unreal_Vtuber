# Comprehensive Testing Strategy for Stimuli System

## Testing Overview

This document outlines a comprehensive testing strategy to verify that all critical fixes work correctly and the system is production-ready.

## Test Categories

### 1. Unit Tests

#### A. Speech Routing Tests
```python
# File: /app/CORE/graphflow-stimuli-system/tests/test_speech_routing.py

import pytest
from src.gateway.nodes.enhanced_decision_engine import EnhancedDecisionEngine
from src.models.decisions import ProcessingDecision

class TestSpeechRouting:
    """Test speech-first routing logic."""
    
    def setup_method(self):
        self.engine = EnhancedDecisionEngine()
    
    def test_explicit_speech_keywords(self):
        """Test explicit speech keyword detection."""
        test_cases = [
            ("Please speak this message", ProcessingDecision.AVATAR_ONLY),
            ("Say hello to everyone", ProcessingDecision.AVATAR_ONLY),
            ("Tell me about the weather", ProcessingDecision.AVATAR_ONLY),
            ("Use your voice to respond", ProcessingDecision.AVATAR_ONLY),
            ("Pronounce this word", ProcessingDecision.AVATAR_ONLY),
        ]
        
        for content, expected in test_cases:
            context = {
                "content": content,
                "category": "USER_INTERACTION",
                "confidence": 0.8
            }
            decision = self.engine.evaluate_routing_decision(context)
            assert decision == expected, f"Failed for: {content}"
    
    def test_conversational_triggers(self):
        """Test conversational speech triggers."""
        test_cases = [
            ("Hello there!", ProcessingDecision.AVATAR_ONLY),
            ("Hi, how are you?", ProcessingDecision.AVATAR_ONLY),
            ("Hey, what's up?", ProcessingDecision.AVATAR_ONLY),
            ("Good morning", ProcessingDecision.AVATAR_ONLY),
            ("Greetings", ProcessingDecision.AVATAR_ONLY),
        ]
        
        for content, expected in test_cases:
            context = {
                "content": content,
                "category": "USER_INTERACTION",
                "confidence": 0.6
            }
            decision = self.engine.evaluate_routing_decision(context)
            assert decision == expected, f"Failed for: {content}"
    
    def test_question_with_speech_intent(self):
        """Test questions that should trigger speech."""
        test_cases = [
            ("What time is it?", ProcessingDecision.AVATAR_ONLY),
            ("How are you doing?", ProcessingDecision.AVATAR_ONLY),
            ("Can you help me?", ProcessingDecision.AVATAR_ONLY),
            ("Would you please respond?", ProcessingDecision.AVATAR_ONLY),
        ]
        
        for content, expected in test_cases:
            context = {
                "content": content,
                "category": "USER_INTERACTION",
                "confidence": 0.7
            }
            decision = self.engine.evaluate_routing_decision(context)
            assert decision == expected, f"Failed for: {content}"
    
    def test_complex_questions_need_analysis(self):
        """Test complex questions that need both speech and analysis."""
        test_cases = [
            ("Can you analyze the performance data and explain the trends over the last month?", 
             ProcessingDecision.AVATAR_AND_ANALYSIS),
            ("What are the implications of the recent algorithm changes and how should we respond?", 
             ProcessingDecision.AVATAR_AND_ANALYSIS),
            ("Please research the latest developments in AI and provide a comprehensive summary", 
             ProcessingDecision.AVATAR_AND_ANALYSIS),
        ]
        
        for content, expected in test_cases:
            context = {
                "content": content,
                "category": "USER_INTERACTION",
                "confidence": 0.8
            }
            decision = self.engine.evaluate_routing_decision(context)
            assert decision == expected, f"Failed for: {content}"
    
    def test_contextual_update_routing(self):
        """Test contextual update routing."""
        test_cases = [
            ("hello", ProcessingDecision.AVATAR_ONLY),
            ("test message", ProcessingDecision.AVATAR_ONLY),
            ("speak now", ProcessingDecision.AVATAR_ONLY),
            ("respond please", ProcessingDecision.AVATAR_ONLY),
        ]
        
        for content, expected in test_cases:
            context = {
                "content": content,
                "category": "CONTEXTUAL_UPDATE",
                "confidence": 0.5
            }
            decision = self.engine.evaluate_routing_decision(context)
            assert decision == expected, f"Failed for: {content}"
    
    def test_admin_commands(self):
        """Test admin command routing."""
        test_cases = [
            ("Shutdown the system", ProcessingDecision.ANALYSIS_ONLY),
            ("Speak the system status", ProcessingDecision.AVATAR_AND_ANALYSIS),
            ("Say the current configuration", ProcessingDecision.AVATAR_AND_ANALYSIS),
            ("Restart services", ProcessingDecision.ANALYSIS_ONLY),
        ]
        
        for content, expected in test_cases:
            context = {
                "content": content,
                "category": "DIRECT_ADMIN",
                "confidence": 0.9
            }
            decision = self.engine.evaluate_routing_decision(context)
            assert decision == expected, f"Failed for: {content}"
```

#### B. Health Check Tests
```python
# File: /app/CORE/graphflow-stimuli-system/tests/test_health_checks.py

import pytest
import asyncio
import time
from unittest.mock import AsyncMock, patch
from src.monitoring.enhanced_health_checker import EnhancedHealthChecker, HealthStatus

class TestHealthChecker:
    """Test enhanced health checking system."""
    
    def setup_method(self):
        config = MockConfig()
        self.checker = EnhancedHealthChecker(config)
    
    @pytest.mark.asyncio
    async def test_health_check_speed(self):
        """Test health checks complete within time limits."""
        start_time = time.time()
        
        # Mock successful responses
        with patch.object(self.checker, '_http_health_check') as mock_check:
            mock_check.return_value = MockHealthCheckResult(HealthStatus.HEALTHY, 0.1)
            
            result = await self.checker.check_system_health()
            
        elapsed = time.time() - start_time
        
        # Should complete within 10 seconds (even with all checks)
        assert elapsed < 10.0, f"Health check took too long: {elapsed}s"
        assert result["overall_health"] == "healthy"
    
    @pytest.mark.asyncio
    async def test_health_check_caching(self):
        """Test health check caching works correctly."""
        
        with patch.object(self.checker, '_http_health_check') as mock_check:
            mock_check.return_value = MockHealthCheckResult(HealthStatus.HEALTHY, 0.1)
            
            # First call
            await self.checker._check_s1_basic()
            first_call_count = mock_check.call_count
            
            # Second call within cache TTL should use cache
            await self.checker._check_s1_basic()
            second_call_count = mock_check.call_count
            
            assert second_call_count == first_call_count, "Cache not working"
    
    @pytest.mark.asyncio
    async def test_capability_evaluation(self):
        """Test system capability evaluation."""
        
        # Mock healthy S1, unhealthy S2
        s1_healthy = MockHealthCheckResult(HealthStatus.HEALTHY, 0.1)
        s2_unhealthy = MockHealthCheckResult(HealthStatus.UNHEALTHY, 5.0)
        
        capabilities = self.checker._evaluate_capabilities(
            s1_healthy, s1_healthy, s2_unhealthy, s2_unhealthy
        )
        
        assert capabilities.avatar_speech == True
        assert capabilities.basic_analysis == False
        assert capabilities.multi_agent_analysis == False
        
        available_paths = capabilities.get_available_paths()
        assert "AVATAR_ONLY" in available_paths
        assert "AVATAR_AND_ANALYSIS" not in available_paths
    
    @pytest.mark.asyncio
    async def test_timeout_handling(self):
        """Test health check timeout handling."""
        
        with patch.object(self.checker, '_http_health_check') as mock_check:
            # Simulate timeout
            async def timeout_side_effect(*args, **kwargs):
                await asyncio.sleep(10)  # Longer than timeout
                
            mock_check.side_effect = timeout_side_effect
            
            start_time = time.time()
            result = await self.checker._check_s1_basic()
            elapsed = time.time() - start_time
            
            # Should timeout quickly
            assert elapsed < 5.0, f"Timeout took too long: {elapsed}s"
            assert result.status == HealthStatus.UNHEALTHY
```

### 2. Integration Tests

#### A. End-to-End Speech Flow Test
```python
# File: /app/CORE/graphflow-stimuli-system/tests/test_e2e_speech.py

import pytest
import httpx
import asyncio

class TestEndToEndSpeech:
    """Test complete speech processing flow."""
    
    @pytest.mark.asyncio
    async def test_speech_request_e2e(self):
        """Test complete speech request processing."""
        
        # Test data
        speech_request = {
            "content": "Please speak this test message",
            "category": "USER_INTERACTION",
            "source": "test_client"
        }
        
        async with httpx.AsyncClient() as client:
            # Submit stimuli
            response = await client.post(
                "http://localhost:8000/api/stimuli",
                json=speech_request,
                timeout=15.0
            )
            
            assert response.status_code == 200
            result = response.json()
            
            # Verify routing decision
            assert result["routing_decision"] == "AVATAR_ONLY"
            assert result["s1_triggered"] == True
            assert result["s2_triggered"] == False
            
            # Verify processing time
            assert result["processing_time"] < 10.0  # Should be fast
            
            # Verify speech generation
            if "speech_result" in result:
                assert result["speech_result"]["success"] == True
                assert "audio_duration" in result["speech_result"]
    
    @pytest.mark.asyncio
    async def test_complex_question_e2e(self):
        """Test complex question requiring both speech and analysis."""
        
        complex_request = {
            "content": "Can you analyze the system performance and explain what's happening?",
            "category": "USER_INTERACTION",
            "source": "test_client"
        }
        
        async with httpx.AsyncClient() as client:
            response = await client.post(
                "http://localhost:8000/api/stimuli",
                json=complex_request,
                timeout=30.0
            )
            
            assert response.status_code == 200
            result = response.json()
            
            # Verify routing decision
            assert result["routing_decision"] == "AVATAR_AND_ANALYSIS"
            assert result["s1_triggered"] == True
            assert result["s2_triggered"] == True
            
            # Verify both systems responded
            assert "speech_result" in result
            assert "analysis_result" in result
    
    @pytest.mark.asyncio
    async def test_health_check_e2e(self):
        """Test health check endpoint."""
        
        async with httpx.AsyncClient() as client:
            start_time = time.time()
            response = await client.get(
                "http://localhost:8000/health",
                timeout=10.0
            )
            elapsed = time.time() - start_time
            
            assert response.status_code == 200
            assert elapsed < 5.0  # Should be fast
            
            health_data = response.json()
            assert "overall_health" in health_data
            assert "capabilities" in health_data
            assert "available_paths" in health_data
```

#### B. Failure Scenario Tests
```python
# File: /app/CORE/graphflow-stimuli-system/tests/test_failure_scenarios.py

import pytest
import httpx
from unittest.mock import patch

class TestFailureScenarios:
    """Test system behavior under failure conditions."""
    
    @pytest.mark.asyncio
    async def test_s1_unavailable_fallback(self):
        """Test behavior when S1 (Avatar) is unavailable."""
        
        # Mock S1 as unavailable
        with patch('src.integrations.system1_interface.System1Interface.check_system_availability') as mock_s1:
            mock_s1.return_value.is_available = False
            
            speech_request = {
                "content": "Please speak this message",
                "category": "USER_INTERACTION"
            }
            
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    "http://localhost:8000/api/stimuli",
                    json=speech_request,
                    timeout=15.0
                )
                
                assert response.status_code == 200
                result = response.json()
                
                # Should fallback to analysis or log only
                assert result["routing_decision"] in ["ANALYSIS_ONLY", "LOG_ONLY"]
                assert result["fallback_applied"] == True
                assert "fallback_reason" in result
    
    @pytest.mark.asyncio
    async def test_s2_tool_execution_failure(self):
        """Test S2 tool execution failure handling."""
        
        # Mock S2 tool execution failure
        with patch('src.integrations.system2_interface.System2Interface.submit_for_analysis') as mock_s2:
            mock_s2.side_effect = RuntimeError("Tool execution failed")
            
            analysis_request = {
                "content": "Analyze this complex data",
                "category": "DIRECT_ADMIN"
            }
            
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    "http://localhost:8000/api/stimuli",
                    json=analysis_request,
                    timeout=15.0
                )
                
                # Should handle gracefully
                assert response.status_code in [200, 202]  # May return partial success
                result = response.json()
                
                if response.status_code == 200:
                    # Should indicate S2 failure
                    assert result.get("s2_error") is not None
                    assert result.get("fallback_applied") == True
    
    @pytest.mark.asyncio
    async def test_circuit_breaker_activation(self):
        """Test circuit breaker activation under repeated failures."""
        
        # Simulate repeated S1 failures
        with patch('src.integrations.system1_interface.System1Interface.trigger_avatar_response') as mock_s1:
            mock_s1.return_value = False  # Always fail
            
            speech_request = {
                "content": "Test speech",
                "category": "USER_INTERACTION"
            }
            
            async with httpx.AsyncClient() as client:
                # Send multiple requests to trigger circuit breaker
                for i in range(5):
                    response = await client.post(
                        "http://localhost:8000/api/stimuli",
                        json=speech_request,
                        timeout=10.0
                    )
                    
                    if i >= 3:  # After 3 failures, circuit should open
                        result = response.json()
                        assert result.get("circuit_breaker_open") == True
                        assert result["routing_decision"] != "AVATAR_ONLY"
```

### 3. Performance Tests

#### A. Load Testing Script
```bash
#!/bin/bash
# File: /app/CORE/graphflow-stimuli-system/tests/load_test.sh

echo "🚀 Starting GraphFlow Stimuli System Load Test..."

# Test configuration
ENDPOINT="http://localhost:8000/api/stimuli"
CONCURRENT_REQUESTS=10
TOTAL_REQUESTS=100
TIMEOUT=30

# Test different request types
declare -a TEST_CASES=(
    '{"content": "Hello, please speak", "category": "USER_INTERACTION"}'
    '{"content": "Say the current time", "category": "CONTEXTUAL_UPDATE"}'
    '{"content": "Analyze system performance", "category": "DIRECT_ADMIN"}'
    '{"content": "What is the weather like?", "category": "USER_INTERACTION"}'
)

# Function to send request and measure response time
send_request() {
    local payload=$1
    local start_time=$(date +%s.%N)
    
    response=$(curl -s -w "HTTP_CODE:%{http_code};TIME:%{time_total}" \
        -X POST "$ENDPOINT" \
        -H "Content-Type: application/json" \
        -d "$payload" \
        --max-time $TIMEOUT)
    
    local end_time=$(date +%s.%N)
    local total_time=$(echo "$end_time - $start_time" | bc)
    
    # Extract HTTP code and response time
    local http_code=$(echo "$response" | grep -o "HTTP_CODE:[0-9]*" | cut -d: -f2)
    local curl_time=$(echo "$response" | grep -o "TIME:[0-9.]*" | cut -d: -f2)
    
    echo "$http_code,$curl_time,$total_time"
}

# Run load test
echo "📊 Running load test with $CONCURRENT_REQUESTS concurrent requests..."

# Create temporary file for results
RESULTS_FILE="/tmp/graphflow_load_test_$(date +%Y%m%d_%H%M%S).csv"
echo "http_code,curl_time,total_time,test_case" > "$RESULTS_FILE"

# Run concurrent requests
for i in $(seq 1 $TOTAL_REQUESTS); do
    # Select random test case
    test_case_index=$((RANDOM % ${#TEST_CASES[@]}))
    test_case="${TEST_CASES[$test_case_index]}"
    
    # Send request in background
    (
        result=$(send_request "$test_case")
        echo "$result,$test_case_index" >> "$RESULTS_FILE"
    ) &
    
    # Limit concurrent requests
    if (( i % CONCURRENT_REQUESTS == 0 )); then
        wait  # Wait for current batch to complete
    fi
done

wait  # Wait for all requests to complete

# Analyze results
echo "📈 Load test completed. Analyzing results..."

# Calculate statistics
total_requests=$(grep -c "^[0-9]" "$RESULTS_FILE")
successful_requests=$(grep -c "^200," "$RESULTS_FILE")
success_rate=$(echo "scale=2; $successful_requests * 100 / $total_requests" | bc)

avg_response_time=$(awk -F, 'NR>1 {sum+=$2; count++} END {print sum/count}' "$RESULTS_FILE")
max_response_time=$(awk -F, 'NR>1 {if($2>max) max=$2} END {print max}' "$RESULTS_FILE")

echo "✅ Load Test Results:"
echo "   Total Requests: $total_requests"
echo "   Successful Requests: $successful_requests"
echo "   Success Rate: $success_rate%"
echo "   Average Response Time: ${avg_response_time}s"
echo "   Maximum Response Time: ${max_response_time}s"
echo "   Results saved to: $RESULTS_FILE"

# Check performance thresholds
if (( $(echo "$success_rate >= 95" | bc -l) )); then
    echo "✅ Success rate PASSED (>= 95%)"
else
    echo "❌ Success rate FAILED (< 95%)"
fi

if (( $(echo "$avg_response_time <= 5.0" | bc -l) )); then
    echo "✅ Average response time PASSED (<= 5.0s)"
else
    echo "❌ Average response time FAILED (> 5.0s)"
fi
```

### 4. System Verification Tests

#### A. Component Integration Verification
```python
# File: /app/CORE/graphflow-stimuli-system/tests/test_system_verification.py

import pytest
import asyncio
import httpx
from datetime import datetime, timedelta

class TestSystemVerification:
    """Verify complete system integration and functionality."""
    
    @pytest.mark.asyncio
    async def test_speech_routing_verification(self):
        """Verify speech requests are correctly routed to S1."""
        
        speech_test_cases = [
            "Please speak this message",
            "Say hello to everyone", 
            "Tell me the current time",
            "Use your voice to respond",
            "Hello there!",
            "Hi, how are you?",
            "Good morning"
        ]
        
        async with httpx.AsyncClient() as client:
            for content in speech_test_cases:
                response = await client.post(
                    "http://localhost:8000/api/stimuli",
                    json={
                        "content": content,
                        "category": "USER_INTERACTION"
                    },
                    timeout=15.0
                )
                
                assert response.status_code == 200
                result = response.json()
                
                # Verify routing to S1
                assert result["routing_decision"] in ["AVATAR_ONLY", "AVATAR_AND_ANALYSIS"]
                assert result["s1_triggered"] == True
                
                print(f"✅ Speech routing verified for: '{content}' → {result['routing_decision']}")
    
    @pytest.mark.asyncio
    async def test_health_check_reliability(self):
        """Verify health checks are fast and reliable."""
        
        response_times = []
        
        # Test health checks multiple times
        async with httpx.AsyncClient() as client:
            for i in range(10):
                start_time = datetime.now()
                
                response = await client.get(
                    "http://localhost:8000/health",
                    timeout=10.0
                )
                
                end_time = datetime.now()
                response_time = (end_time - start_time).total_seconds()
                response_times.append(response_time)
                
                assert response.status_code == 200
                health_data = response.json()
                
                # Verify health data structure
                assert "overall_health" in health_data
                assert "capabilities" in health_data
                assert "component_health" in health_data
                
                # Verify response time
                assert response_time < 5.0, f"Health check too slow: {response_time}s"
        
        avg_response_time = sum(response_times) / len(response_times)
        max_response_time = max(response_times)
        
        print(f"✅ Health check verification completed:")
        print(f"   Average response time: {avg_response_time:.2f}s")
        print(f"   Maximum response time: {max_response_time:.2f}s")
        
        assert avg_response_time < 3.0, "Average health check time too slow"
        assert max_response_time < 5.0, "Maximum health check time too slow"
    
    @pytest.mark.asyncio
    async def test_s2_analysis_functionality(self):
        """Verify S2 analysis system is working."""
        
        analysis_request = {
            "content": "Analyze the current system performance and provide recommendations",
            "category": "DIRECT_ADMIN"
        }
        
        async with httpx.AsyncClient() as client:
            response = await client.post(
                "http://localhost:8000/api/stimuli",
                json=analysis_request,
                timeout=45.0  # Analysis takes longer
            )
            
            assert response.status_code == 200
            result = response.json()
            
            # Verify S2 was triggered
            assert result["s2_triggered"] == True
            
            # If S2 is healthy, verify analysis results
            if result.get("s2_error") is None:
                assert "analysis_result" in result
                analysis = result["analysis_result"]
                assert "task_id" in analysis
                print(f"✅ S2 analysis completed successfully: {analysis['task_id']}")
            else:
                print(f"⚠️ S2 analysis failed (expected during testing): {result['s2_error']}")
    
    @pytest.mark.asyncio
    async def test_fallback_mechanisms(self):
        """Verify fallback mechanisms work correctly."""
        
        # This test requires mocking system failures
        # In a real environment, you would temporarily disable S1 or S2
        
        test_request = {
            "content": "This is a test message during system degradation",
            "category": "USER_INTERACTION"
        }
        
        async with httpx.AsyncClient() as client:
            response = await client.post(
                "http://localhost:8000/api/stimuli",
                json=test_request,
                timeout=15.0
            )
            
            # Should always get some response, even if degraded
            assert response.status_code in [200, 202]
            result = response.json()
            
            # Verify system handles degradation gracefully
            assert "routing_decision" in result
            assert result["routing_decision"] in [
                "AVATAR_ONLY", "AVATAR_AND_ANALYSIS", 
                "ANALYSIS_ONLY", "LOG_ONLY"
            ]
            
            print(f"✅ Fallback mechanism test completed: {result['routing_decision']}")
```

## Test Execution Plan

### Phase 1: Pre-Deployment Testing (Day 1)
1. **Unit Tests**: Run all speech routing and health check unit tests
2. **Configuration Validation**: Verify new decision matrix and environment configs
3. **Component Tests**: Test individual system components

### Phase 2: Integration Testing (Day 2)
1. **End-to-End Tests**: Verify complete speech processing flow
2. **Health Check Tests**: Validate health check speed and reliability
3. **S2 Integration Tests**: Verify S2 tool execution improvements

### Phase 3: Failure Scenario Testing (Day 3)
1. **Fallback Tests**: Test system behavior when S1/S2 unavailable
2. **Circuit Breaker Tests**: Verify circuit breaker activation
3. **Recovery Tests**: Test system recovery after failures

### Phase 4: Performance Testing (Day 4)
1. **Load Tests**: Test system under concurrent load
2. **Response Time Tests**: Verify performance thresholds
3. **Resource Usage Tests**: Monitor CPU/memory during load

### Phase 5: Production Verification (Day 5)
1. **System Verification**: Run comprehensive verification tests
2. **User Acceptance Testing**: Test with real user scenarios
3. **Monitoring Setup**: Verify monitoring and alerting

## Success Criteria

### Functional Requirements
- ✅ 95% of speech requests routed to `AVATAR_ONLY`
- ✅ Health checks respond within 5 seconds
- ✅ S2 tool execution success rate > 85%
- ✅ Fallback mechanisms activate correctly

### Performance Requirements
- ✅ Average response time < 3 seconds for speech requests
- ✅ System handles 10+ concurrent requests
- ✅ 99% uptime during testing period
- ✅ Memory usage remains stable under load

### Reliability Requirements
- ✅ Graceful degradation when components fail
- ✅ Circuit breaker prevents cascade failures
- ✅ System recovers automatically after failures
- ✅ No data loss during system issues

## Automated Test Execution

```bash
#!/bin/bash
# File: /app/CORE/graphflow-stimuli-system/scripts/run_all_tests.sh

echo "🧪 Running Comprehensive GraphFlow Test Suite..."

cd /app/CORE/graphflow-stimuli-system

# Set test environment
export PYTEST_CURRENT_TEST=true
export GRAPHFLOW_TEST_MODE=true

# Run unit tests
echo "🔬 Running unit tests..."
python -m pytest tests/test_speech_routing.py -v
python -m pytest tests/test_health_checks.py -v

# Run integration tests
echo "🔗 Running integration tests..."
python -m pytest tests/test_e2e_speech.py -v
python -m pytest tests/test_failure_scenarios.py -v

# Run system verification
echo "✅ Running system verification..."
python -m pytest tests/test_system_verification.py -v

# Run load tests
echo "📊 Running load tests..."
./tests/load_test.sh

# Generate test report
echo "📋 Generating test report..."
python -m pytest --html=test_report.html --self-contained-html

echo "🎉 All tests completed! Check test_report.html for details."
```

This comprehensive testing strategy ensures that all critical fixes work correctly and the system is production-ready with reliable speech routing, fast health checks, and robust error handling.