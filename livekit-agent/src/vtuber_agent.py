#!/usr/bin/env python3
"""
LiveKit VTuber Agent - Real-time streaming agent with blendshape control
"""

import asyncio
import logging
import os
from typing import Dict, List, Optional, Any
from dataclasses import dataclass
import json

from livekit.agents import (
    Agent,
    AgentContext,
    JobContext,
    WorkerOptions,
    cli,
    llm,
    stt,
    tts,
    vad
)
from livekit.agents.pipeline import AgentPipeline
from livekit.agents.voice_assistant import VoiceAssistant
from livekit import rtc, api
import httpx

from blendshape_controller import BlendshapeController, EmotionAnalyzer
from platform_integration import PlatformChatIntegration
from memory_manager import SessionMemoryManager
from tcp_client import VTuberTCPClient

logger = logging.getLogger(__name__)


@dataclass
class VTuberConfig:
    """Configuration for VTuber agent"""
    agent_name: str = "Luna"
    personality: str = "friendly, energetic, engaging streamer"
    voice_model: str = "nova"
    llm_model: str = "gpt-4o-mini"
    tcp_host: str = "neurosync_s1"
    tcp_port: int = 5001
    central_manager_url: str = "http://central-manager:8000"
    enable_platforms: bool = True
    chat_response_rate: float = 0.3


