# Scripts Directory

This directory contains all shell scripts for the autonomy project, organized by functionality.

## Directory Structure

### `/testing`
Scripts for testing various components:
- `simple_character_test.sh` - Simple character testing with visual setup
- `test_character_modes.sh` - Comprehensive character testing including autonomous mode
- `quick_test.sh` - Quick cognitive system connectivity test
- `test_cognitive_live.sh` - Detailed cognitive system diagnostics
- `debug_tool_parsing.sh` - Debug tool parsing functionality
- `test_log_parsing.sh` - Test log parsing capabilities
- `test_obs_realtime.sh` - Test OBS real-time integration
- `test_rtmp_audio.sh` - Test RTMP audio streaming
- `validate_fixes.sh` - Validate system fixes

### `/monitoring`
System monitoring and logging scripts:
- `monitor_autonomous_system.sh` - Production-ready autonomous system monitor
- `docker-log-collector.sh` - Generic Docker log collector
- `simple_monitor_test.sh` - Test monitoring system functionality
- `clean_duplicate_logs.sh` - Clean up old monitoring logs

### `/database`
Database management and diagnostics:
- `diagnose_autonomous_db.sh` - Comprehensive database health diagnostics
- `investigate_database.sh` - Database schema and data analysis
- `run_statistics_migration.sh` - Run statistics database migration

### `/setup`
System setup and initialization:
- `init-ollama.sh` - Initialize Ollama with standard models
- `init-ollama-fast.sh` - Quick Ollama setup with small models
- `setup_ollama_vtuber.sh` - VTuber-specific Ollama Docker setup
- `download-models-host.sh` - Download models to host system
- `check-ollama-health.sh` - Check Ollama service health

### `/docker`
Docker container management:
- `docker-manager.sh` - Comprehensive Docker Compose management tool
- `start-v3-orchestrator.sh` - Start VTuber V3 orchestrator with migration

### `/entrypoints`
Container entrypoint scripts:
- `entrypoint.sh` - Basic entrypoint script
- `combined_entrypoint.sh` - Combined services entrypoint
- `entrypoint_bridge.sh` - NeuroBridge entrypoint
- `run_transcode.sh` - RTMP transcoding script

### `/utils`
Utility scripts:
- `run_cognitive_system.sh` - Run cognitive system
- `test_rtmp_streaming.sh` - Test RTMP streaming functionality

## Usage

Most scripts can be run directly from their location:
```bash
./scripts/testing/simple_character_test.sh
```

Or from the project root:
```bash
scripts/docker/docker-manager.sh --build-run
```

## Important Scripts

### Quick Start
- `scripts/docker/docker-manager.sh` - Main tool for managing all services
- `scripts/testing/quick_test.sh` - Verify system is working

### Development
- `scripts/monitoring/monitor_autonomous_system.sh` - Monitor system activity
- `scripts/database/diagnose_autonomous_db.sh` - Check database health

### Testing
- `scripts/testing/test_character_modes.sh` - Full character testing
- `scripts/testing/test_cognitive_live.sh` - Cognitive system testing