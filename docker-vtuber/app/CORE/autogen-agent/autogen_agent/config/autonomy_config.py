"""
Graduated Autonomy Configuration System

This module implements a 5-level autonomy system for the AutoGen Agent,
allowing graduated control from observer to fully autonomous operation.
"""

from enum import Enum, auto
from typing import Optional, Dict, Any, List
from dataclasses import dataclass, field
import logging

logger = logging.getLogger(__name__)


class AutonomyLevel(Enum):
    """
    Enumeration of autonomy levels from lowest to highest.
    
    Levels:
    - OBSERVER: Can only observe and report, no actions
    - SUGGESTOR: Can suggest actions but requires approval
    - EXECUTOR: Can execute pre-approved actions
    - PLANNER: Can plan and execute with minimal oversight
    - AUTONOMOUS: Full autonomous operation
    """
    OBSERVER = 1
    SUGGESTOR = 2
    EXECUTOR = 3
    PLANNER = 4
    AUTONOMOUS = 5


@dataclass
class AutonomyConfig:
    """Configuration for autonomy system"""
    
    current_level: AutonomyLevel = AutonomyLevel.OBSERVER
    allowed_actions: List[str] = field(default_factory=list)
    require_approval: bool = True
    max_decision_complexity: int = 1
    audit_trail: bool = True
    
    def can_execute(self, action: str) -> bool:
        """Check if an action can be executed at current autonomy level"""
        if self.current_level == AutonomyLevel.OBSERVER:
            return False
        
        if self.current_level == AutonomyLevel.SUGGESTOR:
            return False  # Can only suggest, not execute
        
        if self.current_level == AutonomyLevel.EXECUTOR:
            return action in self.allowed_actions
        
        # PLANNER and AUTONOMOUS can execute most actions
        return True
    
    def requires_approval(self, action: str) -> bool:
        """Check if an action requires approval"""
        if self.current_level >= AutonomyLevel.AUTONOMOUS:
            return False
        
        if self.current_level == AutonomyLevel.PLANNER:
            # Complex actions still need approval
            return action not in self.allowed_actions
        
        return self.require_approval


class AutonomyManager:
    """Manages autonomy levels and permissions"""
    
    def __init__(self, initial_level: AutonomyLevel = AutonomyLevel.OBSERVER):
        self.config = AutonomyConfig(current_level=initial_level)
        self._history: List[Dict[str, Any]] = []
        
    def set_level(self, level: AutonomyLevel) -> None:
        """Set the autonomy level"""
        old_level = self.config.current_level
        self.config.current_level = level
        
        self._history.append({
            'timestamp': self._get_timestamp(),
            'action': 'level_change',
            'from': old_level.name,
            'to': level.name
        })
        
        logger.info(f"Autonomy level changed from {old_level.name} to {level.name}")
        
    def can_perform_action(self, action: str, context: Optional[Dict[str, Any]] = None) -> bool:
        """Check if an action can be performed"""
        can_execute = self.config.can_execute(action)
        
        self._history.append({
            'timestamp': self._get_timestamp(),
            'action': 'permission_check',
            'requested_action': action,
            'result': can_execute,
            'level': self.config.current_level.name,
            'context': context
        })
        
        return can_execute
    
    def add_allowed_action(self, action: str) -> None:
        """Add an action to the allowed list"""
        if action not in self.config.allowed_actions:
            self.config.allowed_actions.append(action)
            logger.info(f"Added '{action}' to allowed actions")
    
    def remove_allowed_action(self, action: str) -> None:
        """Remove an action from the allowed list"""
        if action in self.config.allowed_actions:
            self.config.allowed_actions.remove(action)
            logger.info(f"Removed '{action}' from allowed actions")
    
    def get_capabilities(self) -> Dict[str, Any]:
        """Get current capabilities based on autonomy level"""
        level = self.config.current_level
        
        capabilities = {
            'level': level.name,
            'can_observe': True,  # All levels can observe
            'can_suggest': level.value >= AutonomyLevel.SUGGESTOR.value,
            'can_execute': level.value >= AutonomyLevel.EXECUTOR.value,
            'can_plan': level.value >= AutonomyLevel.PLANNER.value,
            'is_autonomous': level == AutonomyLevel.AUTONOMOUS,
            'allowed_actions': self.config.allowed_actions.copy(),
            'requires_approval': self.config.require_approval and level != AutonomyLevel.AUTONOMOUS
        }
        
        return capabilities
    
    def get_history(self, limit: Optional[int] = None) -> List[Dict[str, Any]]:
        """Get action history"""
        if limit:
            return self._history[-limit:]
        return self._history.copy()
    
    def _get_timestamp(self) -> str:
        """Get current timestamp"""
        from datetime import datetime
        return datetime.utcnow().isoformat()


# Global instance
_autonomy_manager: Optional[AutonomyManager] = None


def get_autonomy_manager() -> AutonomyManager:
    """Get or create the global autonomy manager instance"""
    global _autonomy_manager
    if _autonomy_manager is None:
        _autonomy_manager = AutonomyManager()
    return _autonomy_manager


def check_autonomy(action: str, context: Optional[Dict[str, Any]] = None) -> bool:
    """
    Quick check if an action is allowed under current autonomy level.
    
    Args:
        action: The action to check
        context: Optional context for the action
        
    Returns:
        bool: True if action is allowed, False otherwise
    """
    manager = get_autonomy_manager()
    return manager.can_perform_action(action, context)