"""
Decision Engine for rule-based routing decisions.

This module implements the core decision-making logic for the router node,
evaluating rules from the decision matrix in priority order.
"""

import re
import operator
from typing import Dict, Any, Optional, List, Tuple, Callable
from datetime import datetime
from dataclasses import dataclass, field
from collections import defaultdict

from ...models.decisions import ProcessingDecision
from ...utils.logging import get_structured_logger
from ...utils.metrics import MetricsCollector


@dataclass
class DecisionRule:
    """Represents a single decision rule."""
    id: str
    condition: str  # String representation of the condition
    decision: ProcessingDecision
    priority: int
    category: str  # Rule category (emergency, system_state, category, resource, default)
    description: str = ""
    compiled_condition: Optional[Callable] = field(default=None, init=False)
    
    def __post_init__(self):
        """Compile the condition after initialization."""
        self.compiled_condition = self._compile_condition()
    
    def _compile_condition(self) -> Optional[Callable]:
        """Compile string condition to callable function."""
        try:
            # Replace condition syntax with Python syntax
            condition = self.condition
            condition = condition.replace(" == ", " == ")
            condition = condition.replace(" != ", " != ")
            condition = condition.replace(" && ", " and ")
            condition = condition.replace(" || ", " or ")
            condition = condition.replace(" AND ", " and ")
            condition = condition.replace(" OR ", " or ")
            
            # Create a safe evaluation function
            def evaluate_condition(context: Dict[str, Any]) -> bool:
                # Create a safe namespace for evaluation
                safe_dict = {
                    '__builtins__': {},
                    'True': True,
                    'False': False,
                    'None': None,
                }
                
                # Add context variables to namespace
                for key, value in context.items():
                    if isinstance(value, dict):
                        # Flatten nested dicts with dot notation
                        for sub_key, sub_value in value.items():
                            safe_dict[f"{key}.{sub_key}"] = sub_value
                    else:
                        safe_dict[key] = value
                
                # Replace dot notation in condition with underscore
                eval_condition = condition
                for key in safe_dict.keys():
                    if '.' in key:
                        eval_condition = eval_condition.replace(key, key.replace('.', '_'))
                        safe_dict[key.replace('.', '_')] = safe_dict[key]
                
                try:
                    return eval(eval_condition, {"__builtins__": {}}, safe_dict)
                except Exception:
                    return False
            
            return evaluate_condition
            
        except Exception as e:
            logger = get_structured_logger("decision_engine")
            logger.error(f"Failed to compile condition '{self.condition}': {e}")
            return None
    
    def evaluate(self, context: Dict[str, Any]) -> bool:
        """Evaluate the rule against given context."""
        if self.compiled_condition:
            try:
                return self.compiled_condition(context)
            except Exception:
                return False
        return False


@dataclass
class RuleEvaluationResult:
    """Result of rule evaluation."""
    rule_id: str
    matched: bool
    decision: Optional[ProcessingDecision] = None
    confidence: float = 1.0
    reasoning: str = ""
    evaluation_time: float = 0.0


