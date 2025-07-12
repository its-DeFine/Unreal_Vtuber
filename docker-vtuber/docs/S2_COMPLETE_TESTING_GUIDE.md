# S2 Complete Testing Guide

## Overview

This guide covers comprehensive testing of all routing scenarios:
- **S1 Only**: Direct avatar speech (NeuroSync)
- **S2 Only**: Background analysis with specialized teams (AutoGen)
- **S1 + S2**: Combined speech and analysis

## Prerequisites

1. Ensure Docker is running
2. Verify environment variables in `.env` file
3. Check `USE_S2_TEAMS=true` in `docker-compose.all.yml`

## Quick Start

```bash
# 1. Start the system with proper initialization
./scripts/start_s2_system.sh

# 2. Run comprehensive routing tests
python3 scripts/test_all_routing_scenarios.py

# 3. Monitor results
python3 scripts/monitor_s2_queue.py
```

## Detailed Testing Process

### Step 1: System Startup

```bash
cd docker-vtuber
docker-compose -f docker-compose.all.yml up -d
```

Wait for all services to be healthy (about 30 seconds).

### Step 2: Verify Setup

```bash
python3 scripts/verify_s2_setup.py
```

This checks:
- Service health (GraphFlow, NeuroSync, AutoGen)
- S2 teams configuration
- API endpoints availability
- Queue file system

Expected output:
```
✅ GraphFlow is healthy
✅ NeuroSync S1 is healthy
✅ AutoGen S2 is healthy
✅ S2 Teams Enabled: True
✅ Queue Consumer: True
✅ Orchestrator: True
```

### Step 3: Test All Routing Scenarios

```bash
python3 scripts/test_all_routing_scenarios.py --verbose
```

This tests 9 scenarios across 3 routing types:

#### S1 Only Tests (Avatar Speech)
1. **Direct Speech Request**: "Say hello to everyone"
2. **Announcement**: "announce: Welcome to the stream"
3. **Interactive Response**: "Thanks for the donation!"

#### S2 Only Tests (Background Analysis)
1. **Trader Analysis**: Market trends (dr._house character)
2. **Streaming Strategy**: Growth planning (weatherman character)
3. **Educational Content**: Lesson creation (emma_teacher character)

#### S1 + S2 Tests (Combined)
1. **Explain and Demonstrate**: Teaching with speech + analysis
2. **Market Update**: Spoken update + detailed analysis
3. **Stream Planning**: Discussion + strategic analysis

### Step 4: Monitor Processing

In a separate terminal:
```bash
python3 scripts/monitor_s2_queue.py
```

This shows:
- Queue file status (pending items)
- Processed items count
- AutoGen health status
- Real-time updates every 5 seconds

### Step 5: Check Results

After tests complete, check:

1. **Test Summary**:
   ```
   TOTAL: 9/9 passed (100.0%)
   ```

2. **Results File**:
   ```
   routing_test_results_YYYYMMDD_HHMMSS.json
   ```

3. **Queue Files** (in containers):
   ```bash
   docker exec autogen_agent cat /tmp/s2_queue/s2_processing_queue.json | jq .
   docker exec autogen_agent cat /tmp/s2_queue/s2_processed_stimuli.json | jq .
   ```

## Expected Behavior by Routing Type

### S1 Only (AVATAR_ONLY)
- GraphFlow routes to NeuroSync `/process_text`
- Avatar generates speech
- No S2 processing
- Immediate response

### S2 Only (ANALYSIS_ONLY)
- GraphFlow routes to AutoGen `/api/stimuli/receive`
- S2QueueOrchestrator writes to queue file
- Queue consumer picks up within 5 seconds
- Character-specific team processes
- Results stored in processed file

### S1 + S2 (AVATAR_AND_ANALYSIS)
- GraphFlow routes to both systems
- S1 generates speech immediately
- S2 processes in background
- Both systems work independently

## Character-Team Mapping

| Character ID | Team Type | Specialized Tools |
|-------------|-----------|-------------------|
| dr._house_doctor_template | TRADER | market_data_tool, portfolio_tool, risk_analysis_tool |
| weatherman_template | STREAMER | social_media_tool, streaming_tool, content_analytics_tool |
| emma_teacher_template | TEACHER | educational_content_tool, assessment_tool, curriculum_tool |
| secretary_template | DEFAULT | core_evolution_tool, goal_management_tools |

## Troubleshooting

### Services Not Healthy
```bash
docker-compose -f docker-compose.all.yml logs [service_name]
docker-compose -f docker-compose.all.yml restart [service_name]
```

### Queue Not Processing
1. Check AutoGen logs:
   ```bash
   docker logs autogen_agent -f | grep -E "QUEUE_CONSUMER|ERROR"
   ```

2. Verify queue file permissions:
   ```bash
   docker exec autogen_agent ls -la /tmp/s2_queue/
   ```

3. Check S2 teams initialization:
   ```bash
   docker logs autogen_agent | grep "S2 teams initialization"
   ```

### Wrong Routing Decision
1. Check GraphFlow decision matrix:
   ```bash
   docker logs graphflow_gateway | grep -E "Decision:|Nuclear"
   ```

2. Verify metadata flags in test

### API 404 Errors
1. Ensure latest code is deployed
2. Restart AutoGen container
3. Check orchestrator initialization in logs

## Advanced Testing

### Test Specific Routing Type
```bash
python3 scripts/test_all_routing_scenarios.py --routing s2_only
```

### Test with Custom Stimuli
```bash
curl -X POST http://localhost:8000/api/v1/stimuli/submit \
  -H "Content-Type: application/json" \
  -d '{
    "content": "Your custom test content",
    "metadata": {
      "force_s2": true,
      "character_id": "emma_teacher_template"
    }
  }'
```

### Monitor Specific Character Team
```bash
docker logs autogen_agent -f | grep -E "TEACHER|emma"
```

## Performance Expectations

- **S1 Response Time**: < 2 seconds
- **S2 Queue Pickup**: 5 seconds (configurable)
- **S2 Processing Time**: 10-30 seconds (depends on complexity)
- **Memory Usage**: ~2GB per container
- **CPU Usage**: Moderate during processing

## Next Steps

After successful testing:
1. Configure autonomous background processing
2. Set up S2→S1 communication for educator/streamer
3. Enhance role-specific tools
4. Implement continuous learning systems