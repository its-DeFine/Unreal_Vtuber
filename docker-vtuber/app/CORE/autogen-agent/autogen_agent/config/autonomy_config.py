"""
Graduated Autonomy Configuration System

This module implements a trust-based autonomy system where the autonomous team
can earn increased capabilities based on their performance and safety record.

Autonomy Levels:
1. OBSERVER - Can only analyze and suggest (default)
2. SUGGESTER - Can generate improvements but not apply
3. MODIFIER - Can apply changes with approval
4. CREATOR - Can create tools with approval
5. AUTONOMOUS - Full autonomy (use with extreme caution)
"""

import os
import json
import logging
from enum import Enum
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
from dataclasses import dataclass, asdict
import asyncio

logger = logging.getLogger(__name__)


class AutonomyLevel(Enum):
    """Graduated autonomy levels"""
    OBSERVER = 1      # Read-only, no modifications
    SUGGESTER = 2     # Can suggest but not implement
    MODIFIER = 3      # Can modify with approval
    CREATOR = 4       # Can create tools with approval  
    AUTONOMOUS = 5    # Full autonomy (dangerous!)


@dataclass
class AutonomyMetrics:
    """Track metrics for autonomy decisions"""
    successful_operations: int = 0
    failed_operations: int = 0
    rollbacks: int = 0
    safety_violations: int = 0
    approved_changes: int = 0
    rejected_changes: int = 0
    uptime_hours: float = 0.0
    last_evaluation: Optional[str] = None


@dataclass
class AutonomyConfig:
    """Current autonomy configuration"""
    level: AutonomyLevel = AutonomyLevel.OBSERVER
    require_approval: bool = True
    allow_file_modifications: bool = False
    allow_tool_creation: bool = False
    allow_external_calls: bool = False
    max_daily_operations: int = 100
    max_execution_time: int = 30
    trusted_operations: List[str] = None
    restricted_operations: List[str] = None
    
    def __post_init__(self):
        if self.trusted_operations is None:
            self.trusted_operations = []
        if self.restricted_operations is None:
            self.restricted_operations = ['file_delete', 'system_exec', 'network_access']


