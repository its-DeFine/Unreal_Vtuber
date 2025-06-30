# This software is licensed under a **dual-license model**
# For individuals and businesses earning **under $1M per year**, this software is licensed under the **MIT License**
# Businesses or organizations with **annual revenue of $1,000,000 or more** must obtain permission to use this software commercially.

"""
Orchestrator Integration Layer
=============================

This module provides seamless integration between the Autonomous Orchestrator 
and the existing NeuroSync Player system. It wraps the existing Flask application
with autonomous decision-making capabilities while maintaining full backward compatibility.

Key Features:
1. Non-intrusive integration - existing API continues to work
2. Real-time state monitoring of TTS/audio/blendshape systems
3. Autonomous decision-making overlay
4. Configurable enable/disable via environment variables
5. Maintains all existing functionality

Architecture:
- Wraps existing Flask routes with orchestrator decision-making
- Monitors system state through hooks into existing components
- Provides autonomous behavior while respecting manual overrides
"""

import os
import asyncio
import logging
import threading
import time
from typing import Dict, Any, Optional
from flask import Flask, request, jsonify

from autonomous_orchestrator import (
    AutonomousOrchestrator, 
    ActionType, 
    Priority, 
    create_autonomous_orchestrator
)


class OrchestrationConfig:
    """Configuration for orchestrator integration"""
    
    def __init__(self):
        # Enable/disable orchestration
        self.enabled = os.getenv("AUTONOMOUS_ORCHESTRATION_ENABLED", "true").lower() == "true"
        
        # Orchestration behavior settings
        self.auto_interrupt_enabled = os.getenv("AUTO_INTERRUPT_ENABLED", "true").lower() == "true"
        self.decision_loop_interval = float(os.getenv("DECISION_LOOP_INTERVAL", "0.1"))
        self.scb_integration_enabled = os.getenv("SCB_INTEGRATION_ENABLED", "true").lower() == "true"
        
        # Priority thresholds
        self.interrupt_threshold = int(os.getenv("INTERRUPT_THRESHOLD", "4"))  # HIGH priority
        self.idle_timeout = float(os.getenv("ORCHESTRATOR_IDLE_TIMEOUT", "2.0"))
        
        # Autonomous behavior settings
        self.autonomous_speech_enabled = os.getenv("AUTONOMOUS_SPEECH_ENABLED", "false").lower() == "true"
        self.autonomous_environment_enabled = os.getenv("AUTONOMOUS_ENVIRONMENT_ENABLED", "true").lower() == "true"
        
        # Logging
        self.log_level = os.getenv("ORCHESTRATOR_LOG_LEVEL", "INFO").upper()
        
    def __str__(self):
        return f"""OrchestrationConfig:
  Enabled: {self.enabled}
  Auto-interrupt: {self.auto_interrupt_enabled}  
  Decision interval: {self.decision_loop_interval}s
  SCB integration: {self.scb_integration_enabled}
  Interrupt threshold: {self.interrupt_threshold}
  Idle timeout: {self.idle_timeout}s
  Autonomous speech: {self.autonomous_speech_enabled}
  Autonomous environment: {self.autonomous_environment_enabled}
  Log level: {self.log_level}"""