class VTuberAgent:
    """
    LiveKit-based VTuber agent with real-time audio/video processing
    and blendshape control for facial animations
    """
    
    def __init__(self, config: VTuberConfig):
        self.config = config
        self.ctx: Optional[AgentContext] = None
        self.assistant: Optional[VoiceAssistant] = None
        
        # Initialize components
        self.blendshape_controller = BlendshapeController()
        self.emotion_analyzer = EmotionAnalyzer()
        self.tcp_client = VTuberTCPClient(config.tcp_host, config.tcp_port)
        self.memory_manager = SessionMemoryManager(config.agent_name)
        self.platform_chat = PlatformChatIntegration() if config.enable_platforms else None
        
        # Track state
        self.current_emotion = "neutral"
        self.is_speaking = False
        self.session_active = False
        
    async def on_worker_start(self, worker: WorkerOptions) -> None:
        """Called when the worker starts"""
        logger.info(f"VTuber Agent {self.config.agent_name} starting...")
        
        # Connect to services
        await self.tcp_client.connect()
        await self.memory_manager.initialize()
        
        if self.platform_chat:
            await self.platform_chat.connect()
    
    async def on_job_start(self, job: JobContext) -> None:
        """Called when a new job (room) is assigned"""
        logger.info(f"Joining room: {job.room.name}")
        
        # Initialize session
        self.session_active = True
        await self.memory_manager.start_session(job.room.name)
        
        # Connect to the room
        await job.connect()
        
        # Set up the voice assistant pipeline
        self.ctx = job
        await self.setup_assistant()
        
        # Start platform chat monitoring if enabled
        if self.platform_chat:
            asyncio.create_task(self.monitor_platform_chat())
        
        # Send initial greeting
        await self.send_greeting()
    
    async def setup_assistant(self) -> None:
        """Set up the voice assistant with STT-LLM-TTS pipeline"""
        
        # Create the assistant with LiveKit's pipeline
        self.assistant = VoiceAssistant(
            vad=vad.SileroVAD.load(),  # Voice activity detection
            stt=stt.DeepgramSTT(model="nova-2"),  # Speech to text
            llm=self.create_llm(),  # Language model
            tts=self.create_tts(),  # Text to speech
            allow_interruptions=True,
            interrupt_speech_duration=0.5,
        )
        
        # Set up event handlers
        self.assistant.on("user_speech_started", self.on_user_speech_started)
        self.assistant.on("user_speech_ended", self.on_user_speech_ended)
        self.assistant.on("agent_speech_started", self.on_agent_speech_started)
        self.assistant.on("agent_speech_ended", self.on_agent_speech_ended)
        self.assistant.on("agent_thinking", self.on_agent_thinking)
        
        # Start the assistant
        await self.assistant.start(self.ctx.room)
    
    def create_llm(self) -> llm.LLM:
        """Create the language model with VTuber personality"""
        
        # System prompt with personality
        system_prompt = f"""
You are {self.config.agent_name}, a virtual streamer with this personality: {self.config.personality}.

Guidelines:
- Be engaging and interactive with viewers
- React naturally to what's happening
- Use expressive language that matches your personality
- Keep responses concise and natural for conversation
- Reference streaming context when appropriate
- Be supportive and encouraging to viewers

Current context:
- You're live streaming and interacting with viewers
- Respond naturally as if in a real conversation
- Express emotions through your voice and words
"""
        
        # Create LLM (can use OpenAI or local Ollama)
        if "gpt" in self.config.llm_model:
            from livekit.plugins import openai
            return openai.LLM(
                model=self.config.llm_model,
                temperature=0.8,
                system_prompt=system_prompt
            )
        else:
            # Use local Ollama
            return self.create_ollama_llm(system_prompt)
    
    def create_ollama_llm(self, system_prompt: str) -> llm.LLM:
        """Create Ollama LLM for local inference"""
        # Custom Ollama integration
        from ollama_integration import OllamaLLM
        return OllamaLLM(
            model=self.config.llm_model,
            base_url="http://vtuber-ollama:11434",
            system_prompt=system_prompt
        )
    
    def create_tts(self) -> tts.TTS:
        """Create TTS with blendshape generation"""
        
        # Use ElevenLabs or custom TTS
        from livekit.plugins import elevenlabs
        
        # Wrap TTS with blendshape generation
        base_tts = elevenlabs.TTS(
            voice=self.config.voice_model,
            model="eleven_turbo_v2"
        )
        
        # Create wrapper that generates blendshapes
        return BlendshapeTTS(
            base_tts=base_tts,
            blendshape_controller=self.blendshape_controller,
            tcp_client=self.tcp_client
        )
    
    async def on_user_speech_started(self, event: Dict) -> None:
        """Handle user starting to speak"""
        logger.debug("User started speaking")
        
        # Update VTuber to listening state
        await self.tcp_client.send_command("FACE.Listening")
        self.current_emotion = "listening"
    
    async def on_user_speech_ended(self, event: Dict) -> None:
        """Handle user finishing speech"""
        text = event.get("text", "")
        logger.info(f"User said: {text}")
        
        # Store in memory
        await self.memory_manager.add_interaction(
            user_text=text,
            platform="voice"
        )
    
    async def on_agent_thinking(self, event: Dict) -> None:
        """Handle agent thinking state"""
        logger.debug("Agent thinking...")
        
        # Show thinking animation
        await self.tcp_client.send_command("FACE.Thinking")
        self.current_emotion = "thinking"
    
    async def on_agent_speech_started(self, event: Dict) -> None:
        """Handle agent starting to speak"""
        text = event.get("text", "")
        logger.info(f"Agent saying: {text}")
        
        # Analyze emotion from text
        emotion = self.emotion_analyzer.analyze(text)
        self.current_emotion = emotion
        
        # Send facial expression
        await self.tcp_client.send_command(f"FACE.{emotion.capitalize()}")
        await self.tcp_client.send_command("startspeaking")
        
        self.is_speaking = True
        
        # Store response in memory
        await self.memory_manager.add_interaction(
            agent_text=text,
            emotion=emotion
        )
    
    async def on_agent_speech_ended(self, event: Dict) -> None:
        """Handle agent finishing speech"""
        logger.debug("Agent finished speaking")
        
        await self.tcp_client.send_command("stopspeaking")
        self.is_speaking = False
        
        # Return to neutral/idle
        await asyncio.sleep(0.5)
        if not self.is_speaking:
            await self.tcp_client.send_command("FACE.Neutral")
            self.current_emotion = "neutral"
    
    async def monitor_platform_chat(self) -> None:
        """Monitor platform chat and inject messages into conversation"""
        
        while self.session_active:
            try:
                # Get chat messages from platforms
                messages = await self.platform_chat.get_messages(timeout=0.1)
                
                for msg in messages:
                    # Decide if we should respond
                    if self.should_respond_to_chat(msg):
                        await self.handle_chat_message(msg)
                
                await asyncio.sleep(0.1)
                
            except Exception as e:
                logger.error(f"Error monitoring chat: {e}")
    
    def should_respond_to_chat(self, message: Dict) -> bool:
        """Determine if we should respond to a chat message"""
        
        # Always respond to mentions
        if f"@{self.config.agent_name}" in message.get("text", ""):
            return True
        
        # Random response based on rate
        import random
        return random.random() < self.config.chat_response_rate
    
    async def handle_chat_message(self, message: Dict) -> None:
        """Handle a chat message from platforms"""
        
        user = message.get("user", "Viewer")
        text = message.get("text", "")
        platform = message.get("platform", "chat")
        
        logger.info(f"[{platform}] {user}: {text}")
        
        # Store in memory
        await self.memory_manager.add_interaction(
            user_text=text,
            platform=platform,
            user=user
        )
        
        # Generate response using LLM
        response = await self.generate_chat_response(user, text, platform)
        
        if response:
            # Speak the response
            await self.speak(response)
            
            # Send to platform chat
            if self.platform_chat:
                await self.platform_chat.send_message(response, platform)
    
    async def generate_chat_response(self, user: str, text: str, platform: str) -> str:
        """Generate a response to a chat message"""
        
        # Use the assistant's LLM
        prompt = f"Respond to {user} from {platform} who said: {text}"
        
        # Get response from LLM
        # This would use the assistant's LLM instance
        response = await self.assistant.llm.generate(prompt)
        
        return response
    
    async def speak(self, text: str) -> None:
        """Make the VTuber speak with animation"""
        
        # Trigger speech through the assistant
        await self.assistant.say(text)
    
    async def send_greeting(self) -> None:
        """Send initial greeting when joining"""
        
        greeting = f"Hey everyone! {self.config.agent_name} here! Ready for an awesome stream? Let's go!"
        await self.speak(greeting)
        
        # Do a wave animation
        await self.tcp_client.send_command("EMOTE.Wave")
    
    async def on_job_end(self, job: JobContext) -> None:
        """Called when the job (room) ends"""
        logger.info("Leaving room")
        
        self.session_active = False
        
        # Consolidate memory
        summary = await self.memory_manager.end_session()
        
        # Send to central manager
        if summary:
            await self.send_session_summary(summary)
        
        # Cleanup
        if self.assistant:
            await self.assistant.stop()
        
        await self.tcp_client.disconnect()
    
    async def send_session_summary(self, summary: Dict) -> None:
        """Send session summary to central manager"""
        
        try:
            async with httpx.AsyncClient() as client:
                await client.post(
                    f"{self.config.central_manager_url}/api/sessions",
                    json={
                        "agent_id": self.config.agent_name,
                        "summary": summary
                    }
                )
        except Exception as e:
            logger.error(f"Failed to send session summary: {e}")


