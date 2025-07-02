"""
Character Visual Setup Package

Provides automated visual appearance configuration for different character types.
Each character has a distinct visual identity with specific colors, outfits, and environments.

Available Characters:
- Professor Agatha: Blue hair, blue eyes, professional academic look
- Streamer: Pink/purple hair, bright violet eyes, modern streaming setup

Usage:
    from character_visual_setups import apply_professor_agatha_appearance, apply_streamer_appearance
    
    # Apply Professor Agatha's look
    apply_professor_agatha_appearance(enhanced=True)
    
    # Apply Streamer's look  
    apply_streamer_appearance(enhanced=True, dynamic=True)
"""

import os
import socket

from .professor_agatha_setup import apply_professor_agatha_appearance, ProfessorAgathaVisualSetup
from .streamer_setup import apply_streamer_appearance, StreamerVisualSetup

__all__ = [
    'apply_professor_agatha_appearance',
    'ProfessorAgathaVisualSetup', 
    'apply_streamer_appearance',
    'StreamerVisualSetup',
    'get_tcp_host'
]

def get_tcp_host() -> str:
    """
    Automatically detect the correct TCP host for Unreal Engine connection
    
    Returns:
        str: The appropriate host address
    """
    # Check if we're running inside a Docker container
    if os.path.exists('/.dockerenv'):
        # Running inside container - use host.docker.internal to reach host
        return "host.docker.internal"
    else:
        # Running on host - use localhost
        return "127.0.0.1"

def test_tcp_connection(host: str = None, port: int = 7777, timeout: float = 2.0) -> bool:
    """
    Test TCP connection to Unreal Engine server
    
    Args:
        host: Host to test (auto-detected if None)
        port: TCP port (default: 7777)
        timeout: Connection timeout in seconds
        
    Returns:
        bool: True if connection successful
    """
    if host is None:
        host = get_tcp_host()
    
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(timeout)
        result = sock.connect_ex((host, port))
        sock.close()
        return result == 0
    except Exception:
        return False

# Character mapping for easy access
CHARACTER_SETUPS = {
    'demo_teacher': apply_professor_agatha_appearance,
    'professor_agatha': apply_professor_agatha_appearance,
    'reactive_default': apply_streamer_appearance,
    'streamer': apply_streamer_appearance,
    'streaming_star': apply_streamer_appearance
}

def apply_character_appearance(character_id: str, enhanced: bool = True, **kwargs) -> bool:
    """
    Apply visual appearance for a character by ID
    
    Args:
        character_id: Character identifier (e.g., 'demo_teacher', 'reactive_default')
        enhanced: Whether to apply enhanced features
        **kwargs: Additional arguments for specific character setups
    
    Returns:
        True if setup completed successfully
    """
    if character_id in CHARACTER_SETUPS:
        setup_function = CHARACTER_SETUPS[character_id]
        return setup_function(enhanced=enhanced, **kwargs)
    else:
        print(f"❌ Unknown character ID: {character_id}")
        return False 