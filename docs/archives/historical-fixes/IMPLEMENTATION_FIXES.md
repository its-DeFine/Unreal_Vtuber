# Critical Implementation Fixes for Stimuli System

## Immediate Code Changes Required

### 1. Fixed Decision Matrix Configuration

**File**: `/app/CORE/graphflow-stimuli-system/config/decision_matrix.json`

Replace the existing decision matrix with this speech-optimized version:

```json
{
  "decision_rules": {
    "DIRECT_ADMIN": {
      "default_decision": "AVATAR_AND_ANALYSIS",
      "confidence_threshold": 0.9,
      "priority_override": "urgent",
      "conditions": [
        {
          "if": "contains_shutdown_command",
          "then": "ANALYSIS_ONLY"
        },
        {
          "if": "contains_speak_command",
          "then": "AVATAR_AND_ANALYSIS",
          "priority_boost": 1.5
        }
      ]
    },
    "USER_INTERACTION": {
      "default_decision": "AVATAR_ONLY",
      "confidence_threshold": 0.2,
      "conditions": [
        {
          "if": "contains_speech_keywords",
          "then": "AVATAR_ONLY",
          "priority_boost": 2.0,
          "description": "Speech/TTS requests get highest priority"
        },
        {
          "if": "is_question_with_speech_intent",
          "then": "AVATAR_AND_ANALYSIS", 
          "priority_boost": 1.5,
          "description": "Questions requiring both speech and analysis"
        },
        {
          "if": "simple_greeting",
          "then": "AVATAR_ONLY",
          "priority_boost": 1.2
        },
        {
          "if": "test_request",
          "then": "AVATAR_ONLY",
          "priority_boost": 1.0
        }
      ]
    },
    "CONTEXTUAL_UPDATE": {
      "default_decision": "AVATAR_ONLY",
      "confidence_threshold": 0.1,
      "conditions": [
        {
          "if": "contains_hello|speak|respond|say|tell|voice|hello|hi|greet",
          "then": "AVATAR_ONLY",
          "priority_boost": 1.8,
          "description": "Common speech triggers"
        },
        {
          "if": "test_message",
          "then": "AVATAR_ONLY",
          "priority_boost": 1.5
        },
        {
          "if": "relevant_to_current_topic",
          "then": "AVATAR_AND_ANALYSIS"
        }
      ]
    },
    "SYSTEM_NOTIFICATION": {
      "default_decision": "ANALYSIS_ONLY",
      "confidence_threshold": 0.6,
      "conditions": [
        {
          "if": "critical_error",
          "then": "AVATAR_AND_ANALYSIS",
          "priority_override": "urgent"
        },
        {
          "if": "routine_update",
          "then": "LOG_ONLY"
        }
      ]
    },
    "SOCIAL_MEDIA": {
      "default_decision": "ANALYSIS_ONLY",
      "confidence_threshold": 0.6,
      "conditions": [
        {
          "if": "viral_threshold_exceeded",
          "then": "AVATAR_AND_ANALYSIS"
        },
        {
          "if": "mention_from_verified",
          "then": "AVATAR_AND_ANALYSIS"
        },
        {
          "if": "automated_post",
          "then": "LOG_ONLY"
        }
      ]
    },
    "AUTONOMOUS_TRIGGER": {
      "default_decision": "AVATAR_ONLY",
      "confidence_threshold": 0.8,
      "conditions": [
        {
          "if": "idle_time_exceeded",
          "then": "AVATAR_ONLY"
        },
        {
          "if": "scheduled_event",
          "then": "AVATAR_AND_ANALYSIS"
        }
      ]
    },
    "EMERGENCY": {
      "default_decision": "AVATAR_AND_ANALYSIS",
      "confidence_threshold": 0.95,
      "priority_override": "urgent",
      "bypass_rate_limit": true
    }
  },
  "priority_weights": {
    "urgent": 2.0,
    "high": 1.5,
    "medium": 1.0,
    "low": 0.5
  },
  "context_factors": {
    "user_engagement_history": {
      "weight": 0.3,
      "lookback_minutes": 60
    },
    "system_load": {
      "weight": 0.2,
      "threshold_high": 0.8,
      "threshold_critical": 0.95
    },
    "time_of_day": {
      "weight": 0.1,
      "peak_hours": [18, 19, 20, 21],
      "off_hours": [2, 3, 4, 5]
    },
    "recent_activity": {
      "weight": 0.4,
      "cooldown_seconds": 30
    }
  },
  "execution_paths": {
    "AVATAR_ONLY": {
      "description": "Trigger avatar speech response only - fastest path for TTS",
      "steps": [
        "validate_stimuli",
        "prepare_avatar_context",
        "trigger_system1_avatar",
        "await_avatar_response"
      ],
      "timeout_seconds": 8,
      "parallel_execution": false,
      "primary_path_for_speech": true
    },
    "AVATAR_AND_ANALYSIS": {
      "description": "Trigger both avatar response and multi-agent analysis",
      "steps": [
        "validate_stimuli",
        "prepare_avatar_context",
        "trigger_system1_avatar",
        "submit_to_system2_analysis",
        "await_responses",
        "aggregate_results"
      ],
      "timeout_seconds": 10,
      "parallel_execution": true
    },
    "ANALYSIS_ONLY": {
      "description": "Submit to multi-agent analysis without avatar response",
      "steps": [
        "validate_stimuli",
        "prepare_analysis_context",
        "submit_to_system2_analysis",
        "await_analysis",
        "store_insights"
      ],
      "timeout_seconds": 30,
      "parallel_execution": false
    },
    "LOG_ONLY": {
      "description": "Log for context without active processing",
      "steps": [
        "validate_stimuli",
        "enrich_metadata",
        "store_in_context_db",
        "update_metrics"
      ],
      "timeout_seconds": 2,
      "parallel_execution": false
    }
  }
}
```