class AutonomyManager:
    """
    Manages graduated autonomy for the autonomous team
    """
    
    def __init__(self, config_file: str = "autonomy_config.json"):
        self.config_file = config_file
        self.config = self._load_config()
        self.metrics = AutonomyMetrics()
        self.operation_log = []
        self.start_time = datetime.now()
        
        # Apply environment overrides
        self._apply_env_overrides()
        
        logger.info(f"🎯 [AUTONOMY] Initialized at level: {self.config.level.name}")
    
    def _load_config(self) -> AutonomyConfig:
        """Load autonomy configuration from file"""
        if os.path.exists(self.config_file):
            try:
                with open(self.config_file, 'r') as f:
                    data = json.load(f)
                    # Convert level string to enum
                    if 'level' in data:
                        data['level'] = AutonomyLevel[data['level']]
                    return AutonomyConfig(**data)
            except Exception as e:
                logger.warning(f"Failed to load config: {e}, using defaults")
        
        return AutonomyConfig()
    
    def _save_config(self):
        """Save current configuration to file"""
        try:
            config_dict = asdict(self.config)
            # Convert enum to string for JSON
            config_dict['level'] = self.config.level.name
            
            with open(self.config_file, 'w') as f:
                json.dump(config_dict, f, indent=2)
        except Exception as e:
            logger.error(f"Failed to save config: {e}")
    
    def _apply_env_overrides(self):
        """Apply environment variable overrides"""
        # Check for level override
        env_level = os.getenv("AUTONOMY_LEVEL")
        if env_level:
            try:
                self.config.level = AutonomyLevel[env_level.upper()]
                logger.info(f"🔧 [AUTONOMY] Level overridden by env: {env_level}")
            except:
                logger.warning(f"Invalid AUTONOMY_LEVEL: {env_level}")
        
        # Check for approval override
        if os.getenv("DARWIN_GODEL_REQUIRE_APPROVAL"):
            self.config.require_approval = os.getenv("DARWIN_GODEL_REQUIRE_APPROVAL", "true").lower() == "true"
        
        # Apply level-based defaults
        self._apply_level_defaults()
    
    def _apply_level_defaults(self):
        """Apply default settings based on autonomy level"""
        level_configs = {
            AutonomyLevel.OBSERVER: {
                "require_approval": True,
                "allow_file_modifications": False,
                "allow_tool_creation": False,
                "allow_external_calls": False,
                "max_daily_operations": 50
            },
            AutonomyLevel.SUGGESTER: {
                "require_approval": True,
                "allow_file_modifications": False,
                "allow_tool_creation": False,
                "allow_external_calls": False,
                "max_daily_operations": 100
            },
            AutonomyLevel.MODIFIER: {
                "require_approval": True,
                "allow_file_modifications": True,
                "allow_tool_creation": False,
                "allow_external_calls": False,
                "max_daily_operations": 200
            },
            AutonomyLevel.CREATOR: {
                "require_approval": True,
                "allow_file_modifications": True,
                "allow_tool_creation": True,
                "allow_external_calls": False,
                "max_daily_operations": 500
            },
            AutonomyLevel.AUTONOMOUS: {
                "require_approval": False,
                "allow_file_modifications": True,
                "allow_tool_creation": True,
                "allow_external_calls": True,
                "max_daily_operations": 1000
            }
        }
        
        # Apply defaults for current level
        defaults = level_configs.get(self.config.level, {})
        for key, value in defaults.items():
            if not os.getenv(f"AUTONOMY_{key.upper()}"):  # Only if not overridden by env
                setattr(self.config, key, value)
    
    def can_perform_operation(self, operation: str, context: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        Check if an operation is allowed under current autonomy level
        
        Args:
            operation: Type of operation (e.g., 'file_modify', 'tool_create')
            context: Additional context about the operation
            
        Returns:
            Dict with 'allowed' bool and 'reason' if not allowed
        """
        # Check restricted operations
        if operation in self.config.restricted_operations:
            return {
                "allowed": False,
                "reason": f"Operation '{operation}' is restricted"
            }
        
        # Check daily operation limit
        today_ops = sum(1 for op in self.operation_log 
                       if datetime.fromisoformat(op['timestamp']).date() == datetime.now().date())
        
        if today_ops >= self.config.max_daily_operations:
            return {
                "allowed": False,
                "reason": f"Daily operation limit reached ({self.config.max_daily_operations})"
            }
        
        # Check specific operations
        checks = {
            "file_modify": self.config.allow_file_modifications,
            "file_create": self.config.allow_file_modifications,
            "tool_create": self.config.allow_tool_creation,
            "tool_register": self.config.allow_tool_creation,
            "external_call": self.config.allow_external_calls,
            "network_request": self.config.allow_external_calls
        }
        
        if operation in checks and not checks[operation]:
            return {
                "allowed": False,
                "reason": f"Operation '{operation}' not allowed at {self.config.level.name} level"
            }
        
        # Check if it's a trusted operation
        if operation in self.config.trusted_operations:
            return {
                "allowed": True,
                "reason": "Trusted operation"
            }
        
        # Default allow for unspecified operations at MODIFIER+ levels
        if self.config.level.value >= AutonomyLevel.MODIFIER.value:
            return {
                "allowed": True,
                "reason": f"Allowed at {self.config.level.name} level"
            }
        
        # Default deny for lower levels
        return {
            "allowed": False,
            "reason": f"Operation requires higher autonomy level than {self.config.level.name}"
        }
    
    def record_operation(self, operation: str, success: bool, details: Dict[str, Any] = None):
        """Record an operation for metrics tracking"""
        self.operation_log.append({
            "operation": operation,
            "success": success,
            "timestamp": datetime.now().isoformat(),
            "details": details or {}
        })
        
        # Update metrics
        if success:
            self.metrics.successful_operations += 1
        else:
            self.metrics.failed_operations += 1
            
            # Check for safety violations
            if details and details.get('safety_violation'):
                self.metrics.safety_violations += 1
        
        # Keep log size manageable
        if len(self.operation_log) > 1000:
            self.operation_log = self.operation_log[-500:]
    
    def evaluate_autonomy_upgrade(self) -> Dict[str, Any]:
        """
        Evaluate if the system qualifies for autonomy upgrade
        
        Returns:
            Dict with upgrade recommendation and reasoning
        """
        # Calculate metrics
        total_ops = self.metrics.successful_operations + self.metrics.failed_operations
        success_rate = self.metrics.successful_operations / total_ops if total_ops > 0 else 0
        
        uptime_hours = (datetime.now() - self.start_time).total_seconds() / 3600
        self.metrics.uptime_hours = uptime_hours
        
        # Upgrade criteria by level
        upgrade_criteria = {
            AutonomyLevel.OBSERVER: {
                "min_operations": 50,
                "min_success_rate": 0.95,
                "max_safety_violations": 0,
                "min_uptime_hours": 24
            },
            AutonomyLevel.SUGGESTER: {
                "min_operations": 100,
                "min_success_rate": 0.97,
                "max_safety_violations": 0,
                "min_uptime_hours": 72,
                "min_approved_changes": 10
            },
            AutonomyLevel.MODIFIER: {
                "min_operations": 200,
                "min_success_rate": 0.98,
                "max_safety_violations": 0,
                "min_uptime_hours": 168,  # 1 week
                "min_approved_changes": 25,
                "max_rollbacks": 2
            },
            AutonomyLevel.CREATOR: {
                "min_operations": 500,
                "min_success_rate": 0.99,
                "max_safety_violations": 0,
                "min_uptime_hours": 720,  # 30 days
                "min_approved_changes": 50,
                "max_rollbacks": 1
            }
        }
        
        current_level = self.config.level
        
        # Can't upgrade from AUTONOMOUS
        if current_level == AutonomyLevel.AUTONOMOUS:
            return {
                "eligible": False,
                "reason": "Already at maximum autonomy level",
                "current_level": current_level.name
            }
        
        # Get next level
        next_level = AutonomyLevel(current_level.value + 1)
        criteria = upgrade_criteria.get(current_level, {})
        
        # Check criteria
        reasons = []
        eligible = True
        
        if total_ops < criteria.get('min_operations', 0):
            eligible = False
            reasons.append(f"Need {criteria['min_operations']} operations, have {total_ops}")
        
        if success_rate < criteria.get('min_success_rate', 1.0):
            eligible = False
            reasons.append(f"Need {criteria['min_success_rate']*100}% success rate, have {success_rate*100:.1f}%")
        
        if self.metrics.safety_violations > criteria.get('max_safety_violations', 0):
            eligible = False
            reasons.append(f"Too many safety violations: {self.metrics.safety_violations}")
        
        if uptime_hours < criteria.get('min_uptime_hours', 0):
            eligible = False
            reasons.append(f"Need {criteria['min_uptime_hours']} hours uptime, have {uptime_hours:.1f}")
        
        if 'min_approved_changes' in criteria:
            if self.metrics.approved_changes < criteria['min_approved_changes']:
                eligible = False
                reasons.append(f"Need {criteria['min_approved_changes']} approved changes, have {self.metrics.approved_changes}")
        
        if 'max_rollbacks' in criteria:
            if self.metrics.rollbacks > criteria['max_rollbacks']:
                eligible = False
                reasons.append(f"Too many rollbacks: {self.metrics.rollbacks}")
        
        self.metrics.last_evaluation = datetime.now().isoformat()
        
        return {
            "eligible": eligible,
            "current_level": current_level.name,
            "next_level": next_level.name,
            "metrics": asdict(self.metrics),
            "reasons": reasons if not eligible else ["All criteria met"],
            "success_rate": success_rate,
            "total_operations": total_ops
        }
    
    def upgrade_autonomy(self, force: bool = False) -> Dict[str, Any]:
        """
        Upgrade to the next autonomy level
        
        Args:
            force: Force upgrade without checking criteria (requires env var)
            
        Returns:
            Upgrade result
        """
        if not force:
            evaluation = self.evaluate_autonomy_upgrade()
            if not evaluation['eligible']:
                return {
                    "success": False,
                    "error": "Not eligible for upgrade",
                    "evaluation": evaluation
                }
        else:
            # Force upgrade requires special env var
            if os.getenv("ALLOW_FORCE_AUTONOMY_UPGRADE", "false").lower() != "true":
                return {
                    "success": False,
                    "error": "Force upgrade not allowed without ALLOW_FORCE_AUTONOMY_UPGRADE=true"
                }
        
        old_level = self.config.level
        
        if old_level == AutonomyLevel.AUTONOMOUS:
            return {
                "success": False,
                "error": "Already at maximum autonomy level"
            }
        
        # Upgrade to next level
        self.config.level = AutonomyLevel(old_level.value + 1)
        self._apply_level_defaults()
        self._save_config()
        
        logger.info(f"🎉 [AUTONOMY] Upgraded from {old_level.name} to {self.config.level.name}")
        
        return {
            "success": True,
            "old_level": old_level.name,
            "new_level": self.config.level.name,
            "new_capabilities": {
                "allow_file_modifications": self.config.allow_file_modifications,
                "allow_tool_creation": self.config.allow_tool_creation,
                "allow_external_calls": self.config.allow_external_calls,
                "max_daily_operations": self.config.max_daily_operations
            }
        }
    
    def downgrade_autonomy(self, reason: str = "Manual downgrade") -> Dict[str, Any]:
        """Downgrade autonomy level (safety measure)"""
        old_level = self.config.level
        
        if old_level == AutonomyLevel.OBSERVER:
            return {
                "success": False,
                "error": "Already at minimum autonomy level"
            }
        
        # Downgrade to previous level
        self.config.level = AutonomyLevel(old_level.value - 1)
        self._apply_level_defaults()
        self._save_config()
        
        logger.warning(f"⬇️ [AUTONOMY] Downgraded from {old_level.name} to {self.config.level.name} - Reason: {reason}")
        
        return {
            "success": True,
            "old_level": old_level.name,
            "new_level": self.config.level.name,
            "reason": reason
        }
    
    def get_status(self) -> Dict[str, Any]:
        """Get current autonomy status"""
        return {
            "level": self.config.level.name,
            "configuration": asdict(self.config),
            "metrics": asdict(self.metrics),
            "can_modify_files": self.config.allow_file_modifications,
            "can_create_tools": self.config.allow_tool_creation,
            "requires_approval": self.config.require_approval,
            "operations_today": sum(1 for op in self.operation_log 
                                  if datetime.fromisoformat(op['timestamp']).date() == datetime.now().date()),
            "operations_remaining": self.config.max_daily_operations - sum(1 for op in self.operation_log 
                                  if datetime.fromisoformat(op['timestamp']).date() == datetime.now().date()),
            "last_evaluation": self.metrics.last_evaluation
        }


# Global autonomy manager instance
_autonomy_manager: Optional[AutonomyManager] = None


def get_autonomy_manager() -> AutonomyManager:
    """Get or create the global autonomy manager"""
    global _autonomy_manager
    
    if _autonomy_manager is None:
        _autonomy_manager = AutonomyManager()
    
    return _autonomy_manager


def check_autonomy(operation: str, context: Dict[str, Any] = None) -> Dict[str, Any]:
    """
    Quick check if an operation is allowed
    
    Args:
        operation: Type of operation
        context: Additional context
        
    Returns:
        Dict with 'allowed' bool and details
    """
    manager = get_autonomy_manager()
    return manager.can_perform_operation(operation, context)