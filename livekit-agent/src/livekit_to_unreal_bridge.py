#!/usr/bin/env python3
"""
LiveKit to Unreal Bridge
Converts LiveKit blendshapes to Unreal LiveLink format and sends them
"""

import socket
import struct
import time
import logging
from typing import List, Dict, Any
import numpy as np

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# UDP connection settings for Unreal
UNREAL_IP = "host.docker.internal"  # For Docker container to host
UNREAL_PORT = 11111

# LiveKit to Unreal blendshape mapping
# LiveKit uses simplified names, Unreal uses ARKit standard (51 shapes)
LIVEKIT_TO_ARKIT_MAPPING = {
    "mouthOpen": 25,        # JawOpen in ARKit
    "jawOpen": 25,          # JawOpen
    "mouthSmile": 12,       # MouthSmileLeft
    "mouthFrown": 14,       # MouthFrownLeft
    "eyeBlinkLeft": 8,      # EyeBlinkLeft
    "eyeBlinkRight": 9,     # EyeBlinkRight
    "browInnerUp": 1,       # BrowInnerUp
    "browDownLeft": 2,      # BrowDownLeft
    "browDownRight": 3,     # BrowDownRight
    "browOuterUpLeft": 4,   # BrowOuterUpLeft
    "browOuterUpRight": 5,  # BrowOuterUpRight
    "cheekPuff": 6,         # CheekPuff
    "cheekSquintLeft": 7,   # CheekSquintLeft
    "cheekSquintRight": 10, # CheekSquintRight (adjusted index)
    "noseSneerLeft": 11,    # NoseSneerLeft
    "noseSneerRight": 13,   # NoseSneerRight (adjusted index)
}

# Full ARKit blendshape names (for reference)
ARKIT_BLENDSHAPES = [
    "EyeBlinkLeft", "EyeBlinkRight", "EyeLookDownLeft", "EyeLookDownRight",
    "EyeLookInLeft", "EyeLookInRight", "EyeLookOutLeft", "EyeLookOutRight",
    "EyeLookUpLeft", "EyeLookUpRight", "EyeSquintLeft", "EyeSquintRight",
    "EyeWideLeft", "EyeWideRight", "JawForward", "JawLeft",
    "JawRight", "JawOpen", "MouthClose", "MouthFunnel",
    "MouthPucker", "MouthLeft", "MouthRight", "MouthSmileLeft",
    "MouthSmileRight", "MouthFrownLeft", "MouthFrownRight", "MouthDimpleLeft",
    "MouthDimpleRight", "MouthStretchLeft", "MouthStretchRight", "MouthRollLower",
    "MouthRollUpper", "MouthShrugLower", "MouthShrugUpper", "MouthPressLeft",
    "MouthPressRight", "MouthLowerDownLeft", "MouthLowerDownRight", "MouthUpperUpLeft",
    "MouthUpperUpRight", "BrowDownLeft", "BrowDownRight", "BrowInnerUp",
    "BrowOuterUpLeft", "BrowOuterUpRight", "CheekPuff", "CheekSquintLeft",
    "CheekSquintRight", "NoseSneerLeft", "NoseSneerRight"
]


