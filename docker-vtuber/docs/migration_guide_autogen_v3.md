# Migration Guide: AutoGen Orchestrator V2 to V3

## Overview

This guide provides step-by-step instructions for migrating from the existing Autonomous Orchestrator V2 to the new AutoGen-based Orchestrator V3. The migration is designed to be smooth with minimal disruption to existing services.

## Key Differences

### V2 (Current System)
- Custom Python-based orchestrator
- Single decision engine
- Basic state management
- Limited persona configurations

### V3 (AutoGen System)
- Microsoft AutoGen multi-agent framework
- Specialized agents for different tasks
- Advanced state management with enhanced hooks
- Comprehensive persona system with dynamic filtering
- Performance monitoring and metrics

## Prerequisites

Before starting the migration:

1. **Backup Current System**
   ```bash
   # Backup database
   docker exec vtuber_postgres pg_dump -U postgres vtuber_autogen > backup_$(date +%Y%m%d).sql
   
   # Backup configuration
   cp -r ./app/AVATAR/NeuroBridge/NeuroSync_Player ./backup/neurosync_player_v2
   ```

2. **Verify Requirements**
   - Docker and Docker Compose installed
   - OpenAI API key (or alternative LLM provider configured)
   - At least 4GB RAM available
   - Python 3.10+ (for local testing)

## Migration Steps

### Phase 1: Parallel Deployment (Recommended)

This approach allows you to test V3 alongside V2 without disrupting the existing system.

#### Step 1: Deploy AutoGen Orchestrator Service

1. **Copy new files to your project:**
   ```bash
   # Create directories if needed
   mkdir -p app/AVATAR/NeuroBridge/NeuroSync_Player
   mkdir -p docs
   mkdir -p logs/autogen
   mkdir -p logs/neurosync
   ```

2. **Set up environment variables:**
   ```bash
   # Add to your .env file
   echo "AUTOGEN_ORCHESTRATOR_ENABLED=true" >> .env
   echo "ORCHESTRATOR_PERSONA=interactive_streamer" >> .env
   echo "AUTONOMOUS_CONTENT_ENABLED=true" >> .env
   ```

3. **Start AutoGen orchestrator only:**
   ```bash
   # Start just the orchestrator service
   docker-compose -f docker-compose.autogen.yml up -d autogen_orchestrator postgres redis
   
   # Check logs
   docker logs -f autogen_orchestrator
   ```

4. **Verify orchestrator health:**
   ```bash
   # Check health endpoint
   curl http://localhost:8300/orchestrator/v3/health
   
   # Check status
   curl http://localhost:8300/orchestrator/v3/status
   ```

#### Step 2: Configure NeuroSync Player for V3

1. **Update llm_to_face.py to support both versions:**
   ```python
   # Add to imports
   from orchestrator_integration_v3 import create_autogen_integration
   from autogen_api_routes import register_autogen_routes
   
   # Add configuration flag
   USE_AUTOGEN_V3 = os.getenv("USE_AUTOGEN_V3", "false").lower() == "true"
   
   # In main_setup(), add conditional initialization
   if USE_AUTOGEN_V3:
       orchestrator_wrapper = create_autogen_integration(
           app,
           autogen_enabled=True,
           persona=os.getenv("ORCHESTRATOR_PERSONA", "interactive_streamer")
       )
       register_autogen_routes(app, orchestrator_wrapper)
   else:
       # Existing V2 initialization
       orchestrator_wrapper = setup_orchestration()
   ```

2. **Enable V3 gradually:**
   ```bash
   # Start with V3 disabled (default)
   docker-compose -f docker-compose.autogen.yml up -d neurosync_player
   
   # Enable V3 for testing
   docker-compose -f docker-compose.autogen.yml exec neurosync_player \
       bash -c "export USE_AUTOGEN_V3=true && python llm_to_face.py"
   ```

#### Step 3: Test Core Functionality

1. **Test basic text processing:**
   ```bash
   # Test V3 process endpoint
   curl -X POST http://localhost:5001/orchestrator/v3/process \
     -H "Content-Type: application/json" \
     -d '{
       "input_type": "viewer_comment",
       "content": "Hello VTuber!",
       "metadata": {
         "viewer_name": "TestUser",
         "platform": "twitch"
       }
     }'
   ```

