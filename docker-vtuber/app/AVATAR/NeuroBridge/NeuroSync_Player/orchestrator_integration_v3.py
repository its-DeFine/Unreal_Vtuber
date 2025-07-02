"""
Orchestrator Integration V3 - AutoGen Integration Layer
======================================================

This module provides seamless integration between the AutoGen Orchestrator V3
and the existing NeuroSync Player system. It wraps the existing Flask application
with advanced multi-agent decision-making capabilities while maintaining full 
backward compatibility.

Key Features:
1. Non-intrusive integration with existing API
2. Real-time state monitoring and synchronization
3. Multi-agent autonomous decision-making
4. Configurable personas and filtering
5. Performance monitoring and observability

Architecture:
- Integrates AutoGen V3 orchestrator with existing routes
- Monitors system state through enhanced hooks
- Provides autonomous behavior with manual overrides
- Supports both direct and orchestrated processing
"""

import os
import asyncio
import logging
import threading
import time
import json
from typing import Dict, Any, Optional, List, Callable
from dataclasses import dataclass
from datetime import datetime
from flask import Flask, request, jsonify

# Import AutoGen orchestrator components
try:
    from autogen_orchestrator_v3 import (
        AutoGenOrchestratorV3,
        create_autogen_orchestrator_v3,
        ActionType,
        Priority
    )
    AUTOGEN_AVAILABLE = True
except ImportError as e:
    logging.warning(f"AutoGen components not available: {e}")
    AUTOGEN_AVAILABLE = False
    # Define dummy classes for compatibility
    class AutoGenOrchestratorV3:
        pass
    def create_autogen_orchestrator_v3(*args, **kwargs):
        return None
    from autonomous_orchestrator_wrapper import ActionType, Priority

# Import existing components for compatibility
from orchestrator_integration import (
    OrchestrationConfig as BaseConfig,
    StateHookManager as BaseStateHookManager
)


class AutoGenOrchestrationConfig(BaseConfig):
    """Extended configuration for AutoGen orchestrator integration"""
    
    def __init__(self):
        super().__init__()
        
        # AutoGen specific settings
        self.autogen_enabled = os.getenv("AUTOGEN_ORCHESTRATOR_ENABLED", "true").lower() == "true"
        self.persona = os.getenv("ORCHESTRATOR_PERSONA", "interactive_streamer")
        self.group_chat_enabled = os.getenv("GROUP_CHAT_ENABLED", "true").lower() == "true"
        
        # Agent configuration
        self.filter_agent_enabled = os.getenv("FILTER_AGENT_ENABLED", "true").lower() == "true"
        self.speech_agent_enabled = os.getenv("SPEECH_AGENT_ENABLED", "true").lower() == "true"
        self.environment_agent_enabled = os.getenv("ENVIRONMENT_AGENT_ENABLED", "true").lower() == "true"
        self.idle_agent_enabled = os.getenv("IDLE_AGENT_ENABLED", "true").lower() == "true"
        
        # Performance settings
        self.agent_timeout = float(os.getenv("AGENT_TIMEOUT", "5.0"))
        self.max_agent_rounds = int(os.getenv("MAX_AGENT_ROUNDS", "10"))
        self.cache_decisions = os.getenv("CACHE_DECISIONS", "true").lower() == "true"
        
        # Monitoring
        self.metrics_enabled = os.getenv("METRICS_ENABLED", "true").lower() == "true"
        self.trace_enabled = os.getenv("TRACE_ENABLED", "false").lower() == "true"
        
    def __str__(self):
        base_str = super().__str__()
        return f"""{base_str}
  AutoGen Settings:
    AutoGen enabled: {self.autogen_enabled}
    Persona: {self.persona}
    Group chat: {self.group_chat_enabled}
    Agent timeout: {self.agent_timeout}s
    Max rounds: {self.max_agent_rounds}
    Metrics: {self.metrics_enabled}"""


