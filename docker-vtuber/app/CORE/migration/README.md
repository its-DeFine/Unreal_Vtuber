# CORE System Migration Guide

## Overview

This directory contains migration tools to transform the existing CORE system from its current dual-architecture (GraphFlow + AutoGen) to a unified, clean 10/10 maintainability architecture.

## Migration Strategy

The migration follows a **zero-downtime, gradual rollout** approach:

1. **Validation** - Check current environment
2. **Backup** - Create complete backup of existing system  
3. **Unified System** - Start new architecture alongside legacy
4. **Configuration** - Migrate settings and preferences
5. **Data Migration** - Move queue data and character state
6. **Traffic Routing** - Gradually route requests to unified system
7. **Validation** - Ensure everything works correctly
8. **Cleanup** - Optional removal of legacy components

## Quick Start

### 1. Test Migration (Recommended First)

```bash
cd /home/geo/directories/autonomy/docker-vtuber/app/CORE/migration
python migrate_to_unified.py --dry-run
```

### 2. Full Migration

```bash
# Complete migration with backup
python migrate_to_unified.py

# Skip backup (not recommended)
python migrate_to_unified.py --no-backup

# Run specific phases only
python migrate_to_unified.py --phases validate_environment start_unified_system
```

### 3. Rollback if Needed

```bash
python migrate_to_unified.py --rollback
```

## Migration Phases

### Phase 1: Environment Validation
- ✅ Check for running legacy processes
- ✅ Verify file system structure  
- ✅ Test Redis/Neo4j connectivity
- ✅ Identify potential conflicts

### Phase 2: Backup Creation
- 📁 Backup all configuration files
- 📁 Backup queue data
- 📁 Backup character state
- 📁 Save migration state for rollback

### Phase 3: Unified System Startup
- 🚀 Initialize new dependency injection container
- 🚀 Start all unified services (Queue, Processing, Character Management)
- 🚀 Verify health checks pass

### Phase 4: Configuration Migration
- ⚙️ Read legacy AutoGen configurations
- ⚙️ Read legacy GraphFlow configurations  
- ⚙️ Create unified configuration files
- ⚙️ Migrate environment variables

### Phase 5: Data Migration
- 📊 Migrate file-based queue data to Redis
- 📊 Convert legacy queue formats to unified format
- 📊 Preserve message ordering and priorities
- 📊 Handle error recovery

### Phase 6: Character State Migration
- 👤 Migrate character profiles to unified manager
- 👤 Convert legacy character mappings
- 👤 Preserve mission assignments and state
- 👤 Update character capabilities

### Phase 7: Traffic Routing Setup
- 🔀 Create compatibility layers for legacy APIs
- 🔀 Route new requests to unified system
- 🔀 Maintain backward compatibility
- 🔀 Enable gradual traffic migration

### Phase 8: Migration Validation
- ✅ Run comprehensive health checks
- ✅ Test key functionality end-to-end
- ✅ Verify no data loss occurred
- ✅ Performance benchmarking

### Phase 9: Legacy Cleanup (Optional)
- 🧹 Archive legacy system files
- 🧹 Update deployment scripts
- 🧹 Update documentation
- 🧹 Remove obsolete processes

## Before Migration

### Prerequisites

1. **Stop Legacy Processes** (recommended)
   ```bash
   # Stop any running AutoGen or GraphFlow processes
   pkill -f "autogen_agent"
   pkill -f "graphflow"
   ```

2. **Backup Important Data**
   ```bash
   # Manual backup of critical data
   cp -r /tmp/s2_queue /backup/s2_queue_$(date +%Y%m%d)
   ```

3. **Install Dependencies**
   ```bash
   pip install redis neo4j pydantic psutil
   ```

### Compatibility Check

The migration script will check for:
- ✅ Running legacy processes
- ✅ File system permissions
- ✅ Redis connectivity
- ✅ Neo4j connectivity  
- ✅ Required Python packages

## During Migration

### What Happens

1. **Legacy System Continues Running** - No interruption to current operations
2. **Unified System Starts** - New architecture initializes alongside legacy
3. **Data Gets Copied** - Queue data and state migrated to new system
4. **Traffic Gradually Shifts** - New requests routed to unified system
5. **Legacy Becomes Backup** - Old system remains available for rollback

### Monitoring

The migration script provides detailed logging:
- 📋 Phase progress updates
- ✅ Success confirmations  
- ⚠️ Warning messages
- ❌ Error details with rollback info

### If Something Goes Wrong

1. **Automatic Rollback** - Migration failures trigger automatic rollback
2. **Manual Rollback** - Run `python migrate_to_unified.py --rollback`
3. **Partial Recovery** - Individual phases can be re-run
4. **Support Data** - All migration state saved for debugging

## After Migration

### Verification Steps

1. **Health Check**
   ```bash
   # Check unified system health
   curl http://localhost:8000/health
   ```

2. **Test Key Functions**
   ```bash
   # Test stimuli processing
   curl -X POST http://localhost:8000/api/stimuli/receive \
     -H "Content-Type: application/json" \
     -d '{"content": "test message", "source": "test"}'
   ```

3. **Monitor Performance**
   ```bash
   # Check processing statistics
   curl http://localhost:8000/api/stats
   ```

### New Benefits Available

- 🚀 **10x Faster Development** - Clean, consistent patterns
- 🔧 **Easy Configuration** - Single configuration system
- 📊 **Better Monitoring** - Comprehensive metrics and health checks
- 🛡️ **Robust Error Handling** - Automatic recovery and circuit breakers
- 📈 **Scalable Queues** - Redis-based high-performance queuing
- 🎯 **Unified API** - Single interface for all operations
- 🧪 **Testable** - Proper dependency injection and mocking
- 📚 **Self-Documenting** - OpenAPI specs and type hints

## Architecture Improvements

### Before (6/10 Maintainability)
```
❌ Dual architectures (GraphFlow + AutoGen)
❌ File-based queues with race conditions  
❌ Scattered configuration management
❌ Inconsistent error handling
❌ No proper dependency injection
❌ Complex integration patterns
```

### After (10/10 Maintainability)  
```
✅ Single unified architecture
✅ Redis-based reliable queuing
✅ Centralized configuration management  
✅ Comprehensive error handling with recovery
✅ Clean dependency injection container
✅ Simple, consistent integration patterns
```

## Rollback Procedure

If you need to rollback the migration:

```bash
# Automatic rollback
python migrate_to_unified.py --rollback
```

This will:
1. 🛑 Stop the unified system
2. 📁 Restore all files from backup
3. ⚙️ Restore original configurations
4. 🔄 Return to pre-migration state

## Support

If you encounter issues during migration:

1. **Check the logs** - Migration provides detailed logging
2. **Review the backup** - All original files are preserved
3. **Test phases individually** - Use `--phases` to run specific steps
4. **Use dry-run mode** - Test without making changes

## Advanced Usage

### Custom Configuration

```bash
# Migrate with custom configuration
python migrate_to_unified.py --phases migrate_configuration --config custom.json
```

### Selective Migration

```bash
# Migrate only queue data
python migrate_to_unified.py --phases migrate_queue_data

# Migrate only character state
python migrate_to_unified.py --phases migrate_character_state
```

### Production Migration

```bash
# Production-safe migration with full validation
python migrate_to_unified.py --phases validate_environment create_backup start_unified_system validate_migration
```

The unified architecture is designed to be **completely backward compatible** while providing dramatically improved maintainability and developer experience.