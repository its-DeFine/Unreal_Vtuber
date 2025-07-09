"""
Decision Flow Manager for GraphFlow Pipeline.

This module manages the decision-making flow including routing decisions
and execution planning based on analyzed stimuli and decision matrices.
"""

import asyncio
from typing import Optional, Dict, Any, List, Tuple
from datetime import datetime
import uuid

from autogen_core import SingleThreadedAgentRuntime, AgentId, MessageContext

from ...config.settings import GraphFlowConfig
from ...config.decision_matrix import DecisionMatrix, DecisionRule
from ...models.stimuli import AnalyzedStimuli, RoutingDecision
from ...models.decisions import (
    ProcessingDecision,
    ExecutionPlan,
    RetryPolicy,
    ExecutionPriority
)
from ...utils.logging import get_structured_logger
from ..nodes.router_node import DecisionRouterNode
from ..nodes.executor_node import ExecutionCoordinatorNode


class DecisionFlowManager:
    """
    Manages the decision flow through routing and execution planning.
    
    This manager coordinates decision-making based on analyzed stimuli,
    applies decision matrices, and creates execution plans for the
    selected processing paths.
    """
    
    def __init__(self, config: GraphFlowConfig, runtime: SingleThreadedAgentRuntime):
        """
        Initialize the decision flow manager.
        
        Args:
            config: GraphFlow configuration
            runtime: AutoGen runtime for agent management
        """
        self.config = config
        self.runtime = runtime
        self.logger = get_structured_logger("decision_flow_manager")
        
        # Initialize decision matrix
        self.decision_matrix = DecisionMatrix()
        self._load_custom_rules()
        
        # Initialize nodes
        self.router_node = DecisionRouterNode(
            config=config.router,
            decision_matrix=self.decision_matrix
        )
        
        self.executor_node = ExecutionCoordinatorNode(
            config=config.executor,
            system1_config=config.system1,
            system2_config=config.system2
        )
        
        # Flow state management
        self._decision_cache: Dict[str, RoutingDecision] = {}
        self._cache_lock = asyncio.Lock()
        self.is_initialized = False
        
        # Decision metrics
        self._decision_metrics: Dict[str, int] = {
            decision.value: 0 for decision in ProcessingDecision
        }
    
    async def initialize(self) -> None:
        """Initialize the decision flow manager and its nodes."""
        try:
            self.logger.info("Initializing decision flow manager")
            
            # Initialize nodes
            await self.router_node.initialize()
            await self.executor_node.initialize()
            
            # Load any persisted decision patterns
            await self._load_decision_patterns()
            
            self.is_initialized = True
            self.logger.info("Decision flow manager initialized successfully")
            
        except Exception as e:
            self.logger.error(
                "Failed to initialize decision flow manager",
                error=str(e)
            )
            raise
    
    async def shutdown(self) -> None:
        """Shutdown the decision flow manager and cleanup resources."""
        try:
            self.logger.info("Shutting down decision flow manager")
            
            # Save decision patterns for learning
            await self._save_decision_patterns()
            
            # Shutdown nodes
            await self.router_node.shutdown()
            await self.executor_node.shutdown()
            
            # Clear caches
            async with self._cache_lock:
                self._decision_cache.clear()
            
            self.is_initialized = False
            self.logger.info("Decision flow manager shutdown complete")
            
        except Exception as e:
            self.logger.error(
                "Error during decision flow manager shutdown",
                error=str(e)
            )
    
    async def process_decision(self, analyzed_stimuli: AnalyzedStimuli) -> RoutingDecision:
        """
        Process routing decision for analyzed stimuli.
        
        This method:
        1. Checks cache for recent similar decisions
        2. Applies decision matrix rules
        3. Creates execution plan
        4. Validates decision feasibility
        
        Args:
            analyzed_stimuli: Analyzed stimuli with context
            
        Returns:
            RoutingDecision with execution plan
            
        Raises:
            RuntimeError: If decision processing fails
        """
        if not self.is_initialized:
            raise RuntimeError("Decision flow manager not initialized")
        
        start_time = datetime.now()
        
        try:
            self.logger.info(
                "Processing routing decision",
                stimuli_id=analyzed_stimuli.id,
                category=analyzed_stimuli.category.value,
                context_score=analyzed_stimuli.get_context_score()
            )
            
            # Check cache for similar recent decisions
            cached_decision = await self._check_decision_cache(analyzed_stimuli)
            if cached_decision:
                self.logger.info(
                    "Using cached routing decision",
                    stimuli_id=analyzed_stimuli.id,
                    cached_decision=cached_decision.decision.value
                )
                return cached_decision
            
            # Process through router node
            routing_decision = await self.router_node.process(analyzed_stimuli)
            
            # Enhance execution plan based on context
            enhanced_plan = await self._enhance_execution_plan(
                routing_decision.execution_plan,
                analyzed_stimuli
            )
            routing_decision.execution_plan = enhanced_plan
            
            # Validate decision feasibility
            is_valid, validation_reason = await self._validate_decision(
                routing_decision,
                analyzed_stimuli
            )
            
            if not is_valid:
                self.logger.warning(
                    "Decision validation failed, applying fallback",
                    stimuli_id=analyzed_stimuli.id,
                    reason=validation_reason
                )
                routing_decision = await self._apply_fallback_decision(
                    analyzed_stimuli,
                    validation_reason
                )
            
            # Cache the decision
            await self._cache_decision(analyzed_stimuli, routing_decision)
            
            # Update metrics
            self._decision_metrics[routing_decision.decision.value] += 1
            
            processing_time = (datetime.now() - start_time).total_seconds()
            self.logger.info(
                "Routing decision completed",
                stimuli_id=analyzed_stimuli.id,
                decision=routing_decision.decision.value,
                confidence=routing_decision.confidence_score,
                processing_time=processing_time
            )
            
            return routing_decision
            
        except Exception as e:
            self.logger.error(
                "Decision processing failed",
                stimuli_id=analyzed_stimuli.id,
                error=str(e)
            )
            raise RuntimeError(f"Decision processing failed: {str(e)}")
    
    def _load_custom_rules(self) -> None:
        """Load custom decision rules if configured."""
        if self.config.router.custom_rules_path:
            try:
                # Load custom rules from JSON file
                import json
                import os
                
                if os.path.exists(self.config.router.custom_rules_path):
                    with open(self.config.router.custom_rules_path, 'r') as f:
                        custom_rules_data = json.load(f)
                    
                    custom_rules = []
                    
                    # Process each category of rules
                    for category_name, rules_list in custom_rules_data.items():
                        for rule_data in rules_list:
                            if rule_data.get('enabled', True):
                                # Convert condition string to executable function
                                condition_str = rule_data['condition']
                                condition_func = self._compile_condition(condition_str)
                                
                                # Convert decision string to enum
                                decision_str = rule_data['decision']
                                decision_enum = getattr(ProcessingDecision, decision_str, ProcessingDecision.ANALYSIS_ONLY)
                                
                                rule = DecisionRule(
                                    name=rule_data['id'],
                                    condition=condition_func,
                                    decision=decision_enum,
                                    priority=rule_data.get('priority', 50),
                                    reasoning=rule_data.get('description', f"Custom rule: {rule_data['id']}")
                                )
                                custom_rules.append(rule)
                else:
                    # Fallback to example rules
                    custom_rules = [
                        DecisionRule(
                            name="high_priority_admin",
                            condition=lambda s: (
                                s.category == "DIRECT_ADMIN" and 
                                s.priority.value in ["high", "critical"]
                            ),
                            decision=ProcessingDecision.AVATAR_AND_ANALYSIS,
                            priority=95,
                            reasoning="High priority admin command requires immediate avatar response"
                        ),
                        DecisionRule(
                            name="system_notification_idle",
                            condition=lambda s: (
                                s.category == "SYSTEM_NOTIFICATION" and
                                s.system_state_analysis and
                                s.system_state_analysis.is_idle
                            ),
                            decision=ProcessingDecision.ANALYSIS_ONLY,
                            priority=85,
                            reasoning="System notifications during idle state only need analysis"
                        )
                    ]
                
                for rule in custom_rules:
                    self.decision_matrix.add_custom_rule(rule)
                
                self.logger.info(
                    f"Loaded {len(custom_rules)} custom decision rules"
                )
                
            except Exception as e:
                self.logger.warning(
                    "Failed to load custom rules",
                    error=str(e)
                )
    
    def _compile_condition(self, condition_str: str):
        """Compile a condition string into a callable function."""
        def condition_func(s):
            try:
                # Create a safe evaluation environment
                eval_env = {
                    'source': s.source,
                    'category': s.category,
                    'priority': s.priority,
                    'metadata': s.metadata if hasattr(s, 'metadata') else {},
                    'system_state_analysis': getattr(s, 'system_state_analysis', None),
                    'user_context_analysis': getattr(s, 'user_context_analysis', None),
                    'environmental_analysis': getattr(s, 'environmental_analysis', None),
                    'resource_analysis': getattr(s, 'resource_analysis', None),
                    'processing_context': getattr(s, 'processing_context', None),
                    'contains': lambda text, substring: substring in text,
                    'get': lambda d, k, default=None: d.get(k, default) if hasattr(d, 'get') else default
                }
                
                # Debug logging for E2E test rule
                if 'e2e_test' in condition_str:
                    self.logger.info(
                        f"Evaluating E2E test condition: {condition_str}",
                        source=s.source,
                        metadata=s.metadata,
                        eval_env_source=eval_env.get('source'),
                        eval_env_metadata=eval_env.get('metadata')
                    )
                
                # Evaluate the condition
                result = eval(condition_str, {"__builtins__": {}}, eval_env)
                
                # Debug logging for E2E test rule results
                if 'e2e_test' in condition_str:
                    self.logger.info(
                        f"E2E test condition result: {result}",
                        condition=condition_str,
                        stimuli_source=s.source,
                        stimuli_metadata=s.metadata
                    )
                
                return bool(result)
            except Exception as e:
                self.logger.warning(f"Failed to evaluate condition '{condition_str}': {e}")
                return False
        
        return condition_func
    
    async def _check_decision_cache(
        self, 
        analyzed_stimuli: AnalyzedStimuli
    ) -> Optional[RoutingDecision]:
        """Check if we have a cached decision for similar stimuli."""
        # Simple cache key based on category and context score
        cache_key = f"{analyzed_stimuli.category.value}_{int(analyzed_stimuli.get_context_score() * 10)}"
        
        async with self._cache_lock:
            if cache_key in self._decision_cache:
                cached = self._decision_cache[cache_key]
                # Check if cache is still valid (within 5 minutes)
                if (datetime.now() - cached.decision_timestamp).seconds < 300:
                    # Create new decision with same logic but new IDs
                    return RoutingDecision(
                        stimuli_id=analyzed_stimuli.id,
                        decision=cached.decision,
                        execution_plan=ExecutionPlan(
                            id=str(uuid.uuid4()),
                            stimuli_id=analyzed_stimuli.id,
                            decision=cached.decision,
                            target_systems=cached.execution_plan.target_systems,
                            execution_order=cached.execution_plan.execution_order,
                            parallel_execution=cached.execution_plan.parallel_execution,
                            timeout_settings=cached.execution_plan.timeout_settings,
                            retry_policies=cached.execution_plan.retry_policies,
                            priority=cached.execution_plan.priority,
                            execution_params=cached.execution_plan.execution_params
                        ),
                        confidence_score=cached.confidence_score * 0.9,  # Slightly lower confidence
                        reasoning=f"Cached decision: {cached.reasoning}",
                        decision_timestamp=datetime.now()
                    )
        
        return None
    
    async def _cache_decision(
        self,
        analyzed_stimuli: AnalyzedStimuli,
        routing_decision: RoutingDecision
    ) -> None:
        """Cache a routing decision for future use."""
        cache_key = f"{analyzed_stimuli.category.value}_{int(analyzed_stimuli.get_context_score() * 10)}"
        
        async with self._cache_lock:
            self._decision_cache[cache_key] = routing_decision
            
            # Limit cache size
            if len(self._decision_cache) > 100:
                # Remove oldest entries
                sorted_items = sorted(
                    self._decision_cache.items(),
                    key=lambda x: x[1].decision_timestamp
                )
                for key, _ in sorted_items[:20]:
                    del self._decision_cache[key]
    
    async def _enhance_execution_plan(
        self,
        execution_plan: ExecutionPlan,
        analyzed_stimuli: AnalyzedStimuli
    ) -> ExecutionPlan:
        """Enhance execution plan based on context and system state."""
        # Adjust timeouts based on system load
        if analyzed_stimuli.resource_analysis:
            cpu_avail = analyzed_stimuli.resource_analysis.cpu_availability
            if cpu_avail < 0.3:  # High load
                # Increase timeouts
                for system, timeout in execution_plan.timeout_settings.items():
                    execution_plan.timeout_settings[system] = timeout * 1.5
        
        # Adjust parallelization based on resource availability
        if analyzed_stimuli.resource_analysis:
            capacity = analyzed_stimuli.resource_analysis.estimated_processing_capacity
            if capacity < 5:  # Low capacity
                execution_plan.parallel_execution = False
                execution_plan.execution_order = ["sequential"]
        
        # Add execution parameters based on stimuli content
        if execution_plan.decision == ProcessingDecision.AVATAR_AND_ANALYSIS:
            # Prepare avatar-specific parameters
            execution_plan.execution_params["avatar_content"] = analyzed_stimuli.content
            execution_plan.execution_params["avatar_metadata"] = {
                "category": analyzed_stimuli.category.value,
                "priority": analyzed_stimuli.priority.value,
                "source": analyzed_stimuli.source
            }
            
            # Add character preferences if available
            if analyzed_stimuli.metadata.get("character_id"):
                execution_plan.execution_params["character_id"] = (
                    analyzed_stimuli.metadata["character_id"]
                )
        
        return execution_plan
    
    async def _validate_decision(
        self,
        routing_decision: RoutingDecision,
        analyzed_stimuli: AnalyzedStimuli
    ) -> Tuple[bool, str]:
        """
        Validate if the routing decision is feasible.
        
        Returns:
            Tuple of (is_valid, reason)
        """
        # Check system availability for target systems
        if "system1" in routing_decision.execution_plan.target_systems:
            if (analyzed_stimuli.resource_analysis and 
                not analyzed_stimuli.resource_analysis.system1_availability):
                return False, "System1 not available"
        
        if "system2" in routing_decision.execution_plan.target_systems:
            if (analyzed_stimuli.resource_analysis and
                not analyzed_stimuli.resource_analysis.system2_availability):
                return False, "System2 not available"
        
        # Check resource constraints
        if routing_decision.decision == ProcessingDecision.AVATAR_AND_ANALYSIS:
            if analyzed_stimuli.resource_analysis:
                if analyzed_stimuli.resource_analysis.cpu_availability < 0.2:
                    return False, "Insufficient CPU for avatar processing"
                if analyzed_stimuli.resource_analysis.memory_availability < 0.2:
                    return False, "Insufficient memory for avatar processing"
        
        # Check for system state conflicts
        if routing_decision.decision == ProcessingDecision.AVATAR_AND_ANALYSIS:
            if (analyzed_stimuli.system_state_analysis and
                analyzed_stimuli.system_state_analysis.is_speaking):
                return False, "Avatar already speaking"
        
        return True, "Valid"
    
    async def _apply_fallback_decision(
        self,
        analyzed_stimuli: AnalyzedStimuli,
        validation_reason: str
    ) -> RoutingDecision:
        """Apply fallback decision when primary decision is not feasible."""
        # Determine fallback based on the validation reason
        if "System1 not available" in validation_reason:
            fallback_decision = ProcessingDecision.ANALYSIS_ONLY
        elif "System2 not available" in validation_reason:
            fallback_decision = ProcessingDecision.LOG_ONLY
        elif "Insufficient" in validation_reason:
            fallback_decision = ProcessingDecision.LOG_ONLY
        elif "Avatar already speaking" in validation_reason:
            fallback_decision = ProcessingDecision.ANALYSIS_ONLY
        else:
            # Use configured fallback
            fallback_decision = ProcessingDecision[self.config.router.fallback_decision]
        
        # Create fallback execution plan
        target_systems = []
        if fallback_decision == ProcessingDecision.ANALYSIS_ONLY:
            target_systems = ["system2"]
        elif fallback_decision == ProcessingDecision.LOG_ONLY:
            target_systems = ["log"]
        
        execution_plan = ExecutionPlan(
            id=str(uuid.uuid4()),
            stimuli_id=analyzed_stimuli.id,
            decision=fallback_decision,
            target_systems=target_systems,
            execution_order=["sequential"],
            parallel_execution=False,
            timeout_settings={"default": 10.0},
            retry_policies=[
                RetryPolicy(
                    system="default",
                    max_attempts=1,
                    initial_delay=1.0,
                    max_delay=5.0,
                    exponential_base=2.0
                )
            ],
            priority=ExecutionPriority.NORMAL,
            execution_params={}
        )
        
        return RoutingDecision(
            stimuli_id=analyzed_stimuli.id,
            decision=fallback_decision,
            execution_plan=execution_plan,
            confidence_score=0.7,  # Lower confidence for fallback
            reasoning=f"Fallback decision due to: {validation_reason}",
            decision_timestamp=datetime.now(),
            override_applied=True
        )
    
    async def _load_decision_patterns(self) -> None:
        """Load historical decision patterns for learning."""
        # In a real implementation, this would load from database
        # For now, just log the intent
        self.logger.info("Loading decision patterns (not implemented)")
    
    async def _save_decision_patterns(self) -> None:
        """Save decision patterns for future learning."""
        # In a real implementation, this would save to database
        self.logger.info(
            "Saving decision patterns",
            metrics=self._decision_metrics
        )
    
    def get_decision_metrics(self) -> Dict[str, int]:
        """Get metrics on decisions made."""
        return self._decision_metrics.copy()
    
    def get_cache_stats(self) -> Dict[str, Any]:
        """Get cache statistics."""
        return {
            "cache_size": len(self._decision_cache),
            "cache_keys": list(self._decision_cache.keys())
        }