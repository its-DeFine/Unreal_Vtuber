# This software is licensed under a **dual-license model**
# For individuals and businesses earning **under $1M per year**, this software is licensed under the **MIT License**
# Businesses or organizations with **annual revenue of $1,000,000 or more** must obtain permission to use this software commercially.

# unreal_tcp_controller.py
import socket
import asyncio
import logging
import time
from typing import List, Optional, Dict, Any
from dataclasses import dataclass

@dataclass
class TCPConnectionConfig:
    """Configuration for TCP connection to Unreal Engine"""
    host: str = "127.0.0.1"
    port: int = 7777
    timeout: float = 2.0
    retry_attempts: int = 3
    retry_delay: float = 1.0

class UnrealTCPController:
    """
    TCP controller for sending commands to Unreal Engine avatar/VTuber application
    Handles connection management, error recovery, and batch command processing
    """
    
    def __init__(self, config: Optional[TCPConnectionConfig] = None):
        self.config = config or TCPConnectionConfig()
        self.logger = logging.getLogger(__name__)
        self.connection_status = {"connected": False, "last_test": 0}
        
        self.logger.info(f"🎮 Unreal TCP Controller initialized - {self.config.host}:{self.config.port}")
    
    async def test_connection(self) -> bool:
        """
        Test if the TCP server is reachable
        
        Returns:
            True if connection successful, False otherwise
        """
        try:
            reader, writer = await asyncio.wait_for(
                asyncio.open_connection(self.config.host, self.config.port),
                timeout=self.config.timeout
            )
            writer.close()
            await writer.wait_closed()
            
            self.connection_status["connected"] = True
            self.connection_status["last_test"] = time.time()
            self.logger.debug(f"✅ TCP connection test successful")
            return True
            
        except asyncio.TimeoutError:
            self.logger.warning(f"⏰ TCP connection timeout to {self.config.host}:{self.config.port}")
            return False
        except ConnectionRefusedError:
            self.logger.warning(f"🚫 TCP connection refused to {self.config.host}:{self.config.port}")
            return False
        except Exception as e:
            self.logger.error(f"❌ TCP connection test failed: {e}")
            return False
    
    async def send_command(self, command: str) -> bool:
        """
        Send a single command to the TCP server
        
        Args:
            command: TCP command string (e.g., "HCR.0.9")
            
        Returns:
            True if command sent successfully, False otherwise
        """
        if not command or not isinstance(command, str):
            self.logger.warning(f"🚫 Invalid command: {command}")
            return False
        
        # Add newline if not present
        if not command.endswith('\n'):
            command += '\n'
            
        try:
            reader, writer = await asyncio.wait_for(
                asyncio.open_connection(self.config.host, self.config.port),
                timeout=self.config.timeout
            )
            
            writer.write(command.encode())
            await writer.drain()
            
            writer.close()
            await writer.wait_closed()
            
            self.logger.info(f"🎯 Sent command: {command.strip()}")
            return True
            
        except asyncio.TimeoutError:
            self.logger.error(f"⏰ Timeout sending command: {command.strip()}")
            return False
        except ConnectionRefusedError:
            self.logger.error(f"🚫 Connection refused for command: {command.strip()}")
            return False
        except Exception as e:
            self.logger.error(f"❌ Failed to send command '{command.strip()}': {e}")
            return False
    
    async def send_commands_batch(self, commands: List[str], delay_between: float = 0.1) -> Dict[str, Any]:
        """
        Send multiple commands in sequence with optional delays
        
        Args:
            commands: List of TCP command strings
            delay_between: Delay in seconds between commands
            
        Returns:
            Dictionary with results summary
        """
        if not commands:
            self.logger.info("📝 No commands to send")
            return {"success": 0, "failed": 0, "total": 0, "commands": []}
        
        self.logger.info(f"🚀 Sending batch of {len(commands)} commands to Unreal Engine")
        
        # Test connection first
        if not await self.test_connection():
            self.logger.error("🚫 Cannot connect to Unreal Engine - skipping batch")
            return {
                "success": 0, 
                "failed": len(commands), 
                "total": len(commands),
                "commands": commands,
                "error": "Connection failed"
            }
        
        results = {"success": 0, "failed": 0, "total": len(commands), "commands": []}
        
        for i, command in enumerate(commands):
            # Attempt to send command with retries
            success = await self._send_command_with_retry(command)
            
            if success:
                results["success"] += 1
                results["commands"].append({"command": command, "status": "success"})
            else:
                results["failed"] += 1
                results["commands"].append({"command": command, "status": "failed"})
            
            # Add delay between commands (except for the last one)
            if i < len(commands) - 1 and delay_between > 0:
                await asyncio.sleep(delay_between)
        
        self.logger.info(f"✅ Batch complete: {results['success']}/{results['total']} commands successful")
        return results
    
    async def _send_command_with_retry(self, command: str) -> bool:
        """
        Send command with retry logic
        
        Args:
            command: TCP command string
            
        Returns:
            True if command sent successfully after retries
        """
        for attempt in range(self.config.retry_attempts):
            success = await self.send_command(command)
            if success:
                return True
            
            if attempt < self.config.retry_attempts - 1:
                self.logger.debug(f"🔄 Retrying command {command.strip()} (attempt {attempt + 2}/{self.config.retry_attempts})")
                await asyncio.sleep(self.config.retry_delay)
        
        self.logger.error(f"💥 Failed to send command after {self.config.retry_attempts} attempts: {command.strip()}")
        return False
    
    async def send_preset_sequence(self, preset_name: str) -> bool:
        """
        Send a predefined sequence of commands for common setups
        
        Args:
            preset_name: Name of preset sequence
            
        Returns:
            True if sequence sent successfully
        """
        sequences = {
            "reset": ["PRS.Fem", "OF.Default", "HS.Default", "LVL.Home"],
            "medieval_fem": ["PRS.Fem", "OF.Kimono", "LVL.Medieval"],
            "dj_party": ["PRS.Fem", "OF.Pop Star", "LVL.DJ", "ANIM.Dance"],
            "maid_cafe": ["PRS.Fem", "OF.Maid Dress", "LVL.Lofi"],
            "night_scene": ["SNH.0.1", "STRB.0.9", "CLDS.0.2"]
        }
        
        if preset_name not in sequences:
            self.logger.error(f"🚫 Unknown preset sequence: {preset_name}")
            return False
        
        commands = sequences[preset_name]
        self.logger.info(f"🎭 Sending preset sequence '{preset_name}': {commands}")
        
        result = await self.send_commands_batch(commands)
        return result["success"] == result["total"]
    
    def get_connection_status(self) -> Dict[str, Any]:
        """
        Get current connection status information
        
        Returns:
            Dictionary with connection status details
        """
        return {
            "connected": self.connection_status["connected"],
            "last_test": self.connection_status["last_test"],
            "host": self.config.host,
            "port": self.config.port,
            "timeout": self.config.timeout
        }
    
    async def health_check(self) -> Dict[str, Any]:
        """
        Perform comprehensive health check
        
        Returns:
            Dictionary with health status
        """
        self.logger.info("🔍 Performing Unreal Engine TCP health check")
        
        # Test connection
        connection_ok = await self.test_connection()
        
        # Test simple command if connection works
        command_ok = False
        if connection_ok:
            # Send a harmless test command (just open/close menu)
            command_ok = await self.send_command("MENU.")
            await asyncio.sleep(0.1)
            await self.send_command("CMENU.")  # Close menu
        
        health_status = {
            "connection": "healthy" if connection_ok else "unhealthy",
            "commands": "healthy" if command_ok else "untested",
            "overall": "healthy" if connection_ok else "unhealthy",
            "timestamp": time.time(),
            "config": {
                "host": self.config.host,
                "port": self.config.port,
                "timeout": self.config.timeout
            }
        }
        
        self.logger.info(f"📊 Health check complete: {health_status['overall']}")
        return health_status 