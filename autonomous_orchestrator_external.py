#!/usr/bin/env python3
"""
External Autonomous Orchestrator - "The Brain"
=============================================

This script acts as an external controller that:
1. Monitors VTuber and Game system status
2. Makes intelligent decisions about speech and actions
3. Handles external prompts and inputs
4. Controls timing and flow
5. Coordinates between multiple systems

Architecture:
- Standalone script (no embedded integration)
- API-based communication with all systems
- Context-aware decision making
- External input processing
"""

import asyncio
import aiohttp
import time
import json
import random
import logging
import os
from datetime import datetime
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field
from enum import Enum


# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(name)s: %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger("Orchestrator")


class ActionType(Enum):
    """Types of actions the orchestrator can execute"""
    SPEAK = "speak"
    GAME_CONTROL = "game_control"
    WAIT = "wait"
    ANALYZE = "analyze"


class Priority(Enum):
    """Priority levels for actions"""
    LOW = 1
    MEDIUM = 2
    HIGH = 3
    URGENT = 4


@dataclass
class SystemStatus:
    """Current status of all monitored systems"""
    vtuber_speaking: bool = False
    vtuber_idle_duration: float = 0.0
    vtuber_queue_size: int = 0
    vtuber_last_speech: Optional[str] = None
    game_environment: str = "default"
    game_changing: bool = False
    last_update: float = field(default_factory=time.time)
    
    def is_ready_for_speech(self) -> bool:
        """Check if system is ready for new speech"""
        return not self.vtuber_speaking and self.vtuber_queue_size == 0
    
    def get_idle_duration(self) -> float:
        """Get current idle duration in seconds"""
        return time.time() - self.last_update + self.vtuber_idle_duration


@dataclass
class Action:
    """Represents an action to be executed"""
    type: ActionType
    content: str
    priority: Priority = Priority.MEDIUM
    metadata: Dict[str, Any] = field(default_factory=dict)
    timestamp: float = field(default_factory=time.time)


class ContentGenerator:
    """Generates contextual content for different situations"""
    
    def __init__(self):
        self.recent_topics = []
        self.conversation_context = {}
        
    def generate_idle_content(self, idle_duration: float, context: Dict[str, Any]) -> Optional[str]:
        """Generate appropriate content based on idle time and context"""
        
        if idle_duration < 10:
            # Very short idle - ambient sounds
            options = [
                "Hmm...",
                "*looks around thoughtfully*",
                "Interesting...",
                "Let me think...",
                "*adjusts posture*"
            ]
        elif idle_duration < 30:
            # Medium idle - gentle prompts
            options = [
                "What's on your mind?",
                "Feel free to ask me anything!",
                "I'm here if you want to chat.",
                "Is there something you'd like to explore?",
                "What would you like to talk about?"
            ]
        elif idle_duration < 60:
            # Longer idle - more engaging
            options = [
                "I've been thinking about some interesting topics...",
                "Would you like me to share something fascinating?",
                "There are so many cool things we could discuss!",
                "I'm curious about what interests you most.",
                "Let me tell you about something I find intriguing..."
            ]
        else:
            # Very long idle - re-engagement
            options = [
                "Hey, are you still there?",
                "I'm here whenever you're ready to continue!",
                "Take your time - I'll be here waiting.",
                "Let me know when you'd like to chat again.",
                "I'm always here if you need anything!"
            ]
            
        return random.choice(options)
    
    def generate_contextual_content(self, prompt: str, context: Dict[str, Any]) -> str:
        """Generate contextual response to external prompts"""
        
        # This could be enhanced with LLM processing
        # For now, we'll do simple contextual responses
        
        if "question" in prompt.lower():
            return f"That's a great question! Let me think about {prompt}..."
        elif "tell me" in prompt.lower():
            return f"I'd be happy to tell you about {prompt}!"
        elif "explain" in prompt.lower():
            return f"Let me explain {prompt} in detail..."
        else:
            return f"Interesting! You mentioned: {prompt}. Let me elaborate on that..."


class VTuberAPI:
    """Interface to VTuber system API"""
    
    def __init__(self, base_url: str = "http://localhost:5001"):
        self.base_url = base_url
        self.session = None
        
    async def __aenter__(self):
        self.session = aiohttp.ClientSession()
        return self
        
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.session:
            await self.session.close()
    
    async def get_status(self) -> Dict[str, Any]:
        """Get VTuber system status"""
        try:
            async with self.session.get(f"{self.base_url}/orchestrator/status") as response:
                if response.status == 200:
                    return await response.json()
                else:
                    logger.warning(f"VTuber status request failed: {response.status}")
                    return {}
        except Exception as e:
            logger.error(f"Error getting VTuber status: {e}")
            return {}
    
    async def send_speech(self, text: str, context: Dict[str, Any] = None) -> bool:
        """Send speech to VTuber system"""
        try:
            payload = {
                "text": text,
                "autonomous_context": context or {"source": "external_orchestrator"}
            }
            
            async with self.session.post(
                f"{self.base_url}/process_text",
                json=payload,
                headers={"Content-Type": "application/json"}
            ) as response:
                success = response.status == 200
                if success:
                    logger.info(f"✅ Speech sent: {text[:50]}...")
                else:
                    logger.warning(f"❌ Speech failed ({response.status}): {text[:50]}...")
                return success
                
        except Exception as e:
            logger.error(f"Error sending speech: {e}")
            return False
    
    async def control_orchestrator(self, action: str, **kwargs) -> bool:
        """Send control commands to embedded orchestrator"""
        try:
            payload = {"action": action, **kwargs}
            
            async with self.session.post(
                f"{self.base_url}/orchestrator/control",
                json=payload,
                headers={"Content-Type": "application/json"}
            ) as response:
                success = response.status == 200
                if success:
                    logger.info(f"✅ Orchestrator control: {action}")
                else:
                    logger.warning(f"❌ Orchestrator control failed: {action}")
                return success
                
        except Exception as e:
            logger.error(f"Error controlling orchestrator: {e}")
            return False


