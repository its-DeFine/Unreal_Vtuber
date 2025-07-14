"""
Visual Identity Manager
Handles character visual appearance switching via TCP commands to Unreal Engine
Created: 2025-07-14
"""
import logging
import asyncio
from typing import Dict, List, Any, Optional
from dataclasses import dataclass

from .unreal_tcp_controller import UnrealTCPController, TCPConnectionConfig

logger = logging.getLogger(__name__)

@dataclass
class VisualIdentity:
    """Visual identity configuration for a character"""
    preset_name: str
    tcp_commands: List[str]
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'VisualIdentity':
        """Create VisualIdentity from dictionary"""
        return cls(
            preset_name=data.get('preset_name', 'default'),
            tcp_commands=data.get('tcp_commands', [])
        )


class VisualIdentityManager:
    """
    Manages visual identity switching for VTuber characters
    Sends TCP commands to Unreal Engine when characters switch
    """
    
    def __init__(self, tcp_controller: Optional[UnrealTCPController] = None):
        """
        Initialize Visual Identity Manager
        
        Args:
            tcp_controller: Optional TCP controller instance
        """
        self.tcp_controller = tcp_controller
        self.current_visual_identity: Optional[str] = None
        
        # If no controller provided, create one
        if not self.tcp_controller:
            tcp_host = "host.docker.internal"  # Default for Docker
            tcp_port = 7777
            config = TCPConnectionConfig(host=tcp_host, port=tcp_port)
            self.tcp_controller = UnrealTCPController(config)
            
        logger.info("🎨 Visual Identity Manager initialized")
    
    async def apply_visual_identity(self, visual_identity: VisualIdentity) -> bool:
        """
        Apply a visual identity by sending TCP commands to Unreal Engine
        
        Args:
            visual_identity: Visual identity configuration to apply
            
        Returns:
            True if successful, False otherwise
        """
        if not visual_identity or not visual_identity.tcp_commands:
            logger.warning("🚫 No visual identity commands to apply")
            return False
        
        logger.info(f"🎭 Applying visual identity: {visual_identity.preset_name}")
        
        # Test connection first
        if not await self.tcp_controller.test_connection():
            logger.error("🚫 Cannot connect to Unreal Engine - visual identity not applied")
            return False
        
        # Send commands with optimized delay
        # Group commands that can be sent quickly vs those that need processing time
        critical_commands = ['PRS.', 'OF.']  # Preset and outfit changes need more time
        
        optimized_commands = []
        for cmd in visual_identity.tcp_commands:
            delay = 0.2 if any(cmd.startswith(prefix) for prefix in critical_commands) else 0.05
            optimized_commands.append((cmd, delay))
        
        # Send commands with dynamic delays
        total = len(optimized_commands)
        success = 0
        failed = 0
        
        for i, (cmd, delay) in enumerate(optimized_commands):
            result = await self.tcp_controller.send_command(cmd)
            if result['success']:
                success += 1
            else:
                failed += 1
            
            # Only delay if not the last command
            if i < total - 1:
                await asyncio.sleep(delay)
        
        if success == total:
            self.current_visual_identity = visual_identity.preset_name
            logger.info(f"✅ Visual identity '{visual_identity.preset_name}' applied successfully")
            return True
        else:
            logger.error(f"❌ Failed to apply visual identity: {failed}/{total} commands failed")
            return False
    
    async def apply_character_visual_identity(self, character_data: Dict[str, Any]) -> bool:
        """
        Apply visual identity from character data
        
        Args:
            character_data: Character data containing visual_identity field
            
        Returns:
            True if successful, False otherwise
        """
        visual_identity_data = character_data.get('visual_identity', {})
        
        if not visual_identity_data:
            logger.info("📝 No visual identity defined for character")
            return True  # Not an error, just no visual identity
        
        visual_identity = VisualIdentity.from_dict(visual_identity_data)
        return await self.apply_visual_identity(visual_identity)
    
    async def reset_to_default(self) -> bool:
        """
        Reset to default visual appearance
        
        Returns:
            True if successful
        """
        default_commands = [
            "PRS.Fem",      # Default feminine preset
            "OF.Default",   # Default outfit
            "HS.Default",   # Default hair style
            "HCR.0.5",      # Neutral hair color
            "HCG.0.5",
            "HCB.0.5",
            "EC.0.5",       # Neutral eye color
            "ES.30000.0"    # Medium eye saturation
        ]
        
        logger.info("🔄 Resetting to default visual appearance")
        
        result = await self.tcp_controller.send_commands_batch(
            default_commands,
            delay_between=0.1
        )
        
        if result['success'] == result['total']:
            self.current_visual_identity = "default"
            return True
        return False
    
    def get_current_identity(self) -> Optional[str]:
        """Get the name of the current visual identity"""
        return self.current_visual_identity
    
    async def health_check(self) -> Dict[str, Any]:
        """
        Check health of visual identity system
        
        Returns:
            Health status dictionary
        """
        tcp_health = await self.tcp_controller.health_check()
        
        return {
            "visual_identity_manager": "healthy",
            "current_identity": self.current_visual_identity,
            "tcp_connection": tcp_health
        }


# Singleton instance
_visual_identity_manager: Optional[VisualIdentityManager] = None

def get_visual_identity_manager() -> VisualIdentityManager:
    """Get or create the singleton VisualIdentityManager instance"""
    global _visual_identity_manager
    if _visual_identity_manager is None:
        _visual_identity_manager = VisualIdentityManager()
    return _visual_identity_manager