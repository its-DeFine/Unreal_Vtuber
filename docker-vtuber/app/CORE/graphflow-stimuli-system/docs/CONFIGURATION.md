# GraphFlow External Stimuli System - Configuration Guide

## Table of Contents

1. [Configuration Overview](#configuration-overview)
2. [Environment Variables](#environment-variables)
3. [Decision Matrix Configuration](#decision-matrix-configuration)
4. [Emergency Override Setup](#emergency-override-setup)
5. [API Key Configuration](#api-key-configuration)
6. [Custom Rules](#custom-rules)
7. [Advanced Configuration](#advanced-configuration)

## Configuration Overview

The GraphFlow External Stimuli System uses a hierarchical configuration system:

1. **Environment Variables**: Core system settings
2. **JSON Configuration Files**: Decision matrices, API keys, custom rules
3. **Python Configuration**: Emergency overrides and advanced logic

Configuration loading priority:
1. Environment variables (highest priority)
2. Configuration files
3. Default values (lowest priority)

## Environment Variables

### Core Settings

```bash
# Logging Configuration
GRAPHFLOW_LOG_LEVEL=INFO                    # Options: DEBUG, INFO, WARNING, ERROR
GRAPHFLOW_DETAILED_LOGGING=false            # Enable JSON structured logging
GRAPHFLOW_LOG_FILE=/var/log/graphflow.log   # Log file path (optional)

# Processing Configuration
GRAPHFLOW_MAX_CONCURRENT_STIMULI=50         # Maximum concurrent processing
GRAPHFLOW_PROCESSING_TIMEOUT=30.0           # Timeout in seconds
GRAPHFLOW_RETRY_ATTEMPTS=3                  # Retry attempts for failed operations
GRAPHFLOW_RETRY_DELAY=1.0                   # Delay between retries in seconds

# Performance Settings
GRAPHFLOW_ENABLE_CACHING=true               # Enable response caching
GRAPHFLOW_CACHE_TTL=300                     # Cache TTL in seconds
GRAPHFLOW_BATCH_SIZE=10                     # Batch processing size
GRAPHFLOW_QUEUE_SIZE=1000                   # Maximum queue size
```

### LLM Configuration

```bash
# LLM Provider Settings
GRAPHFLOW_LLM_PROVIDER=ollama               # Options: ollama, openai, anthropic
GRAPHFLOW_LLM_MODEL=llama3.2:3b             # Model identifier
GRAPHFLOW_LLM_ENDPOINT=http://ollama:11434  # LLM service endpoint
GRAPHFLOW_LLM_API_KEY=                      # API key if required
GRAPHFLOW_LLM_TEMPERATURE=0.7               # Model temperature
GRAPHFLOW_LLM_MAX_TOKENS=1000               # Maximum response tokens
GRAPHFLOW_LLM_TIMEOUT=10.0                  # LLM request timeout

# Fallback LLM (if primary fails)
GRAPHFLOW_FALLBACK_LLM_ENABLED=true
GRAPHFLOW_FALLBACK_LLM_PROVIDER=openai
GRAPHFLOW_FALLBACK_LLM_MODEL=gpt-3.5-turbo
```

### Integration Endpoints

```bash
# System1 (Avatar/Speech) Configuration
SYSTEM1_VTUBER_ENDPOINT=http://neurosync:5001
SYSTEM1_API_KEY=vtuber-secret-key
SYSTEM1_TIMEOUT=5.0
SYSTEM1_MAX_RETRIES=2
SYSTEM1_ENABLE_CACHING=true

# System2 (Multi-Agent) Configuration
SYSTEM2_AUTOGEN_ENDPOINT=http://autogen-agent:3100
SYSTEM2_API_KEY=autogen-secret-key
SYSTEM2_TIMEOUT=20.0
SYSTEM2_MAX_AGENTS=5
SYSTEM2_ENABLE_ASYNC=true

# Additional Integrations
COGNEE_ENDPOINT=http://cognee:8000
COGNEE_API_KEY=cognee-secret-key
TTS_ENDPOINT=http://tts-service:5000
TTS_VOICE_ID=en-US-Standard-A
```

### Database Configuration

```bash
# Redis Configuration
REDIS_URL=redis://redis:6379
REDIS_PASSWORD=                             # Optional password
REDIS_DB=0                                  # Database number
REDIS_MAX_CONNECTIONS=50                    # Connection pool size
REDIS_SOCKET_TIMEOUT=5.0                    # Socket timeout
REDIS_SOCKET_CONNECT_TIMEOUT=5.0            # Connection timeout

# PostgreSQL Configuration
POSTGRES_URL=postgresql://postgres:password@postgres:5432/graphflow
POSTGRES_POOL_SIZE=20                       # Connection pool size
POSTGRES_MAX_OVERFLOW=10                    # Maximum overflow connections
POSTGRES_POOL_TIMEOUT=30                    # Pool timeout
POSTGRES_ECHO=false                         # Echo SQL queries
```

### Monitoring Configuration

```bash
# Metrics Configuration
GRAPHFLOW_METRICS_ENABLED=true              # Enable Prometheus metrics
GRAPHFLOW_METRICS_PORT=8081                 # Metrics endpoint port
GRAPHFLOW_METRICS_PATH=/metrics             # Metrics endpoint path

# Health Check Configuration
GRAPHFLOW_HEALTH_CHECK_INTERVAL=30          # Health check interval in seconds
GRAPHFLOW_HEALTH_CHECK_TIMEOUT=5            # Health check timeout

# Tracing Configuration
GRAPHFLOW_TRACING_ENABLED=false             # Enable OpenTelemetry tracing
GRAPHFLOW_TRACING_ENDPOINT=http://jaeger:14268/api/traces
GRAPHFLOW_TRACING_SERVICE_NAME=graphflow-gateway
```

### Security Configuration

```bash
# API Security
GRAPHFLOW_API_KEY_HEADER=Authorization      # API key header name
GRAPHFLOW_API_KEY_PREFIX=Bearer             # API key prefix
GRAPHFLOW_ENABLE_CORS=true                  # Enable CORS
GRAPHFLOW_ALLOWED_ORIGINS=*                 # CORS allowed origins

# Encryption
GRAPHFLOW_ENCRYPT_SENSITIVE_DATA=true       # Encrypt sensitive data
GRAPHFLOW_ENCRYPTION_KEY=                   # Encryption key (auto-generated if empty)

# Rate Limiting
GRAPHFLOW_RATE_LIMIT_ENABLED=true           # Enable rate limiting
GRAPHFLOW_RATE_LIMIT_DEFAULT=100            # Default requests per minute
GRAPHFLOW_RATE_LIMIT_BURST=20               # Burst allowance
```

## Decision Matrix Configuration

The decision matrix is configured via `config/decision_matrix.json`:

### Basic Structure

```json
{
  "version": "1.0",
  "default_decision": "LOG_ONLY",
  "confidence_threshold": 0.7,
  "rules": [
    {
      "id": "rule_001",
      "name": "high_priority_admin",
      "description": "Direct admin commands get immediate attention",
      "conditions": {
        "category": "DIRECT_ADMIN",
        "priority": ["high", "critical"]
      },
      "decision": "AVATAR_AND_ANALYSIS",
      "confidence_modifier": 0.2,
      "priority": 100
    }
  ]
}
```

### Rule Configuration

Each rule can have the following properties:

| Property | Type | Required | Description |
|----------|------|----------|-------------|
| id | string | Yes | Unique identifier |
| name | string | Yes | Human-readable name |
| description | string | No | Rule description |
| conditions | object | Yes | Conditions to match |
| decision | string | Yes | Decision outcome |
| confidence_modifier | float | No | Confidence adjustment (-1 to 1) |
| priority | integer | No | Rule priority (higher = first) |
| enabled | boolean | No | Enable/disable rule |

### Condition Types

```json
{
  "conditions": {
    // Exact match
    "category": "USER_INTERACTION",
    
    // Array match (any)
    "priority": ["high", "critical"],
    
    // Nested property
    "metadata.user_type": "vip",
    
    // Numeric comparison
    "metadata.message_count": {
      "operator": "gte",
      "value": 10
    },
    
    // String pattern
    "content": {
      "pattern": "urgent|emergency|critical",
      "case_sensitive": false
    },
    
    // Time-based
    "time_of_day": {
      "start": "09:00",
      "end": "17:00"
    },
    
    // Complex conditions
    "or": [
      {"category": "EMERGENCY"},
      {"priority": "critical"}
    ],
    
    "and": [
      {"source": "monitoring"},
      {"metadata.severity": "high"}
    ]
  }
}
```

### Decision Types

Available decisions:
- `AVATAR_AND_ANALYSIS`: Both avatar response and multi-agent analysis
- `ANALYSIS_ONLY`: Multi-agent analysis without avatar
- `LOG_ONLY`: Log for context without processing
- `CUSTOM`: Custom decision with additional parameters

### Complete Example

```json
{
  "version": "1.0",
  "default_decision": "LOG_ONLY",
  "confidence_threshold": 0.7,
  "rules": [
    {
      "id": "vip_user_interaction",
      "name": "VIP User Interaction",
      "description": "VIP users get immediate avatar response",
      "conditions": {
        "category": "USER_INTERACTION",
        "metadata.user_type": "vip"
      },
      "decision": "AVATAR_AND_ANALYSIS",
      "confidence_modifier": 0.3,
      "priority": 100
    },
    {
      "id": "system_emergency",
      "name": "System Emergency",
      "description": "Emergency alerts trigger full response",
      "conditions": {
        "or": [
          {"category": "EMERGENCY"},
          {
            "and": [
              {"category": "SYSTEM_NOTIFICATION"},
              {"metadata.severity": "critical"}
            ]
          }
        ]
      },
      "decision": "AVATAR_AND_ANALYSIS",
      "confidence_modifier": 0.5,
      "priority": 200
    },
    {
      "id": "quiet_hours",
      "name": "Quiet Hours",
      "description": "Reduce avatar responses during quiet hours",
      "conditions": {
        "time_of_day": {
          "start": "22:00",
          "end": "06:00"
        }
      },
      "decision": "ANALYSIS_ONLY",
      "confidence_modifier": -0.2,
      "priority": 50
    },
    {
      "id": "social_media_mentions",
      "name": "Social Media Mentions",
      "description": "Social media requires analysis",
      "conditions": {
        "category": "SOCIAL_MEDIA",
        "metadata.engagement": {
          "operator": "gte",
          "value": 100
        }
      },
      "decision": "ANALYSIS_ONLY",
      "priority": 60
    }
  ]
}
```

## Emergency Override Setup

Emergency overrides allow runtime rule injection without restarting the system.

### Configuration File

`config/emergency_override.py`:

```python
from typing import Dict, Any, List
from datetime import datetime, timedelta

class EmergencyOverride:
    """Emergency override configuration for runtime rule changes."""
    
    @staticmethod
    def get_overrides() -> List[Dict[str, Any]]:
        """
        Return active emergency overrides.
        
        Returns:
            List of override rules to apply
        """
        overrides = []
        
        # Example: Maintenance mode
        if is_maintenance_mode():
            overrides.append({
                "id": "maintenance_override",
                "name": "Maintenance Mode",
                "conditions": {"all": True},  # Matches everything
                "decision": "LOG_ONLY",
                "priority": 1000,  # Highest priority
                "expires": datetime.now() + timedelta(hours=2)
            })
        
        # Example: High load protection
        if get_system_load() > 0.8:
            overrides.append({
                "id": "high_load_override",
                "name": "High Load Protection",
                "conditions": {
                    "priority": ["low", "medium"]
                },
                "decision": "LOG_ONLY",
                "priority": 900,
                "confidence_modifier": -0.5
            })
        
        # Example: Specific user override
        overrides.append({
            "id": "user_override_123",
            "name": "Specific User Override",
            "conditions": {
                "metadata.user_id": "user123"
            },
            "decision": "AVATAR_AND_ANALYSIS",
            "priority": 800,
            "expires": datetime(2025, 1, 5, 12, 0, 0)
        })
        
        return [o for o in overrides if not is_expired(o)]
    
    @staticmethod
    def validate_override(override: Dict[str, Any]) -> bool:
        """Validate override rule structure."""
        required = ["id", "name", "conditions", "decision", "priority"]
        return all(field in override for field in required)

def is_maintenance_mode() -> bool:
    """Check if system is in maintenance mode."""
    # Implement your logic
    return False

def get_system_load() -> float:
    """Get current system load."""
    # Implement your logic
    return 0.5

def is_expired(override: Dict[str, Any]) -> bool:
    """Check if override has expired."""
    if "expires" not in override:
        return False
    return datetime.now() > override["expires"]
```

### Using Emergency Overrides

```python
# Apply emergency override via API
curl -X POST http://localhost:8080/api/v1/admin/override \
  -H "Authorization: Bearer admin-key" \
  -H "Content-Type: application/json" \
  -d '{
    "id": "emergency_001",
    "name": "Emergency Override",
    "conditions": {"category": "USER_INTERACTION"},
    "decision": "LOG_ONLY",
    "priority": 999,
    "duration_minutes": 60
  }'
```

## API Key Configuration

Configure API keys in `config/api_keys.json`:

```json
{
  "version": "1.0",
  "api_keys": [
    {
      "key": "dev-key-123",
      "name": "Development Key",
      "permissions": ["read", "write", "admin"],
      "rate_limit": 1000,
      "metadata": {
        "environment": "development",
        "owner": "dev-team"
      }
    },
    {
      "key": "prod-read-only-456",
      "name": "Production Read-Only",
      "permissions": ["read"],
      "rate_limit": 100,
      "allowed_ips": ["192.168.1.0/24"],
      "expires": "2025-12-31T23:59:59Z"
    },
    {
      "key": "webhook-key-789",
      "name": "Webhook Integration",
      "permissions": ["write"],
      "rate_limit": 500,
      "allowed_sources": ["webhook", "integration"],
      "metadata": {
        "integration": "discord-bot"
      }
    }
  ]
}
```

### API Key Properties

| Property | Type | Required | Description |
|----------|------|----------|-------------|
| key | string | Yes | The API key value |
| name | string | Yes | Descriptive name |
| permissions | array | Yes | List of permissions |
| rate_limit | integer | No | Requests per minute (default: 100) |
| allowed_ips | array | No | IP whitelist |
| allowed_sources | array | No | Allowed source values |
| expires | string | No | ISO 8601 expiration date |
| metadata | object | No | Additional metadata |

## Custom Rules

Configure custom processing rules in `config/custom_rules.json`:

```json
{
  "version": "1.0",
  "custom_rules": [
    {
      "name": "sentiment_based_routing",
      "description": "Route based on detected sentiment",
      "type": "processor",
      "config": {
        "sentiment_thresholds": {
          "positive": 0.7,
          "negative": -0.7
        },
        "routing_map": {
          "very_positive": "AVATAR_AND_ANALYSIS",
          "positive": "ANALYSIS_ONLY",
          "neutral": "LOG_ONLY",
          "negative": "AVATAR_AND_ANALYSIS",
          "very_negative": "AVATAR_AND_ANALYSIS"
        }
      }
    },
    {
      "name": "keyword_extraction",
      "description": "Extract and tag important keywords",
      "type": "enricher",
      "config": {
        "keyword_patterns": {
          "technical": ["bug", "error", "crash", "issue"],
          "feedback": ["suggestion", "idea", "improve", "feature"],
          "urgent": ["asap", "urgent", "immediately", "now"]
        },
        "tag_metadata": true
      }
    },
    {
      "name": "rate_limiter",
      "description": "Per-user rate limiting",
      "type": "filter",
      "config": {
        "limits": {
          "default": {
            "requests_per_minute": 10,
            "burst": 20
          },
          "vip": {
            "requests_per_minute": 100,
            "burst": 200
          }
        },
        "key_field": "metadata.user_id"
      }
    }
  ]
}
```

## Advanced Configuration

### Performance Tuning

```bash
# Optimize for high throughput
GRAPHFLOW_MAX_CONCURRENT_STIMULI=100
GRAPHFLOW_BATCH_SIZE=20
GRAPHFLOW_QUEUE_SIZE=5000
GRAPHFLOW_ENABLE_CACHING=true
GRAPHFLOW_CACHE_TTL=600

# Optimize for low latency
GRAPHFLOW_MAX_CONCURRENT_STIMULI=20
GRAPHFLOW_BATCH_SIZE=1
GRAPHFLOW_PROCESSING_TIMEOUT=10.0
GRAPHFLOW_ENABLE_CACHING=false
```

### Multi-Environment Setup

```bash
# development.env
GRAPHFLOW_LOG_LEVEL=DEBUG
GRAPHFLOW_LLM_PROVIDER=ollama
GRAPHFLOW_LLM_MODEL=llama3.2:3b
REDIS_URL=redis://localhost:6379

# staging.env
GRAPHFLOW_LOG_LEVEL=INFO
GRAPHFLOW_LLM_PROVIDER=openai
GRAPHFLOW_LLM_MODEL=gpt-3.5-turbo
REDIS_URL=redis://redis-staging:6379

# production.env
GRAPHFLOW_LOG_LEVEL=WARNING
GRAPHFLOW_LLM_PROVIDER=openai
GRAPHFLOW_LLM_MODEL=gpt-4
REDIS_URL=redis://redis-prod:6379
GRAPHFLOW_ENABLE_CACHING=true
```

### Feature Flags

```json
{
  "feature_flags": {
    "enable_sentiment_analysis": true,
    "enable_entity_extraction": true,
    "enable_context_memory": true,
    "enable_parallel_execution": false,
    "enable_experimental_llm": false,
    "max_context_window": 4096,
    "enable_fallback_processing": true
  }
}
```

### Monitoring Alerts

```json
{
  "alert_rules": [
    {
      "name": "high_error_rate",
      "condition": "error_rate > 0.05",
      "severity": "critical",
      "notification": {
        "webhook": "https://alerts.example.com/webhook",
        "email": "ops@example.com"
      }
    },
    {
      "name": "slow_processing",
      "condition": "p95_latency > 5000",
      "severity": "warning",
      "notification": {
        "webhook": "https://alerts.example.com/webhook"
      }
    }
  ]
}
```

## Configuration Best Practices

1. **Use Environment Variables for Secrets**
   - Never commit API keys or passwords
   - Use secret management systems in production

2. **Version Your Configurations**
   - Track changes in version control
   - Document configuration changes

3. **Validate Configurations**
   - Use schema validation for JSON files
   - Test configurations before deployment

4. **Monitor Configuration Changes**
   - Log all configuration updates
   - Alert on unexpected changes

5. **Use Sensible Defaults**
   - Provide defaults for all settings
   - Make defaults production-safe

6. **Document Everything**
   - Comment complex configurations
   - Maintain a configuration changelog