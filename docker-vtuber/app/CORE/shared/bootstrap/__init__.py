"""
Core System Bootstrap
====================

Central bootstrap system that initializes and wires all services.
"""

from .core_bootstrap import (
    CoreBootstrap,
    get_bootstrap,
    initialize_core_system,
    start_simplified_system,
    start_production_system,
    start_test_system,
    main
)

__all__ = [
    "CoreBootstrap",
    "get_bootstrap",
    "initialize_core_system",
    "start_simplified_system",
    "start_production_system", 
    "start_test_system",
    "main"
]