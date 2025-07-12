"""
Core System Bootstrap
====================

Central bootstrap system that initializes and wires all services with proper DI.
Single entry point for the entire CORE system.
"""

import asyncio
import logging
import os
import signal
import sys
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Dict, Any, Optional

from ..config import (
    initialize_config, 
    load_development_config, 
    load_production_config, 
    load_test_config,
    get_config,
    SystemMode
)
from ..di import get_container, DIContainer
from ..errors import ErrorHandler
from ..queue import QueueService
from ..processing import StimuliProcessor
from ..character import CharacterManager


logger = logging.getLogger(__name__)


class CoreBootstrap:
    """
    Bootstrap manager for the entire CORE system.
    
    Responsibilities:
    - Configuration initialization
    - Service registration and dependency injection
    - Lifecycle management
    - Graceful shutdown
    - Health monitoring
    """
    
    def __init__(self):
        self.container: Optional[DIContainer] = None
        self.config = None
        self._shutdown_event = asyncio.Event()
        self._startup_complete = False
    
    async def initialize(
        self,
        config_file: Optional[str] = None,
        environment: str = None,
        **config_overrides
    ):
        """
        Initialize the CORE system.
        
        Args:
            config_file: Path to configuration file
            environment: Environment name (development, production, test)
            **config_overrides: Configuration overrides
        """
        try:
            # 1. Initialize configuration
            await self._setup_configuration(config_file, environment, **config_overrides)
            
            # 2. Setup dependency injection
            await self._setup_container()
            
            # 3. Register all services
            await self._register_services()
            
            # 4. Start all services
            await self._start_services()
            
            # 5. Setup signal handlers for graceful shutdown
            self._setup_signal_handlers()
            
            self._startup_complete = True
            logger.info("🚀 CORE system initialization complete!")
            
        except Exception as e:
            logger.error(f"Failed to initialize CORE system: {e}")
            await self.shutdown()
            raise
    
    async def _setup_configuration(
        self,
        config_file: Optional[str],
        environment: Optional[str],
        **overrides
    ):
        """Setup configuration based on environment"""
        environment = environment or os.getenv("CORE_ENVIRONMENT", "development")
        
        if environment == "production":
            self.config = load_production_config()
        elif environment == "test":
            self.config = load_test_config()
        else:
            self.config = load_development_config()
        
        # Apply file-based config if provided
        if config_file and Path(config_file).exists():
            self.config = initialize_config(config_file, **overrides)
        elif overrides:
            # Apply overrides to existing config
            from ..config import CoreConfig
            config_dict = self.config.dict()
            config_dict.update(overrides)
            self.config = CoreConfig.parse_obj(config_dict)
        
        logger.info(f"Configuration loaded for environment: {environment}")
        logger.info(f"System mode: {self.config.system_mode}")
        logger.info(f"Queue type: {self.config.queue.type}")
    
    async def _setup_container(self):
        """Setup dependency injection container"""
        self.container = get_container()
        logger.info("Dependency injection container initialized")
    
    async def _register_services(self):
        """Register all services in the container"""
        # Core services with dependency injection
        self.container.register_singleton(ErrorHandler)
        self.container.register_singleton(QueueService, self._create_queue_service)
        self.container.register_singleton(CharacterManager, self._create_character_manager)
        self.container.register_singleton(StimuliProcessor, self._create_stimuli_processor)
        
        # Register configuration as instance
        self.container.register_instance(self.config, name="CoreConfig")
        
        logger.info("All services registered in DI container")
    
    def _create_queue_service(self) -> QueueService:
        """Factory for QueueService with config injection"""
        return QueueService(self.config.queue)
    
    def _create_character_manager(self, queue_service: QueueService) -> CharacterManager:
        """Factory for CharacterManager with dependencies"""
        return CharacterManager(queue_service)
    
    def _create_stimuli_processor(
        self, 
        queue_service: QueueService, 
        error_handler: ErrorHandler
    ) -> StimuliProcessor:
        """Factory for StimuliProcessor with dependencies"""
        return StimuliProcessor(queue_service, error_handler)
    
    async def _start_services(self):
        """Start all lifecycle services"""
        await self.container.start_all()
        logger.info("All services started successfully")
    
    def _setup_signal_handlers(self):
        """Setup graceful shutdown signal handlers"""
        if sys.platform != "win32":
            for sig in [signal.SIGINT, signal.SIGTERM]:
                signal.signal(sig, self._signal_handler)
    
    def _signal_handler(self, signum, frame):
        """Handle shutdown signals"""
        logger.info(f"Received signal {signum}, initiating graceful shutdown...")
        asyncio.create_task(self.shutdown())
    
    async def shutdown(self):
        """Graceful shutdown of all services"""
        if not self._startup_complete:
            logger.info("Shutdown requested during startup")
            return
        
        logger.info("Starting graceful shutdown...")
        
        try:
            if self.container:
                await self.container.stop_all()
            
            self._shutdown_event.set()
            logger.info("Graceful shutdown complete")
            
        except Exception as e:
            logger.error(f"Error during shutdown: {e}")
    
    async def wait_for_shutdown(self):
        """Wait for shutdown signal"""
        await self._shutdown_event.wait()
    
    async def health_check(self) -> Dict[str, Any]:
        """Comprehensive system health check"""
        if not self._startup_complete or not self.container:
            return {
                "status": "starting",
                "healthy": False,
                "services": {}
            }
        
        try:
            service_health = await self.container.health_check_all()
            
            overall_healthy = all(service_health.values())
            
            # Get service statistics
            stats = {}
            try:
                error_handler = self.container.get(ErrorHandler)
                stats["errors"] = error_handler.get_error_stats()
            except:
                pass
            
            try:
                queue_service = self.container.get(QueueService)
                stats["queues"] = await queue_service.get_stats()
            except:
                pass
            
            try:
                character_manager = self.container.get(CharacterManager)
                stats["characters"] = character_manager.get_system_stats()
            except:
                pass
            
            try:
                stimuli_processor = self.container.get(StimuliProcessor)
                stats["processing"] = stimuli_processor.get_stats()
            except:
                pass
            
            return {
                "status": "running",
                "healthy": overall_healthy,
                "services": service_health,
                "statistics": stats,
                "configuration": {
                    "system_mode": self.config.system_mode.value,
                    "environment": self.config.environment,
                    "queue_type": self.config.queue.type
                }
            }
            
        except Exception as e:
            logger.error(f"Health check failed: {e}")
            return {
                "status": "error",
                "healthy": False,
                "error": str(e)
            }
    
    @asynccontextmanager
    async def lifespan(self):
        """Context manager for full system lifecycle"""
        try:
            yield self
        finally:
            await self.shutdown()
    
    def get_service(self, service_type):
        """Get service from container"""
        if not self.container:
            raise RuntimeError("System not initialized")
        return self.container.get(service_type)