class StateHookManager:
    """Manages hooks into existing NeuroSync components for state monitoring"""
    
    def __init__(self, orchestrator: AutonomousOrchestrator):
        self.orchestrator = orchestrator
        self.logger = logging.getLogger("StateHookManager")
        
        # State tracking
        self.current_speech_active = False
        self.current_tts_queue_size = 0
        self.current_environment = "default"
        
        # Timing tracking
        self.last_speech_start = None
        self.last_environment_change = None
        
    def hook_audio_start(self, text: str, estimated_duration: float = None):
        """Hook called when audio/TTS generation starts"""
        self.current_speech_active = True
        self.last_speech_start = time.time()
        
        if not estimated_duration:
            estimated_duration = self._estimate_speech_duration(text)
            
        estimated_end_time = time.time() + estimated_duration
        
        self.orchestrator.state_monitor.update_audio_state(
            is_speaking=True,
            queue_size=self.current_tts_queue_size,
            estimated_end_time=estimated_end_time
        )
        
        self.logger.info(f"🔊 Audio started: {text[:30]}... (est. {estimated_duration:.1f}s)")
        
    def hook_audio_end(self):
        """Hook called when audio/TTS playback ends"""
        self.current_speech_active = False
        self.last_speech_start = None
        
        self.orchestrator.state_monitor.update_audio_state(
            is_speaking=False,
            queue_size=0
        )
        
        self.logger.info("🔇 Audio ended")
        
    def hook_tts_queue_update(self, queue_size: int):
        """Hook called when TTS queue size changes"""
        self.current_tts_queue_size = queue_size
        
        if self.current_speech_active:
            self.orchestrator.state_monitor.update_audio_state(
                is_speaking=True,
                queue_size=queue_size
            )
            
    def hook_blendshape_update(self, active: bool, queue_size: int = 0):
        """Hook called when blendshape state changes"""
        self.orchestrator.state_monitor.update_blendshape_state(
            active=active,
            queue_size=queue_size
        )
        
        self.logger.debug(f"🎭 Blendshape update: active={active}, queue={queue_size}")
        
    def hook_environment_change_start(self, environment: str):
        """Hook called when environment change starts"""
        self.current_environment = environment
        self.last_environment_change = time.time()
        
        self.orchestrator.state_monitor.update_environment_state(
            environment=environment,
            changing=True
        )
        
        self.logger.info(f"🎮 Environment change started: {environment}")
        
    def hook_environment_change_end(self, environment: str, success: bool = True):
        """Hook called when environment change completes"""
        self.orchestrator.state_monitor.update_environment_state(
            environment=environment if success else "error",
            changing=False
        )
        
        status = "✅" if success else "❌"
        self.logger.info(f"{status} Environment change completed: {environment}")
        
    def hook_conversation_input(self, text: str, autonomous_context: str = None):
        """Hook called when new conversation input is received"""
        keywords = self._extract_keywords(text)
        
        self.orchestrator.state_monitor.update_conversation_context(
            keywords=keywords,
            active=True
        )
        
        self.logger.info(f"💬 Conversation input: {text[:50]}...")
        
    def _estimate_speech_duration(self, text: str) -> float:
        """Estimate speech duration based on text length"""
        words = len(text.split())
        duration = (words / 150) * 60  # ~150 words per minute
        return max(1.0, duration)
        
    def _extract_keywords(self, text: str) -> list:
        """Extract keywords from text for context"""
        words = text.lower().split()
        keywords = [w for w in words if len(w) > 3 and w.isalpha()]
        return keywords[:10]