2. **Test persona switching:**
   ```bash
   # Get current persona
   curl http://localhost:5001/orchestrator/v3/persona
   
   # Switch to focused artist
   curl -X PUT http://localhost:5001/orchestrator/v3/persona \
     -H "Content-Type: application/json" \
     -d '{"persona": "focused_artist"}'
   ```

3. **Test autonomous content:**
   ```bash
   # Check autonomous stats
   curl http://localhost:5001/orchestrator/v3/autonomous/stats
   
   # Configure autonomous behavior
   curl -X POST http://localhost:5001/orchestrator/v3/autonomous/control \
     -H "Content-Type: application/json" \
     -d '{
       "action": "configure",
       "settings": {
         "min_idle_time": 10,
         "max_idle_time": 30
       }
     }'
   ```

### Phase 2: Feature Parity Validation

#### Step 1: Compare Behaviors

1. **Create test scenarios:**
   ```python
   # test_scenarios.py
   test_cases = [
       {
           "name": "Simple greeting",
           "input": "Hello! How are you?",
           "expected_behavior": "Should respond with greeting"
       },
       {
           "name": "Spam filtering", 
           "input": "Buy my product! Click here!",
           "expected_behavior": "Should be filtered/suppressed"
       },
       {
           "name": "Art question (focused artist)",
           "input": "What brush are you using?",
           "expected_behavior": "Should pass through with high priority"
       }
   ]
   ```

2. **Run A/B tests:**
   ```bash
   # Send same inputs to both V2 and V3
   # Compare responses and timing
   ```

#### Step 2: Monitor Performance

1. **Set up metrics collection:**
   ```bash
   # Start Prometheus and Grafana
   docker-compose -f docker-compose.autogen.yml up -d prometheus grafana
   
   # Access Grafana at http://localhost:3001 (admin/admin)
   ```

2. **Monitor key metrics:**
   - Response latency
   - Decision accuracy
   - Resource usage
   - Error rates

### Phase 3: Full Migration

#### Step 1: Update Configuration

1. **Enable V3 permanently:**
   ```bash
   # Update .env
   echo "USE_AUTOGEN_V3=true" >> .env
   echo "AUTONOMOUS_ORCHESTRATION_ENABLED=false" >> .env  # Disable V2
   ```

2. **Update docker-compose.yml:**
   ```yaml
   # In your main docker-compose.yml, update neurosync_player:
   environment:
     - USE_AUTOGEN_V3=true
     - AUTOGEN_ORCHESTRATOR_URL=http://autogen_orchestrator:8000
   ```

#### Step 2: Migrate Custom Configurations

1. **Persona configurations:**
   ```python
   # If you have custom personas in V2, add them to V3:
   # In autogen_orchestrator_v3.py, _load_persona_configs():
   
   "custom_persona": PersonaConfig(
       name="Your Custom Persona",
       orchestrator_prompt="Your custom prompt...",
       filter_threshold=0.5,
       idle_behavior=IdleBehaviorConfig(
           min_idle_time=10,
           max_idle_time=30,
           content_types={
               # Your content types
           }
       )
   )
   ```

2. **Environment variables:**
   ```bash
   # Map V2 variables to V3
   # V2 -> V3
   DECISION_LOOP_INTERVAL -> DECISION_INTERVAL
   ORCHESTRATOR_IDLE_TIMEOUT -> MAX_IDLE_TIME
   AUTO_INTERRUPT_ENABLED -> (built into V3)
   ```

#### Step 3: Deprecate V2

1. **Remove V2 imports:**
   ```python
   # In llm_to_face.py, remove:
   # from orchestrator_integration import OrchestrationWrapper
   # from autonomous_orchestrator_wrapper import Priority, ActionType
   ```

2. **Clean up V2 files (optional):**
   ```bash
   # After confirming V3 is stable
   mv autonomous_orchestrator_v2.py ./archive/
   mv orchestrator_integration.py ./archive/
   ```

## Rollback Procedures

If issues arise, you can quickly rollback to V2:

### Quick Rollback

1. **Disable V3:**
   ```bash
   # Update environment
   export USE_AUTOGEN_V3=false
   export AUTONOMOUS_ORCHESTRATION_ENABLED=true
   
   # Restart services
   docker-compose restart neurosync_player
   ```

