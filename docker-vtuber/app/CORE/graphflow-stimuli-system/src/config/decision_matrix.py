"""
Decision matrix configuration for GraphFlow External Stimuli System.

This module defines the decision rules and rule evaluation logic for routing
stimuli to appropriate processing paths.
"""

import os
import json
import logging
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any, Callable
from enum import Enum
import re

# Handle relative imports more gracefully
try:
    from .settings import Priority
    from ..models.stimuli import StimuliCategory
    from ..models.decisions import ProcessingDecision
except ImportError:
    # Fallback for direct script execution
    import sys
    import os
    sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    from config.settings import Priority
    from models.stimuli import StimuliCategory
    from models.decisions import ProcessingDecision


@dataclass
class DecisionRule:
    """Individual decision rule configuration."""
    name: str = ""  # Alias for id
    condition: Any = None  # Can be string expression or callable
    decision: ProcessingDecision = ProcessingDecision.ANALYSIS_ONLY
    priority: int = 50
    reasoning: str = ""  # Alias for description
    enabled: bool = True
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    # Legacy support
    id: str = ""
    description: str = ""
    
    def __post_init__(self):
        """Handle aliases and defaults."""
        # Handle aliases
        if self.name and not self.id:
            self.id = self.name
        elif self.id and not self.name:
            self.name = self.id
        elif not self.id and not self.name:
            self.id = self.name = f"rule_{id(self)}"
            
        if self.reasoning and not self.description:
            self.description = self.reasoning
        elif self.description and not self.reasoning:
            self.reasoning = self.description
    
    def evaluate(self, context: Any) -> bool:
        """
        Evaluate the rule condition against the provided context.
        
        Args:
            context: Evaluation context (can be dict or AnalyzedStimuli object)
            
        Returns:
            True if condition matches, False otherwise
        """
        if not self.enabled:
            return False
            
        try:
            # If condition is callable, call it directly
            if callable(self.condition):
                return bool(self.condition(context))
            
            # If condition is a string, evaluate it
            if isinstance(self.condition, str):
                # Convert object to dict if needed
                if hasattr(context, '__dict__'):
                    eval_context = {
                        'category': getattr(context, 'category', None),
                        'confidence': getattr(context, 'confidence', 0.0),
                        'priority': getattr(context, 'priority', None),
                        'system_state': getattr(context, 'system_state_analysis', {}),
                        'resource_analysis': getattr(context, 'resource_analysis', {}),
                        'user_context': getattr(context, 'user_context_analysis', {}),
                        'environmental_analysis': getattr(context, 'environmental_analysis', {}),
                        'metadata': getattr(context, 'metadata', {}),
                    }
                else:
                    eval_context = {
                        'category': context.get('category'),
                        'confidence': context.get('confidence', 0.0),
                        'priority': context.get('priority'),
                        'system_state': context.get('system_state', {}),
                        'resource_analysis': context.get('resource_analysis', {}),
                        'user_context': context.get('user_context', {}),
                        'environmental_analysis': context.get('environmental_analysis', {}),
                        'metadata': context.get('metadata', {}),
                    }
                
                # Add helper functions
                eval_context.update({
                    'has_metadata': lambda key: key in context.get('metadata', {}),
                    'contains': lambda text, pattern: pattern.lower() in text.lower() if isinstance(text, str) else False,
                    'matches': lambda text, pattern: bool(re.match(pattern, text)) if isinstance(text, str) else False,
                })
                
                # Evaluate condition
                result = eval(self.condition, {"__builtins__": {}}, eval_context)
                return bool(result)
            
            # Default to False if condition type is not recognized
            return False
            
        except Exception as e:
            logging.error(f"Error evaluating rule {self.id}: {e}")
            return False