class OrchestrationWrapper:
    """
    Main wrapper class that integrates autonomous orchestration with existing NeuroSync Player
    
    This class:
    1. Wraps existing Flask routes with orchestration logic
    2. Provides state monitoring hooks
    3. Manages autonomous decision-making
    4. Maintains backward compatibility
    """
    
    def __init__(self, app: Flask, config: OrchestrationConfig, system_objects=None):
        """Initialize orchestration wrapper
        
        Args:
            app: Flask application instance
            config: Orchestration configuration
            system_objects: System objects including queues for interruption
        """
        
        self.app = app
        self.config = config
        self.logger = logging.getLogger(__name__)
        
        # Create the orchestrator
        self.orchestrator = AutonomousOrchestrator()
        
        # Pass system objects if available
        if system_objects:
            self.orchestrator.system_objects = system_objects
            self.logger.info("✅ System objects passed to orchestrator for interruption support")
        
        # Create state hooks for monitoring
        self.state_hooks = StateHookManager(self.orchestrator)
        
        # Set up logging
        orchestrator_logger = logging.getLogger("AutonomousOrchestrator")
        orchestrator_logger.setLevel(logging.DEBUG)  # Force DEBUG for testing
        
        # Add console handler to ensure logs are visible
        console_handler = logging.StreamHandler()
        console_handler.setLevel(logging.DEBUG)
        formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        console_handler.setFormatter(formatter)
        orchestrator_logger.addHandler(console_handler)
        
        # Initialize orchestrator if enabled
        self.orchestrator_task = None
        
        if self.config.enabled:
            self._initialize_orchestrator()
        else:
            self.logger.info("🚫 Autonomous orchestration disabled")
            
        self.logger.info(f"🎭 OrchestrationWrapper initialized:\n{self.config}")
        
    def _initialize_orchestrator(self):
        """Initialize the autonomous orchestrator"""
        try:
            self.orchestrator.decision_engine.interruption_threshold = Priority(self.config.interrupt_threshold)
            self.orchestrator.decision_engine.idle_timeout = self.config.idle_timeout
            self.orchestrator.decision_loop_interval = self.config.decision_loop_interval
            
            self.logger.info("✅ Autonomous orchestrator initialized")
            
        except Exception as e:
            self.logger.error(f"❌ Failed to initialize orchestrator: {e}")
            self.orchestrator = None
            self.state_hooks = None
            
    async def start_orchestrator(self):
        """Start the autonomous orchestrator"""
        if self.orchestrator and self.config.enabled:
            try:
                await self.orchestrator.start()
                self.logger.info("🚀 Autonomous orchestrator started")
            except Exception as e:
                self.logger.error(f"❌ Failed to start orchestrator: {e}")
                
    async def stop_orchestrator(self):
        """Stop the autonomous orchestrator"""
        if self.orchestrator:
            try:
                await self.orchestrator.stop()
                self.logger.info("🛑 Autonomous orchestrator stopped")
            except Exception as e:
                self.logger.error(f"❌ Failed to stop orchestrator: {e}")
                
    def should_orchestrate_request(self, text: str, autonomous_context: str = None) -> bool:
        """Determine if request should be handled by orchestrator"""
        
        if not self.orchestrator or not self.config.enabled:
            return False
            
        # Check for autonomous context indicators
        if autonomous_context:
            # Handle both string and dict formats
            if isinstance(autonomous_context, dict):
                # Check source field
                source = autonomous_context.get('source', '')
                if 'autonomous' in source.lower() or 'orchestrate' in source.lower():
                    return True
            elif isinstance(autonomous_context, str):
                if "autonomous" in autonomous_context.lower():
                    return True
                if "orchestrate" in autonomous_context.lower():
                    return True
                
        # Check for environment-related requests if autonomous environment is enabled
        if self.config.autonomous_environment_enabled:
            env_keywords = ["scene", "environment", "hair", "color", "appearance", "lighting"]
            if any(keyword in text.lower() for keyword in env_keywords):
                return True
                
        # Check for autonomous speech if enabled
        if self.config.autonomous_speech_enabled:
            # Could add more sophisticated logic here
            return False
            
        return False
        
    def process_orchestrated_input(self, text: str, autonomous_context: str = None):
        """Process input through orchestrator"""
        if self.orchestrator:
            # Hook conversation input for state monitoring
            if self.state_hooks:
                self.state_hooks.hook_conversation_input(text, autonomous_context)
                
            # Process through orchestrator
            self.orchestrator.process_external_input(text, autonomous_context)
            
            self.logger.info(f"🎯 Processed through orchestrator: {text[:50]}...")
            
    def add_monitoring_hooks(self, text: str):
        """Add monitoring hooks for regular (non-orchestrated) requests"""
        if self.state_hooks:
            self.state_hooks.hook_conversation_input(text)
            self.state_hooks.hook_audio_start(text)
            
            # Schedule audio end hook (simplified timing)
            estimated_duration = self.state_hooks._estimate_speech_duration(text)
            threading.Timer(estimated_duration, self.state_hooks.hook_audio_end).start()
            
    def get_orchestrator_status(self) -> Dict[str, Any]:
        """Get current orchestrator status"""
        if not self.orchestrator:
            return {
                "enabled": False,
                "status": "disabled",
                "message": "Autonomous orchestration is disabled"
            }
            
        state = self.orchestrator.state_monitor.get_state_snapshot()
        
        current_action_info = {
            "is_speaking": state.is_speaking,
            "tts_queue_size": state.tts_queue_size,
            "blendshape_active": state.blendshape_active,
            "current_environment": state.current_environment,
            "environment_changing": state.environment_changing,
            "conversation_active": state.conversation_active,
            "last_input_time": state.last_input_time
        }
        
        system_state_info = {
            "current_environment": state.current_environment,
            "environment_changing": state.environment_changing,
            "conversation_active": state.conversation_active,
            "last_input_time": state.last_input_time
        }
        
        return {
            "enabled": self.config.enabled,
            "running": self.orchestrator.running if self.orchestrator else False,
            "current_action": current_action_info,
            "pending_actions": len(self.orchestrator.action_queue) if self.orchestrator else 0,
            "last_decision_time": self.orchestrator.last_action_time if self.orchestrator else None,
            "system_state": system_state_info,
            "config": {
                "interrupt_threshold": self.config.interrupt_threshold,
                "idle_timeout": self.config.idle_timeout,
                "autonomous_environment_enabled": self.config.autonomous_environment_enabled
            }
        }
        
    def interrupt_current_activities(self):
        """Interrupt current activities"""
        if self.orchestrator:
            self.orchestrator.queue_action(
                ActionType.INTERRUPT,
                "Manual interrupt request",
                Priority.URGENT,
                interrupt_current=True
            )
            self.logger.info("⚡ Manual interrupt requested")
            
    def queue_speech_action(self, text: str, priority: str = "medium", interrupt: bool = False):
        """Queue a speech action"""
        if self.orchestrator:
            priority_enum = getattr(Priority, priority.upper(), Priority.MEDIUM)
            
            self.orchestrator.queue_action(
                ActionType.SPEECH,
                text,
                priority_enum,
                interrupt_current=interrupt
            )
            
            self.logger.info(f"📝 Queued speech action: {text[:50]}... (priority: {priority})")
            
    def queue_environment_action(self, prompt: str, priority: str = "medium", interrupt: bool = False):
        """Queue an environment action"""
        if self.orchestrator:
            priority_enum = getattr(Priority, priority.upper(), Priority.MEDIUM)
            
            self.orchestrator.queue_action(
                ActionType.ENVIRONMENT,
                prompt,
                priority_enum,
                interrupt_current=interrupt
            )
            
            self.logger.info(f"🎮 Queued environment action: {prompt} (priority: {priority})")