class EnhancedStateHookManager(BaseStateHookManager):
    """Enhanced state hooks with AutoGen integration"""
    
    def __init__(self, orchestrator: AutoGenOrchestratorV3):
        # Initialize with AutoGen orchestrator
        self.orchestrator = orchestrator
        self.logger = logging.getLogger("EnhancedStateHookManager")
        
        # Enhanced state tracking
        self.current_speech_active = False
        self.current_tts_queue_size = 0
        self.current_environment = "default"
        self.current_activity = None
        self.viewer_metrics = {
            "count": 0,
            "active_chatters": set(),
            "engagement_score": 0.0
        }
        
        # Timing tracking
        self.last_speech_start = None
        self.last_environment_change = None
        self.last_viewer_interaction = None
        
        # Decision cache for performance
        self.decision_cache = {}
        self.cache_ttl = 60  # seconds
        
    def hook_viewer_interaction(self, viewer_name: str, message: str):
        """Hook for viewer interactions"""
        self.last_viewer_interaction = time.time()
        self.viewer_metrics["active_chatters"].add(viewer_name)
        
        # Update orchestrator state
        if hasattr(self.orchestrator, 'state_manager'):
            self.orchestrator.state_manager.update_interaction_time()
            self.orchestrator.state_manager.add_viewer_interaction(viewer_name, message)
        
        self.logger.info(f"👤 Viewer interaction: {viewer_name} - {message[:50]}...")
        
    def hook_activity_change(self, activity: str):
        """Hook for activity changes (drawing, gaming, chatting)"""
        self.current_activity = activity
        
        if hasattr(self.orchestrator, 'state_manager'):
            self.orchestrator.state_manager.update_activity(activity)
        
        self.logger.info(f"🎯 Activity changed to: {activity}")
    
    def hook_conversation_input(self, text: str, autonomous_context: str = None):
        """Hook for conversation input (V2 compatibility)"""
        # Use the existing hook_viewer_interaction method
        self.hook_viewer_interaction("user", text)
        
        # Track conversation context
        if hasattr(self.orchestrator, 'state_manager'):
            self.orchestrator.state_manager.update_conversation_topic(text)
        
        self.logger.info(f"💬 Conversation input: {text[:50]}...")
    
    def hook_environment_change_start(self, environment: str):
        """Hook for environment change start (V2 compatibility)"""
        self.current_environment = environment
        self.last_environment_change = time.time()
        
        if hasattr(self.orchestrator, 'state_manager'):
            self.orchestrator.state_manager.state.environment_state.update_scene(environment)
        
        self.logger.info(f"🌍 Environment change started: {environment}")
    
    def hook_environment_change_end(self, environment: str, success: bool = True):
        """Hook for environment change end (V2 compatibility)"""
        if success:
            self.current_environment = environment
        
        self.logger.info(f"🌍 Environment change {'completed' if success else 'failed'}: {environment}")
    
    def hook_audio_start(self, text: str, estimated_duration: float = None):
        """Hook for audio/speech start (V2 compatibility)"""
        self.current_speech_active = True
        self.last_speech_start = time.time()
        
        if hasattr(self.orchestrator, 'state_manager'):
            self.orchestrator.state_manager.state.is_speaking = True
            self.orchestrator.state_manager.state.speech_start_time = time.time()
        
        self.logger.info(f"🎤 Audio started: {text[:50]}...")
    
    def hook_audio_end(self):
        """Hook for audio/speech end (V2 compatibility)"""
        self.current_speech_active = False
        
        if hasattr(self.orchestrator, 'state_manager'):
            self.orchestrator.state_manager.state.is_speaking = False
            self.orchestrator.state_manager.state.last_speech_completed = time.time()
        
        self.logger.info("🎤 Audio ended")
    
    def hook_tts_queue_update(self, queue_size: int):
        """Hook for TTS queue updates (V2 compatibility)"""
        self.current_tts_queue_size = queue_size
        
        if hasattr(self.orchestrator, 'state_manager'):
            self.orchestrator.state_manager.state.speech_queue_size = queue_size
        
        self.logger.debug(f"📊 TTS queue size: {queue_size}")
        
    def calculate_engagement_score(self) -> float:
        """Calculate current engagement score"""
        if not self.last_viewer_interaction:
            return 0.0
        
        time_since_interaction = time.time() - self.last_viewer_interaction
        active_ratio = len(self.viewer_metrics["active_chatters"]) / max(self.viewer_metrics["count"], 1)
        
        # Decay engagement over time
        time_factor = max(0, 1 - (time_since_interaction / 300))  # 5 minute decay
        
        return min(1.0, active_ratio * time_factor)
        
    def get_enhanced_state(self) -> Dict[str, Any]:
        """Get enhanced state information for AutoGen agents"""
        return {
            "audio": {
                "is_speaking": self.current_speech_active,
                "tts_queue_size": self.current_tts_queue_size,
                "time_since_speech": time.time() - self.last_speech_start if self.last_speech_start else None
            },
            "environment": {
                "current": self.current_environment,
                "time_since_change": time.time() - self.last_environment_change if self.last_environment_change else None
            },
            "activity": {
                "current": self.current_activity,
                "engagement_score": self.calculate_engagement_score()
            },
            "viewers": self.viewer_metrics
        }