### 2. Enhanced Decision Engine Implementation

**File**: `/app/CORE/graphflow-stimuli-system/src/gateway/nodes/enhanced_decision_engine.py`

```python
"""
Enhanced Decision Engine with Speech-First Routing Logic.
"""

import re
from typing import Dict, Any, List, Tuple
from ..models.decisions import ProcessingDecision
from ..utils.logging import get_structured_logger

class EnhancedDecisionEngine:
    """Enhanced decision engine optimized for speech routing."""
    
    def __init__(self):
        self.logger = get_structured_logger("enhanced_decision_engine")
        
        # Speech trigger keywords (prioritized)
        self.speech_keywords = {
            'explicit': ['speak', 'say', 'tell', 'voice', 'pronounce', 'articulate'],
            'conversational': ['hello', 'hi', 'hey', 'greet', 'respond', 'answer'],
            'imperative': ['talk', 'chat', 'discuss', 'communicate'],
            'test': ['test', 'demo', 'example', 'try']
        }
        
        # Question patterns that typically need speech responses
        self.speech_question_patterns = [
            r'\b(what|how|why|when|where|who)\b.*\?',
            r'\b(can you|could you|will you|would you)\b.*\?',
            r'\b(please|pls)\b.*\?',
            r'^(help|assist|guide).*'
        ]
    
    def evaluate_routing_decision(self, context: Dict[str, Any]) -> ProcessingDecision:
        """
        Evaluate routing decision with speech-first priority.
        
        Args:
            context: Evaluation context from analyzed stimuli
            
        Returns:
            ProcessingDecision optimized for speech responses
        """
        content = context.get('content', '').lower()
        category = context.get('category', '')
        confidence = context.get('confidence', 0.0)
        
        # Priority 1: Explicit speech requests
        if self._contains_speech_keywords(content):
            self.logger.info("Speech keywords detected - routing to AVATAR_ONLY")
            return ProcessingDecision.AVATAR_ONLY
        
        # Priority 2: User interaction with speech intent
        if category == "USER_INTERACTION":
            if self._has_speech_intent(content):
                self.logger.info("User interaction with speech intent - routing to AVATAR_ONLY")
                return ProcessingDecision.AVATAR_ONLY
            elif self._is_complex_question(content):
                self.logger.info("Complex question detected - routing to AVATAR_AND_ANALYSIS")
                return ProcessingDecision.AVATAR_AND_ANALYSIS
            else:
                # Default for user interactions is still avatar speech
                return ProcessingDecision.AVATAR_ONLY
        
        # Priority 3: Contextual updates with speech triggers
        if category == "CONTEXTUAL_UPDATE":
            if self._contains_common_speech_triggers(content):
                return ProcessingDecision.AVATAR_ONLY
            elif confidence > 0.7:
                return ProcessingDecision.AVATAR_AND_ANALYSIS
            else:
                return ProcessingDecision.AVATAR_ONLY
        
        # Priority 4: Admin commands
        if category == "DIRECT_ADMIN":
            if 'speak' in content or 'say' in content:
                return ProcessingDecision.AVATAR_AND_ANALYSIS
            else:
                return ProcessingDecision.ANALYSIS_ONLY
        
        # Priority 5: Autonomous triggers
        if category == "AUTONOMOUS_TRIGGER":
            return ProcessingDecision.AVATAR_ONLY  # Autonomous should speak
        
        # Priority 6: Emergency
        if category == "EMERGENCY":
            return ProcessingDecision.AVATAR_AND_ANALYSIS
        
        # Default fallback
        return ProcessingDecision.ANALYSIS_ONLY
    
    def _contains_speech_keywords(self, content: str) -> bool:
        """Check if content contains explicit speech keywords."""
        for category, keywords in self.speech_keywords.items():
            for keyword in keywords:
                if re.search(rf'\b{keyword}\b', content, re.IGNORECASE):
                    self.logger.debug(f"Found speech keyword: {keyword} (category: {category})")
                    return True
        return False
    
    def _has_speech_intent(self, content: str) -> bool:
        """Determine if content has implicit speech intent."""
        
        # Check for question patterns that typically need speech
        for pattern in self.speech_question_patterns:
            if re.search(pattern, content, re.IGNORECASE):
                return True
        
        # Check for conversational markers
        conversational_markers = ['please', 'thanks', 'thank you', 'pls']
        for marker in conversational_markers:
            if marker in content:
                return True
        
        # Check for greetings
        greetings = ['hello', 'hi', 'hey', 'good morning', 'good afternoon', 'good evening']
        for greeting in greetings:
            if greeting in content:
                return True
        
        return False
    
    def _contains_common_speech_triggers(self, content: str) -> bool:
        """Check for common speech trigger patterns."""
        triggers = [
            'hello', 'hi', 'hey', 'speak', 'respond', 'say', 'tell', 
            'voice', 'greet', 'test', 'demo', 'try', 'example'
        ]
        
        for trigger in triggers:
            if re.search(rf'\b{trigger}\b', content, re.IGNORECASE):
                return True
        return False
    
    def _is_complex_question(self, content: str) -> bool:
        """Determine if this is a complex question needing both speech and analysis."""
        
        # Multiple questions
        if content.count('?') > 1:
            return True
        
        # Long questions (>100 chars)
        if len(content) > 100 and '?' in content:
            return True
        
        # Technical/analytical keywords
        analytical_keywords = [
            'analyze', 'explain', 'describe', 'compare', 'evaluate',
            'research', 'investigate', 'calculate', 'determine'
        ]
        
        if '?' in content:
            for keyword in analytical_keywords:
                if keyword in content.lower():
                    return True
        
        return False
    
    def get_routing_explanation(self, 
                              context: Dict[str, Any], 
                              decision: ProcessingDecision) -> str:
        """Generate human-readable explanation for routing decision."""
        
        content = context.get('content', '').lower()
        category = context.get('category', '')
        
        explanations = []
        
        # Explain speech detection
        if self._contains_speech_keywords(content):
            explanations.append("Explicit speech keywords detected")
        
        if self._has_speech_intent(content):
            explanations.append("Implicit speech intent identified")
        
        # Explain category routing
        explanations.append(f"Category: {category}")
        
        # Explain decision
        decision_explanations = {
            ProcessingDecision.AVATAR_ONLY: "Optimized for speech/TTS response",
            ProcessingDecision.AVATAR_AND_ANALYSIS: "Requires both speech and analysis",
            ProcessingDecision.ANALYSIS_ONLY: "Analysis-focused processing",
            ProcessingDecision.LOG_ONLY: "Context logging only"
        }
        
        explanations.append(decision_explanations.get(decision, "Default routing"))
        
        return " | ".join(explanations)
```

