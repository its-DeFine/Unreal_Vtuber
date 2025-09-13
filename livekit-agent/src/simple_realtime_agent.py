#!/usr/bin/env python3
"""
Simple Real-time Agent for Testing
A basic WebSocket-based agent that can do real-time speech processing
without full LiveKit SDK dependencies
"""

import asyncio
import logging
import json
import os
from typing import Dict, List, Optional, Any
from dataclasses import dataclass
import websockets
import httpx

try:
    from .ollama_integration import OllamaLLM
except ImportError:
    from ollama_integration import OllamaLLM

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@dataclass
class AgentConfig:
    """Agent configuration"""
    agent_name: str = "Luna"
    personality: str = "friendly, energetic streamer"
    ollama_url: str = "http://vtuber-ollama:11434"
    ollama_model: str = "llama3.2:3b"
    tcp_host: str = "host.docker.internal"  # Connect to host for Unreal
    tcp_port: int = 7777  # Unreal TCP port (Windows) 
    websocket_port: int = 8201
    enable_tcp: bool = False  # Disable TCP by default since Unreal may not be running


class SimpleRealtimeAgent:
    """
    Simple real-time agent for testing without full LiveKit SDK
    """
    
    def __init__(self, config: AgentConfig):
        self.config = config
        self.llm = OllamaLLM(
            model=config.ollama_model,
            base_url=config.ollama_url,
            system_prompt=f"You are {config.agent_name}, a {config.personality}. Keep responses short and conversational."
        )
        self.tcp_reader = None
        self.tcp_writer = None
        self.websocket_server = None
        self.clients = set()
        self.is_running = False
    
    async def connect_tcp(self):
        """Connect to neurosync_s1 TCP server"""
        try:
            logger.info(f"Connecting to TCP server at {self.config.tcp_host}:{self.config.tcp_port}")
            self.tcp_reader, self.tcp_writer = await asyncio.open_connection(
                self.config.tcp_host,
                self.config.tcp_port
            )
            logger.info("Connected to TCP server")
            return True
        except Exception as e:
            logger.error(f"Failed to connect to TCP server: {e}")
            return False
    
    async def send_tcp_command(self, command: str):
        """Send command to Unreal with auto-reconnect"""
        # Skip if TCP is disabled
        if not self.config.enable_tcp:
            logger.debug("TCP commands disabled")
            return True
            
        # Try to reconnect if connection is lost
        if not self.tcp_writer:
            logger.info("TCP not connected, attempting to reconnect...")
            if not await self.connect_tcp():
                logger.warning("Failed to reconnect to TCP")
                return False
        
        try:
            logger.debug(f"Sending TCP command: {command}")
            self.tcp_writer.write(f"{command}\n".encode())
            await self.tcp_writer.drain()
            return True
        except (ConnectionResetError, BrokenPipeError, ConnectionAbortedError) as e:
            logger.warning(f"TCP connection lost: {e}, will reconnect on next command")
            # Close the broken connection
            if self.tcp_writer:
                self.tcp_writer.close()
                self.tcp_writer = None
                self.tcp_reader = None
            return False
        except Exception as e:
            logger.error(f"Failed to send TCP command: {e}")
            # Close connection on any error
            if self.tcp_writer:
                self.tcp_writer.close()
                self.tcp_writer = None
                self.tcp_reader = None
            return False
    
    async def process_text(self, text: str) -> Dict[str, Any]:
        """Process text input and generate response"""
        
        # Generate response using Ollama
        response_text = await self.llm.generate(text, max_tokens=100)
        
        # Analyze emotion (simple keyword-based for now)
        emotion = self.detect_emotion(response_text)
        
        # Generate simple blendshapes (basic mouth movement)
        blendshapes = self.generate_simple_blendshapes(response_text)
        
        return {
            "input": text,
            "response": response_text,
            "emotion": emotion,
            "blendshapes": blendshapes,
            "tcp_commands": [
                f"FACE.{emotion.capitalize()}",
                "startspeaking"
            ]
        }
    
    def detect_emotion(self, text: str) -> str:
        """Simple emotion detection"""
        text_lower = text.lower()
        
        if any(word in text_lower for word in ["happy", "great", "awesome", "wonderful"]):
            return "happy"
        elif any(word in text_lower for word in ["sad", "sorry", "unfortunately"]):
            return "sad"
        elif any(word in text_lower for word in ["excited", "amazing", "wow"]):
            return "excited"
        elif "?" in text:
            return "thinking"
        else:
            return "neutral"
    
    def generate_simple_blendshapes(self, text: str) -> List[Dict]:
        """Generate simple blendshapes for mouth movement"""
        
        # Simple phoneme-like breakdown (very basic)
        words = text.split()
        blendshapes = []
        
        for i, word in enumerate(words):
            # Open mouth for vowels
            vowel_count = sum(1 for c in word.lower() if c in "aeiou")
            mouth_open = min(1.0, vowel_count * 0.2)
            
            blendshapes.append({
                "timestamp": i * 0.3,  # 0.3 seconds per word
                "shapes": {
                    "mouthOpen": mouth_open,
                    "jawOpen": mouth_open * 0.5
                }
            })
            
            # Close mouth between words
            blendshapes.append({
                "timestamp": i * 0.3 + 0.2,
                "shapes": {
                    "mouthOpen": 0.1,
                    "jawOpen": 0.0
                }
            })
        
        return blendshapes
    
    async def handle_websocket(self, websocket, path):
        """Handle WebSocket connections"""
        
        logger.info(f"New WebSocket connection from {websocket.remote_address}")
        self.clients.add(websocket)
        
        try:
            async for message in websocket:
                data = json.loads(message)
                
                if data.get("type") == "text":
                    # Process text input
                    result = await self.process_text(data.get("text", ""))
                    
                    # Send TCP commands
                    for cmd in result.get("tcp_commands", []):
                        await self.send_tcp_command(cmd)
                    
                    # Send response back
                    await websocket.send(json.dumps(result))
                    
                    # Broadcast to all clients
                    for client in self.clients:
                        if client != websocket:
                            try:
                                await client.send(json.dumps({
                                    "type": "broadcast",
                                    "data": result
                                }))
                            except:
                                pass
                
                elif data.get("type") == "command":
                    # Direct TCP command
                    cmd = data.get("command")
                    if cmd:
                        await self.send_tcp_command(cmd)
                        await websocket.send(json.dumps({
                            "type": "command_sent",
                            "command": cmd
                        }))
                
        except websockets.exceptions.ConnectionClosed:
            logger.info("WebSocket connection closed")
        except Exception as e:
            logger.error(f"WebSocket error: {e}")
        finally:
            self.clients.remove(websocket)
    
    async def start_websocket_server(self):
        """Start WebSocket server"""
        
        logger.info(f"Starting WebSocket server on port {self.config.websocket_port}")
        self.websocket_server = await websockets.serve(
            self.handle_websocket,
            "0.0.0.0",
            self.config.websocket_port
        )
        logger.info(f"WebSocket server started on port {self.config.websocket_port}")
    
    async def test_ollama(self):
        """Test Ollama connection"""
        
        logger.info("Testing Ollama connection...")
        
        if await self.llm.ensure_model():
            test_response = await self.llm.generate("Hello! Can you hear me?")
            logger.info(f"Ollama test response: {test_response}")
            return True
        else:
            logger.error("Failed to connect to Ollama or load model")
            return False
    
    async def run(self):
        """Main run loop"""
        
        self.is_running = True
        logger.info(f"Starting Simple Realtime Agent: {self.config.agent_name}")
        
        # Test Ollama
        if not await self.test_ollama():
            logger.warning("Ollama not available, using fallback responses")
        
        # Connect to TCP if enabled
        if self.config.enable_tcp:
            await self.connect_tcp()
        else:
            logger.info("TCP commands disabled - skipping TCP connection")
        
        # Start WebSocket server
        await self.start_websocket_server()
        
        # Send initial greeting
        greeting = f"Hello! {self.config.agent_name} is online and ready!"
        await self.send_tcp_command("FACE.Happy")
        await self.send_tcp_command("EMOTE.Wave")
        
        logger.info("Agent is running. Press Ctrl+C to stop.")
        
        # Keep running
        try:
            while self.is_running:
                await asyncio.sleep(1)
        except KeyboardInterrupt:
            logger.info("Shutting down...")
        finally:
            await self.shutdown()
    
    async def shutdown(self):
        """Shutdown the agent"""
        
        self.is_running = False
        
        # Close WebSocket server
        if self.websocket_server:
            self.websocket_server.close()
            await self.websocket_server.wait_closed()
        
        # Close TCP connection
        if self.tcp_writer:
            self.tcp_writer.close()
            await self.tcp_writer.wait_closed()
        
        # Close LLM
        await self.llm.close()
        
        logger.info("Agent shutdown complete")


async def main():
    """Main entry point"""
    
    config = AgentConfig(
        agent_name=os.getenv("AGENT_NAME", "Luna"),
        personality=os.getenv("PERSONALITY", "friendly, energetic streamer"),
        ollama_url=os.getenv("OLLAMA_URL", "http://vtuber-ollama:11434"),
        ollama_model=os.getenv("LLM_MODEL", "llama3.2:3b"),
        tcp_host=os.getenv("TCP_HOST", "host.docker.internal"),
        tcp_port=int(os.getenv("TCP_PORT", "7777")),
        websocket_port=int(os.getenv("WEBSOCKET_PORT", "8201")),
        enable_tcp=os.getenv("ENABLE_TCP", "false").lower() == "true"
    )
    
    agent = SimpleRealtimeAgent(config)
    await agent.run()


if __name__ == "__main__":
    asyncio.run(main())