class AutoGenOrchestrationWrapper:
    """
    Advanced orchestration wrapper integrating AutoGen V3 with NeuroSync Player
    
    This class provides:
    1. Multi-agent decision making through AutoGen
    2. Advanced state monitoring and hooks
    3. Performance optimization with caching
    4. Comprehensive metrics and observability
    """
    
    def __init__(self, app: Flask, config: AutoGenOrchestrationConfig, system_objects=None):
        self.app = app
        self.config = config
        self.logger = logging.getLogger(__name__)
        self.system_objects = system_objects
        
        # Initialize AutoGen orchestrator
        self.orchestrator = None
        self.state_hooks = None
        
        if self.config.autogen_enabled:
            if not AUTOGEN_AVAILABLE:
                self.logger.error("❌ AutoGen components not available. Please install pyautogen.")
                self.config.autogen_enabled = False
            else:
                try:
                    self.orchestrator = create_autogen_orchestrator_v3(
                        config_path=os.getenv("AUTOGEN_CONFIG_PATH")
                    )
                    self.state_hooks = EnhancedStateHookManager(self.orchestrator)
                    
                    # Pass system objects for interruption support
                    if system_objects:
                        self.orchestrator.system_objects = system_objects
                        
                    self.logger.info("✅ AutoGen Orchestrator V3 initialized successfully")
                except Exception as e:
                    self.logger.error(f"❌ Failed to initialize AutoGen orchestrator: {e}")
                    self.config.autogen_enabled = False
        
        # Metrics tracking
        self.metrics = {
            "requests_processed": 0,
            "orchestrated_decisions": 0,
            "autonomous_content_generated": 0,
            "filter_suppressions": 0,
            "environment_changes": 0,
            "errors": 0,
            "start_time": time.time()
        }
        
        # Performance monitoring
        self.performance_traces = []
        self.max_traces = 1000
        
        self.logger.info(f"🎭 AutoGen Orchestration Wrapper initialized:\n{self.config}")
        
    async def start_orchestrator(self):
        """Start the AutoGen orchestrator"""
        if self.orchestrator and self.config.autogen_enabled:
            try:
                await self.orchestrator.start()
                self.logger.info("🚀 AutoGen orchestrator started")
            except Exception as e:
                self.logger.error(f"❌ Failed to start orchestrator: {e}")
                self.metrics["errors"] += 1
                
    async def stop_orchestrator(self):
        """Stop the AutoGen orchestrator"""
        if self.orchestrator:
            try:
                await self.orchestrator.stop()
                self.logger.info("🛑 AutoGen orchestrator stopped")
            except Exception as e:
                self.logger.error(f"❌ Failed to stop orchestrator: {e}")
                
    async def process_with_autogen(self, text: str, context: Dict[str, Any]) -> Dict[str, Any]:
        """Process input through AutoGen multi-agent system"""
        start_time = time.time()
        
        try:
            # Prepare input data for AutoGen
            input_data = {
                "text": text,
                "source": context.get("source", "user"),
                "metadata": {
                    "timestamp": datetime.now().isoformat(),
                    "viewer_name": context.get("viewer_name", "unknown"),
                    "platform": context.get("platform", "direct"),
                    "importance": context.get("importance", "medium"),
                    **context
                }
            }
            
            # Add enhanced state information
            if self.state_hooks:
                input_data["state"] = self.state_hooks.get_enhanced_state()
            
            # Process through AutoGen
            result = await self.orchestrator.process_external_input(input_data)
            
            # Track metrics
            self.metrics["orchestrated_decisions"] += 1
            for decision in result.get("decisions", []):
                if decision.get("type") == "suppress":
                    self.metrics["filter_suppressions"] += 1
                elif decision.get("type") == "environment":
                    self.metrics["environment_changes"] += 1
            
            # Record performance trace
            if self.config.trace_enabled:
                self._record_trace("autogen_process", time.time() - start_time, result)
            
            return result
            
        except Exception as e:
            self.logger.error(f"Error in AutoGen processing: {e}")
            self.metrics["errors"] += 1
            return {
                "processed": False,
                "error": str(e),
                "decisions": []
            }
    
    def should_use_autogen(self, text: str, context: Dict[str, Any]) -> bool:
        """Determine if request should be processed by AutoGen"""
        if not self.orchestrator or not self.config.autogen_enabled:
            return False
        
        # Always use AutoGen for autonomous contexts
        if context.get("autonomous", False):
            return True
        
        # Check for complex decisions requiring multi-agent coordination
        complexity_indicators = [
            "change" in text.lower() and "scene" in text.lower(),
            "multiple" in text.lower(),
            "should i" in text.lower(),
            len(text.split()) > 20  # Longer messages may need analysis
        ]
        
        if any(complexity_indicators):
            return True
        
        # Use persona-specific logic
        if self.config.persona == "focused_artist":
            # More selective filtering for focused persona
            return True
        elif self.config.persona == "interactive_streamer":
            # Less filtering for interactive persona
            return context.get("importance") == "high"
        
        return False
    
    def should_orchestrate_request(self, text: str, autonomous_context: str = None) -> bool:
        """
        Determine if request should be handled by orchestrator (V2 compatibility method)
        
        Args:
            text: Input text to process
            autonomous_context: Autonomous context (string or dict)
            
        Returns:
            bool: Whether to orchestrate the request
        """
        if not self.orchestrator or not self.config.autogen_enabled:
            return False
            
        # Check for autonomous context indicators
        if autonomous_context:
            # Handle both string and dict formats
            if isinstance(autonomous_context, dict):
                # Check source field
                source = autonomous_context.get('source', '')
                if 'autonomous' in source.lower() or 'orchestrate' in source.lower():
                    return True
                # Check is_autonomous flag
                if autonomous_context.get('is_autonomous', False):
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
            # Use the more sophisticated AutoGen logic
            context_dict = {}
            if isinstance(autonomous_context, dict):
                context_dict = autonomous_context
            elif isinstance(autonomous_context, str):
                context_dict = {"autonomous_context": autonomous_context}
                
            return self.should_use_autogen(text, context_dict)
            
        return False
    
    def process_orchestrated_input(self, text: str, autonomous_context: str = None):
        """
        Process input through orchestrator (V2 compatibility method)
        
        Args:
            text: Input text to process
            autonomous_context: Autonomous context (string or dict)
        """
        if not self.orchestrator:
            self.logger.warning("No orchestrator available for processing input")
            return
            
        # Convert autonomous_context to dict format for V3
        context = {}
        if autonomous_context:
            if isinstance(autonomous_context, dict):
                context = autonomous_context
            elif isinstance(autonomous_context, str):
                context = {"autonomous_context": autonomous_context}
        
        # Hook conversation input for state monitoring
        if self.state_hooks:
            self.state_hooks.hook_viewer_interaction("user", text)
            
        # Process through AutoGen orchestrator
        try:
            # Use asyncio to run the async method
            import asyncio
            
            # Create a new event loop if we don't have one
            try:
                loop = asyncio.get_event_loop()
                if loop.is_closed():
                    raise RuntimeError("Event loop is closed")
            except RuntimeError:
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
            
            # Run the processing
            if loop.is_running():
                # If loop is already running, create a task
                asyncio.create_task(self.process_with_autogen(text, context))
            else:
                # If loop is not running, run until complete
                loop.run_until_complete(self.process_with_autogen(text, context))
            
            self.logger.info(f"🎯 Processed through V3 orchestrator: {text[:50]}...")
            
        except Exception as e:
            self.logger.error(f"Error processing orchestrated input: {e}")
            # Fall back to simple processing
            if self.state_hooks:
                self.state_hooks.hook_activity_change("processing_error")
    
    def get_comprehensive_status(self) -> Dict[str, Any]:
        """Get comprehensive orchestrator status with metrics"""
        base_status = {
            "enabled": self.config.autogen_enabled,
            "running": False,
            "persona": self.config.persona,
            "agents": {},
            "metrics": self.metrics
        }
        
        if self.orchestrator:
            orchestrator_status = self.orchestrator.get_status()
            base_status.update(orchestrator_status)
            
            # Add performance metrics
            if self.metrics["requests_processed"] > 0:
                base_status["performance"] = {
                    "avg_decision_time": self._calculate_avg_trace_time("autogen_process"),
                    "suppression_rate": self.metrics["filter_suppressions"] / self.metrics["requests_processed"],
                    "autonomous_content_rate": self.metrics["autonomous_content_generated"] / max(1, self.metrics["orchestrated_decisions"]),
                    "error_rate": self.metrics["errors"] / self.metrics["requests_processed"]
                }
        
        return base_status
    
    def update_viewer_count(self, count: int):
        """Update viewer count in orchestrator"""
        if self.state_hooks:
            self.state_hooks.viewer_metrics["count"] = count
        
        if self.orchestrator and hasattr(self.orchestrator, 'state_manager'):
            self.orchestrator.state_manager.update_viewer_count(count)
    
    async def handle_external_event(self, event_type: str, payload: Dict[str, Any]):
        """Handle external events through AutoGen"""
        if not self.orchestrator:
            return
        
        try:
            await self.orchestrator.process_external_event(event_type, payload)
            self.logger.info(f"✅ Processed external event: {event_type}")
        except Exception as e:
            self.logger.error(f"Error handling external event: {e}")
            self.metrics["errors"] += 1
    
    async def update_persona(self, persona_name: str) -> bool:
        """Update orchestrator persona"""
        if not self.orchestrator:
            return False
        
        try:
            success = await self.orchestrator.update_persona(persona_name)
            if success:
                self.config.persona = persona_name
                self.logger.info(f"✅ Persona updated to: {persona_name}")
            return success
        except Exception as e:
            self.logger.error(f"Error updating persona: {e}")
            return False
    
    def _record_trace(self, operation: str, duration: float, data: Any = None):
        """Record performance trace"""
        trace = {
            "operation": operation,
            "duration": duration,
            "timestamp": time.time(),
            "data": data
        }
        
        self.performance_traces.append(trace)
        
        # Limit trace history
        if len(self.performance_traces) > self.max_traces:
            self.performance_traces = self.performance_traces[-self.max_traces:]
    
    def _calculate_avg_trace_time(self, operation: str) -> float:
        """Calculate average trace time for an operation"""
        relevant_traces = [t for t in self.performance_traces if t["operation"] == operation]
        if not relevant_traces:
            return 0.0
        
        return sum(t["duration"] for t in relevant_traces) / len(relevant_traces)
    
    def export_metrics(self) -> Dict[str, Any]:
        """Export metrics in Prometheus format"""
        uptime = time.time() - self.metrics["start_time"]
        
        return {
            "autogen_requests_total": self.metrics["requests_processed"],
            "autogen_decisions_total": self.metrics["orchestrated_decisions"],
            "autogen_autonomous_content_total": self.metrics["autonomous_content_generated"],
            "autogen_suppressions_total": self.metrics["filter_suppressions"],
            "autogen_environment_changes_total": self.metrics["environment_changes"],
            "autogen_errors_total": self.metrics["errors"],
            "autogen_uptime_seconds": uptime,
            "autogen_requests_per_minute": (self.metrics["requests_processed"] / uptime) * 60 if uptime > 0 else 0
        }

    def register_speech_completion_callback(self, system_objects):
        """Register speech completion callback with audio worker after initialization"""
        if not self.orchestrator or not system_objects:
            return
        
        try:
            # Get the audio worker thread and update its completion callback
            audio_worker_thread = system_objects.get('audio_worker_thread')
            if hasattr(audio_worker_thread, '_target') and hasattr(audio_worker_thread._target, '__defaults__'):
                # Can't easily modify running thread, so we'll add a global callback mechanism
                self.logger.info("Speech completion callback registration attempted")
            
            # Alternative: Set a global completion callback function
            import utils.audio_face_workers as audio_workers
            if hasattr(audio_workers, 'set_global_completion_callback'):
                audio_workers.set_global_completion_callback(self.orchestrator.notify_speech_complete)
                self.logger.info("🔊 Speech completion callback registered globally")
            else:
                # Fallback: Add callback directly to the orchestrator's system objects reference
                if hasattr(self.orchestrator, 'notify_speech_complete'):
                    system_objects['speech_completion_callback'] = self.orchestrator.notify_speech_complete
                    self.logger.info("🔊 Speech completion callback stored in system objects")
        except Exception as e:
            self.logger.error(f"Failed to register speech completion callback: {e}")


