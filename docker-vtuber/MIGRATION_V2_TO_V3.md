# Migration Guide: Orchestrator V2 to V3

## Overview

The VTuber system now defaults to the **V3 (AutoGen-based) orchestrator**, which provides superior multi-agent coordination, better content variety, and more sophisticated decision-making capabilities. The V2 orchestrator is deprecated and will be removed in a future release.

## Quick Migration

### Option 1: Automatic Migration (Recommended)

Run the new startup script:

```bash
./start-v3-orchestrator.sh
```

This script will:
- Check your current orchestrator version
- Prompt to upgrade if using V2
- Add necessary V3 configuration
- Start the system with V3

### Option 2: Manual Migration

1. **Update your `.env` file:**

   Change:
   ```env
   # ORCHESTRATOR_VERSION=v2  # Old (if present)
   ```

   To:
   ```env
   ORCHESTRATOR_VERSION=v3
   ```

2. **Add V3 configuration to `.env`:**

   ```env
   # AutoGen V3 Configuration
   AUTOGEN_ORCHESTRATOR_ENABLED=true
   ORCHESTRATOR_PERSONA=interactive_streamer
   AUTONOMOUS_CONTENT_ENABLED=true
   GROUP_CHAT_ENABLED=true
   SCB_INTEGRATION_ENABLED=true
   ```

3. **Start your containers normally:**

   ```bash
   docker-compose up -d
   # or
   ./your-usual-startup-script.sh
   ```

## What's New in V3

### 1. **Multi-Agent Architecture**
- **Orchestrator Agent**: Main coordinator
- **Content Filter Agent**: Applies persona-based filtering
- **Speech Coordinator**: Manages speech generation
- **Environment Controller**: Handles game/avatar changes
- **Idle Content Agent**: Generates autonomous content
- **Decision Agent**: Determines when to act

### 2. **Configurable Personas**

V3 supports different streaming personas:

- **`interactive_streamer`** (default): High engagement, frequent responses
- **`focused_artist`**: Longer quiet periods, art-focused content
- **`casual_gamer`**: Balanced interaction, game-focused

Set in `.env`:
```env
ORCHESTRATOR_PERSONA=interactive_streamer
```

### 3. **Enhanced Autonomous Content**

V3 provides better variety in autonomous content generation:
- Context-aware idle content
- Activity-based responses
- Dynamic pacing based on viewer count
- Content variety tracking to avoid repetition

### 4. **New API Endpoints**

V3 adds new endpoints while maintaining V2 compatibility:

- `/orchestrator/v3/process` - Process external inputs with agent reasoning
- `/orchestrator/v3/persona` - Get/set persona configuration
- `/orchestrator/v3/agents/status` - Monitor agent states
- `/orchestrator/v3/autonomous/control` - Control autonomous behavior
- `/orchestrator/v3/autonomous/stats` - View performance metrics

## Configuration Options

### Basic Configuration

```env
# Enable V3
ORCHESTRATOR_VERSION=v3
AUTOGEN_ORCHESTRATOR_ENABLED=true

# Choose persona
ORCHESTRATOR_PERSONA=interactive_streamer

# Enable features
AUTONOMOUS_CONTENT_ENABLED=true
GROUP_CHAT_ENABLED=true
SCB_INTEGRATION_ENABLED=true
```

### Advanced Configuration

```env
# Timing controls (seconds)
MIN_IDLE_TIME=8
MAX_IDLE_TIME=20

# Content variety
CONTENT_VARIETY=high  # high, medium, low

# Agent settings
SCB_MAX_INPUTS=3
AGENT_DECISION_TIMEOUT=5000
MAX_AGENT_ROUNDS=10

# Agent temperatures
ORCHESTRATOR_AGENT_TEMP=0.3
FILTER_AGENT_TEMP=0.1
SPEECH_AGENT_TEMP=0.7
IDLE_AGENT_TEMP=0.8
```

## Compatibility

### Backward Compatibility

V3 maintains full backward compatibility with V2:
- All existing endpoints continue to work
- `/process_text` and `/game_control` function identically
- V2 orchestrator routes are supported

### Breaking Changes

None! V3 is designed as a drop-in replacement.

## Troubleshooting

### 1. Import Errors

If you see import errors for V3 components:
```bash
# Ensure all V3 files are present
ls -la autogen_*.py orchestrator_integration_v3.py
```

### 2. V3 Not Starting

Check logs:
```bash
docker-compose logs neurosync | grep -i orchestrator
```

Verify environment:
```bash
grep ORCHESTRATOR_VERSION .env
```

### 3. Falling Back to V2

If V3 fails to initialize, the system automatically falls back to V2 with a warning. Check logs to diagnose the issue.

### 4. Performance Issues

V3 uses more sophisticated decision-making which may require more resources:
- Ensure adequate CPU/memory
- Consider adjusting `AGENT_DECISION_TIMEOUT`
- Monitor with `/orchestrator/v3/agents/status`

## Rollback (If Needed)

To rollback to V2:

```env
ORCHESTRATOR_VERSION=v2
```

Note: V2 is deprecated and this option will be removed in future releases.

## Support

For issues or questions:
1. Check logs: `docker-compose logs -f neurosync`
2. Monitor status: `curl http://localhost:5001/orchestrator/v3/agents/status`
3. Review configuration: Ensure all V3 settings are present in `.env`

## Next Steps

After migration:
1. Test the system with various inputs
2. Adjust persona settings to match your streaming style
3. Monitor autonomous content generation
4. Explore new V3 API endpoints
5. Provide feedback for future improvements