2. **Stop V3 orchestrator:**
   ```bash
   docker-compose -f docker-compose.autogen.yml stop autogen_orchestrator
   ```

### Full Rollback

1. **Restore V2 configuration:**
   ```bash
   # Restore backup
   cp -r ./backup/neurosync_player_v2/* ./app/AVATAR/NeuroBridge/NeuroSync_Player/
   
   # Restore database if needed
   docker exec -i vtuber_postgres psql -U postgres vtuber_autogen < backup_20240101.sql
   ```

2. **Restart with V2:**
   ```bash
   docker-compose down
   docker-compose up -d
   ```

## Troubleshooting

### Common Issues

1. **AutoGen agents not responding:**
   ```bash
   # Check agent status
   curl http://localhost:8300/orchestrator/v3/agents/status
   
   # Restart orchestrator
   docker-compose -f docker-compose.autogen.yml restart autogen_orchestrator
   ```

2. **High latency in responses:**
   ```bash
   # Check performance metrics
   curl http://localhost:8300/orchestrator/v3/debug
   
   # Adjust timeouts
   export AGENT_TIMEOUT=10.0
   export MAX_AGENT_ROUNDS=5
   ```

3. **Persona not working as expected:**
   ```bash
   # Verify current persona
   curl http://localhost:8300/orchestrator/v3/persona
   
   # Check agent decisions in logs
   docker logs autogen_orchestrator | grep DECISION
   ```

### Debug Mode

Enable debug logging for detailed troubleshooting:

```bash
# Set debug environment variables
export TRACE_ENABLED=true
export LOG_LEVEL=DEBUG

# Restart services
docker-compose -f docker-compose.autogen.yml restart
```

## Performance Tuning

### Optimize Agent Performance

1. **Adjust agent parameters:**
   ```bash
   # Reduce agent rounds for faster responses
   export MAX_AGENT_ROUNDS=5
   
   # Increase timeout for complex decisions
   export AGENT_TIMEOUT=10.0
   
   # Enable decision caching
   export CACHE_DECISIONS=true
   ```

2. **Scale horizontally (advanced):**
   ```yaml
   # In docker-compose.autogen.yml
   autogen_orchestrator:
     deploy:
       replicas: 2
   ```

### Monitor Resource Usage

```bash
# Check container resources
docker stats autogen_orchestrator neurosync_player

# Monitor database connections
docker exec vtuber_postgres psql -U postgres -c "SELECT count(*) FROM pg_stat_activity;"
```

## Best Practices

### 1. Gradual Rollout
- Start with low-traffic periods
- Monitor closely for first 24-48 hours
- Keep V2 ready as fallback

### 2. Persona Customization
- Test each persona thoroughly
- Adjust filter thresholds based on your audience
- Create custom personas for special events

### 3. Performance Monitoring
- Set up alerts for high latency (>500ms)
- Monitor agent decision patterns
- Track autonomous content effectiveness

### 4. Regular Maintenance
- Update AutoGen library monthly
- Review and optimize agent prompts
- Clean up old performance traces

## Support and Resources

### Documentation
- [AutoGen Documentation](https://microsoft.github.io/autogen/)
- [API Reference](/docs/autogen_api_reference.md)
- [Persona Configuration Guide](/docs/persona_configuration.md)

### Monitoring Dashboards
- Grafana: http://localhost:3001
- Prometheus: http://localhost:9090
- Debug endpoint: http://localhost:8300/orchestrator/v3/debug

### Getting Help
- Check logs: `docker logs autogen_orchestrator`
- Debug endpoint: `curl http://localhost:8300/orchestrator/v3/debug`
- Test specific agents: `curl http://localhost:8300/orchestrator/v3/agents/status`

## Conclusion

The migration from V2 to V3 brings significant improvements in flexibility, decision-making capabilities, and observability. By following this guide and taking a phased approach, you can ensure a smooth transition with minimal disruption to your VTuber streaming operations.

Remember to:
- Test thoroughly in parallel before full migration
- Monitor performance metrics closely
- Keep backups and rollback procedures ready
- Customize personas to match your streaming style

The AutoGen V3 orchestrator provides a solid foundation for advanced autonomous VTuber behaviors and can be extended with additional agents and capabilities as needed.