class DecisionEngine:
    """
    Engine for evaluating decision rules and determining routing decisions.
    
    This engine:
    - Loads rules from configuration
    - Evaluates rules in priority order
    - Tracks rule hit rates and performance
    - Provides decision explanations
    """
    
    def __init__(self, metrics_collector: Optional[MetricsCollector] = None):
        """
        Initialize the decision engine.
        
        Args:
            metrics_collector: Optional metrics collector for tracking
        """
        self.logger = get_structured_logger("decision_engine")
        self.metrics = metrics_collector
        
        # Rule storage
        self.rules: List[DecisionRule] = []
        self.rules_by_category: Dict[str, List[DecisionRule]] = defaultdict(list)
        
        # Rule statistics
        self.rule_hits: Dict[str, int] = defaultdict(int)
        self.rule_evaluations: Dict[str, int] = defaultdict(int)
        
        self.is_initialized = False
    
    def load_rules(self, rules_config: Dict[str, List[Dict[str, Any]]]) -> None:
        """
        Load decision rules from configuration.
        
        Args:
            rules_config: Dictionary of rule categories and their rules
        """
        self.rules.clear()
        self.rules_by_category.clear()
        
        rule_count = 0
        for category, category_rules in rules_config.items():
            for rule_data in category_rules:
                try:
                    # Convert string decision to enum
                    decision_str = rule_data['decision']
                    decision = ProcessingDecision[decision_str]
                    
                    rule = DecisionRule(
                        id=f"{category}_{rule_count}",
                        condition=rule_data['condition'],
                        decision=decision,
                        priority=rule_data.get('priority', 50),
                        category=category,
                        description=rule_data.get('description', '')
                    )
                    
                    self.rules.append(rule)
                    self.rules_by_category[category].append(rule)
                    rule_count += 1
                    
                except Exception as e:
                    self.logger.error(
                        f"Failed to load rule from {category}: {e}",
                        rule_data=rule_data
                    )
        
        # Sort rules by priority (highest first)
        self.rules.sort(key=lambda r: r.priority, reverse=True)
        
        self.logger.info(f"Loaded {len(self.rules)} decision rules")
        self.is_initialized = True
    
    def evaluate(self, context: Dict[str, Any]) -> ProcessingDecision:
        """
        Evaluate all rules against context and return decision.
        
        Args:
            context: Evaluation context containing stimuli and analysis data
            
        Returns:
            Processing decision based on rule evaluation
        """
        if not self.is_initialized:
            self.logger.warning("Decision engine not initialized, using default decision")
            return ProcessingDecision.ANALYSIS_ONLY
        
        start_time = datetime.now()
        
        # Evaluate rules in priority order
        for rule in self.rules:
            self.rule_evaluations[rule.id] += 1
            
            if rule.evaluate(context):
                self.rule_hits[rule.id] += 1
                
                evaluation_time = (datetime.now() - start_time).total_seconds()
                
                self.logger.debug(
                    "Rule matched",
                    rule_id=rule.id,
                    category=rule.category,
                    decision=rule.decision.value,
                    priority=rule.priority
                )
                
                # Track metrics
                if self.metrics:
                    self.metrics.record_decision_rule_hit(rule.category, rule.decision.value)
                
                return rule.decision
        
        # No rules matched, use default
        self.logger.warning("No rules matched, using default decision")
        return ProcessingDecision.ANALYSIS_ONLY
    
    def evaluate_with_explanation(self, context: Dict[str, Any]) -> Tuple[ProcessingDecision, List[RuleEvaluationResult]]:
        """
        Evaluate rules and provide detailed explanation of the decision process.
        
        Args:
            context: Evaluation context
            
        Returns:
            Tuple of (decision, evaluation_results)
        """
        if not self.is_initialized:
            return ProcessingDecision.ANALYSIS_ONLY, []
        
        results = []
        matched_rule = None
        
        # Evaluate all rules to provide comprehensive explanation
        for rule in self.rules:
            start_time = datetime.now()
            matched = rule.evaluate(context)
            evaluation_time = (datetime.now() - start_time).total_seconds()
            
            result = RuleEvaluationResult(
                rule_id=rule.id,
                matched=matched,
                decision=rule.decision if matched else None,
                confidence=1.0 if matched else 0.0,
                reasoning=rule.description or f"Rule {rule.id} from {rule.category}",
                evaluation_time=evaluation_time
            )
            
            results.append(result)
            
            # Use first matched rule (highest priority)
            if matched and matched_rule is None:
                matched_rule = rule
        
        decision = matched_rule.decision if matched_rule else ProcessingDecision.ANALYSIS_ONLY
        return decision, results
    
    def apply_emergency_override(self, context: Dict[str, Any]) -> Optional[ProcessingDecision]:
        """
        Check and apply emergency override rules specifically.
        
        Args:
            context: Evaluation context
            
        Returns:
            Emergency decision if applicable, None otherwise
        """
        emergency_rules = self.rules_by_category.get('emergency_rules', [])
        
        for rule in emergency_rules:
            if rule.evaluate(context):
                self.logger.warning(
                    "Emergency override triggered",
                    rule_id=rule.id,
                    condition=rule.condition
                )
                return rule.decision
        
        return None
    
    def get_applicable_rules(self, context: Dict[str, Any]) -> List[DecisionRule]:
        """
        Get all rules that would match the given context.
        
        Args:
            context: Evaluation context
            
        Returns:
            List of matching rules
        """
        matching_rules = []
        
        for rule in self.rules:
            if rule.evaluate(context):
                matching_rules.append(rule)
        
        return matching_rules
    
    def get_rule_statistics(self) -> Dict[str, Any]:
        """
        Get statistics about rule usage and performance.
        
        Returns:
            Dictionary containing rule statistics
        """
        stats = {
            'total_rules': len(self.rules),
            'rules_by_category': {
                category: len(rules) 
                for category, rules in self.rules_by_category.items()
            },
            'rule_hit_rates': {},
            'most_used_rules': [],
            'least_used_rules': [],
            'never_matched_rules': []
        }
        
        # Calculate hit rates
        for rule_id, evaluations in self.rule_evaluations.items():
            if evaluations > 0:
                hit_rate = self.rule_hits[rule_id] / evaluations
                stats['rule_hit_rates'][rule_id] = {
                    'evaluations': evaluations,
                    'hits': self.rule_hits[rule_id],
                    'hit_rate': hit_rate
                }
        
        # Find most/least used rules
        if stats['rule_hit_rates']:
            sorted_rules = sorted(
                stats['rule_hit_rates'].items(),
                key=lambda x: x[1]['hits'],
                reverse=True
            )
            
            stats['most_used_rules'] = sorted_rules[:5]
            stats['least_used_rules'] = sorted_rules[-5:]
            
            # Find never matched rules
            for rule in self.rules:
                if rule.id not in self.rule_hits or self.rule_hits[rule.id] == 0:
                    stats['never_matched_rules'].append(rule.id)
        
        return stats
    
    def explain_decision(self, context: Dict[str, Any], decision: ProcessingDecision) -> str:
        """
        Generate human-readable explanation for a decision.
        
        Args:
            context: The context that led to the decision
            decision: The decision that was made
            
        Returns:
            Explanation string
        """
        # Find which rule matched
        matched_rule = None
        for rule in self.rules:
            if rule.evaluate(context) and rule.decision == decision:
                matched_rule = rule
                break
        
        if matched_rule:
            explanation_parts = [
                f"Decision: {decision.value}",
                f"Triggered by: {matched_rule.category} rule",
                f"Rule priority: {matched_rule.priority}",
            ]
            
            if matched_rule.description:
                explanation_parts.append(f"Reason: {matched_rule.description}")
            
            # Add context details
            if 'category' in context:
                explanation_parts.append(f"Stimuli category: {context['category']}")
            
            if 'system_state' in context and context['system_state']:
                state = context['system_state']
                if state.get('is_speaking'):
                    explanation_parts.append("System is currently speaking")
                elif state.get('is_idle'):
                    explanation_parts.append("System is idle")
            
            if 'resource_analysis' in context and context['resource_analysis']:
                resources = context['resource_analysis']
                if resources.get('cpu_availability', 1.0) < 0.3:
                    explanation_parts.append("Low CPU availability")
                if resources.get('memory_availability', 1.0) < 0.3:
                    explanation_parts.append("Low memory availability")
            
            return " | ".join(explanation_parts)
        
        return f"Decision: {decision.value} | No specific rule matched, using default"
    
    def reset_statistics(self) -> None:
        """Reset rule usage statistics."""
        self.rule_hits.clear()
        self.rule_evaluations.clear()
        self.logger.info("Rule statistics reset")