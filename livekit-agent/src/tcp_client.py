"""
TCP Client for VTuber control
Sends commands to neurosync_s1 for avatar control
"""

import asyncio
import json
import logging
from typing import Dict, Optional, List
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class TCPCommand:
    """TCP command structure"""
    command: str
    params: Optional[Dict] = None
    timestamp: Optional[float] = None


class VTuberTCPClient:
    """
    TCP client for controlling VTuber avatar via neurosync_s1
    """
    
    def __init__(self, host: str = "neurosync_s1", port: int = 5001):
        self.host = host
        self.port = port
        self.reader: Optional[asyncio.StreamReader] = None
        self.writer: Optional[asyncio.StreamWriter] = None
        self.connected = False
        self.command_queue = asyncio.Queue()
        self.processor_task: Optional[asyncio.Task] = None
    
    async def connect(self) -> bool:
        """Connect to neurosync_s1 TCP server"""
        
        try:
            logger.info(f"Connecting to VTuber TCP server at {self.host}:{self.port}")
            self.reader, self.writer = await asyncio.open_connection(self.host, self.port)
            self.connected = True
            
            # Start command processor
            self.processor_task = asyncio.create_task(self._process_commands())
            
            logger.info("Successfully connected to VTuber TCP server")
            return True
            
        except Exception as e:
            logger.error(f"Failed to connect to TCP server: {e}")
            self.connected = False
            return False
    
    async def disconnect(self) -> None:
        """Disconnect from TCP server"""
        
        if self.processor_task:
            self.processor_task.cancel()
            
        if self.writer:
            self.writer.close()
            await self.writer.wait_closed()
            
        self.connected = False
        logger.info("Disconnected from VTuber TCP server")
    
    async def send_command(self, command: str, params: Optional[Dict] = None) -> bool:
        """Send a command to the VTuber"""
        
        if not self.connected:
            logger.warning(f"Not connected. Cannot send command: {command}")
            return False
        
        try:
            # Create command object
            cmd = TCPCommand(command=command, params=params)
            
            # Add to queue for processing
            await self.command_queue.put(cmd)
            return True
            
        except Exception as e:
            logger.error(f"Failed to queue command {command}: {e}")
            return False
    
    async def _process_commands(self) -> None:
        """Process commands from the queue"""
        
        while self.connected:
            try:
                # Get next command
                cmd = await asyncio.wait_for(self.command_queue.get(), timeout=0.1)
                
                # Send the command
                await self._send_raw_command(cmd.command, cmd.params)
                
                # Small delay between commands to avoid overwhelming
                await asyncio.sleep(0.01)
                
            except asyncio.TimeoutError:
                continue
            except Exception as e:
                logger.error(f"Error processing command: {e}")
    
    async def _send_raw_command(self, command: str, params: Optional[Dict] = None) -> None:
        """Send raw command to TCP server"""
        
        if not self.writer:
            return
        
        try:
            # Format command based on neurosync_s1 protocol
            if params:
                message = json.dumps({"command": command, "params": params})
            else:
                # Simple text command
                message = command
            
            # Send command
            self.writer.write(f"{message}\n".encode())
            await self.writer.drain()
            
            logger.debug(f"Sent TCP command: {command}")
            
        except Exception as e:
            logger.error(f"Failed to send TCP command: {e}")
            # Try to reconnect
            await self.reconnect()
    
    async def reconnect(self) -> bool:
        """Reconnect to TCP server"""
        
        logger.info("Attempting to reconnect to TCP server...")
        await self.disconnect()
        await asyncio.sleep(1)
        return await self.connect()
    
    # High-level command methods
    
    async def set_face_expression(self, expression: str) -> bool:
        """Set facial expression"""
        return await self.send_command(f"FACE.{expression}")
    
    async def play_emote(self, emote: str) -> bool:
        """Play an emote animation"""
        return await self.send_command(f"EMOTE.{emote}")
    
    async def start_speaking(self) -> bool:
        """Start speaking animation"""
        return await self.send_command("startspeaking")
    
    async def stop_speaking(self) -> bool:
        """Stop speaking animation"""
        return await self.send_command("stopspeaking")
    
    async def send_blendshape(self, blendshape: Dict[str, float]) -> bool:
        """Send blendshape values"""
        
        # Convert blendshape dict to commands
        commands = []
        for shape_name, value in blendshape.items():
            if value > 0.01:  # Only send significant values
                commands.append(f"BS_{shape_name}_{value:.3f}")
        
        # Send all commands
        for cmd in commands:
            await self.send_command(cmd)
        
        return True
    
    async def set_morph_target(self, target: str, value: float) -> bool:
        """Set a morph target value"""
        return await self.send_command(f"MT_{target}_{value:.2f}")
    
    async def change_outfit(self, outfit: str) -> bool:
        """Change character outfit"""
        return await self.send_command(f"OUTFIT.{outfit}")
    
    async def change_character(self, character: str) -> bool:
        """Change to a different character"""
        return await self.send_command(f"NEW.Character_{character}")
    
    async def set_camera(self, view: str) -> bool:
        """Set camera view"""
        return await self.send_command(f"CAMERA.{view}")
    
    async def spawn_object(self, object_type: str, params: Optional[Dict] = None) -> bool:
        """Spawn a 3D object"""
        return await self.send_command(f"3D.{object_type}", params)
    
    async def play_video(self, url: str) -> bool:
        """Play video on virtual screen"""
        return await self.send_command("PLAYVIDEO", {"url": url})
    
    async def send_batch_commands(self, commands: List[str]) -> bool:
        """Send multiple commands in sequence"""
        
        for cmd in commands:
            await self.send_command(cmd)
            await asyncio.sleep(0.05)  # Small delay between commands
        
        return True
    
    async def ping(self) -> bool:
        """Send ping to check connection"""
        
        try:
            await self._send_raw_command("PING")
            return True
        except:
            return False
    
    async def health_check(self) -> bool:
        """Check if connection is healthy"""
        
        if not self.connected:
            return False
        
        return await self.ping()