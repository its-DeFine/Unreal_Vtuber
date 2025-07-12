"""
Dependency Injection Module
==========================

Clean service management with proper lifecycle handling.
"""

from .container import (
    DIContainer,
    ServiceLifecycle,
    get_container,
    reset_container,
    singleton,
    transient
)

__all__ = [
    "DIContainer",
    "ServiceLifecycle", 
    "get_container",
    "reset_container",
    "singleton",
    "transient"
]