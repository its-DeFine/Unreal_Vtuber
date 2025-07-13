# 🔄 GraphFlow to Orchestrator Migration Guide
*Created: 2025-07-13 16:00*

## Overview

This document guides the migration from GraphFlow Gateway to the new lightweight Orchestrator service. The Orchestrator provides simpler, faster routing with better maintainability.

## Architecture Comparison

### GraphFlow Gateway
- **Port**: 8081
- **Complexity**: High - includes PostgreSQL database, complex routing rules
- **Latency**: Variable, depends on DB queries
- **Dependencies**: PostgreSQL, custom rules engine
- **Memory**: Higher due to database requirements

### Orchestrator
- **Port**: 8082  
- **Complexity**: Low - single Ollama agent with YAML config
- **Latency**: < 10ms target for routing decisions
- **Dependencies**: Ollama only
- **Memory**: Minimal, stateless design

## Migration Benefits

1. **Simplicity**: Single configuration file vs database + JSON rules
2. **Performance**: 10ms routing vs variable GraphFlow latency
3. **Maintainability**: Clear YAML config, easy to understand
4. **Reduced Infrastructure**: No dedicated PostgreSQL needed
5. **Better Integration**: Native AutoGen support

## Migration Steps

### Phase 1: Parallel Running (Current State)
Both services run simultaneously for testing:
- GraphFlow on port 8081
- Orchestrator on port 8082

### Phase 2: Traffic Shifting
1. Test orchestrator thoroughly:
   ```bash
   cd /home/geo/directories/autonomy/tests/orchestrator
   ./run_tests.sh
   ```

2. Update any clients using GraphFlow to use Orchestrator:
   - Change endpoint from `http://localhost:8081` to `http://localhost:8082`
   - Update API calls to match new contract

3. Monitor both services for comparison

### Phase 3: GraphFlow Removal

1. Stop GraphFlow container:
   ```bash
   docker-compose -f docker-compose.all.yml stop graphflow_gateway
   ```

2. Remove GraphFlow from docker-compose.all.yml:
   ```yaml
   # Remove these services:
   - graphflow_gateway
   - graphflow_postgres
   - postgres_exporter_graphflow
   ```

3. Clean up volumes:
   ```bash
   docker volume rm autonomy_graphflow_postgres_data
   ```

## API Migration

### GraphFlow API
```http
POST http://localhost:8081/api/v1/stimuli
{
  "text": "What's the BTC price?",
  "metadata": {...}
}
```

### Orchestrator API
```http
POST http://localhost:8082/route
{
  "stimulus_id": "stim_123",
  "text": "What's the BTC price?",
  "context": {...},
  "priority": "normal"
}
```

## Configuration Migration

### GraphFlow Configuration
- Database tables for routing rules
- JSON files for custom rules
- Environment variables for configuration

### Orchestrator Configuration
- Single `api_registry.yaml` file
- All routing logic in one place
- Easy to version control

## Testing Checklist

- [ ] Health checks pass for orchestrator
- [ ] All routing scenarios work correctly
- [ ] Latency meets < 10ms target
- [ ] S1 integration works
- [ ] S2 integration works
- [ ] Hybrid routing works
- [ ] Metrics are collected
- [ ] Error handling works as expected

## Rollback Plan

If issues arise:
1. Stop orchestrator: `docker-compose stop orchestrator`
2. Restart GraphFlow: `docker-compose start graphflow_gateway`
3. Revert client endpoints back to port 8081

## Post-Migration Cleanup

After successful migration:
1. Remove GraphFlow code from repository
2. Update documentation to remove GraphFlow references
3. Update monitoring dashboards
4. Archive GraphFlow configuration for reference

## Monitoring

Compare metrics between services:
- Routing latency: Orchestrator should be consistently < 10ms
- Error rates: Should be equal or lower
- Resource usage: Orchestrator should use less memory/CPU

## Support

For issues during migration:
1. Check orchestrator logs: `docker logs vtuber_orchestrator`
2. Run integration tests
3. Verify API registry is loaded correctly
4. Check Ollama connectivity