# Global bootstrap instance
_bootstrap: Optional[CoreBootstrap] = None


def get_bootstrap() -> CoreBootstrap:
    """Get global bootstrap instance"""
    global _bootstrap
    if _bootstrap is None:
        _bootstrap = CoreBootstrap()
    return _bootstrap


async def initialize_core_system(
    config_file: Optional[str] = None,
    environment: str = None,
    **config_overrides
) -> CoreBootstrap:
    """
    Initialize the entire CORE system.
    
    Returns the bootstrap instance for lifecycle management.
    """
    bootstrap = get_bootstrap()
    await bootstrap.initialize(config_file, environment, **config_overrides)
    return bootstrap


# Convenience functions for common operations
async def start_simplified_system() -> CoreBootstrap:
    """Start system in simplified S2-only mode"""
    return await initialize_core_system(
        system_mode=SystemMode.SIMPLIFIED,
        environment="development"
    )


async def start_production_system(config_file: str) -> CoreBootstrap:
    """Start system in production mode"""
    return await initialize_core_system(
        config_file=config_file,
        environment="production"
    )


async def start_test_system() -> CoreBootstrap:
    """Start system for testing"""
    return await initialize_core_system(
        environment="test",
        queue={"type": "memory"},  # Use memory queue for tests
        database={"neo4j_uri": "neo4j://localhost:7688"}  # Test database
    )


# Main entry point for standalone execution
async def main():
    """Main entry point for running CORE system standalone"""
    import argparse
    
    parser = argparse.ArgumentParser(description="CORE System Bootstrap")
    parser.add_argument("--config", help="Configuration file path")
    parser.add_argument("--env", default="development", help="Environment (development/production/test)")
    parser.add_argument("--mode", help="System mode (simplified/full_autogen/hybrid)")
    args = parser.parse_args()
    
    # Override config with CLI args
    overrides = {}
    if args.mode:
        overrides["system_mode"] = args.mode
    
    try:
        bootstrap = await initialize_core_system(
            config_file=args.config,
            environment=args.env,
            **overrides
        )
        
        logger.info("🎯 CORE system running. Press Ctrl+C to stop.")
        
        # Wait for shutdown
        await bootstrap.wait_for_shutdown()
        
    except KeyboardInterrupt:
        logger.info("Shutdown requested by user")
    except Exception as e:
        logger.error(f"System error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    # Setup basic logging for standalone execution
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        pass