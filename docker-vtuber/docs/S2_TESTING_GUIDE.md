# S2 Teams Testing Guide

## Quick Start

After starting the Docker containers with S2 teams enabled:

```bash
# 1. Check service health
curl http://localhost:8000/health   # GraphFlow
curl http://localhost:8200/health   # AutoGen

# 2. Test S2 queue system
python3 scripts/test_s2_queue_system.py --test-characters

# 3. Monitor queue processing in real-time
python3 scripts/monitor_s2_queue.py
```

## Testing Different Character Teams

### 1. Trader Team (S2 Only)
Send market analysis requests:
```bash
curl -X POST http://localhost:8000/api/v1/stimuli/submit \
  -H "Content-Type: application/json" \
  -d '{
    "content": "Analyze Bitcoin trends and investment opportunities",
    "source": "test",
    "metadata": {
      "force_s2": true,
      "character_id": "dr._house_doctor_template"
    }
  }'
```

### 2. Streamer Team
Send streaming-related queries:
```bash
curl -X POST http://localhost:8000/api/v1/stimuli/submit \
  -H "Content-Type: application/json" \
  -d '{
    "content": "How can I improve my streaming setup and grow my audience?",
    "source": "test",
    "metadata": {
      "force_s2": true,
      "character_id": "weatherman_template"
    }
  }'
```

### 3. Teacher Team
Send educational requests:
```bash
curl -X POST http://localhost:8000/api/v1/stimuli/submit \
  -H "Content-Type: application/json" \
  -d '{
    "content": "Explain machine learning concepts for beginners",
    "source": "test",
    "metadata": {
      "force_s2": true,
      "character_id": "emma_teacher_template"
    }
  }'
```

## Verifying S2 Processing

1. **Check Queue File**:
   ```bash
   # Inside autogen container
   docker exec -it autogen_agent cat /tmp/s2_queue/s2_processing_queue.json | jq .
   ```

2. **Check Processed Items**:
   ```bash
   docker exec -it autogen_agent cat /tmp/s2_queue/s2_processed_stimuli.json | jq .
   ```

3. **View AutoGen Logs**:
   ```bash
   docker logs autogen_agent -f | grep -E "QUEUE_CONSUMER|S2"
   ```

## Expected Behavior

1. **Routing**: S2-targeted stimuli should show decision "ANALYSIS_ONLY"
2. **Queue**: Items should appear in queue file within seconds
3. **Processing**: Queue consumer should process items every 5 seconds
4. **Teams**: Correct team should activate based on character_id
5. **Tools**: Team-specific tools should be triggered

## Troubleshooting

### API Returns 404
- Check AutoGen health endpoint includes `s2_teams_status`
- Verify `USE_S2_TEAMS=true` in docker-compose
- Restart AutoGen container

### Queue Not Processing
- Check queue file exists and is writable
- Verify queue consumer is running in AutoGen logs
- Check poll interval (default: 5 seconds)

### Wrong Team Activated
- Verify character_id in metadata
- Check character team mapping in logs
- Ensure character is loaded in S1

## Configuration

Key environment variables:
```yaml
USE_S2_TEAMS: true
S2_QUEUE_FILE: /tmp/s2_queue/s2_processing_queue.json
S2_POLL_INTERVAL: 5
S2_EXECUTION_INTERVAL: 60
```

## Next Steps

After verifying basic functionality:
1. Test autonomous background processing
2. Verify SCB communication
3. Check Neo4j semantic storage
4. Test S2→S1 communication for educator/streamer roles