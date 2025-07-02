"""
Orchestrator Version Manager
===========================

This module manages the selection and initialization of the appropriate orchestrator version
based on environment configuration. It provides a seamless way to switch between V2 (deprecated),
V3 (AutoGen-based), and Reactive (character-driven) orchestrators.

Default: reactive (Character-driven reactive system)
"""

import os
import logging
from typing import Optional, Any
from flask import Flask

# Configure logging
logger = logging.getLogger(__name__)


class OrchestratorVersionManager:
    """Manages orchestrator version selection and initialization"""
    
    def __init__(self):
        self.version = os.getenv("ORCHESTRATOR_VERSION", "reactive").lower()
        self.orchestrator_instance = None
        self.wrapper_instance = None
        
        # Log deprecation warning for V2
        if self.version == "v2":
            logger.warning(
                "⚠️ DEPRECATION WARNING: Orchestrator V2 is deprecated and will be removed in a future release. "
                "Please migrate to V3 (AutoGen) or Reactive (character-driven) orchestrator"
            )
        elif self.version == "v3":
            logger.info(
                "ℹ️ Using AutoGen-based orchestrator V3. Consider the new Reactive orchestrator for "
                "simplified character-driven interactions"
            )
        
        logger.info(f"🎯 Orchestrator Version Manager initialized with version: {self.version.upper()}")
    
    def initialize_orchestrator(self, app: Flask, system_objects: dict = None) -> Optional[Any]:
        """Initialize the appropriate orchestrator version"""
        
        if self.version == "reactive":
            return self._initialize_reactive_orchestrator(app, system_objects)
        elif self.version == "v3":
            return self._initialize_v3_orchestrator(app, system_objects)
        elif self.version == "v2":
            return self._initialize_v2_orchestrator(app, system_objects)
        else:
            logger.error(f"❌ Unknown orchestrator version: {self.version}. Defaulting to Reactive.")
            self.version = "reactive"
            return self._initialize_reactive_orchestrator(app, system_objects)
    
    def _initialize_reactive_orchestrator(self, app: Flask, system_objects: dict = None) -> Optional[Any]:
        """Initialize the Reactive (character-driven) orchestrator"""
        logger.info("🎭 Initializing Reactive (Character-driven) Orchestrator...")
        
        try:
            # Import Reactive orchestrator components
            from reactive_llm_integration import initialize_reactive_orchestrator
            
            # Initialize reactive wrapper
            self.wrapper_instance = initialize_reactive_orchestrator(app, system_objects)
            
            if self.wrapper_instance:
                # Get the orchestrator instance
                self.orchestrator_instance = self.wrapper_instance.orchestrator
                
                logger.info("✅ Reactive Orchestrator initialized successfully")
                logger.info("🎯 Character-driven system ready for external events and reactive responses")
                return self.wrapper_instance
            else:
                logger.error("❌ Failed to initialize Reactive orchestrator wrapper")
                return None
            
        except ImportError as e:
            logger.error(f"❌ Failed to import Reactive orchestrator components: {e}")
            logger.info("📝 Falling back to V3 orchestrator...")
            self.version = "v3"
            return self._initialize_v3_orchestrator(app, system_objects)
        except Exception as e:
            logger.error(f"❌ Failed to initialize Reactive orchestrator: {e}")
            import traceback
            logger.error(traceback.format_exc())
            return None
    
    def _initialize_v3_orchestrator(self, app: Flask, system_objects: dict = None) -> Optional[Any]:
        """Initialize the V3 (AutoGen) orchestrator"""
        logger.info("🚀 Initializing V3 (AutoGen) Orchestrator...")
        
        try:
            # Import V3 orchestrator components
            from orchestrator_integration_v3 import (
                AutoGenOrchestrationWrapper as OrchestrationWrapperV3,
                AutoGenOrchestrationConfig as OrchestrationConfigV3
            )
            from autogen_api_routes import register_autogen_routes
            
            # Create V3 configuration
            config = OrchestrationConfigV3()
            
            # Create V3 wrapper
            self.wrapper_instance = OrchestrationWrapperV3(app, config, system_objects)
            
            # Register V3 API routes
            register_autogen_routes(app, self.wrapper_instance)
            
            # Get the orchestrator instance
            self.orchestrator_instance = self.wrapper_instance.orchestrator
            
            logger.info("✅ V3 (AutoGen) Orchestrator initialized successfully")
            return self.wrapper_instance
            
        except ImportError as e:
            logger.error(f"❌ Failed to import V3 orchestrator components: {e}")
            logger.info("📝 Falling back to V2 orchestrator...")
            self.version = "v2"
            return self._initialize_v2_orchestrator(app, system_objects)
        except Exception as e:
            logger.error(f"❌ Failed to initialize V3 orchestrator: {e}")
            return None
    
    def _initialize_v2_orchestrator(self, app: Flask, system_objects: dict = None) -> Optional[Any]:
        """Initialize the V2 orchestrator (deprecated)"""
        logger.warning("⚠️ Initializing deprecated V2 Orchestrator...")
        
        try:
            # Import V2 orchestrator components
            from orchestrator_integration import (
                OrchestrationWrapper,
                OrchestrationConfig
            )
            
            # Log deprecation warning again
            logger.warning(
                "⚠️ You are using the deprecated V2 orchestrator. "
                "Please update your configuration to use Reactive by setting ORCHESTRATOR_VERSION=reactive"
            )
            
            # Create V2 configuration
            config = OrchestrationConfig()
            
            # Create V2 wrapper
            self.wrapper_instance = OrchestrationWrapper(app, config, system_objects)
            
            # Get the orchestrator instance
            self.orchestrator_instance = self.wrapper_instance.orchestrator
            
            logger.info("✅ V2 Orchestrator initialized (DEPRECATED)")
            return self.wrapper_instance
            
        except Exception as e:
            logger.error(f"❌ Failed to initialize V2 orchestrator: {e}")
            return None
    
    def get_orchestrator(self):
        """Get the current orchestrator instance"""
        return self.orchestrator_instance
    
    def get_wrapper(self):
        """Get the current wrapper instance"""
        return self.wrapper_instance
    
    def get_version(self):
        """Get the current orchestrator version"""
        return self.version
    
    def is_v3(self):
        """Check if using V3 orchestrator"""
        return self.version == "v3"
    
    def is_v2(self):
        """Check if using V2 orchestrator"""
        return self.version == "v2"
    
    def is_reactive(self):
        """Check if using Reactive orchestrator"""
        return self.version == "reactive"


# Singleton instance
_version_manager = None


def get_version_manager() -> OrchestratorVersionManager:
    """Get or create the singleton version manager"""
    global _version_manager
    if _version_manager is None:
        _version_manager = OrchestratorVersionManager()
    return _version_manager


def initialize_orchestrator(app: Flask, system_objects: dict = None) -> Optional[Any]:
    """Initialize the orchestrator based on environment configuration"""
    manager = get_version_manager()
    return manager.initialize_orchestrator(app, system_objects)


def get_current_orchestrator():
    """Get the current orchestrator instance"""
    manager = get_version_manager()
    return manager.get_orchestrator()


def get_current_wrapper():
    """Get the current wrapper instance"""
    manager = get_version_manager()
    return manager.get_wrapper()


def get_orchestrator_version() -> str:
    """Get the current orchestrator version"""
    manager = get_version_manager()
    return manager.get_version()