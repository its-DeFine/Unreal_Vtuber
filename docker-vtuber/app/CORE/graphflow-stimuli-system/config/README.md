# GraphFlow External Stimuli System - Configuration Guide

This directory contains configuration files for the GraphFlow External Stimuli System.

## Configuration Files

### Environment Files

- **`development.env`**: Configuration for local development environment
- **`testing.env`**: Configuration for automated testing
- **`production.env`**: Template for production deployment (update before use)

### Additional Configuration Files

- **`api_keys.json`**: API key definitions and permissions
- **`custom_rules.json`**: Custom decision matrix rules
- **`emergency_override.py`**: Emergency override handler implementation

## Configuration Management

### Loading Configuration

The system automatically loads configuration based on the environment:

```python
from src.config import load_config

# Automatically loads from environment variables
config = load_config()

# Or load from specific file
config = load_config("config/development.env")
```

### Environment Variables

All configuration is managed through environment variables. The system follows these conventions:

- `GRAPHFLOW_*`: Core system settings
- `SYSTEM1_*`: Avatar/Speech integration settings
- `SYSTEM2_*`: Multi-agent system settings
- `EXTERNAL_*`: External API settings
- `CATEGORIZER_*`: Categorizer node settings
- `ANALYZER_*`: Analyzer node settings
- `ROUTER_*`: Router node settings
- `EXECUTOR_*`: Executor node settings
- `SECURITY_*`: Security settings
- `ERROR_*`: Error handling settings

### Decision Matrix Configuration

The decision matrix determines how stimuli are routed. Rules are evaluated in priority order:

1. **Emergency Rules** (Priority 90-100): Handle critical situations
2. **System State Rules** (Priority 70-89): Based on current system state
3. **Category Rules** (Priority 50-69): Based on stimuli category
4. **Resource Rules** (Priority 40-49): Based on resource availability
5. **User Context Rules** (Priority 30-39): Based on user patterns
6. **Environmental Rules** (Priority 20-29): Based on environment
7. **Default Rules** (Priority 0-19): Fallback rules

### Custom Rules

Add custom rules by creating or updating `custom_rules.json`:

```json
{
  "custom_category_name": [
    {
      "id": "unique_rule_id",
      "condition": "Python expression to evaluate",
      "decision": "AVATAR_AND_ANALYSIS|ANALYSIS_ONLY|LOG_ONLY|EMERGENCY_OVERRIDE",
      "priority": 50,
      "description": "What this rule does",
      "enabled": true,
      "metadata": {}
    }
  ]
}
```

### Emergency Override

The `emergency_override.py` file defines actions taken during emergency situations:

1. Load emergency character preset
2. Switch to reactive mode
3. Announce emergency status (optional)
4. Execute custom emergency procedures

Customize this file for your specific emergency response needs.

## Security Considerations

1. **Production Secrets**: Never commit production secrets to version control
2. **API Keys**: Store production API keys securely (e.g., AWS Secrets Manager)
3. **Encryption Keys**: Generate unique encryption keys for production
4. **Database Credentials**: Use strong, unique passwords for production databases
5. **IP Whitelisting**: Configure allowed/blocked IPs for production

## Configuration Validation

The system validates configuration on startup. Common validation checks:

- Required values are present
- Numeric values are within valid ranges
- Enum values are valid options
- File paths exist (for required files)
- URLs are properly formatted

## Troubleshooting

### Configuration Not Loading

1. Check environment variable names (case-sensitive)
2. Verify file paths are correct
3. Check for syntax errors in JSON files
4. Review logs for validation errors

### Decision Matrix Issues

1. Enable decision logging: `ROUTER_DECISION_LOGGING=true`
2. Check rule conditions for syntax errors
3. Verify rule priorities don't conflict
4. Test rules with sample contexts

### Performance Tuning

1. Adjust `GRAPHFLOW_MAX_CONCURRENT_STIMULI` based on resources
2. Tune cache TTLs for your use case
3. Configure thread/worker pools appropriately
4. Monitor metrics to identify bottlenecks

## Best Practices

1. **Environment Separation**: Use different configs for each environment
2. **Gradual Rollout**: Test configuration changes in development first
3. **Monitoring**: Enable metrics and logging in production
4. **Documentation**: Document custom rules and emergency procedures
5. **Backup**: Keep backups of production configuration
6. **Version Control**: Track configuration changes over time
7. **Secrets Management**: Use proper secret management tools

## Quick Start

1. Copy appropriate `.env` file for your environment
2. Update configuration values as needed
3. Set environment variables or specify config path
4. Start the GraphFlow system
5. Monitor logs for any configuration issues