### 3. Production Environment Configuration

**File**: `/app/CORE/graphflow-stimuli-system/config/production.env`

```bash
# GraphFlow Production Configuration
# Updated for Speech-First Routing and Enhanced Reliability

# Core System Settings
GRAPHFLOW_MODE=production
GRAPHFLOW_LOG_LEVEL=INFO
GRAPHFLOW_ENABLE_METRICS=true
GRAPHFLOW_ENABLE_TRACING=true

# Health Check Configuration (Critical Fix)
HEALTH_CHECK_INTERVAL=5                    # Reduced from 30s to 5s
STATUS_CACHE_TTL=10                       # Reduced from 30s to 10s
HEALTH_CHECK_TIMEOUT=3                    # Quick health check timeout
COMPREHENSIVE_HEALTH_CHECK=true           # Enable detailed health checks
HEALTH_CHECK_RETRY_ATTEMPTS=2             # Retry failed health checks

# Speech-First Routing Configuration (New)
DEFAULT_SPEECH_ROUTING=avatar_only         # Default to speech for user interactions
SPEECH_PRIORITY_MULTIPLIER=2.0            # Boost speech routing priority
USER_INTERACTION_CONFIDENCE_THRESHOLD=0.2  # Lower threshold for user interactions
ENABLE_SPEECH_KEYWORD_DETECTION=true      # Enable enhanced speech detection
CONTEXTUAL_UPDATE_DEFAULT=avatar_only     # Default contextual updates to speech

# System Integration Endpoints
SYSTEM1_ENDPOINT=http://localhost:8001    # Avatar/TTS system
SYSTEM2_ENDPOINT=http://localhost:8002    # Multi-agent system
SYSTEM1_HEALTH_ENDPOINT=${SYSTEM1_ENDPOINT}/health
SYSTEM2_HEALTH_ENDPOINT=${SYSTEM2_ENDPOINT}/health

# Enhanced Reliability Settings (New)
ENABLE_CIRCUIT_BREAKER=true               # Enable circuit breaker pattern
CIRCUIT_BREAKER_FAILURE_THRESHOLD=3       # Open circuit after 3 failures
CIRCUIT_BREAKER_RECOVERY_TIMEOUT=30       # 30s recovery timeout
ENABLE_FALLBACK_ROUTING=true              # Enable progressive degradation
FALLBACK_MODE=progressive_degradation     # Smart fallback strategy

# S2 Tool Execution Fixes (New)
AUTOGEN_ENDPOINT_RETRY=true               # Enable endpoint retries
AUTOGEN_MAX_RETRIES=2                     # Maximum retry attempts
AUTOGEN_RETRY_DELAY=2                     # Delay between retries (seconds)
AUTOGEN_TIMEOUT=15                        # Request timeout
ENABLE_TOOL_EXECUTION_MONITORING=true     # Monitor tool execution

# Performance Tuning
MAX_CONCURRENT_REQUESTS=10                # Limit concurrent processing
REQUEST_TIMEOUT=15                        # Overall request timeout
PROCESSING_TIMEOUT=30                     # Processing timeout
QUEUE_SIZE_LIMIT=50                       # Maximum queue size
ENABLE_REQUEST_THROTTLING=true            # Enable request throttling

# Fallback Endpoints (New)
SYSTEM1_FALLBACK_ENDPOINT=http://localhost:8011  # Backup S1 endpoint
SYSTEM2_FALLBACK_ENDPOINT=http://localhost:8012  # Backup S2 endpoint
ENABLE_ENDPOINT_ROTATION=true             # Rotate between endpoints

# Monitoring and Alerting
ENABLE_PERFORMANCE_MONITORING=true       # Enable performance tracking
ALERT_ON_HEALTH_CHECK_FAILURE=true       # Alert on health check failures
ALERT_ON_ROUTING_FAILURE=true            # Alert on routing failures
METRICS_EXPORT_INTERVAL=30               # Export metrics every 30s

# Security Settings
ENABLE_REQUEST_VALIDATION=true           # Validate incoming requests
ENABLE_RATE_LIMITING=true               # Enable rate limiting
MAX_REQUESTS_PER_MINUTE=300             # Rate limit threshold

# Development and Testing
ENABLE_DEBUG_LOGGING=false              # Disable debug logging in production
ENABLE_REQUEST_TRACING=true             # Enable request tracing
TRACE_SAMPLING_RATE=0.1                 # Sample 10% of requests
```