@dataclass
class RuleCategory:
    """Category of decision rules."""
    name: str
    rules: List[DecisionRule] = field(default_factory=list)
    enabled: bool = True
    
    def add_rule(self, rule: DecisionRule) -> None:
        """Add a rule to this category."""
        self.rules.append(rule)
        
    def get_matching_rules(self, context: Dict[str, Any]) -> List[DecisionRule]:
        """Get all rules that match the given context."""
        if not self.enabled:
            return []
            
        matching_rules = []
        for rule in self.rules:
            if rule.evaluate(context):
                matching_rules.append(rule)
                
        return matching_rules


@dataclass
class DecisionRulesConfig:
    """Configuration for decision rules engine."""
    categories: Dict[str, RuleCategory] = field(default_factory=dict)
    default_decision: ProcessingDecision = ProcessingDecision.ANALYSIS_ONLY
    enable_caching: bool = True
    cache_ttl: int = 300  # seconds
    log_decisions: bool = True
    custom_rules_path: Optional[str] = None
    
    def __post_init__(self):
        """Initialize default rule categories."""
        self._initialize_default_rules()
        self._load_custom_rules()
        
    def _initialize_default_rules(self) -> None:
        """Initialize the default decision matrix rules."""
        # Emergency rules
        emergency_category = RuleCategory("emergency_rules")
        emergency_category.add_rule(DecisionRule(
            id="emergency_1",
            condition='category == "EMERGENCY"',
            decision=ProcessingDecision.EMERGENCY_OVERRIDE,
            priority=100,
            description="Handle emergency stimuli with override"
        ))
        emergency_category.add_rule(DecisionRule(
            id="emergency_2",
            condition='priority == "emergency"',
            decision=ProcessingDecision.EMERGENCY_OVERRIDE,
            priority=99,
            description="Handle high-priority emergency requests"
        ))
        emergency_category.add_rule(DecisionRule(
            id="emergency_3",
            condition='contains(metadata.get("content", ""), "EMERGENCY") or contains(metadata.get("content", ""), "URGENT")',
            decision=ProcessingDecision.EMERGENCY_OVERRIDE,
            priority=98,
            description="Detect emergency keywords in content"
        ))
        self.categories["emergency_rules"] = emergency_category
        
        # System state rules
        system_state_category = RuleCategory("system_state_rules")
        system_state_category.add_rule(DecisionRule(
            id="system_state_1",
            condition='system_state.get("is_speaking", False) == True',
            decision=ProcessingDecision.ANALYSIS_ONLY,
            priority=90,
            description="Avoid avatar when already speaking"
        ))
        system_state_category.add_rule(DecisionRule(
            id="system_state_2",
            condition='system_state.get("is_idle", False) == True and category == "USER_INTERACTION"',
            decision=ProcessingDecision.AVATAR_AND_ANALYSIS,
            priority=80,
            description="Use avatar for user interactions when idle"
        ))
        system_state_category.add_rule(DecisionRule(
            id="system_state_3",
            condition='system_state.get("has_errors", False) == True',
            decision=ProcessingDecision.LOG_ONLY,
            priority=85,
            description="Log only when system has errors"
        ))
        system_state_category.add_rule(DecisionRule(
            id="system_state_4",
            condition='system_state.get("queue_size", 0) > 10',
            decision=ProcessingDecision.ANALYSIS_ONLY,
            priority=75,
            description="Skip avatar when queue is backed up"
        ))
        self.categories["system_state_rules"] = system_state_category
        
        # Category-specific rules
        category_rules = RuleCategory("category_rules")
        category_rules.add_rule(DecisionRule(
            id="category_1",
            condition='category == "DIRECT_ADMIN"',
            decision=ProcessingDecision.AVATAR_AND_ANALYSIS,
            priority=70,
            description="Process admin requests with full capabilities"
        ))
        category_rules.add_rule(DecisionRule(
            id="category_2",
            condition='category == "USER_INTERACTION" and confidence > 0.8',
            decision=ProcessingDecision.AVATAR_AND_ANALYSIS,
            priority=65,
            description="High-confidence user interactions get avatar response"
        ))
        category_rules.add_rule(DecisionRule(
            id="category_3",
            condition='category == "SYSTEM_NOTIFICATION"',
            decision=ProcessingDecision.ANALYSIS_ONLY,
            priority=50,
            description="System notifications for analysis only"
        ))
        category_rules.add_rule(DecisionRule(
            id="category_4",
            condition='category == "SOCIAL_MEDIA" and environmental_analysis.get("streaming_status") == "live"',
            decision=ProcessingDecision.AVATAR_AND_ANALYSIS,
            priority=60,
            description="Social media during live streaming gets avatar response"
        ))
        category_rules.add_rule(DecisionRule(
            id="category_5",
            condition='category == "CONTEXTUAL_UPDATE"',
            decision=ProcessingDecision.LOG_ONLY,
            priority=30,
            description="Context updates are logged only"
        ))
        category_rules.add_rule(DecisionRule(
            id="category_6",
            condition='category == "AUTONOMOUS_TRIGGER" and system_state.get("is_idle", False)',
            decision=ProcessingDecision.AVATAR_AND_ANALYSIS,
            priority=55,
            description="Autonomous triggers when idle use avatar"
        ))
        self.categories["category_rules"] = category_rules
        
        # Resource availability rules
        resource_rules = RuleCategory("resource_rules")
        resource_rules.add_rule(DecisionRule(
            id="resource_1",
            condition='resource_analysis.get("cpu_availability", 1.0) < 0.3',
            decision=ProcessingDecision.LOG_ONLY,
            priority=60,
            description="Low CPU availability forces log only"
        ))
        resource_rules.add_rule(DecisionRule(
            id="resource_2",
            condition='resource_analysis.get("memory_availability", 1.0) < 0.2',
            decision=ProcessingDecision.LOG_ONLY,
            priority=61,
            description="Low memory availability forces log only"
        ))
        resource_rules.add_rule(DecisionRule(
            id="resource_3",
            condition='resource_analysis.get("system1_availability", True) == False',
            decision=ProcessingDecision.ANALYSIS_ONLY,
            priority=62,
            description="System1 unavailable forces analysis only"
        ))
        resource_rules.add_rule(DecisionRule(
            id="resource_4",
            condition='resource_analysis.get("system2_availability", True) == False and category != "DIRECT_ADMIN"',
            decision=ProcessingDecision.LOG_ONLY,
            priority=63,
            description="System2 unavailable forces log only for non-admin"
        ))
        self.categories["resource_rules"] = resource_rules
        
        # User context rules
        user_context_rules = RuleCategory("user_context_rules")
        user_context_rules.add_rule(DecisionRule(
            id="user_context_1",
            condition='user_context.get("engagement_level") == "high" and category == "USER_INTERACTION"',
            decision=ProcessingDecision.AVATAR_AND_ANALYSIS,
            priority=68,
            description="High engagement users get avatar responses"
        ))
        user_context_rules.add_rule(DecisionRule(
            id="user_context_2",
            condition='user_context.get("interaction_frequency", 0) > 10 and environmental_analysis.get("time_of_day_factor", 1.0) > 0.8',
            decision=ProcessingDecision.AVATAR_AND_ANALYSIS,
            priority=64,
            description="Frequent users during peak hours get avatar"
        ))
        user_context_rules.add_rule(DecisionRule(
            id="user_context_3",
            condition='user_context.get("user_preference_match", 0) > 0.7',
            decision=ProcessingDecision.AVATAR_AND_ANALYSIS,
            priority=66,
            description="Content matching user preferences gets avatar"
        ))
        self.categories["user_context_rules"] = user_context_rules
        
        # Environmental rules
        environmental_rules = RuleCategory("environmental_rules")
        environmental_rules.add_rule(DecisionRule(
            id="environmental_1",
            condition='environmental_analysis.get("autonomous_mode_active", False) == True',
            decision=ProcessingDecision.ANALYSIS_ONLY,
            priority=45,
            description="Autonomous mode limits to analysis only"
        ))
        environmental_rules.add_rule(DecisionRule(
            id="environmental_2",
            condition='environmental_analysis.get("recent_activity_level") == "low" and category == "AUTONOMOUS_TRIGGER"',
            decision=ProcessingDecision.AVATAR_AND_ANALYSIS,
            priority=48,
            description="Low activity allows autonomous avatar triggers"
        ))
        self.categories["environmental_rules"] = environmental_rules
        
        # Default rules (lowest priority)
        default_rules = RuleCategory("default_rules")
        default_rules.add_rule(DecisionRule(
            id="default_1",
            condition='True',  # Always matches
            decision=ProcessingDecision.ANALYSIS_ONLY,
            priority=10,
            description="Default fallback to analysis only"
        ))
        self.categories["default_rules"] = default_rules
        
    def _load_custom_rules(self) -> None:
        """Load custom rules from file if specified."""
        if not self.custom_rules_path:
            return
            
        try:
            if os.path.exists(self.custom_rules_path):
                with open(self.custom_rules_path, 'r') as f:
                    custom_rules_data = json.load(f)
                    
                for category_name, rules_data in custom_rules_data.items():
                    if category_name not in self.categories:
                        self.categories[category_name] = RuleCategory(category_name)
                        
                    category = self.categories[category_name]
                    for rule_data in rules_data:
                        rule = DecisionRule(
                            id=rule_data['id'],
                            condition=rule_data['condition'],
                            decision=ProcessingDecision(rule_data['decision']),
                            priority=rule_data.get('priority', 50),
                            description=rule_data.get('description', ''),
                            enabled=rule_data.get('enabled', True),
                            metadata=rule_data.get('metadata', {})
                        )
                        category.add_rule(rule)
                        
                logging.info(f"Loaded custom rules from {self.custom_rules_path}")
                
        except Exception as e:
            logging.error(f"Failed to load custom rules: {e}")
            
    def evaluate_rules(self, context: Dict[str, Any]) -> ProcessingDecision:
        """
        Evaluate all rules against the context and return the decision.
        
        Args:
            context: Evaluation context containing stimuli information
            
        Returns:
            Processing decision based on highest priority matching rule
        """
        all_matching_rules = []
        
        # Evaluate rules in order of category priority
        category_order = [
            "emergency_rules",
            "system_state_rules",
            "category_rules",
            "resource_rules",
            "user_context_rules",
            "environmental_rules",
            "default_rules"
        ]
        
        for category_name in category_order:
            if category_name in self.categories:
                category = self.categories[category_name]
                matching_rules = category.get_matching_rules(context)
                all_matching_rules.extend(matching_rules)
                
        # Sort by priority (highest first)
        all_matching_rules.sort(key=lambda r: r.priority, reverse=True)
        
        # Log decision if enabled
        if self.log_decisions and all_matching_rules:
            best_rule = all_matching_rules[0]
            logging.info(
                f"Decision made: {best_rule.decision.value} "
                f"(rule: {best_rule.id}, priority: {best_rule.priority})"
            )
            
        # Return the decision from the highest priority matching rule
        if all_matching_rules:
            return all_matching_rules[0].decision
        else:
            logging.warning("No matching rules found, using default decision")
            return self.default_decision
            
    def add_rule(self, category_name: str, rule: DecisionRule) -> None:
        """Add a new rule to a category."""
        if category_name not in self.categories:
            self.categories[category_name] = RuleCategory(category_name)
            
        self.categories[category_name].add_rule(rule)
        
    def remove_rule(self, rule_id: str) -> bool:
        """Remove a rule by ID."""
        for category in self.categories.values():
            for i, rule in enumerate(category.rules):
                if rule.id == rule_id:
                    category.rules.pop(i)
                    return True
        return False
        
    def get_rule(self, rule_id: str) -> Optional[DecisionRule]:
        """Get a rule by ID."""
        for category in self.categories.values():
            for rule in category.rules:
                if rule.id == rule_id:
                    return rule
        return None
        
    def enable_rule(self, rule_id: str) -> bool:
        """Enable a rule by ID."""
        rule = self.get_rule(rule_id)
        if rule:
            rule.enabled = True
            return True
        return False
        
    def disable_rule(self, rule_id: str) -> bool:
        """Disable a rule by ID."""
        rule = self.get_rule(rule_id)
        if rule:
            rule.enabled = False
            return True
        return False
        
    def export_rules(self) -> Dict[str, Any]:
        """Export all rules to a dictionary."""
        export_data = {}
        
        for category_name, category in self.categories.items():
            export_data[category_name] = []
            for rule in category.rules:
                export_data[category_name].append({
                    'id': rule.id,
                    'condition': rule.condition,
                    'decision': rule.decision.value,
                    'priority': rule.priority,
                    'description': rule.description,
                    'enabled': rule.enabled,
                    'metadata': rule.metadata
                })
                
        return export_data
        
    def save_rules(self, filepath: str) -> None:
        """Save all rules to a JSON file."""
        with open(filepath, 'w') as f:
            json.dump(self.export_rules(), f, indent=2)
            

