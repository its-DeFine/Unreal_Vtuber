"""
Shared CORE Components
=====================

Common utilities, configuration, and services used across the CORE system.
"""

# Configuration management
from .config import get_config, initialize_config

__all__ = [
    "get_config",
    "initialize_config"
]