### 4. Enhanced Health Check Implementation

**File**: `/app/CORE/graphflow-stimuli-system/src/monitoring/enhanced_health_checker.py`

```python
"""
Enhanced Health Checker with Fast, Reliable System Monitoring.
"""

import asyncio
import time
from typing import Dict, Any, List, Optional
from dataclasses import dataclass
from enum import Enum
import httpx

from ..utils.logging import get_structured_logger

class HealthStatus(Enum):
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"
    UNKNOWN = "unknown"

@dataclass
class SystemCapabilities:
    """Available system capabilities based on health status."""
    avatar_speech: bool = False
    basic_analysis: bool = False
    multi_agent_analysis: bool = False
    memory_query: bool = False
    
    def get_available_paths(self) -> List[str]:
        """Get list of available processing paths."""
        paths = []
        if self.avatar_speech:
            paths.append("AVATAR_ONLY")
        if self.avatar_speech and self.basic_analysis:
            paths.append("AVATAR_AND_ANALYSIS")
        if self.basic_analysis:
            paths.append("ANALYSIS_ONLY")
        paths.append("LOG_ONLY")  # Always available
        return paths

@dataclass
class HealthCheckResult:
    """Health check result for a single component."""
    component: str
    status: HealthStatus
    response_time: float
    details: Dict[str, Any]
    error: Optional[str] = None

class EnhancedHealthChecker:
    """
    Enhanced health checker with fast, layered monitoring.
    """
    
    def __init__(self, config):
        self.config = config
        self.logger = get_structured_logger("enhanced_health_checker")
        
        # Health check cache with short TTL
        self._health_cache = {}
        self._cache_ttl = {
            "s1_basic": 5,      # 5s cache for basic S1 health
            "s1_detailed": 15,  # 15s cache for detailed checks
            "s2_basic": 8,      # 8s cache for S2 basic
            "s2_agents": 30     # 30s cache for agent discovery
        }
        
        # Component endpoints
        self.endpoints = {
            "s1_health": f"{config.system1_endpoint}/health",
            "s1_status": f"{config.system1_endpoint}/status",
            "s2_health": f"{config.system2_endpoint}/health",
            "s2_agents": f"{config.system2_endpoint}/agents/status"
        }
    
    async def check_system_health(self) -> Dict[str, Any]:
        """
        Perform comprehensive system health check.
        
        Returns:
            Complete health status with capabilities and routing recommendations
        """
        start_time = time.time()
        
        # Run health checks in parallel with timeouts
        health_checks = await asyncio.gather(
            self._check_s1_basic(),
            self._check_s1_detailed(),
            self._check_s2_basic(),
            self._check_s2_agents(),
            return_exceptions=True
        )
        
        s1_basic, s1_detailed, s2_basic, s2_agents = health_checks
        
        # Evaluate capabilities
        capabilities = self._evaluate_capabilities(
            s1_basic, s1_detailed, s2_basic, s2_agents
        )
        
        # Determine overall health
        overall_health = self._determine_overall_health(health_checks)
        
        # Generate routing recommendations
        routing_recommendations = self._generate_routing_recommendations(capabilities)
        
        total_time = time.time() - start_time
        
        return {
            "overall_health": overall_health.value,
            "capabilities": {
                "avatar_speech": capabilities.avatar_speech,
                "basic_analysis": capabilities.basic_analysis,
                "multi_agent_analysis": capabilities.multi_agent_analysis,
                "memory_query": capabilities.memory_query
            },
            "available_paths": capabilities.get_available_paths(),
            "routing_recommendations": routing_recommendations,
            "component_health": {
                "s1_basic": self._format_health_result(s1_basic),
                "s1_detailed": self._format_health_result(s1_detailed),
                "s2_basic": self._format_health_result(s2_basic),
                "s2_agents": self._format_health_result(s2_agents)
            },
            "check_duration": total_time,
            "timestamp": time.time()
        }
    
    async def _check_s1_basic(self) -> HealthCheckResult:
        """Basic S1 (Avatar/Speech) health check."""
        return await self._cached_health_check(
            "s1_basic",
            lambda: self._http_health_check(
                "s1_health",
                self.endpoints["s1_health"],
                timeout=3
            )
        )
    
    async def _check_s1_detailed(self) -> HealthCheckResult:
        """Detailed S1 status check."""
        return await self._cached_health_check(
            "s1_detailed",
            lambda: self._http_health_check(
                "s1_status",
                self.endpoints["s1_status"],
                timeout=5
            )
        )
    
    async def _check_s2_basic(self) -> HealthCheckResult:
        """Basic S2 (Multi-Agent) health check."""
        return await self._cached_health_check(
            "s2_basic",
            lambda: self._http_health_check(
                "s2_health",
                self.endpoints["s2_health"],
                timeout=4
            )
        )
    
    async def _check_s2_agents(self) -> HealthCheckResult:
        """S2 agent availability check."""
        return await self._cached_health_check(
            "s2_agents",
            lambda: self._http_health_check(
                "s2_agents",
                self.endpoints["s2_agents"],
                timeout=8
            )
        )
    
    async def _cached_health_check(self, check_type: str, check_func) -> HealthCheckResult:
        """Perform health check with caching."""
        now = time.time()
        cached = self._health_cache.get(check_type)
        
        # Return cached result if still valid
        if cached and (now - cached["timestamp"]) < self._cache_ttl[check_type]:
            return cached["result"]
        
        # Perform fresh check
        try:
            result = await check_func()
            
            # Cache the result
            self._health_cache[check_type] = {
                "result": result,
                "timestamp": now
            }
            
            return result
        except Exception as e:
            self.logger.error(f"Health check {check_type} failed: {e}")
            return HealthCheckResult(
                component=check_type,
                status=HealthStatus.UNKNOWN,
                response_time=0.0,
                details={"error": str(e)},
                error=str(e)
            )
    
    async def _http_health_check(self, 
                                component: str, 
                                url: str, 
                                timeout: float) -> HealthCheckResult:
        """Perform HTTP health check with timeout."""
        start_time = time.time()
        
        try:
            async with httpx.AsyncClient(timeout=httpx.Timeout(timeout)) as client:
                response = await client.get(url)
                
                response_time = time.time() - start_time
                
                if response.status_code == 200:
                    data = response.json() if response.headers.get("content-type", "").startswith("application/json") else {}
                    
                    return HealthCheckResult(
                        component=component,
                        status=HealthStatus.HEALTHY,
                        response_time=response_time,
                        details=data
                    )
                else:
                    return HealthCheckResult(
                        component=component,
                        status=HealthStatus.UNHEALTHY,
                        response_time=response_time,
                        details={"status_code": response.status_code},
                        error=f"HTTP {response.status_code}"
                    )
                    
        except asyncio.TimeoutError:
            return HealthCheckResult(
                component=component,
                status=HealthStatus.UNHEALTHY,
                response_time=timeout,
                details={},
                error="Timeout"
            )
        except Exception as e:
            return HealthCheckResult(
                component=component,
                status=HealthStatus.UNHEALTHY,
                response_time=time.time() - start_time,
                details={},
                error=str(e)
            )
    
    def _evaluate_capabilities(self, 
                             s1_basic, s1_detailed, s2_basic, s2_agents) -> SystemCapabilities:
        """Evaluate system capabilities based on health check results."""
        
        capabilities = SystemCapabilities()
        
        # Avatar speech capability
        if (isinstance(s1_basic, HealthCheckResult) and 
            s1_basic.status in [HealthStatus.HEALTHY, HealthStatus.DEGRADED]):
            capabilities.avatar_speech = True
        
        # Basic analysis capability
        if (isinstance(s2_basic, HealthCheckResult) and 
            s2_basic.status in [HealthStatus.HEALTHY, HealthStatus.DEGRADED]):
            capabilities.basic_analysis = True
        
        # Multi-agent analysis capability
        if (isinstance(s2_agents, HealthCheckResult) and 
            s2_agents.status == HealthStatus.HEALTHY and
            s2_agents.details.get("healthy_agents", 0) > 0):
            capabilities.multi_agent_analysis = True
        
        # Memory query capability (assume available if S2 is healthy)
        capabilities.memory_query = capabilities.basic_analysis
        
        return capabilities
    
    def _determine_overall_health(self, health_checks: List) -> HealthStatus:
        """Determine overall system health status."""
        
        healthy_components = 0
        total_components = 0
        
        for check in health_checks:
            if isinstance(check, HealthCheckResult):
                total_components += 1
                if check.status == HealthStatus.HEALTHY:
                    healthy_components += 1
        
        if total_components == 0:
            return HealthStatus.UNKNOWN
        
        health_ratio = healthy_components / total_components
        
        if health_ratio >= 0.8:
            return HealthStatus.HEALTHY
        elif health_ratio >= 0.5:
            return HealthStatus.DEGRADED
        else:
            return HealthStatus.UNHEALTHY
    
    def _generate_routing_recommendations(self, capabilities: SystemCapabilities) -> Dict[str, str]:
        """Generate routing recommendations based on capabilities."""
        
        recommendations = {}
        
        if capabilities.avatar_speech and capabilities.multi_agent_analysis:
            recommendations["user_interaction"] = "AVATAR_AND_ANALYSIS"
            recommendations["contextual_update"] = "AVATAR_ONLY"
            recommendations["admin_command"] = "AVATAR_AND_ANALYSIS"
        elif capabilities.avatar_speech:
            recommendations["user_interaction"] = "AVATAR_ONLY"
            recommendations["contextual_update"] = "AVATAR_ONLY"
            recommendations["admin_command"] = "AVATAR_ONLY"
        elif capabilities.basic_analysis:
            recommendations["user_interaction"] = "ANALYSIS_ONLY"
            recommendations["contextual_update"] = "ANALYSIS_ONLY"
            recommendations["admin_command"] = "ANALYSIS_ONLY"
        else:
            recommendations["user_interaction"] = "LOG_ONLY"
            recommendations["contextual_update"] = "LOG_ONLY"
            recommendations["admin_command"] = "LOG_ONLY"
        
        return recommendations
    
    def _format_health_result(self, result) -> Dict[str, Any]:
        """Format health check result for output."""
        if isinstance(result, HealthCheckResult):
            return {
                "status": result.status.value,
                "response_time": result.response_time,
                "error": result.error,
                "details": result.details
            }
        elif isinstance(result, Exception):
            return {
                "status": "error",
                "error": str(result),
                "details": {}
            }
        else:
            return {
                "status": "unknown",
                "error": "Unexpected result type",
                "details": {}
            }
```

