#!/usr/bin/env python3
"""
LiveKit Integration Bridge for llm_to_face.py
Provides a bridge between the existing llm_to_face system and LiveKit real-time agent
"""

import asyncio
import json
import logging
import websockets
from typing import Dict, Any, Optional
from dataclasses import dataclass
import httpx

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@dataclass
class LiveKitBridgeConfig:
    """Configuration for LiveKit bridge"""
    livekit_ws_url: str = "ws://livekit-agent:8201"
    s1_http_url: str = "http://neurosync_s1:5000"
    enable_blendshapes: bool = True
    enable_tcp_commands: bool = True


class LiveKitBridge:
    """
    Bridge between llm_to_face.py and LiveKit agent
    Replaces the traditional LLM processing with LiveKit real-time processing
    """
    
    def __init__(self, config: LiveKitBridgeConfig = None):
        self.config = config or LiveKitBridgeConfig()
        self.websocket = None
        self.http_client = httpx.AsyncClient(timeout=30.0)
        self.is_connected = False
    
    async def connect(self) -> bool:
        """Connect to LiveKit agent WebSocket"""
        try:
            logger.info(f"Connecting to LiveKit agent at {self.config.livekit_ws_url}")
            self.websocket = await websockets.connect(self.config.livekit_ws_url)
            self.is_connected = True
            logger.info("Connected to LiveKit agent")
            return True
        except Exception as e:
            logger.error(f"Failed to connect to LiveKit agent: {e}")
            self.is_connected = False
            return False
    
    async def process_text_with_livekit(
        self, 
        text: str, 
        autonomous_context: Optional[Dict] = None,
        direct_speech: bool = False
    ) -> Dict[str, Any]:
        """
        Process text through LiveKit agent instead of traditional LLM
        Returns response with generated speech, emotions, and blendshapes
        """
        
        if not self.is_connected:
            if not await self.connect():
                raise ConnectionError("Cannot connect to LiveKit agent")
        
        try:
            # Prepare message for LiveKit
            message = {
                "type": "text",
                "text": text,
                "context": autonomous_context,
                "direct_speech": direct_speech
            }
            
            logger.info(f"Sending to LiveKit: {text[:100]}...")
            
            # Send to LiveKit agent
            await self.websocket.send(json.dumps(message))
            
            # Wait for response
            response_data = await self.websocket.recv()
            response = json.loads(response_data)
            
            logger.info(f"LiveKit response: {response.get('response', '')[:100]}...")
            
            # Extract components from LiveKit response
            result = {
                "text": response.get("response", ""),
                "emotion": response.get("emotion", "neutral"),
                "blendshapes": response.get("blendshapes", []),
                "tcp_commands": response.get("tcp_commands", []),
                "source": "livekit_agent"
            }
            
            # Process blendshapes if enabled
            if self.config.enable_blendshapes and result["blendshapes"]:
                await self.send_blendshapes_to_unreal(result["blendshapes"])
            
            # Process TCP commands if enabled (already sent by LiveKit agent)
            if self.config.enable_tcp_commands and result["tcp_commands"]:
                logger.info(f"TCP commands sent by LiveKit: {result['tcp_commands']}")
            
            return result
            
        except Exception as e:
            logger.error(f"Error processing with LiveKit: {e}")
            raise
    
    async def send_blendshapes_to_unreal(self, blendshapes: list):
        """
        Send blendshapes to Unreal via send_to_unreal.py endpoint
        """
        try:
            # Format blendshapes for Unreal
            formatted_shapes = []
            for shape in blendshapes:
                formatted_shapes.append({
                    "timestamp": shape.get("timestamp", 0),
                    "shapes": shape.get("shapes", {})
                })
            
            # Send to Unreal endpoint (if it exists)
            # This would integrate with send_to_unreal.py
            logger.info(f"Would send {len(formatted_shapes)} blendshape frames to Unreal")
            
            # TODO: Implement actual sending to send_to_unreal.py
            # This would require the endpoint to be available
            
        except Exception as e:
            logger.error(f"Error sending blendshapes: {e}")
    
    async def process_direct_speech(self, text: str) -> Dict[str, Any]:
        """
        Process direct speech through LiveKit (bypasses LLM)
        """
        return await self.process_text_with_livekit(
            text=text,
            direct_speech=True
        )
    
    async def disconnect(self):
        """Disconnect from LiveKit agent"""
        if self.websocket:
            await self.websocket.close()
            self.is_connected = False
        
        await self.http_client.aclose()
        logger.info("Disconnected from LiveKit agent")


# Flask integration helper
def create_livekit_processor():
    """
    Create a LiveKit processor for Flask integration
    This can be imported by llm_to_face.py
    """
    bridge = LiveKitBridge()
    
    async def process_with_livekit(text: str, **kwargs) -> Dict[str, Any]:
        """Process text with LiveKit agent"""
        return await bridge.process_text_with_livekit(text, **kwargs)
    
    return process_with_livekit


# Standalone test
async def test_bridge():
    """Test the LiveKit bridge"""
    
    bridge = LiveKitBridge()
    
    if await bridge.connect():
        # Test normal text processing
        result = await bridge.process_text_with_livekit(
            "Hello! How are you doing today?"
        )
        
        print(f"Response: {result['text']}")
        print(f"Emotion: {result['emotion']}")
        print(f"Blendshapes: {len(result['blendshapes'])} frames")
        print(f"TCP Commands: {result['tcp_commands']}")
        
        await bridge.disconnect()
    else:
        print("Failed to connect to LiveKit agent")


if __name__ == "__main__":
    asyncio.run(test_bridge())