# Create global instance for easy access
DECISION_RULES = DecisionRulesConfig()


class DecisionMatrix:
    """
    Decision matrix for routing stimuli based on rules.
    
    This is a wrapper around DecisionRulesConfig to provide a simpler interface
    for the DecisionFlowManager.
    """
    
    def __init__(self, config: Optional[DecisionRulesConfig] = None):
        """Initialize with optional custom config."""
        self.config = config or DECISION_RULES
        self.custom_rules: List[DecisionRule] = []
    
    def add_custom_rule(self, rule: DecisionRule) -> None:
        """Add a custom rule to the matrix."""
        self.custom_rules.append(rule)
        # Also add to the config
        self.config.add_rule("custom_rules", rule)
    
    def evaluate(self, context: Dict[str, Any]) -> ProcessingDecision:
        """Evaluate rules and return decision."""
        return self.config.evaluate_rules(context)
    
    def get_all_rules(self) -> List[DecisionRule]:
        """Get all rules across all categories."""
        all_rules = []
        for category in self.config.categories.values():
            all_rules.extend(category.rules)
        return all_rules


# Example usage and testing
if __name__ == "__main__":
    # Create test context
    test_context = {
        'category': 'USER_INTERACTION',
        'confidence': 0.9,
        'priority': 'medium',
        'system_state': {
            'is_speaking': False,
            'is_idle': True,
            'has_errors': False,
            'queue_size': 5
        },
        'resource_analysis': {
            'cpu_availability': 0.8,
            'memory_availability': 0.7,
            'system1_availability': True,
            'system2_availability': True
        },
        'user_context': {
            'engagement_level': 'high',
            'interaction_frequency': 15,
            'user_preference_match': 0.85
        },
        'environmental_analysis': {
            'autonomous_mode_active': False,
            'streaming_status': 'live',
            'time_of_day_factor': 0.9,
            'recent_activity_level': 'medium'
        },
        'metadata': {
            'content': 'Hello, how are you today?'
        }
    }
    
    # Evaluate rules
    decision = DECISION_RULES.evaluate_rules(test_context)
    print(f"Decision for test context: {decision.value}")
    
    # Test emergency context
    emergency_context = test_context.copy()
    emergency_context['category'] = 'EMERGENCY'
    emergency_decision = DECISION_RULES.evaluate_rules(emergency_context)
    print(f"Decision for emergency context: {emergency_decision.value}")
    
    # Export rules
    print("\nExporting rules...")
    DECISION_RULES.save_rules("decision_rules_export.json")