class LiveKitToUnrealBridge:
    """
    Bridge to convert LiveKit blendshapes to Unreal LiveLink format
    """
    
    def __init__(self):
        self.socket = None
        self.connected = False
        self.frame_count = 0
    
    def connect(self) -> bool:
        """Connect to Unreal LiveLink UDP server"""
        try:
            logger.info(f"Connecting to Unreal at {UNREAL_IP}:{UNREAL_PORT}")
            self.socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            self.socket.connect((UNREAL_IP, UNREAL_PORT))
            self.connected = True
            logger.info("Connected to Unreal LiveLink")
            return True
        except Exception as e:
            logger.error(f"Failed to connect to Unreal: {e}")
            self.connected = False
            return False
    
    def convert_livekit_to_arkit(self, livekit_shapes: Dict[str, float]) -> List[float]:
        """
        Convert LiveKit blendshape format to ARKit 51-shape array
        
        Args:
            livekit_shapes: Dict with shape names and values from LiveKit
            
        Returns:
            List of 51 float values for ARKit blendshapes
        """
        # Initialize all 51 ARKit blendshapes to 0
        arkit_values = [0.0] * 51
        
        # Map LiveKit shapes to ARKit indices
        for livekit_name, value in livekit_shapes.items():
            if livekit_name in LIVEKIT_TO_ARKIT_MAPPING:
                arkit_index = LIVEKIT_TO_ARKIT_MAPPING[livekit_name]
                if arkit_index < 51:
                    arkit_values[arkit_index] = float(value)
        
        # Add some default animation for missing shapes
        # This helps make the face look more alive
        
        # Subtle eye movement
        if arkit_values[8] == 0 and arkit_values[9] == 0:  # No blinks
            # Add natural eye dart movements
            time_factor = time.time() % 10
            if time_factor < 0.1:  # Quick eye dart
                arkit_values[2] = 0.1  # EyeLookDownLeft
                arkit_values[3] = 0.1  # EyeLookDownRight
        
        # Natural mouth movement based on jawOpen
        jaw_open = arkit_values[25]  # JawOpen
        if jaw_open > 0:
            # Add related mouth shapes
            arkit_values[19] = jaw_open * 0.3  # MouthFunnel
            arkit_values[31] = jaw_open * 0.2  # MouthRollLower
            arkit_values[32] = jaw_open * 0.1  # MouthRollUpper
        
        return arkit_values
    
    def send_blendshapes_to_unreal(self, blendshape_frames: List[Dict]) -> bool:
        """
        Send blendshape frames to Unreal
        
        Args:
            blendshape_frames: List of dicts with 'timestamp' and 'shapes' keys
            
        Returns:
            Success status
        """
        if not self.connected:
            if not self.connect():
                return False
        
        try:
            fps = 60  # Target framerate
            frame_duration = 1.0 / fps
            start_time = time.time()
            
            for frame_index, frame in enumerate(blendshape_frames):
                timestamp = frame.get("timestamp", frame_index * frame_duration)
                shapes = frame.get("shapes", {})
                
                # Convert LiveKit shapes to ARKit format
                arkit_values = self.convert_livekit_to_arkit(shapes)
                
                # Create LiveLink packet
                packet = self.create_livelink_packet(arkit_values, self.frame_count)
                
                # Send to Unreal
                self.socket.sendall(packet)
                self.frame_count += 1
                
                # Maintain target framerate
                elapsed = time.time() - start_time
                expected = timestamp
                if elapsed < expected:
                    time.sleep(expected - elapsed)
                
                # Log progress every 10 frames
                if frame_index % 10 == 0:
                    logger.debug(f"Sent frame {frame_index}/{len(blendshape_frames)}")
            
            logger.info(f"Successfully sent {len(blendshape_frames)} frames to Unreal")
            return True
            
        except Exception as e:
            logger.error(f"Error sending blendshapes to Unreal: {e}")
            return False
    
    def create_livelink_packet(self, blendshape_values: List[float], frame_number: int) -> bytes:
        """
        Create a LiveLink protocol packet for Unreal
        
        This is a simplified version - real LiveLink has more complex protocol
        For now, we'll use a basic format that Unreal can parse
        """
        # Basic packet structure (simplified)
        # [magic_number][frame_number][num_shapes][shape_values...]
        
        packet = bytearray()
        
        # Magic number to identify LiveLink packet
        packet.extend(struct.pack('<I', 0x4C4C464C))  # 'LLFL' in hex
        
        # Frame number
        packet.extend(struct.pack('<I', frame_number))
        
        # Number of blendshapes (51 for ARKit)
        packet.extend(struct.pack('<I', 51))
        
        # Blendshape values as floats
        for value in blendshape_values:
            packet.extend(struct.pack('<f', value))
        
        return bytes(packet)
    
    def send_emotion_command(self, emotion: str):
        """
        Send emotion as TCP command (if TCP controller is available)
        This would normally go through the TCP controller
        """
        logger.info(f"Would send emotion command: FACE.{emotion.capitalize()}")
    
    def disconnect(self):
        """Disconnect from Unreal"""
        if self.socket:
            self.socket.close()
            self.connected = False
            logger.info("Disconnected from Unreal LiveLink")


# Integration with LiveKit agent
def process_livekit_blendshapes(livekit_response: Dict[str, Any]) -> bool:
    """
    Process blendshapes from LiveKit response and send to Unreal
    
    Args:
        livekit_response: Response from LiveKit agent with blendshapes
        
    Returns:
        Success status
    """
    bridge = LiveKitToUnrealBridge()
    
    # Extract blendshapes from LiveKit response
    blendshapes = livekit_response.get("blendshapes", [])
    emotion = livekit_response.get("emotion", "neutral")
    
    if not blendshapes:
        logger.warning("No blendshapes in LiveKit response")
        return False
    
    # Connect to Unreal
    if not bridge.connect():
        logger.error("Failed to connect to Unreal")
        return False
    
    # Send emotion command
    bridge.send_emotion_command(emotion)
    
    # Send blendshapes
    success = bridge.send_blendshapes_to_unreal(blendshapes)
    
    # Disconnect
    bridge.disconnect()
    
    return success


# Test function
def test_bridge():
    """Test the LiveKit to Unreal bridge"""
    
    # Create sample LiveKit blendshapes
    sample_frames = []
    
    for i in range(60):  # 1 second at 60fps
        # Simulate talking animation
        mouth_open = 0.5 + 0.5 * np.sin(i * 0.3)
        jaw_open = mouth_open * 0.8
        
        frame = {
            "timestamp": i / 60.0,
            "shapes": {
                "mouthOpen": mouth_open,
                "jawOpen": jaw_open,
                "mouthSmile": 0.3 if i % 20 < 10 else 0.1,
                "eyeBlinkLeft": 1.0 if i % 40 == 0 else 0.0,
                "eyeBlinkRight": 1.0 if i % 40 == 0 else 0.0,
            }
        }
        sample_frames.append(frame)
    
    # Create bridge and send
    bridge = LiveKitToUnrealBridge()
    
    if bridge.connect():
        print(f"Sending {len(sample_frames)} test frames to Unreal...")
        success = bridge.send_blendshapes_to_unreal(sample_frames)
        
        if success:
            print("✅ Successfully sent blendshapes to Unreal!")
        else:
            print("❌ Failed to send blendshapes")
        
        bridge.disconnect()
    else:
        print("❌ Could not connect to Unreal")


if __name__ == "__main__":
    test_bridge()