class GameAPI:
    """Interface to Game Control system API"""
    
    def __init__(self, base_url: str = "http://localhost:5001"):
        self.base_url = base_url
        self.session = None
        
    async def __aenter__(self):
        self.session = aiohttp.ClientSession()
        return self
        
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.session:
            await self.session.close()
    
    async def get_health(self) -> Dict[str, Any]:
        """Get game system health status"""
        try:
            async with self.session.get(f"{self.base_url}/game_control/health") as response:
                if response.status == 200:
                    return await response.json()
                else:
                    return {"status": "unhealthy"}
        except Exception as e:
            logger.error(f"Error getting game health: {e}")
            return {"status": "error", "error": str(e)}
    
    async def send_control(self, prompt: str) -> bool:
        """Send game control command"""
        try:
            payload = {"prompt": prompt}
            
            async with self.session.post(
                f"{self.base_url}/game_control",
                json=payload,
                headers={"Content-Type": "application/json"}
            ) as response:
                success = response.status == 200
                if success:
                    logger.info(f"✅ Game control: {prompt}")
                else:
                    logger.warning(f"❌ Game control failed: {prompt}")
                return success
                
        except Exception as e:
            logger.error(f"Error sending game control: {e}")
            return False


class ExternalOrchestrator:
    """
    External Autonomous Orchestrator - The Brain
    
    This orchestrator monitors all systems and makes intelligent decisions
    about when to speak, what to say, and what actions to take.
    """
    
    def __init__(self):
        # Configuration from environment
        self.enabled = os.getenv("EXTERNAL_ORCHESTRATOR_ENABLED", "true").lower() == "true"
        self.decision_interval = float(os.getenv("ORCHESTRATOR_DECISION_INTERVAL", "2.0"))
        self.min_idle_for_speech = float(os.getenv("ORCHESTRATOR_MIN_IDLE", "8.0"))
        self.speech_gap = float(os.getenv("ORCHESTRATOR_SPEECH_GAP", "3.0"))
        
        # Idle thresholds for different content types
        self.idle_thresholds = {
            "ambient": float(os.getenv("IDLE_AMBIENT_THRESHOLD", "10.0")),
            "prompt": float(os.getenv("IDLE_PROMPT_THRESHOLD", "30.0")),
            "engage": float(os.getenv("IDLE_ENGAGE_THRESHOLD", "60.0")),
            "reactivate": float(os.getenv("IDLE_REACTIVATE_THRESHOLD", "120.0"))
        }
        
        # Components
        self.content_generator = ContentGenerator()
        self.system_status = SystemStatus()
        self.action_queue: List[Action] = []
        
        # State tracking
        self.running = False
        self.last_speech_time = 0.0
        self.last_decision_time = 0.0
        self.decision_count = 0
        
        logger.info(f"🧠 External Orchestrator initialized:")
        logger.info(f"   Decision interval: {self.decision_interval}s")
        logger.info(f"   Min idle for speech: {self.min_idle_for_speech}s")
        logger.info(f"   Speech gap: {self.speech_gap}s")
        logger.info(f"   Idle thresholds: {self.idle_thresholds}")
    
    async def start(self):
        """Start the orchestrator"""
        if not self.enabled:
            logger.warning("�� External Orchestrator disabled by configuration")
            return
            
        logger.info("🚀 Starting External Autonomous Orchestrator")
        self.running = True
        
        # Start main decision loop
        await self._decision_loop()
    
    async def stop(self):
        """Stop the orchestrator"""
        logger.info("🛑 Stopping External Orchestrator")
        self.running = False
    
    async def process_external_input(self, prompt: str, context: Dict[str, Any] = None):
        """Process external input and decide what to do"""
        logger.info(f"📥 External input received: {prompt}")
        
        # Generate contextual response
        response = self.content_generator.generate_contextual_content(prompt, context or {})
        
        # Queue high-priority speech action
        action = Action(
            type=ActionType.SPEAK,
            content=response,
            priority=Priority.HIGH,
            metadata={"source": "external_input", "original_prompt": prompt}
        )
        
        self.action_queue.append(action)
        logger.info(f"📋 Queued response: {response[:50]}...")
    
    async def _decision_loop(self):
        """Main decision-making loop"""
        logger.info("�� Decision loop started")
        
        async with VTuberAPI() as vtuber, GameAPI() as game:
            
            while self.running:
                try:
                    # Update system status
                    await self._update_system_status(vtuber, game)
                    
                    # Make decision
                    await self._make_decision(vtuber, game)
                    
                    # Process action queue
                    await self._process_actions(vtuber, game)
                    
                    # Update timing
                    self.last_decision_time = time.time()
                    self.decision_count += 1
                    
                    # Log periodic status
                    if self.decision_count % 30 == 0:  # Every 60 seconds at 2s intervals
                        idle_duration = self.system_status.get_idle_duration()
                        logger.info(f"📊 Status: Idle {idle_duration:.1f}s | "
                                  f"Queue: {len(self.action_queue)} | "
                                  f"Speaking: {self.system_status.vtuber_speaking}")
                    
                    # Wait for next decision cycle
                    await asyncio.sleep(self.decision_interval)
                    
                except Exception as e:
                    logger.error(f"❌ Error in decision loop: {e}")
                    await asyncio.sleep(self.decision_interval)
        
        logger.info("🧠 Decision loop ended")
    
    async def _update_system_status(self, vtuber: VTuberAPI, game: GameAPI):
        """Update current system status"""
        
        # Get VTuber status
        vtuber_status = await vtuber.get_status()
        if vtuber_status:
            current_action = vtuber_status.get("current_action", {})
            self.system_status.vtuber_speaking = current_action.get("is_speaking", False)
            self.system_status.vtuber_queue_size = current_action.get("tts_queue_size", 0)
            
            # Calculate idle duration
            last_input_time = current_action.get("last_input_time", time.time())
            self.system_status.vtuber_idle_duration = time.time() - last_input_time
        
        # Get Game status
        game_status = await game.get_health()
        if game_status and game_status.get("status") == "healthy":
            # Game system is available
            pass
        
        self.system_status.last_update = time.time()
    
    async def _make_decision(self, vtuber: VTuberAPI, game: GameAPI):
        """Make decision about what to do next"""
        
        idle_duration = self.system_status.get_idle_duration()
        
        # Skip if currently speaking or queue is full
        if not self.system_status.is_ready_for_speech():
            return
        
        # Check speech gap
        speech_gap = time.time() - self.last_speech_time
        if speech_gap < self.speech_gap:
            return
        
        # Check if we should generate autonomous content
        if idle_duration >= self.min_idle_for_speech:
            content_type = self._determine_content_type(idle_duration)
            
            if content_type:
                content = self.content_generator.generate_idle_content(
                    idle_duration, 
                    {"type": content_type}
                )
                
                if content:
                    action = Action(
                        type=ActionType.SPEAK,
                        content=content,
                        priority=Priority.LOW,
                        metadata={"source": "autonomous", "content_type": content_type}
                    )
                    
                    self.action_queue.append(action)
                    logger.info(f"🎯 Generated {content_type} content: {content[:50]}...")
    
    def _determine_content_type(self, idle_duration: float) -> Optional[str]:
        """Determine what type of content to generate based on idle duration"""
        
        if idle_duration >= self.idle_thresholds["reactivate"]:
            return "reactivate"
        elif idle_duration >= self.idle_thresholds["engage"]:
            return "engage"
        elif idle_duration >= self.idle_thresholds["prompt"]:
            return "prompt"
        elif idle_duration >= self.idle_thresholds["ambient"]:
            return "ambient"
        
        return None
    
    async def _process_actions(self, vtuber: VTuberAPI, game: GameAPI):
        """Process queued actions"""
        
        if not self.action_queue:
            return
        
        # Sort by priority
        self.action_queue.sort(key=lambda x: x.priority.value, reverse=True)
        
        # Process highest priority action
        action = self.action_queue.pop(0)
        
        if action.type == ActionType.SPEAK:
            success = await vtuber.send_speech(action.content, action.metadata)
            if success:
                self.last_speech_time = time.time()
                logger.info(f"🗣️ Executed speech: {action.content[:50]}...")
            
        elif action.type == ActionType.GAME_CONTROL:
            success = await game.send_control(action.content)
            if success:
                logger.info(f"🎮 Executed game control: {action.content}")


async def main():
    """Main entry point"""
    logger.info("🧠 External Autonomous Orchestrator - Starting")
    
    orchestrator = ExternalOrchestrator()
    
    try:
        # Example: Process external input
        await orchestrator.process_external_input(
            "Tell me something interesting about artificial intelligence"
        )
        
        # Start main orchestrator
        await orchestrator.start()
        
    except KeyboardInterrupt:
        logger.info("👋 Received interrupt signal")
    finally:
        await orchestrator.stop()
        logger.info("🏁 External Orchestrator stopped")


if __name__ == "__main__":
    asyncio.run(main())
