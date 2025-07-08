import asyncio
import aiohttp
import time
import random
import logging
from typing import List, Dict, Any, Optional
from dataclasses import dataclass
import os

logger = logging.getLogger(__name__)

@dataclass
class SpeechConfig:
    """Simple configuration for autonomous speech"""
    speech_interval: float = 15.0  # Generate speech every 15 seconds
    min_speech_gap: float = 3.0    # Minimum gap between speeches
    max_speech_length: int = 80    # Max characters per speech
    endpoint_url: str = "http://localhost:5001/process_text"
    enabled: bool = True

class SimpleAutonomousSpeech:
    """Simple, direct autonomous speech generator"""
    
    def __init__(self, config: SpeechConfig = None):
        self.config = config or SpeechConfig()
        self.logger = logging.getLogger(__name__)
        self.running = False
        self.last_speech_time = 0.0
        self.speech_task = None
        
        # Simple content templates
        self.content_templates = [
            "Hmm, that's interesting...",
            "I'm here if you want to chat!",
            "What's on your mind today?",
            "Feel free to ask me anything.",
            "I'm curious about your thoughts.",
            "How's everything going?",
            "This is a nice moment.",
            "Any interesting ideas lately?",
            "I'm ready to help with anything.",
            "Want to explore something together?",
            "I'm here whenever you need me.",
            "Hope you're having a good day!",
            "Let me know if you'd like to talk.",
            "I'm always happy to chat!",
            "What would you like to discuss?"
        ]
        
        # Recently used content to avoid duplicates
        self.recent_content = []
        self.max_recent = 5
        
        self.logger.info(f"🗣️ Simple Autonomous Speech initialized | Interval: {self.config.speech_interval}s")
        
    async def start(self):
        """Start the autonomous speech generator"""
        if self.running or not self.config.enabled:
            return
        
        # Check environment variable for autonomous speech
        autonomous_speech_enabled = os.getenv('AUTONOMOUS_SPEECH_ENABLED', 'true').lower() == 'true'
        simple_speech_enabled = os.getenv('SIMPLE_SPEECH_ENABLED', 'true').lower() == 'true'
        
        if not autonomous_speech_enabled or not simple_speech_enabled:
            self.logger.info("🚫 Simple Autonomous Speech: DISABLED via environment configuration")
            self.logger.info("✅ Pure stimuli-driven architecture - S1 will only respond to external triggers")
            return
            
        self.running = True
        self.last_speech_time = time.time()
        self.logger.info("🚀 Starting Simple Autonomous Speech Generator")
        
        # Start speech generation loop
        self.speech_task = asyncio.create_task(self._speech_loop())
        
    async def stop(self):
        """Stop the autonomous speech generator"""
        if not self.running:
            return
            
        self.running = False
        self.logger.info("🛑 Stopping Simple Autonomous Speech Generator")
        
        if self.speech_task:
            self.speech_task.cancel()
            try:
                await self.speech_task
            except asyncio.CancelledError:
                pass
                
    async def _speech_loop(self):
        """Main speech generation loop"""
        
        while self.running:
            try:
                current_time = time.time()
                time_since_last = current_time - self.last_speech_time
                
                # Check if it's time to generate speech
                if time_since_last >= self.config.speech_interval:
                    await self._generate_speech()
                    self.last_speech_time = current_time
                    
                # Sleep for a short interval
                await asyncio.sleep(1.0)
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                self.logger.error(f"Error in speech loop: {e}")
                await asyncio.sleep(5.0)  # Wait before retrying
                
    async def _generate_speech(self):
        """Generate and send autonomous speech"""
        
        # Pick content that hasn't been used recently
        content = self._pick_fresh_content()
        
        if not content:
            self.logger.debug("No fresh content available, skipping this cycle")
            return
            
        # Send speech via HTTP
        success = await self._send_speech(content)
        
        if success:
            self.logger.info(f"🎤 Autonomous speech sent: {content[:30]}...")
            
            # Track recent content
            self.recent_content.append(content)
            if len(self.recent_content) > self.max_recent:
                self.recent_content = self.recent_content[-self.max_recent:]
        else:
            self.logger.warning("Failed to send autonomous speech")
            
    def _pick_fresh_content(self) -> Optional[str]:
        """Pick content that hasn't been used recently"""
        
        available_content = [
            content for content in self.content_templates
            if content not in self.recent_content
        ]
        
        if not available_content:
            # Reset if all content has been used
            self.recent_content.clear()
            available_content = self.content_templates
            
        if available_content:
            content = random.choice(available_content)
            
            # Ensure it's not too long
            if len(content) > self.config.max_speech_length:
                content = content[:self.config.max_speech_length]
                
            return content
            
        return None
        
    async def _send_speech(self, content: str) -> bool:
        """Send speech to the process_text endpoint"""
        
        try:
            async with aiohttp.ClientSession() as session:
                payload = {
                    "text": content,
                    "direct_speech": True,
                    "autonomous_context": {
                        "source": "simple_autonomous_speech",
                        "timestamp": time.time(),
                        "speech_interval": self.config.speech_interval,
                        "is_autonomous": True
                    }
                }
                
                async with session.post(self.config.endpoint_url, json=payload) as response:
                    if response.status == 200:
                        return True
                    else:
                        self.logger.error(f"HTTP error: {response.status}")
                        return False
                        
        except Exception as e:
            self.logger.error(f"Error sending speech: {e}")
            return False
            
    def update_last_speech_time(self):
        """Update last speech time (called when user speaks)"""
        self.last_speech_time = time.time()
        
    def get_status(self) -> Dict[str, Any]:
        """Get current status"""
        current_time = time.time()
        time_since_last = current_time - self.last_speech_time
        time_until_next = max(0, self.config.speech_interval - time_since_last)
        
        return {
            "running": self.running,
            "enabled": self.config.enabled,
            "speech_interval": self.config.speech_interval,
            "time_since_last_speech": time_since_last,
            "time_until_next_speech": time_until_next,
            "recent_content_count": len(self.recent_content),
            "endpoint_url": self.config.endpoint_url
        }

# Global instance
_simple_speech_instance = None

def get_simple_speech_instance() -> SimpleAutonomousSpeech:
    """Get the global simple speech instance"""
    global _simple_speech_instance
    
    if _simple_speech_instance is None:
        # Create config from environment variables
        config = SpeechConfig(
            speech_interval=float(os.getenv("SIMPLE_SPEECH_INTERVAL", "15.0")),
            min_speech_gap=float(os.getenv("SIMPLE_SPEECH_GAP", "3.0")),
            max_speech_length=int(os.getenv("SIMPLE_SPEECH_MAX_LENGTH", "80")),
            endpoint_url=os.getenv("SIMPLE_SPEECH_ENDPOINT", "http://localhost:5001/process_text"),
            enabled=os.getenv("SIMPLE_SPEECH_ENABLED", "true").lower() == "true"
        )
        
        _simple_speech_instance = SimpleAutonomousSpeech(config)
        
    return _simple_speech_instance

async def start_simple_autonomous_speech():
    """Start the simple autonomous speech system"""
    speech_system = get_simple_speech_instance()
    await speech_system.start()
    
async def stop_simple_autonomous_speech():
    """Stop the simple autonomous speech system"""
    speech_system = get_simple_speech_instance()
    await speech_system.stop() 