# Factory functions for easy integration
def create_orchestration_config(**kwargs) -> OrchestrationConfig:
    """Create orchestration configuration with custom settings"""
    config = OrchestrationConfig()
    
    for key, value in kwargs.items():
        if hasattr(config, key):
            setattr(config, key, value)
            
    return config


def create_orchestration_wrapper(app: Flask, **config_kwargs) -> OrchestrationWrapper:
    """Create orchestration wrapper with custom configuration"""
    config = create_orchestration_config(**config_kwargs)
    return OrchestrationWrapper(app, config)


# Context manager for orchestrator lifecycle
class OrchestrationContext:
    """Context manager for orchestrator lifecycle in Flask applications"""
    
    def __init__(self, app: Flask, config: OrchestrationConfig = None):
        self.wrapper = OrchestrationWrapper(app, config)
        
    async def __aenter__(self):
        await self.wrapper.start_orchestrator()
        return self.wrapper
        
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.wrapper.stop_orchestrator()


# Example usage and testing
if __name__ == "__main__":
    # Create a test Flask app
    from flask import Flask
    from flask_cors import CORS
    
    app = Flask(__name__)
    CORS(app)
    
    # Enable orchestration
    orchestration = create_orchestration_wrapper(
        app,
        enabled=True,
        autonomous_environment_enabled=True,
        log_level="DEBUG"
    )
    
    # Add test routes
    @app.route("/test", methods=['POST'])
    def test_route():
        return jsonify({"message": "Test route working"}), 200
        
    async def test_integration():
        """Test the orchestration integration"""
        
        print("🧪 Testing Orchestration Integration")
        
        # Start orchestrator
        await orchestration.start_orchestrator()
        
        # Test orchestrator status
        print("📊 Orchestrator Status:")
        status = orchestration.get_orchestrator_status()
        print(f"  - Enabled: {status['enabled']}")
        print(f"  - Status: {status['status']}")
        
        # Test autonomous decision making
        if orchestration.orchestrator:
            orchestration.process_orchestrated_input(
                "Change hair to red and set medieval scene",
                autonomous_context="test_environment_change"
            )
            
        # Let it run briefly
        await asyncio.sleep(2)
        
        # Stop orchestrator
        await orchestration.stop_orchestrator()
        
        print("✅ Integration test completed")
        
    # Run test
    asyncio.run(test_integration()) 