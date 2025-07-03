"""
Decision Router Node for GraphFlow Pipeline.

This node makes routing decisions based on analyzed stimuli and decision matrices,
determining the appropriate processing path.
"""

import asyncio
from typing import Dict, Any, Optional, Tuple, List
from datetime import datetime
import uuid

from ...models.stimuli import AnalyzedStimuli, RoutingDecision
from ...models.decisions import (
    ProcessingDecision,
    ExecutionPlan,
    RetryPolicy,
    ExecutionPriority
)
from ...config.settings import RouterConfig
from ...config.decision_matrix import DecisionMatrix
from ...utils.logging import get_structured_logger
from ...utils.metrics import MetricsCollector
from .decision_engine import DecisionEngine, RuleEvaluationResult


class DecisionRouterNode:
    """
    GraphFlow node for decision routing.
    
    Makes intelligent routing decisions based on:
    - Stimuli category and priority
    - System state and availability
    - User engagement patterns
    - Resource constraints
    - Business rules and policies
    """
    
    def __init__(self, config: RouterConfig, decision_matrix: DecisionMatrix, 
                 metrics_collector: Optional[MetricsCollector] = None):
        """
        Initialize the router node.
        
        Args:
            config: Router configuration
            decision_matrix: Decision matrix for rule evaluation
            metrics_collector: Optional metrics collector for tracking
        """
        self.config = config
        self.decision_matrix = decision_matrix
        self.logger = get_structured_logger("router_node")
        self.metrics = metrics_collector
        
        # Initialize decision engine
        self.decision_engine = DecisionEngine(metrics_collector)
        
        # Decision tracking
        self._decision_history: Dict[str, RoutingDecision] = {}
        self._history_lock = asyncio.Lock()
        
        self.is_initialized = False
    
    async def initialize(self) -> None:
        """Initialize the router node."""
        try:
            self.logger.info("Initializing router node")
            
            # Load rules into decision engine
            rules_config = {}
            for category_name, category in self.decision_matrix.config.categories.items():
                rules_config[category_name] = []
                for rule in category.rules:
                    rules_config[category_name].append({
                        'condition': rule.condition,
                        'decision': rule.decision.name,
                        'priority': rule.priority,
                        'description': rule.description
                    })
            
            self.decision_engine.load_rules(rules_config)
            
            # Load ML model if configured
            if self.config.use_ml_routing and self.config.ml_model_path:
                # In production, would load ML model here
                self.logger.info(f"ML routing configured but not implemented")
            
            self.is_initialized = True
            self.logger.info("Router node initialized successfully")
            
        except Exception as e:
            self.logger.error(f"Failed to initialize router node: {e}")
            raise
    
    async def shutdown(self) -> None:
        """Shutdown the router node."""
        self.logger.info("Shutting down router node")
        
        # Clear history
        async with self._history_lock:
            self._decision_history.clear()
        
        self.is_initialized = False
    
    async def process(self, analyzed_stimuli: AnalyzedStimuli) -> RoutingDecision:
        """
        Make routing decision for analyzed stimuli.
        
        Process:
        1. Check for emergency overrides
        2. Apply decision matrix rules
        3. Consider ML predictions (if enabled)
        4. Generate execution plan
        5. Validate decision feasibility
        
        Args:
            analyzed_stimuli: Analyzed stimuli with context
            
        Returns:
            RoutingDecision with execution plan
        """
        start_time = datetime.now()
        
        try:
            # Check for emergency override first
            if self.config.enable_emergency_override:
                emergency_decision = self._check_emergency_override(analyzed_stimuli)
                if emergency_decision:
                    self.logger.warning(
                        "Emergency override triggered",
                        stimuli_id=analyzed_stimuli.id,
                        reason=emergency_decision[1]
                    )
                    return await self._create_emergency_routing(
                        analyzed_stimuli, 
                        emergency_decision[0],
                        emergency_decision[1]
                    )
            
            # Apply decision matrix
            decision = await self._apply_decision_matrix(analyzed_stimuli)
            
            # Apply ML routing if configured
            if self.config.use_ml_routing:
                ml_decision = await self._apply_ml_routing(analyzed_stimuli)
                if ml_decision and ml_decision != decision:
                    self.logger.info(
                        "ML routing override",
                        matrix_decision=decision.value,
                        ml_decision=ml_decision.value
                    )
                    decision = ml_decision
            
            # Generate execution plan
            execution_plan = await self._generate_execution_plan(decision, analyzed_stimuli)
            
            # Validate decision
            is_valid, validation_reason = await self._validate_decision(
                decision, execution_plan, analyzed_stimuli
            )
            
            # Store validation reason for reasoning generation
            self._last_validation_reason = (is_valid, validation_reason)
            
            if not is_valid:
                self.logger.warning(
                    "Decision validation failed",
                    stimuli_id=analyzed_stimuli.id,
                    decision=decision.value,
                    reason=validation_reason
                )
                # Use fallback decision
                decision = ProcessingDecision[self.config.fallback_decision]
                execution_plan = await self._generate_execution_plan(decision, analyzed_stimuli)
            
            # Calculate confidence score
            confidence_score = self._calculate_confidence_score(
                decision, analyzed_stimuli, is_valid
            )
            
            # Create routing decision
            routing_decision = RoutingDecision(
                stimuli_id=analyzed_stimuli.id,
                decision=decision,
                execution_plan=execution_plan,
                confidence_score=confidence_score,
                reasoning=self._generate_reasoning(decision, analyzed_stimuli),
                decision_timestamp=datetime.now(),
                override_applied=not is_valid
            )
            
            # Track decision
            if self.config.decision_logging_enabled:
                await self._track_decision(routing_decision)
            
            processing_time = (datetime.now() - start_time).total_seconds()
            
            self.logger.info(
                "Routing decision made",
                stimuli_id=analyzed_stimuli.id,
                decision=decision.value,
                confidence=confidence_score,
                processing_time=processing_time
            )
            
            return routing_decision
            
        except Exception as e:
            self.logger.error(
                f"Routing decision failed for stimuli {analyzed_stimuli.id}: {e}"
            )
            # Return safe fallback
            return await self._create_fallback_routing(analyzed_stimuli, str(e))
    
    def _check_emergency_override(
        self, analyzed_stimuli: AnalyzedStimuli
    ) -> Optional[Tuple[ProcessingDecision, str]]:
        """Check if emergency override should be applied."""
        # Check stimuli category
        if analyzed_stimuli.category.value == "EMERGENCY":
            return (ProcessingDecision.EMERGENCY_OVERRIDE, "Emergency category detected")
        
        # Check priority
        if analyzed_stimuli.priority.value == "critical":
            return (ProcessingDecision.EMERGENCY_OVERRIDE, "Critical priority detected")
        
        # Check for emergency keywords in content
        emergency_keywords = ["emergency", "urgent", "critical", "alert", "warning"]
        content_lower = analyzed_stimuli.content.lower()
        for keyword in emergency_keywords:
            if keyword in content_lower:
                return (
                    ProcessingDecision.EMERGENCY_OVERRIDE, 
                    f"Emergency keyword '{keyword}' detected"
                )
        
        # Check system state
        if (analyzed_stimuli.system_state_analysis and 
            analyzed_stimuli.system_state_analysis.has_errors):
            # Don't override on errors, use safe fallback
            return (ProcessingDecision.LOG_ONLY, "System errors detected")
        
        return None
    
    async def _apply_decision_matrix(self, analyzed_stimuli: AnalyzedStimuli) -> ProcessingDecision:
        """Apply decision matrix rules to determine processing path."""
        # Create evaluation context
        context = self._create_evaluation_context(analyzed_stimuli)
        
        # Use decision engine for evaluation with detailed results
        decision, eval_results = self.decision_engine.evaluate_with_explanation(context)
        
        # Log detailed evaluation results if configured
        if self.config.decision_logging_enabled:
            self._log_decision_evaluation(analyzed_stimuli.id, eval_results)
        
        # Track metrics for rule hits
        if self.metrics:
            for result in eval_results:
                if result.matched:
                    self.metrics.record_rule_hit(result.rule_id)
        
        return decision
    
    def _create_evaluation_context(self, analyzed_stimuli: AnalyzedStimuli) -> Dict[str, Any]:
        """Create evaluation context from analyzed stimuli."""
        context = {
            'category': analyzed_stimuli.category.value,
            'confidence': analyzed_stimuli.confidence,
            'priority': analyzed_stimuli.priority.value,
            'system_state': {},
            'resource_analysis': {},
            'user_context': {},
            'environmental_analysis': {},
            'metadata': analyzed_stimuli.metadata
        }
        
        # Add analysis results if available
        if analyzed_stimuli.system_state_analysis:
            context['system_state'] = {
                'is_speaking': analyzed_stimuli.system_state_analysis.is_speaking,
                'is_idle': analyzed_stimuli.system_state_analysis.is_idle,
                'has_errors': analyzed_stimuli.system_state_analysis.has_errors,
                'queue_size': analyzed_stimuli.system_state_analysis.queue_size
            }
        
        if analyzed_stimuli.resource_analysis:
            context['resource_analysis'] = {
                'cpu_availability': analyzed_stimuli.resource_analysis.cpu_availability,
                'memory_availability': analyzed_stimuli.resource_analysis.memory_availability,
                'system1_availability': analyzed_stimuli.resource_analysis.system1_availability,
                'system2_availability': analyzed_stimuli.resource_analysis.system2_availability
            }
        
        if analyzed_stimuli.user_context_analysis:
            context['user_context'] = {
                'engagement_level': analyzed_stimuli.user_context_analysis.engagement_level,
                'interaction_frequency': analyzed_stimuli.user_context_analysis.interaction_frequency,
                'user_preference_match': analyzed_stimuli.user_context_analysis.user_preference_match
            }
        
        if analyzed_stimuli.environmental_analysis:
            context['environmental_analysis'] = {
                'autonomous_mode_active': analyzed_stimuli.environmental_analysis.autonomous_mode_active,
                'streaming_status': analyzed_stimuli.environmental_analysis.streaming_status,
                'time_of_day_factor': analyzed_stimuli.environmental_analysis.time_of_day_factor,
                'recent_activity_level': analyzed_stimuli.environmental_analysis.recent_activity_level
            }
        
        return context
    
    def _log_decision_evaluation(self, stimuli_id: str, eval_results: List[RuleEvaluationResult]) -> None:
        """Log detailed decision evaluation results."""
        matched_rules = [r for r in eval_results if r.matched]
        
        self.logger.debug(
            "Decision evaluation details",
            stimuli_id=stimuli_id,
            total_rules_evaluated=len(eval_results),
            matched_rules_count=len(matched_rules),
            matched_rules=[{
                'rule_id': r.rule_id,
                'decision': r.decision.value if r.decision else None,
                'confidence': r.confidence,
                'reasoning': r.reasoning
            } for r in matched_rules[:3]]  # Log top 3 matched rules
        )
    
    async def _apply_ml_routing(self, analyzed_stimuli: AnalyzedStimuli) -> Optional[ProcessingDecision]:
        """Apply ML-based routing if configured."""
        # Placeholder for ML routing
        # In production, would use trained model to predict best decision
        return None
    
    async def _generate_execution_plan(
        self, 
        decision: ProcessingDecision, 
        analyzed_stimuli: AnalyzedStimuli
    ) -> ExecutionPlan:
        """Generate detailed execution plan for the decision."""
        plan_id = str(uuid.uuid4())
        
        # Determine target systems based on decision
        target_systems = []
        parallel_execution = False
        
        if decision == ProcessingDecision.AVATAR_AND_ANALYSIS:
            target_systems = ["system1", "system2"]
            parallel_execution = True  # Can run concurrently
        elif decision == ProcessingDecision.ANALYSIS_ONLY:
            target_systems = ["system2"]
        elif decision == ProcessingDecision.LOG_ONLY:
            target_systems = ["log"]
        elif decision == ProcessingDecision.EMERGENCY_OVERRIDE:
            target_systems = ["system1", "system2"]
            parallel_execution = False  # Sequential for emergency
        
        # Set timeouts based on priority
        timeout_base = 30.0
        if analyzed_stimuli.priority.value == "critical":
            timeout_base = 10.0
        elif analyzed_stimuli.priority.value == "high":
            timeout_base = 20.0
        
        timeout_settings = {
            "system1": timeout_base,
            "system2": timeout_base * 2,  # Agents may take longer
            "log": 5.0
        }
        
        # Create retry policies
        retry_policies = [
            RetryPolicy(
                system="system1",
                max_attempts=3,
                initial_delay=1.0,
                exponential_base=2.0,
                max_delay=10.0
            ),
            RetryPolicy(
                system="system2",
                max_attempts=2,
                initial_delay=2.0,
                exponential_base=2.0,
                max_delay=20.0
            )
        ]
        
        # Set execution priority
        if decision == ProcessingDecision.EMERGENCY_OVERRIDE:
            priority = ExecutionPriority.CRITICAL
        elif analyzed_stimuli.priority.value == "high":
            priority = ExecutionPriority.HIGH
        else:
            priority = ExecutionPriority.NORMAL
        
        # Prepare execution parameters
        execution_params = {
            "stimuli_content": analyzed_stimuli.content,
            "stimuli_metadata": analyzed_stimuli.metadata,
            "category": analyzed_stimuli.category.value,
            "confidence": analyzed_stimuli.confidence,
            "context_score": analyzed_stimuli.get_context_score()
        }
        
        return ExecutionPlan(
            id=plan_id,
            stimuli_id=analyzed_stimuli.id,
            decision=decision,
            target_systems=target_systems,
            execution_order=["parallel"] if parallel_execution else ["sequential"],
            timeout_settings=timeout_settings,
            retry_policies=retry_policies,
            priority=priority,
            parallel_execution=parallel_execution,
            execution_params=execution_params
        )
    
    async def _validate_decision(
        self,
        decision: ProcessingDecision,
        execution_plan: ExecutionPlan,
        analyzed_stimuli: AnalyzedStimuli
    ) -> Tuple[bool, str]:
        """Validate if the decision is feasible given current context."""
        # Check system availability for target systems
        if analyzed_stimuli.resource_analysis:
            if "system1" in execution_plan.target_systems:
                if not analyzed_stimuli.resource_analysis.system1_availability:
                    return False, "System1 not available"
            
            if "system2" in execution_plan.target_systems:
                if not analyzed_stimuli.resource_analysis.system2_availability:
                    return False, "System2 not available"
        
        # Check resource constraints
        if decision in [ProcessingDecision.AVATAR_AND_ANALYSIS, ProcessingDecision.EMERGENCY_OVERRIDE]:
            if analyzed_stimuli.resource_analysis:
                if analyzed_stimuli.resource_analysis.cpu_availability < 0.2:
                    return False, "Insufficient CPU resources"
                if analyzed_stimuli.resource_analysis.memory_availability < 0.2:
                    return False, "Insufficient memory resources"
        
        # Check system state conflicts
        if analyzed_stimuli.system_state_analysis:
            if decision == ProcessingDecision.AVATAR_AND_ANALYSIS:
                if analyzed_stimuli.system_state_analysis.is_speaking:
                    return False, "Avatar already speaking"
            
            if analyzed_stimuli.system_state_analysis.queue_size > 50:
                if decision != ProcessingDecision.LOG_ONLY:
                    return False, "Processing queue overloaded"
        
        return True, "Valid"
    
    def _calculate_confidence_score(
        self,
        decision: ProcessingDecision,
        analyzed_stimuli: AnalyzedStimuli,
        is_valid: bool
    ) -> float:
        """Calculate confidence score for the routing decision."""
        base_confidence = 0.5
        
        # Start with categorization confidence
        base_confidence += analyzed_stimuli.confidence * 0.2
        
        # Add context quality score
        base_confidence += analyzed_stimuli.get_context_score() * 0.2
        
        # Boost for valid decisions
        if is_valid:
            base_confidence += 0.1
        
        # Adjust based on decision type
        if decision == ProcessingDecision.EMERGENCY_OVERRIDE:
            base_confidence = max(0.9, base_confidence)  # High confidence for emergency
        elif decision == ProcessingDecision.LOG_ONLY:
            base_confidence = min(0.7, base_confidence)  # Lower confidence for log only
        
        return min(1.0, base_confidence)
    
    def _generate_reasoning(
        self, 
        decision: ProcessingDecision, 
        analyzed_stimuli: AnalyzedStimuli
    ) -> str:
        """Generate human-readable reasoning for the decision."""
        # Use decision engine to get detailed explanation
        context = self._create_evaluation_context(analyzed_stimuli)
        explanation = self.decision_engine.explain_decision(context, decision)
        
        # Add any additional context-specific reasoning
        additional_reasons = []
        
        # Add validation-related reasoning if decision was overridden
        if hasattr(self, '_last_validation_reason') and not self._last_validation_reason[0]:
            additional_reasons.append(f"Override: {self._last_validation_reason[1]}")
        
        # Combine explanations
        if additional_reasons:
            return f"{explanation} | {'; '.join(additional_reasons)}"
        
        return explanation
    
    async def _track_decision(self, routing_decision: RoutingDecision) -> None:
        """Track decision for analysis and learning."""
        async with self._history_lock:
            self._decision_history[routing_decision.stimuli_id] = routing_decision
            
            # Limit history size
            if len(self._decision_history) > 1000:
                # Remove oldest entries
                sorted_items = sorted(
                    self._decision_history.items(),
                    key=lambda x: x[1].decision_timestamp
                )
                for stimuli_id, _ in sorted_items[:100]:
                    del self._decision_history[stimuli_id]
    
    async def _create_emergency_routing(
        self,
        analyzed_stimuli: AnalyzedStimuli,
        decision: ProcessingDecision,
        reason: str
    ) -> RoutingDecision:
        """Create emergency routing decision."""
        execution_plan = await self._generate_execution_plan(decision, analyzed_stimuli)
        
        return RoutingDecision(
            stimuli_id=analyzed_stimuli.id,
            decision=decision,
            execution_plan=execution_plan,
            confidence_score=0.95,
            reasoning=f"Emergency override: {reason}",
            decision_timestamp=datetime.now(),
            override_applied=True
        )
    
    async def _create_fallback_routing(
        self,
        analyzed_stimuli: AnalyzedStimuli,
        error: str
    ) -> RoutingDecision:
        """Create safe fallback routing decision."""
        decision = ProcessingDecision.LOG_ONLY
        execution_plan = ExecutionPlan(
            id=str(uuid.uuid4()),
            stimuli_id=analyzed_stimuli.id,
            decision=decision,
            target_systems=["log"],
            execution_order=["sequential"],
            timeout_settings={"log": 5.0},
            retry_policies=[],
            priority=ExecutionPriority.LOW,
            parallel_execution=False,
            execution_params={"error": error}
        )
        
        return RoutingDecision(
            stimuli_id=analyzed_stimuli.id,
            decision=decision,
            execution_plan=execution_plan,
            confidence_score=0.3,
            reasoning=f"Fallback routing due to error: {error}",
            decision_timestamp=datetime.now(),
            override_applied=True
        )
    
    async def get_decision_statistics(self) -> Dict[str, Any]:
        """Get comprehensive decision statistics from the router."""
        from collections import defaultdict
        
        # Get rule statistics from decision engine
        rule_stats = self.decision_engine.get_rule_statistics()
        
        # Calculate decision distribution from history
        decision_distribution = defaultdict(int)
        total_decisions = 0
        
        async with self._history_lock:
            for routing_decision in self._decision_history.values():
                decision_distribution[routing_decision.decision.value] += 1
                total_decisions += 1
        
        # Calculate percentages
        decision_percentages = {}
        if total_decisions > 0:
            for decision, count in decision_distribution.items():
                decision_percentages[decision] = {
                    'count': count,
                    'percentage': (count / total_decisions) * 100
                }
        
        return {
            'total_decisions': total_decisions,
            'decision_distribution': decision_percentages,
            'rule_statistics': rule_stats,
            'history_size': len(self._decision_history),
            'is_initialized': self.is_initialized
        }
    
    def get_decision_reasoning(self, stimuli_id: str) -> Optional[str]:
        """Get the reasoning for a specific decision by stimuli ID."""
        if stimuli_id in self._decision_history:
            return self._decision_history[stimuli_id].reasoning
        return None