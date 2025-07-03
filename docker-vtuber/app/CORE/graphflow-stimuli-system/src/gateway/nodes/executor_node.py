"""
Execution Coordinator Node for GraphFlow Pipeline.

This node coordinates the execution of routing decisions across different systems,
handling parallel/sequential execution, retries, and result aggregation.
"""

import asyncio
import time
from typing import Dict, Any, List, Optional
from datetime import datetime
import importlib.util
import random

from ...models.stimuli import RoutingDecision
from ...models.decisions import ExecutionResult, ExecutionPlan, ProcessingDecision, RetryPolicy
from ...config.settings import ExecutorConfig, System1Config, System2Config
from ...utils.logging import get_structured_logger
from ...utils.metrics import MetricsCollector, MetricTimer


class ExecutionCoordinatorNode:
    """
    GraphFlow node for execution coordination.
    
    Coordinates execution across:
    - System1 (Avatar/Speech)
    - System2 (Multi-Agent)
    - Logging system
    - Emergency overrides
    """
    
    def __init__(
        self, 
        config: ExecutorConfig,
        system1_config: System1Config,
        system2_config: System2Config,
        metrics_collector: Optional[MetricsCollector] = None
    ):
        """
        Initialize the executor node.
        
        Args:
            config: Executor configuration
            system1_config: System1 configuration
            system2_config: System2 configuration
            metrics_collector: Optional metrics collector instance
        """
        self.config = config
        self.system1_config = system1_config
        self.system2_config = system2_config
        self.logger = get_structured_logger("executor_node")
        self.metrics = metrics_collector or MetricsCollector(enabled=False)
        
        # Execution tracking
        self._active_executions: Dict[str, Any] = {}
        self._execution_lock = asyncio.Lock()
        
        # System interfaces (will be initialized)
        self.system1_interface = None
        self.system2_interface = None
        
        # Retry tracking
        self._retry_attempts: Dict[str, int] = {}
        
        self.is_initialized = False
    
    async def initialize(self) -> None:
        """Initialize the executor node."""
        try:
            self.logger.info("Initializing executor node")
            
            # In a real implementation, initialize system interfaces here
            # For now, we'll use them when passed from the gateway
            
            self.is_initialized = True
            self.logger.info("Executor node initialized successfully")
            
        except Exception as e:
            self.logger.error(f"Failed to initialize executor node: {e}")
            raise
    
    async def shutdown(self) -> None:
        """Shutdown the executor node."""
        self.logger.info("Shutting down executor node")
        
        # Wait for active executions to complete
        timeout = 10  # seconds
        start_time = time.time()
        while self._active_executions and (time.time() - start_time) < timeout:
            await asyncio.sleep(0.1)
        
        if self._active_executions:
            self.logger.warning(
                f"Shutting down with {len(self._active_executions)} active executions"
            )
        
        # Clear tracking
        async with self._execution_lock:
            self._active_executions.clear()
        
        self.is_initialized = False
    
    def set_system_interfaces(self, system1_interface, system2_interface):
        """Set system interfaces for execution."""
        self.system1_interface = system1_interface
        self.system2_interface = system2_interface
    
    async def process(self, routing_decision: RoutingDecision) -> ExecutionResult:
        """
        Execute the routing decision.
        
        Coordinates execution based on the execution plan,
        handling parallel/sequential execution and retries.
        
        Args:
            routing_decision: Routing decision with execution plan
            
        Returns:
            ExecutionResult with execution outcome
        """
        execution_plan = routing_decision.execution_plan
        start_time = time.time()
        
        # Track active execution
        async with self._execution_lock:
            self._active_executions[execution_plan.id] = {
                'start_time': start_time,
                'routing_decision': routing_decision
            }
        
        try:
            self.logger.info(
                "Starting execution",
                execution_plan_id=execution_plan.id,
                stimuli_id=routing_decision.stimuli_id,
                decision=routing_decision.decision.value,
                target_systems=execution_plan.target_systems
            )
            
            # Execute based on decision type
            if routing_decision.decision == ProcessingDecision.EMERGENCY_OVERRIDE:
                result = await self._handle_emergency_override(execution_plan)
            elif routing_decision.decision == ProcessingDecision.AVATAR_AND_ANALYSIS:
                result = await self._execute_option_a(execution_plan, routing_decision)
            elif routing_decision.decision == ProcessingDecision.ANALYSIS_ONLY:
                result = await self._execute_option_b(execution_plan, routing_decision)
            elif routing_decision.decision == ProcessingDecision.LOG_ONLY:
                result = await self._execute_option_c(execution_plan, routing_decision)
            else:
                # Default execution path
                if execution_plan.parallel_execution and len(execution_plan.target_systems) > 1:
                    results = await self._execute_parallel(execution_plan, routing_decision)
                else:
                    results = await self._execute_sequential(execution_plan, routing_decision)
                
                # Aggregate results
                result = self._aggregate_results(results, execution_plan)
            
            execution_time = time.time() - start_time
            
            self.logger.info(
                "Execution completed",
                execution_plan_id=execution_plan.id,
                success=result.success,
                execution_time=execution_time
            )
            
            # Record metrics
            self.metrics.set_execution_success_rate(
                self._calculate_success_rate(result)
            )
            
            # Clean up retry tracking
            self._retry_attempts.pop(execution_plan.id, None)
            
            return result
            
        except Exception as e:
            self.logger.error(
                f"Execution failed for plan {execution_plan.id}: {e}"
            )
            self.metrics.increment_processing_errors(type(e).__name__)
            
            return ExecutionResult(
                stimuli_id=routing_decision.stimuli_id,
                execution_plan_id=execution_plan.id,
                success=False,
                results={"error": str(e)},
                execution_time=time.time() - start_time,
                error_details=str(e)
            )
        
        finally:
            # Remove from active executions
            async with self._execution_lock:
                self._active_executions.pop(execution_plan.id, None)
    
    async def _execute_parallel(
        self, 
        execution_plan: ExecutionPlan,
        routing_decision: RoutingDecision
    ) -> List[ExecutionResult]:
        """Execute multiple systems in parallel."""
        tasks = []
        
        for system in execution_plan.target_systems:
            if system == "system1":
                tasks.append(self._execute_system1(execution_plan, routing_decision))
            elif system == "system2":
                tasks.append(self._execute_system2(execution_plan, routing_decision))
            elif system == "log":
                tasks.append(self._execute_logging(execution_plan, routing_decision))
        
        # Execute all tasks concurrently
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Convert exceptions to failed results
        processed_results = []
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                processed_results.append(ExecutionResult(
                    stimuli_id=routing_decision.stimuli_id,
                    execution_plan_id=execution_plan.id,
                    success=False,
                    results={
                        "system": execution_plan.target_systems[i],
                        "error": str(result)
                    },
                    execution_time=0.0,
                    error_details=str(result)
                ))
            else:
                processed_results.append(result)
        
        return processed_results
    
    async def _execute_sequential(
        self,
        execution_plan: ExecutionPlan,
        routing_decision: RoutingDecision
    ) -> List[ExecutionResult]:
        """Execute systems sequentially."""
        results = []
        
        for system in execution_plan.target_systems:
            try:
                if system == "system1":
                    result = await self._execute_system1(execution_plan, routing_decision)
                elif system == "system2":
                    result = await self._execute_system2(execution_plan, routing_decision)
                elif system == "log":
                    result = await self._execute_logging(execution_plan, routing_decision)
                else:
                    continue
                
                results.append(result)
                
                # Stop on failure if configured
                if not result.success and not self.config.retry_failed_executions:
                    break
                    
            except Exception as e:
                results.append(ExecutionResult(
                    stimuli_id=routing_decision.stimuli_id,
                    execution_plan_id=execution_plan.id,
                    success=False,
                    results={"system": system, "error": str(e)},
                    execution_time=0.0,
                    error_details=str(e)
                ))
                
                # Stop on exception if not retrying
                if not self.config.retry_failed_executions:
                    break
        
        return results
    
    async def _execute_option_a(
        self,
        execution_plan: ExecutionPlan,
        routing_decision: RoutingDecision
    ) -> ExecutionResult:
        """
        Execute Option A: Avatar tools + agent analysis (concurrent).
        
        This executes both System1 (avatar/speech) and System2 (agent analysis)
        concurrently for maximum efficiency.
        """
        start_time = time.time()
        
        with MetricTimer(self.metrics, "option_a_execution", record_as_node=True):
            self.logger.info(
                "Executing Option A (Avatar + Analysis)",
                stimuli_id=routing_decision.stimuli_id,
                execution_plan_id=execution_plan.id
            )
            
            # Prepare tasks for concurrent execution
            tasks = []
            
            # Add System1 task if available
            if self.system1_interface:
                tasks.append(
                    self._execute_with_retry(
                        self._execute_system1,
                        execution_plan,
                        routing_decision,
                        "system1"
                    )
                )
            
            # Add System2 task if available
            if self.system2_interface:
                tasks.append(
                    self._execute_with_retry(
                        self._execute_system2,
                        execution_plan,
                        routing_decision,
                        "system2"
                    )
                )
            
            if not tasks:
                return ExecutionResult(
                    stimuli_id=routing_decision.stimuli_id,
                    execution_plan_id=execution_plan.id,
                    success=False,
                    results={"error": "No systems available for Option A"},
                    execution_time=time.time() - start_time,
                    error_details="Neither System1 nor System2 interfaces are initialized"
                )
            
            # Execute concurrently with timeout
            try:
                timeout = execution_plan.get_total_timeout()
                results = await asyncio.wait_for(
                    asyncio.gather(*tasks, return_exceptions=True),
                    timeout=timeout
                )
            except asyncio.TimeoutError:
                self.logger.error(
                    "Option A execution timeout",
                    stimuli_id=routing_decision.stimuli_id,
                    timeout=timeout
                )
                return ExecutionResult(
                    stimuli_id=routing_decision.stimuli_id,
                    execution_plan_id=execution_plan.id,
                    success=False,
                    results={"error": "Execution timeout"},
                    execution_time=time.time() - start_time,
                    error_details=f"Option A execution exceeded timeout of {timeout} seconds"
                )
            
            # Process results
            processed_results = []
            for i, result in enumerate(results):
                if isinstance(result, Exception):
                    system_name = "system1" if i == 0 else "system2"
                    processed_results.append(ExecutionResult(
                        stimuli_id=routing_decision.stimuli_id,
                        execution_plan_id=execution_plan.id,
                        success=False,
                        results={
                            "system": system_name,
                            "error": str(result)
                        },
                        execution_time=0.0,
                        error_details=str(result)
                    ))
                else:
                    processed_results.append(result)
            
            # Aggregate results
            aggregated = self._aggregate_results(processed_results, execution_plan)
            
            # Record option A specific metrics
            self.metrics.increment_decision("option_a")
            
            return aggregated
    
    async def _execute_option_b(
        self,
        execution_plan: ExecutionPlan,
        routing_decision: RoutingDecision
    ) -> ExecutionResult:
        """
        Execute Option B: Agent analysis only.
        
        This executes only System2 (multi-agent analysis) without
        triggering avatar responses.
        """
        start_time = time.time()
        
        with MetricTimer(self.metrics, "option_b_execution", record_as_node=True):
            self.logger.info(
                "Executing Option B (Analysis Only)",
                stimuli_id=routing_decision.stimuli_id,
                execution_plan_id=execution_plan.id
            )
            
            if not self.system2_interface:
                return ExecutionResult(
                    stimuli_id=routing_decision.stimuli_id,
                    execution_plan_id=execution_plan.id,
                    success=False,
                    results={"error": "System2 interface not available"},
                    execution_time=time.time() - start_time,
                    error_details="System2 interface not initialized for analysis-only execution"
                )
            
            # Execute with retry
            result = await self._execute_with_retry(
                self._execute_system2,
                execution_plan,
                routing_decision,
                "system2"
            )
            
            # Record option B specific metrics
            self.metrics.increment_decision("option_b")
            
            return result
    
    async def _execute_option_c(
        self,
        execution_plan: ExecutionPlan,
        routing_decision: RoutingDecision
    ) -> ExecutionResult:
        """
        Execute Option C: Log and store only.
        
        This logs the stimuli for future processing without immediate
        action from either system.
        """
        start_time = time.time()
        
        with MetricTimer(self.metrics, "option_c_execution", record_as_node=True):
            self.logger.info(
                "Executing Option C (Log Only)",
                stimuli_id=routing_decision.stimuli_id,
                execution_plan_id=execution_plan.id
            )
            
            # Execute logging
            result = await self._execute_logging(execution_plan, routing_decision)
            
            # Record option C specific metrics
            self.metrics.increment_decision("option_c")
            
            return result
    
    async def _execute_system1(
        self,
        execution_plan: ExecutionPlan,
        routing_decision: RoutingDecision
    ) -> ExecutionResult:
        """Execute on System1 (Avatar/Speech)."""
        start_time = time.time()
        
        with MetricTimer(self.metrics, "system1_execution", record_as_node=True):
            try:
                if not self.system1_interface:
                    raise RuntimeError("System1 interface not initialized")
                
                # Get timeout for this system
                timeout = execution_plan.timeout_settings.get("system1", 30.0)
                
                # Prepare content and metadata
                content = execution_plan.execution_params.get(
                    "stimuli_content",
                    routing_decision.analyzed_stimuli.content if hasattr(routing_decision, 'analyzed_stimuli') else ""
                )
                
                metadata = {
                    "stimuli_id": routing_decision.stimuli_id,
                    "category": execution_plan.execution_params.get("category"),
                    "priority": execution_plan.priority.value,
                    "source": execution_plan.execution_params.get("stimuli_metadata", {}).get("source")
                }
                
                # Execute with timeout
                success = await asyncio.wait_for(
                    self.system1_interface.trigger_avatar_response(content, metadata),
                    timeout=timeout
                )
                
                execution_time = time.time() - start_time
                
                # Record performance metrics
                self.metrics.record_node_processing_time("system1", execution_time)
                
                return ExecutionResult(
                    stimuli_id=routing_decision.stimuli_id,
                    execution_plan_id=execution_plan.id,
                    success=success,
                    results={
                        "system": "system1",
                        "action": "avatar_response",
                        "content_length": len(content),
                        "execution_time": execution_time
                    },
                    execution_time=execution_time,
                    affected_systems=["system1"],
                    performance_metrics={
                        "avatar_response_time": execution_time,
                        "content_length": len(content)
                    }
                )
                
            except asyncio.TimeoutError:
                execution_time = time.time() - start_time
                self.metrics.increment_processing_errors("System1Timeout")
                
                return ExecutionResult(
                    stimuli_id=routing_decision.stimuli_id,
                    execution_plan_id=execution_plan.id,
                    success=False,
                    results={"system": "system1", "error": "Timeout"},
                    execution_time=execution_time,
                    error_details="System1 execution timeout"
                )
            except Exception as e:
                self.logger.error(f"System1 execution failed: {e}")
                self.metrics.increment_processing_errors(f"System1_{type(e).__name__}")
                raise
    
    async def _execute_system2(
        self,
        execution_plan: ExecutionPlan,
        routing_decision: RoutingDecision
    ) -> ExecutionResult:
        """Execute on System2 (Multi-Agent)."""
        start_time = time.time()
        
        with MetricTimer(self.metrics, "system2_execution", record_as_node=True):
            try:
                if not self.system2_interface:
                    raise RuntimeError("System2 interface not initialized")
                
                # Get timeout for this system
                timeout = execution_plan.timeout_settings.get("system2", 60.0)
                
                # Prepare analyzed stimuli
                # In real implementation, would reconstruct from execution params
                # For now, create a mock analyzed stimuli
                analyzed_stimuli = routing_decision.analyzed_stimuli if hasattr(
                    routing_decision, 'analyzed_stimuli'
                ) else None
                
                if not analyzed_stimuli:
                    # Create minimal analyzed stimuli from execution params
                    from ...models.stimuli import AnalyzedStimuli, StimuliCategory
                    analyzed_stimuli = AnalyzedStimuli(
                        id=routing_decision.stimuli_id,
                        content=execution_plan.execution_params.get("stimuli_content", ""),
                        source=execution_plan.execution_params.get("stimuli_metadata", {}).get("source", "unknown"),
                        category=StimuliCategory[execution_plan.execution_params.get("category", "CONTEXTUAL_UPDATE")],
                        confidence=execution_plan.execution_params.get("confidence", 0.5)
                    )
                
                # Submit for analysis with timeout
                task_id = await asyncio.wait_for(
                    self.system2_interface.submit_for_analysis(analyzed_stimuli),
                    timeout=timeout
                )
                
                execution_time = time.time() - start_time
                
                # Record performance metrics
                self.metrics.record_node_processing_time("system2", execution_time)
                
                return ExecutionResult(
                    stimuli_id=routing_decision.stimuli_id,
                    execution_plan_id=execution_plan.id,
                    success=True,
                    results={
                        "system": "system2",
                        "action": "agent_analysis",
                        "task_id": task_id,
                        "execution_time": execution_time
                    },
                    execution_time=execution_time,
                    affected_systems=["system2"],
                    performance_metrics={
                        "agent_submission_time": execution_time,
                        "task_id": task_id
                    }
                )
                
            except asyncio.TimeoutError:
                execution_time = time.time() - start_time
                self.metrics.increment_processing_errors("System2Timeout")
                
                return ExecutionResult(
                    stimuli_id=routing_decision.stimuli_id,
                    execution_plan_id=execution_plan.id,
                    success=False,
                    results={"system": "system2", "error": "Timeout"},
                    execution_time=execution_time,
                    error_details="System2 execution timeout"
                )
            except Exception as e:
                self.logger.error(f"System2 execution failed: {e}")
                self.metrics.increment_processing_errors(f"System2_{type(e).__name__}")
                raise
    
    async def _execute_logging(
        self,
        execution_plan: ExecutionPlan,
        routing_decision: RoutingDecision
    ) -> ExecutionResult:
        """Execute logging only."""
        start_time = time.time()
        
        with MetricTimer(self.metrics, "logging_execution", record_as_node=True):
            try:
                # Log the stimuli information
                self.logger.info(
                    "Logging stimuli for future processing",
                    stimuli_id=routing_decision.stimuli_id,
                    decision=routing_decision.decision.value,
                    category=execution_plan.execution_params.get("category"),
                    confidence=execution_plan.execution_params.get("confidence"),
                    context_score=execution_plan.execution_params.get("context_score")
                )
                
                # In production, would persist to database
                # For now, just log
                
                execution_time = time.time() - start_time
                
                # Record metrics
                self.metrics.record_node_processing_time("logging", execution_time)
                
                return ExecutionResult(
                    stimuli_id=routing_decision.stimuli_id,
                    execution_plan_id=execution_plan.id,
                    success=True,
                    results={
                        "system": "logging",
                        "action": "log_only",
                        "logged_at": datetime.now().isoformat()
                    },
                    execution_time=execution_time,
                    affected_systems=["logging"],
                    performance_metrics={
                        "logging_time": execution_time
                    }
                )
                
            except Exception as e:
                self.logger.error(f"Logging execution failed: {e}")
                self.metrics.increment_processing_errors("LoggingError")
                
                return ExecutionResult(
                    stimuli_id=routing_decision.stimuli_id,
                    execution_plan_id=execution_plan.id,
                    success=False,
                    results={"system": "logging", "error": str(e)},
                    execution_time=time.time() - start_time,
                    error_details=str(e)
                )
    
    async def _handle_emergency_override(self, execution_plan: ExecutionPlan) -> ExecutionResult:
        """Handle emergency processing with override."""
        start_time = time.time()
        
        try:
            # Try to load emergency override module
            override_path = self.config.emergency_override_path
            
            if override_path:
                spec = importlib.util.spec_from_file_location(
                    "emergency_override",
                    override_path
                )
                
                if spec and spec.loader:
                    module = importlib.util.module_from_spec(spec)
                    spec.loader.exec_module(module)
                    
                    # Call the emergency handler
                    if hasattr(module, 'handle_emergency'):
                        success = await module.handle_emergency({
                            "system1_interface": self.system1_interface,
                            "system2_interface": self.system2_interface,
                            "execution_plan": execution_plan
                        })
                        
                        return ExecutionResult(
                            stimuli_id=execution_plan.stimuli_id,
                            execution_plan_id=execution_plan.id,
                            success=success,
                            results={
                                "override": "emergency",
                                "handler": "custom"
                            },
                            execution_time=time.time() - start_time
                        )
            
            # Fallback emergency handling
            self.logger.warning("Emergency override file not found, using default handling")
            
            # Execute both systems with high priority
            results = await self._execute_parallel(execution_plan, None)
            return self._aggregate_results(results, execution_plan)
            
        except Exception as e:
            self.logger.error(f"Emergency override failed: {e}")
            return ExecutionResult(
                stimuli_id=execution_plan.stimuli_id,
                execution_plan_id=execution_plan.id,
                success=False,
                results={"error": str(e)},
                execution_time=time.time() - start_time,
                error_details=f"Emergency override error: {e}"
            )
    
    def _aggregate_results(
        self,
        results: List[ExecutionResult],
        execution_plan: ExecutionPlan
    ) -> ExecutionResult:
        """Aggregate multiple execution results into a single result."""
        if not results:
            return ExecutionResult(
                stimuli_id=execution_plan.stimuli_id,
                execution_plan_id=execution_plan.id,
                success=False,
                results={"error": "No execution results"},
                execution_time=0.0
            )
        
        # Calculate overall success
        overall_success = all(r.success for r in results)
        partial_success = any(r.success for r in results) and not overall_success
        
        # Aggregate execution times
        total_time = sum(r.execution_time for r in results)
        
        # Collect all affected systems
        affected_systems = []
        for result in results:
            affected_systems.extend(result.affected_systems)
        
        # Aggregate results
        aggregated_results = {
            "executions": len(results),
            "successful": sum(1 for r in results if r.success),
            "failed": sum(1 for r in results if not r.success),
            "details": [r.results for r in results]
        }
        
        # Collect warnings
        warnings = []
        for result in results:
            warnings.extend(result.warnings)
        
        return ExecutionResult(
            stimuli_id=execution_plan.stimuli_id,
            execution_plan_id=execution_plan.id,
            success=overall_success,
            results=aggregated_results,
            execution_time=total_time,
            partial_success=partial_success,
            affected_systems=list(set(affected_systems)),
            warnings=warnings
        )
    
    async def _execute_with_retry(
        self,
        func: callable,
        execution_plan: ExecutionPlan,
        routing_decision: RoutingDecision,
        system_name: str
    ) -> ExecutionResult:
        """
        Execute a function with retry logic based on retry policies.
        
        Args:
            func: The async function to execute
            execution_plan: Execution plan with retry policies
            routing_decision: Routing decision
            system_name: Name of the system being executed
            
        Returns:
            ExecutionResult from the execution
        """
        # Find retry policy for this system
        retry_policy = None
        for policy in execution_plan.retry_policies:
            if policy.system == system_name or policy.system == "default":
                retry_policy = policy
                break
        
        if not retry_policy:
            # Create default retry policy
            retry_policy = RetryPolicy(
                system=system_name,
                max_attempts=self.config.max_retry_attempts,
                initial_delay=self.config.retry_delay
            )
        
        # Track retry attempts
        attempt_key = f"{execution_plan.id}_{system_name}"
        if attempt_key not in self._retry_attempts:
            self._retry_attempts[attempt_key] = 0
        
        last_error = None
        last_result = None
        
        for attempt in range(retry_policy.max_attempts):
            try:
                self._retry_attempts[attempt_key] = attempt + 1
                
                if attempt > 0:
                    # Calculate delay with exponential backoff
                    delay = retry_policy.calculate_delay(attempt)
                    
                    # Add jitter to prevent thundering herd
                    jitter = random.uniform(0, delay * 0.1)
                    actual_delay = delay + jitter
                    
                    self.logger.info(
                        f"Retrying {system_name} execution",
                        attempt=attempt + 1,
                        delay=actual_delay,
                        stimuli_id=routing_decision.stimuli_id
                    )
                    
                    await asyncio.sleep(actual_delay)
                
                # Execute the function
                result = await func(execution_plan, routing_decision)
                
                if result.success:
                    # Update retry count in result
                    result.retry_count = attempt
                    return result
                
                last_result = result
                last_error = result.error_details or "Unknown error"
                
                # Check if we should retry this error type
                error_type = self._extract_error_type(last_error)
                if not retry_policy.should_retry(error_type, attempt + 1):
                    self.logger.warning(
                        f"Error type {error_type} not retryable for {system_name}"
                    )
                    break
                    
            except Exception as e:
                last_error = str(e)
                error_type = type(e).__name__
                
                # Check if we should retry this exception type
                if not retry_policy.should_retry(error_type, attempt + 1):
                    self.logger.warning(
                        f"Exception type {error_type} not retryable for {system_name}"
                    )
                    break
                
                # Create a failed result for this attempt
                last_result = ExecutionResult(
                    stimuli_id=routing_decision.stimuli_id,
                    execution_plan_id=execution_plan.id,
                    success=False,
                    results={
                        "system": system_name,
                        "error": str(e),
                        "attempt": attempt + 1
                    },
                    execution_time=0.0,
                    error_details=str(e),
                    retry_count=attempt
                )
        
        # All retries exhausted
        self.logger.error(
            f"All retry attempts exhausted for {system_name}",
            attempts=self._retry_attempts[attempt_key],
            last_error=last_error,
            stimuli_id=routing_decision.stimuli_id
        )
        
        # Increment error metrics
        self.metrics.increment_processing_errors(f"{system_name}_retry_exhausted")
        
        # Return the last result with updated retry count
        if last_result:
            last_result.retry_count = self._retry_attempts[attempt_key]
            last_result.warnings.append(
                f"Execution failed after {self._retry_attempts[attempt_key]} attempts"
            )
        
        return last_result or ExecutionResult(
            stimuli_id=routing_decision.stimuli_id,
            execution_plan_id=execution_plan.id,
            success=False,
            results={
                "system": system_name,
                "error": "Retry attempts exhausted",
                "last_error": last_error
            },
            execution_time=0.0,
            error_details=f"Exhausted {self._retry_attempts[attempt_key]} retry attempts: {last_error}",
            retry_count=self._retry_attempts[attempt_key]
        )
    
    def _extract_error_type(self, error_message: str) -> str:
        """
        Extract error type from error message.
        
        Args:
            error_message: Error message string
            
        Returns:
            Extracted error type
        """
        # Common error patterns
        if "timeout" in error_message.lower():
            return "TimeoutError"
        elif "connection" in error_message.lower():
            return "ConnectionError"
        elif "unavailable" in error_message.lower():
            return "ServiceUnavailable"
        elif "http 5" in error_message.lower():
            return "ServerError"
        else:
            return "UnknownError"
    
    def _calculate_success_rate(self, result: ExecutionResult) -> float:
        """
        Calculate success rate for metrics.
        
        Args:
            result: Execution result
            
        Returns:
            Success rate as a float between 0 and 1
        """
        if result.success:
            return 1.0
        elif result.partial_success:
            # For partial success, calculate based on successful subsystems
            if isinstance(result.results, dict) and "successful" in result.results:
                total = result.results.get("executions", 1)
                successful = result.results.get("successful", 0)
                return successful / total if total > 0 else 0.0
            return 0.5  # Default partial success rate
        else:
            return 0.0