class BlendshapeTTS(tts.TTS):
    """
    TTS wrapper that generates blendshapes alongside audio
    """
    
    def __init__(
        self,
        base_tts: tts.TTS,
        blendshape_controller: BlendshapeController,
        tcp_client: VTuberTCPClient
    ):
        self.base_tts = base_tts
        self.blendshape_controller = blendshape_controller
        self.tcp_client = tcp_client
    
    async def synthesize(
        self,
        text: str,
        *,
        voice: Optional[str] = None,
        **kwargs
    ) -> tts.SynthesizeResult:
        """Synthesize speech with blendshape generation"""
        
        # Get audio from base TTS
        result = await self.base_tts.synthesize(text, voice=voice, **kwargs)
        
        # Generate blendshapes from audio
        blendshapes = await self.blendshape_controller.generate_from_audio(
            result.audio,
            result.sample_rate
        )
        
        # Send blendshapes to VTuber in sync with audio
        asyncio.create_task(self.send_blendshapes(blendshapes, result.duration))
        
        return result
    
    async def send_blendshapes(self, blendshapes: List[Dict], duration: float) -> None:
        """Send blendshapes to VTuber synchronized with audio"""
        
        if not blendshapes:
            return
        
        # Calculate timing for each blendshape
        interval = duration / len(blendshapes)
        
        for shape in blendshapes:
            # Send blendshape command
            await self.tcp_client.send_blendshape(shape)
            await asyncio.sleep(interval)


async def main():
    """Main entry point"""
    
    # Load configuration
    config = VTuberConfig(
        agent_name=os.getenv("AGENT_NAME", "Luna"),
        personality=os.getenv("PERSONALITY", "friendly, energetic streamer"),
        tcp_host=os.getenv("TCP_HOST", "neurosync_s1"),
        tcp_port=int(os.getenv("TCP_PORT", "5001")),
        central_manager_url=os.getenv("MANAGER_URL", "http://central-manager:8000"),
        enable_platforms=os.getenv("ENABLE_PLATFORMS", "true").lower() == "true"
    )
    
    # Create agent
    agent = VTuberAgent(config)
    
    # Run the LiveKit worker
    worker_options = WorkerOptions(
        entrypoint=agent.on_job_start,
        on_worker_start=agent.on_worker_start,
        on_job_end=agent.on_job_end,
    )
    
    # Start the worker
    await cli.run_app(worker_options)


if __name__ == "__main__":
    # Set up logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # Run the agent
    asyncio.run(main())