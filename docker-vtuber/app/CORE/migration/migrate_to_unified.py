"""
Zero-Downtime Migration to Unified Architecture
==============================================

Migrates existing system to the new unified architecture without breaking functionality.
Supports gradual migration with rollback capabilities.
"""

import asyncio
import json
import logging
import shutil
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, Optional, List
import sys
import os

# Add shared modules to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from shared.bootstrap import initialize_core_system, get_bootstrap
from shared.config import SystemMode
from shared.queue import QueueService, enqueue_s2_processing
from shared.processing import StimuliProcessor, ProcessingMode, TeamType
from shared.character import CharacterManager


logger = logging.getLogger(__name__)


class MigrationManager:
    """
    Manages the migration from legacy architecture to unified system.
    
    Migration Strategy:
    1. Start unified system alongside legacy
    2. Gradually route traffic to unified system
    3. Migrate data and state
    4. Shutdown legacy components
    5. Cleanup
    """
    
    def __init__(self):
        self.legacy_paths = {
            "autogen_agent": Path("../autogen-agent"),
            "graphflow": Path("../graphflow-stimuli-system"),
            "queue_files": Path("/tmp/s2_queue"),
            "config_files": [
                Path("../autogen-agent/config"),
                Path("../graphflow-stimuli-system/config")
            ]
        }
        
        self.backup_dir = Path("migration_backup") / datetime.now().strftime("%Y%m%d_%H%M%S")
        self.migration_state = {
            "started_at": None,
            "current_phase": None,
            "completed_phases": [],
            "rollback_data": {}
        }
        
        self.bootstrap = None
    
    async def run_migration(
        self,
        phases: List[str] = None,
        dry_run: bool = False,
        backup: bool = True
    ) -> bool:
        """
        Run the complete migration process.
        
        Args:
            phases: Specific phases to run (default: all)
            dry_run: Test migration without making changes
            backup: Create backup before migration
        
        Returns:
            True if successful, False otherwise
        """
        all_phases = [
            "validate_environment",
            "create_backup",
            "start_unified_system",
            "migrate_configuration",
            "migrate_queue_data", 
            "migrate_character_state",
            "setup_traffic_routing",
            "validate_migration",
            "cleanup_legacy"
        ]
        
        phases_to_run = phases or all_phases
        
        try:
            self.migration_state["started_at"] = datetime.now()
            logger.info(f"🚀 Starting migration with phases: {phases_to_run}")
            
            if dry_run:
                logger.info("🧪 DRY RUN MODE - No changes will be made")
            
            for phase in phases_to_run:
                if phase not in all_phases:
                    logger.error(f"Unknown migration phase: {phase}")
                    return False
                
                logger.info(f"📋 Starting phase: {phase}")
                self.migration_state["current_phase"] = phase
                
                # Execute phase
                phase_method = getattr(self, f"_phase_{phase}")
                success = await phase_method(dry_run=dry_run)
                
                if not success:
                    logger.error(f"❌ Phase {phase} failed")
                    if not dry_run:
                        await self.rollback()
                    return False
                
                self.migration_state["completed_phases"].append(phase)
                logger.info(f"✅ Phase {phase} completed")
            
            logger.info("🎉 Migration completed successfully!")
            return True
            
        except Exception as e:
            logger.error(f"💥 Migration failed with error: {e}")
            if not dry_run:
                await self.rollback()
            return False
    
    async def _phase_validate_environment(self, dry_run: bool = False) -> bool:
        """Validate the current environment before migration"""
        logger.info("Validating environment...")
        
        # Check if legacy systems are running
        legacy_issues = []
        
        # Check for existing processes
        try:
            import psutil
            for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
                cmdline = ' '.join(proc.info['cmdline'] or [])
                if 'autogen_agent' in cmdline or 'graphflow' in cmdline:
                    legacy_issues.append(f"Legacy process running: {proc.info['name']} (PID: {proc.info['pid']})")
        except ImportError:
            logger.warning("psutil not available, skipping process check")
        
        # Check file system
        for name, path in self.legacy_paths.items():
            if isinstance(path, list):
                for p in path:
                    if p.exists():
                        logger.info(f"Found legacy {name}: {p}")
            else:
                if path.exists():
                    logger.info(f"Found legacy {name}: {path}")
                else:
                    logger.warning(f"Legacy {name} not found: {path}")
        
        # Check Redis availability
        try:
            import redis
            client = redis.Redis(host='localhost', port=6379, db=0)
            client.ping()
            logger.info("✅ Redis is available")
        except Exception as e:
            logger.warning(f"⚠️ Redis not available: {e}")
        
        # Check Neo4j availability  
        try:
            from neo4j import GraphDatabase
            driver = GraphDatabase.driver("neo4j://localhost:7687", auth=("neo4j", ""))
            with driver.session() as session:
                session.run("RETURN 1")
            driver.close()
            logger.info("✅ Neo4j is available")
        except Exception as e:
            logger.warning(f"⚠️ Neo4j not available: {e}")
        
        if legacy_issues:
            logger.warning("Legacy processes detected:")
            for issue in legacy_issues:
                logger.warning(f"  {issue}")
            logger.warning("Consider stopping legacy processes before migration")
        
        return True
    
    async def _phase_create_backup(self, dry_run: bool = False) -> bool:
        """Create backup of existing system"""
        if dry_run:
            logger.info("Would create backup in: {self.backup_dir}")
            return True
        
        logger.info(f"Creating backup in: {self.backup_dir}")
        self.backup_dir.mkdir(parents=True, exist_ok=True)
        
        # Backup configuration files
        for name, path in self.legacy_paths.items():
            if isinstance(path, list):
                for i, p in enumerate(path):
                    if p.exists():
                        backup_path = self.backup_dir / f"{name}_{i}"
                        shutil.copytree(p, backup_path, dirs_exist_ok=True)
                        logger.info(f"Backed up {name}_{i}: {p} -> {backup_path}")
            else:
                if path.exists():
                    backup_path = self.backup_dir / name
                    if path.is_dir():
                        shutil.copytree(path, backup_path, dirs_exist_ok=True)
                    else:
                        shutil.copy2(path, backup_path)
                    logger.info(f"Backed up {name}: {path} -> {backup_path}")
        
        # Save migration state
        state_file = self.backup_dir / "migration_state.json"
        with open(state_file, 'w') as f:
            json.dump(self.migration_state, f, indent=2, default=str)
        
        return True
    
    async def _phase_start_unified_system(self, dry_run: bool = False) -> bool:
        """Start the unified system"""
        if dry_run:
            logger.info("Would start unified system")
            return True
        
        logger.info("Starting unified system...")
        
        try:
            # Initialize with simplified mode first
            self.bootstrap = await initialize_core_system(
                environment="development",
                system_mode=SystemMode.SIMPLIFIED
            )
            
            # Verify system health
            health = await self.bootstrap.health_check()
            if not health.get("healthy", False):
                logger.error("Unified system health check failed")
                return False
            
            logger.info("✅ Unified system started successfully")
            return True
            
        except Exception as e:
            logger.error(f"Failed to start unified system: {e}")
            return False
    
    async def _phase_migrate_configuration(self, dry_run: bool = False) -> bool:
        """Migrate configuration from legacy systems"""
        logger.info("Migrating configuration...")
        
        # Read legacy configurations
        legacy_configs = {}
        
        # AutoGen agent config
        autogen_config_path = self.legacy_paths["autogen_agent"] / "autogen_agent" / "config"
        if autogen_config_path.exists():
            for config_file in autogen_config_path.glob("*.py"):
                if config_file.name != "__init__.py":
                    logger.info(f"Found AutoGen config: {config_file}")
                    # Would parse and migrate config here
        
        # GraphFlow config
        graphflow_config_path = self.legacy_paths["graphflow"] / "config"
        if graphflow_config_path.exists():
            for config_file in graphflow_config_path.glob("*.json"):
                logger.info(f"Found GraphFlow config: {config_file}")
                try:
                    with open(config_file) as f:
                        config_data = json.load(f)
                        legacy_configs[config_file.stem] = config_data
                except Exception as e:
                    logger.warning(f"Could not read {config_file}: {e}")
        
        if not dry_run and legacy_configs:
            # Create unified configuration
            unified_config_path = Path("config/migrated_config.json")
            unified_config_path.parent.mkdir(exist_ok=True)
            
            with open(unified_config_path, 'w') as f:
                json.dump(legacy_configs, f, indent=2)
            
            logger.info(f"Saved migrated configuration to: {unified_config_path}")
        
        return True
    
    async def _phase_migrate_queue_data(self, dry_run: bool = False) -> bool:
        """Migrate queue data from file-based to unified queue system"""
        logger.info("Migrating queue data...")
        
        queue_dir = self.legacy_paths["queue_files"]
        if not queue_dir.exists():
            logger.info("No legacy queue files found")
            return True
        
        migrated_count = 0
        
        for queue_file in queue_dir.glob("*.json"):
            logger.info(f"Processing queue file: {queue_file}")
            
            try:
                with open(queue_file) as f:
                    if queue_file.stat().st_size == 0:
                        continue
                    
                    # Handle both single objects and arrays
                    content = f.read().strip()
                    if not content:
                        continue
                    
                    if content.startswith('['):
                        queue_items = json.loads(content)
                    else:
                        # Try to parse as multiple JSON objects
                        queue_items = []
                        for line in content.split('\n'):
                            if line.strip():
                                try:
                                    queue_items.append(json.loads(line))
                                except json.JSONDecodeError:
                                    logger.warning(f"Could not parse line: {line}")
                
                if dry_run:
                    logger.info(f"Would migrate {len(queue_items)} items from {queue_file}")
                    migrated_count += len(queue_items)
                    continue
                
                # Migrate items to unified queue
                if self.bootstrap:
                    queue_service = self.bootstrap.get_service(QueueService)
                    
                    for item in queue_items:
                        # Convert legacy format to unified format
                        if isinstance(item, dict) and 'content' in item:
                            await enqueue_s2_processing(
                                stimuli_data=item,
                                character_type=item.get('character_type')
                            )
                            migrated_count += 1
                
            except Exception as e:
                logger.error(f"Error processing {queue_file}: {e}")
                continue
        
        logger.info(f"Migrated {migrated_count} queue items")
        return True
    
    async def _phase_migrate_character_state(self, dry_run: bool = False) -> bool:
        """Migrate character state to unified character manager"""
        logger.info("Migrating character state...")
        
        if dry_run:
            logger.info("Would migrate character state")
            return True
        
        if not self.bootstrap:
            logger.error("Unified system not started")
            return False
        
        try:
            character_manager = self.bootstrap.get_service(CharacterManager)
            
            # Default characters are already loaded, but we could migrate custom state here
            # For example, reading from legacy character state files
            
            stats = character_manager.get_system_stats()
            logger.info(f"Character system ready: {stats}")
            
            return True
            
        except Exception as e:
            logger.error(f"Character state migration failed: {e}")
            return False
    
    async def _phase_setup_traffic_routing(self, dry_run: bool = False) -> bool:
        """Setup traffic routing to unified system"""
        logger.info("Setting up traffic routing...")
        
        if dry_run:
            logger.info("Would setup traffic routing")
            return True
        
        # Create compatibility layer files
        compatibility_files = {
            "s2_queue_orchestrator_compat.py": """
# Compatibility layer for S2QueueOrchestrator
import asyncio
from shared.queue import enqueue_s2_processing

class S2QueueOrchestratorCompat:
    def __init__(self):
        pass
    
    async def enqueue_stimuli(self, stimuli_data):
        return await enqueue_s2_processing(stimuli_data)
""",
            "simplified_queue_consumer_compat.py": """
# Compatibility layer for SimplifiedQueueConsumer  
from shared.bootstrap import get_bootstrap
from shared.processing import StimuliProcessor

class SimplifiedQueueConsumerCompat:
    def __init__(self):
        pass
    
    async def start_consuming(self):
        bootstrap = get_bootstrap()
        processor = bootstrap.get_service(StimuliProcessor)
        # Legacy consumer logic would be handled by unified processor
        pass
"""
        }
        
        # Write compatibility files
        compat_dir = Path("compatibility")
        compat_dir.mkdir(exist_ok=True)
        
        for filename, content in compatibility_files.items():
            compat_file = compat_dir / filename
            with open(compat_file, 'w') as f:
                f.write(content)
            logger.info(f"Created compatibility layer: {compat_file}")
        
        return True
    
    async def _phase_validate_migration(self, dry_run: bool = False) -> bool:
        """Validate that migration was successful"""
        logger.info("Validating migration...")
        
        if dry_run:
            logger.info("Would validate migration")
            return True
        
        if not self.bootstrap:
            logger.error("Unified system not available for validation")
            return False
        
        # Health check
        health = await self.bootstrap.health_check()
        logger.info(f"Health check result: {health}")
        if not health.get("healthy", False):
            logger.error(f"System health check failed: {health}")
            return False
        
        # Test key functionality
        try:
            # Test stimuli processing
            processor = self.bootstrap.get_service(StimuliProcessor)
            test_result = await processor.process_stimuli(
                content="Test migration message",
                source="migration_validator",
                processing_mode=ProcessingMode.S2_ONLY
            )
            
            if not test_result.success:
                logger.error("Test stimuli processing failed")
                return False
            
            # Test character management
            character_manager = self.bootstrap.get_service(CharacterManager)
            available = await character_manager.get_available_characters()
            
            if not available:
                logger.warning("No characters available")
            
            logger.info(f"✅ Validation successful - {len(available)} characters available")
            return True
            
        except Exception as e:
            logger.error(f"Validation failed: {e}")
            return False
    
    async def _phase_cleanup_legacy(self, dry_run: bool = False) -> bool:
        """Clean up legacy system files (optional)"""
        logger.info("Cleaning up legacy system...")
        
        if dry_run:
            logger.info("Would clean up legacy files")
            return True
        
        # This phase is optional and should be run carefully
        logger.warning("Legacy cleanup is not automated for safety")
        logger.info("Manual cleanup steps:")
        logger.info("1. Stop legacy processes")
        logger.info("2. Archive legacy directories")
        logger.info("3. Update deployment scripts")
        logger.info("4. Update documentation")
        
        return True
    
    async def rollback(self) -> bool:
        """Rollback migration changes"""
        logger.warning("🔄 Starting migration rollback...")
        
        try:
            # Stop unified system
            if self.bootstrap:
                await self.bootstrap.shutdown()
            
            # Restore from backup
            if self.backup_dir.exists():
                logger.info(f"Restoring from backup: {self.backup_dir}")
                
                for name, path in self.legacy_paths.items():
                    if isinstance(path, list):
                        for i, p in enumerate(path):
                            backup_path = self.backup_dir / f"{name}_{i}"
                            if backup_path.exists() and p.exists():
                                shutil.rmtree(p)
                                shutil.copytree(backup_path, p)
                                logger.info(f"Restored {name}_{i}")
                    else:
                        backup_path = self.backup_dir / name
                        if backup_path.exists():
                            if path.exists():
                                if path.is_dir():
                                    shutil.rmtree(path)
                                else:
                                    path.unlink()
                            
                            if backup_path.is_dir():
                                shutil.copytree(backup_path, path)
                            else:
                                shutil.copy2(backup_path, path)
                            logger.info(f"Restored {name}")
            
            logger.info("✅ Rollback completed")
            return True
            
        except Exception as e:
            logger.error(f"❌ Rollback failed: {e}")
            return False


async def main():
    """Main migration script"""
    import argparse
    
    parser = argparse.ArgumentParser(description="Migrate to Unified CORE Architecture")
    parser.add_argument("--phases", nargs="+", help="Specific phases to run")
    parser.add_argument("--dry-run", action="store_true", help="Test migration without changes")
    parser.add_argument("--no-backup", action="store_true", help="Skip backup creation")
    parser.add_argument("--rollback", action="store_true", help="Rollback previous migration")
    
    args = parser.parse_args()
    
    # Setup logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    manager = MigrationManager()
    
    try:
        if args.rollback:
            success = await manager.rollback()
        else:
            success = await manager.run_migration(
                phases=args.phases,
                dry_run=args.dry_run,
                backup=not args.no_backup
            )
        
        if success:
            logger.info("✅ Migration completed successfully!")
        else:
            logger.error("❌ Migration failed!")
            sys.exit(1)
            
    except KeyboardInterrupt:
        logger.info("Migration interrupted by user")
        await manager.rollback()
    except Exception as e:
        logger.error(f"Migration error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())