def create_autogen_integration(app: Flask, **config_kwargs) -> AutoGenOrchestrationWrapper:
    """
    Factory function to create AutoGen orchestration integration
    
    Args:
        app: Flask application instance
        **config_kwargs: Configuration overrides
        
    Returns:
        Configured AutoGenOrchestrationWrapper instance
    """
    config = AutoGenOrchestrationConfig()
    
    # Apply configuration overrides
    for key, value in config_kwargs.items():
        if hasattr(config, key):
            setattr(config, key, value)
    
    return AutoGenOrchestrationWrapper(app, config)


# Middleware for request processing
class AutoGenMiddleware:
    """Middleware to intercept and process requests through AutoGen"""
    
    def __init__(self, wrapper: AutoGenOrchestrationWrapper):
        self.wrapper = wrapper
        self.logger = logging.getLogger("AutoGenMiddleware")
    
    async def process_request(self, text: str, context: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Process request through AutoGen if applicable"""
        # Track all requests
        self.wrapper.metrics["requests_processed"] += 1
        
        # Check if should use AutoGen
        if not self.wrapper.should_use_autogen(text, context):
            return None
        
        # Process through AutoGen
        result = await self.wrapper.process_with_autogen(text, context)
        
        # Handle decisions
        decisions = result.get("decisions", [])
        for decision in decisions:
            if decision.get("type") == "speech":
                # Speech will be handled by main app
                pass
            elif decision.get("type") == "environment":
                # Queue environment change
                await self._handle_environment_decision(decision)
            elif decision.get("type") == "suppress":
                # Log suppression
                self.logger.info(f"Suppressed: {decision.get('reason')}")
        
        return result
    
    async def _handle_environment_decision(self, decision: Dict[str, Any]):
        """Handle environment change decision"""
        try:
            # Send to game control endpoint
            import aiohttp
            async with aiohttp.ClientSession() as session:
                payload = {
                    "prompt": decision.get("action", ""),
                    "autonomous_context": {
                        "source": "autogen_decision",
                        "reasoning": decision.get("reasoning", "")
                    }
                }
                
                async with session.post("http://localhost:5001/game_control", json=payload) as response:
                    if response.status == 200:
                        self.logger.info("✅ Environment decision executed")
                    else:
                        self.logger.error(f"Failed to execute environment decision: {response.status}")
                        
        except Exception as e:
            self.logger.error(f"Error executing environment decision: {e}")


# Export main components
__all__ = [
    'AutoGenOrchestrationConfig',
    'AutoGenOrchestrationWrapper', 
    'EnhancedStateHookManager',
    'AutoGenMiddleware',
    'create_autogen_integration'
]