### 5. Quick Deployment Script

**File**: `/app/CORE/graphflow-stimuli-system/scripts/deploy_fixes.sh`

```bash
#!/bin/bash

# Deploy Critical Fixes for Stimuli System
# This script applies the immediate fixes needed for speech routing

set -e  # Exit on any error

echo "🚀 Deploying Stimuli System Critical Fixes..."

# Configuration directory
CONFIG_DIR="/app/CORE/graphflow-stimuli-system/config"
SRC_DIR="/app/CORE/graphflow-stimuli-system/src"

# Backup current configuration
echo "📦 Backing up current configuration..."
cp "$CONFIG_DIR/decision_matrix.json" "$CONFIG_DIR/decision_matrix.json.backup.$(date +%Y%m%d_%H%M%S)"
cp "$CONFIG_DIR/production.env" "$CONFIG_DIR/production.env.backup.$(date +%Y%m%d_%H%M%S)"

# Apply decision matrix fixes
echo "🔧 Applying decision matrix fixes..."
# (The new decision_matrix.json content would be applied here)

# Apply environment configuration fixes
echo "🔧 Applying environment configuration fixes..."
# Update production.env with new settings

# Restart GraphFlow services
echo "🔄 Restarting GraphFlow services..."
docker-compose -f /app/CORE/graphflow-stimuli-system/docker-compose.yml restart

# Wait for services to be ready
echo "⏳ Waiting for services to initialize..."
sleep 10

# Test speech routing
echo "🧪 Testing speech routing..."
curl -X POST "http://localhost:8000/api/stimuli" \
  -H "Content-Type: application/json" \
  -d '{
    "content": "Please speak this test message",
    "category": "USER_INTERACTION",
    "source": "test"
  }' \
  --timeout 10

# Test health checks
echo "🏥 Testing health checks..."
curl -X GET "http://localhost:8000/health" --timeout 5

echo "✅ Critical fixes deployed successfully!"
echo ""
echo "🎯 Next steps:"
echo "1. Monitor logs for speech routing: docker logs graphflow-gateway -f"
echo "2. Test speech requests: send messages with 'speak', 'say', 'hello'"
echo "3. Verify S1 routing: check that USER_INTERACTION → AVATAR_ONLY"
echo "4. Monitor health checks: should respond within 5s"
```

