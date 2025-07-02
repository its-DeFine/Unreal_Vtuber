# Quick Start: Running AutoGen V3 Orchestrator

## What Changed

1. **Fixed import names** in `orchestrator_version_manager.py` to properly load V3 components
2. **Added pyautogen** to requirements.txt for AutoGen support
3. **Added graceful fallback** if AutoGen is not installed

## Steps to Run V3

### 1. Rebuild the Container

Since we updated requirements.txt, you need to rebuild:

```bash
# Using docker-compose
docker-compose -f docker-compose.neurobridge.yml build

# Or if using a different compose file
docker-compose -f your-compose-file.yml build
```

### 2. Verify Environment Variables

Your `.env` already has the correct settings:
- `ORCHESTRATOR_VERSION=v3` ✓
- `AUTOGEN_ORCHESTRATOR_ENABLED=true` ✓

### 3. Start the Container

```bash
# Start normally
docker-compose -f docker-compose.neurobridge.yml up -d

# Or use the startup script
./start-v3-orchestrator.sh
```

### 4. Check Logs

Monitor the logs to see if V3 loads successfully:

```bash
# Follow logs
docker-compose logs -f neurosync

# Look for these messages:
# "📌 Orchestrator Version: V3"
# "🎯 Using AutoGen-based Orchestrator V3"
# "✅ V3 (AutoGen) Orchestrator initialized successfully"
```

### 5. Test V3 Endpoints

Once running, test the V3 endpoints:

```bash
# Health check
curl http://localhost:5001/orchestrator/v3/health

# Agent status
curl http://localhost:5001/orchestrator/v3/agents/status

# Get current persona
curl http://localhost:5001/orchestrator/v3/persona
```

## Troubleshooting

### If V3 Still Shows 404

1. **Check if pyautogen installed successfully:**
   ```bash
   docker exec neurosync pip list | grep autogen
   ```

2. **Check for import errors:**
   ```bash
   docker exec neurosync python -c "import autogen; print('AutoGen imported successfully')"
   ```

3. **Check detailed logs:**
   ```bash
   docker logs neurosync 2>&1 | grep -i "orchestrator\|autogen"
   ```

### If AutoGen Installation Fails

The system will gracefully fall back to V2 with warnings. To fix:

1. **Try installing manually in container:**
   ```bash
   docker exec neurosync pip install pyautogen
   ```

2. **Or add to Dockerfile directly:**
   Edit the Dockerfile and add after line 54:
   ```dockerfile
   RUN pip install --no-cache-dir pyautogen>=0.2.0
   ```

## Expected Behavior

When V3 loads successfully:
- `/orchestrator/v3/*` endpoints will respond with 200 status
- Logs will show V3 initialization messages
- Advanced multi-agent features will be available
- Personas can be configured dynamically

## Next Steps

After V3 is running:
1. Test different personas (interactive_streamer, focused_artist)
2. Monitor autonomous content generation
3. Use the new event endpoints for external inputs
4. Check agent coordination in `/orchestrator/v3/agents/status`