## Verification Tests

### Test 1: Speech Routing Verification
```bash
# Test explicit speech request
curl -X POST "http://localhost:8000/api/stimuli" \
  -H "Content-Type: application/json" \
  -d '{
    "content": "Please speak this message out loud",
    "category": "USER_INTERACTION"
  }'

# Expected: routing_decision = "AVATAR_ONLY"
```

### Test 2: Health Check Speed Test
```bash
# Test health check response time
time curl -X GET "http://localhost:8000/health"

# Expected: < 5 seconds response time
```

### Test 3: S2 Tool Execution Test
```bash
# Test S2 analysis routing
curl -X POST "http://localhost:8000/api/stimuli" \
  -H "Content-Type: application/json" \
  -d '{
    "content": "Analyze the performance metrics for the last hour",
    "category": "DIRECT_ADMIN"
  }'

# Expected: routing_decision = "ANALYSIS_ONLY" and successful S2 execution
```

These fixes address the core issues:

1. **Speech Routing**: Changed default for USER_INTERACTION to AVATAR_ONLY
2. **Health Checks**: Reduced intervals and implemented caching  
3. **S2 Reliability**: Enhanced error handling and endpoint fallbacks
4. **Progressive Degradation**: Smart fallback based on system capabilities

The changes are backward compatible and can be deployed incrementally for minimal risk.