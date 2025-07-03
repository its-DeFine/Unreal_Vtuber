"""
Decision and execution models for GraphFlow stimuli processing.

This module defines data models for processing decisions, execution plans,
execution results, and retry policies.
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional
import uuid


class ProcessingDecision(Enum):
    """
    Processing decision options for stimuli.
    
    Defines the available processing paths that can be chosen
    by the decision router based on context and rules.
    """
    
    AVATAR_AND_ANALYSIS = "avatar_and_analysis"
    """Execute both avatar response and agent analysis concurrently."""
    
    ANALYSIS_ONLY = "analysis_only"
    """Execute agent analysis only, no avatar response."""
    
    LOG_ONLY = "log_only"
    """Log and store the stimuli without processing."""
    
    EMERGENCY_OVERRIDE = "emergency_override"
    """Emergency processing with immediate priority."""
    
    DEFERRED = "deferred"
    """Defer processing to a later time."""
    
    REJECTED = "rejected"
    """Reject the stimuli without processing."""


class ExecutionPriority(Enum):
    """Execution priority levels."""
    
    CRITICAL = "critical"
    """Critical priority - execute immediately."""
    
    HIGH = "high"
    """High priority - execute as soon as possible."""
    
    NORMAL = "normal"
    """Normal priority - standard execution."""
    
    LOW = "low"
    """Low priority - can be delayed."""
    
    BACKGROUND = "background"
    """Background priority - execute when resources available."""


@dataclass
class RetryPolicy:
    """
    Retry policy configuration for failed operations.
    
    Defines how and when to retry failed processing operations.
    """
    
    system: str = "default"
    """System this retry policy applies to."""
    
    max_attempts: int = 3
    """Maximum number of retry attempts."""
    
    initial_delay: float = 1.0
    """Initial delay between retries in seconds."""
    
    exponential_base: float = 2.0
    """Exponential backoff base for retry delays."""
    
    max_delay: float = 60.0
    """Maximum delay between retries in seconds."""
    
    retry_on_errors: List[str] = field(default_factory=lambda: [
        "TimeoutError", "ConnectionError", "ServiceUnavailable"
    ])
    """List of error types that should trigger retries."""
    
    def calculate_delay(self, attempt: int) -> float:
        """
        Calculate delay for a given retry attempt.
        
        Args:
            attempt: The retry attempt number (1-based).
            
        Returns:
            float: Delay in seconds before the retry.
        """
        if attempt <= 0:
            return 0.0
            
        delay = self.initial_delay * (self.exponential_base ** (attempt - 1))
        return min(delay, self.max_delay)
    
    def should_retry(self, error_type: str, attempt: int) -> bool:
        """
        Determine if an operation should be retried.
        
        Args:
            error_type: Type of error that occurred.
            attempt: Current attempt number.
            
        Returns:
            bool: True if should retry.
        """
        return (
            attempt < self.max_attempts and
            error_type in self.retry_on_errors
        )


@dataclass
class ExecutionPlan:
    """
    Detailed execution plan for processing decision.
    
    Provides a comprehensive plan for executing the chosen processing
    decision including target systems, ordering, and success criteria.
    """
    
    id: str
    """Unique identifier for the execution plan."""
    
    stimuli_id: str
    """ID of the stimuli being processed."""
    
    decision: ProcessingDecision
    """The processing decision to execute."""
    
    target_systems: List[str]
    """List of target systems to engage (e.g., 'system1', 'system2')."""
    
    execution_order: List[str]
    """Execution order strategy: 'sequential', 'parallel', 'priority'."""
    
    timeout_settings: Dict[str, float] = field(default_factory=dict)
    """Timeout settings for each operation in seconds."""
    
    retry_policies: List[RetryPolicy] = field(default_factory=list)
    """Retry policies for each operation."""
    
    priority: ExecutionPriority = ExecutionPriority.NORMAL
    """Execution priority level."""
    
    parallel_execution: bool = False
    """Whether to execute target systems in parallel."""
    
    execution_params: Dict[str, Any] = field(default_factory=dict)
    """Parameters for execution (e.g., avatar content, metadata)."""
    
    dependencies: List[str] = field(default_factory=list)
    """List of execution plan IDs this plan depends on."""
    
    metadata: Dict[str, Any] = field(default_factory=dict)
    """Additional metadata for execution."""
    
    created_at: datetime = field(default_factory=datetime.now)
    """Timestamp when the plan was created."""
    
    def __post_init__(self):
        """Validate execution plan data."""
        valid_execution_orders = {"sequential", "parallel", "priority"}
        for order in self.execution_order:
            if order not in valid_execution_orders:
                raise ValueError(
                    f"Execution order must be one of {valid_execution_orders}, got {order}"
                )
        
        # Validate that at least one target system is specified
        if not self.target_systems:
            raise ValueError("At least one target system must be specified")
    
    def get_total_timeout(self) -> float:
        """
        Calculate total timeout for the execution plan.
        
        Returns:
            float: Total timeout in seconds.
        """
        if "parallel" in self.execution_order:
            # For parallel execution, use the maximum timeout
            return max(self.timeout_settings.values()) if self.timeout_settings else 30.0
        else:
            # For sequential execution, sum all timeouts
            return sum(self.timeout_settings.values()) if self.timeout_settings else 30.0
    
    def to_dict(self) -> Dict[str, Any]:
        """
        Convert to dictionary for serialization.
        
        Returns:
            Dict[str, Any]: Dictionary representation.
        """
        return {
            "id": self.id,
            "stimuli_id": self.stimuli_id,
            "decision": self.decision.value,
            "target_systems": self.target_systems,
            "execution_order": self.execution_order,
            "timeout_settings": self.timeout_settings,
            "retry_policies": [
                {
                    "system": policy.system,
                    "max_attempts": policy.max_attempts,
                    "initial_delay": policy.initial_delay,
                    "exponential_base": policy.exponential_base,
                    "max_delay": policy.max_delay,
                    "retry_on_errors": policy.retry_on_errors
                }
                for policy in self.retry_policies
            ],
            "priority": self.priority.value,
            "parallel_execution": self.parallel_execution,
            "execution_params": self.execution_params,
            "dependencies": self.dependencies,
            "metadata": self.metadata,
            "created_at": self.created_at.isoformat()
        }


@dataclass
class ExecutionResult:
    """
    Result of execution.
    
    Captures the outcome of executing a processing decision
    including success status, results, and performance metrics.
    """
    
    stimuli_id: str
    """ID of the processed stimuli."""
    
    execution_plan_id: str
    """ID of the execution plan that was executed."""
    
    success: bool
    """Whether the execution was successful."""
    
    results: Dict[str, Any]
    """Detailed results from the execution."""
    
    execution_time: float
    """Total execution time in seconds."""
    
    timestamp: datetime = field(default_factory=datetime.now)
    """Timestamp when execution completed."""
    
    error_details: Optional[str] = None
    """Details about any errors that occurred."""
    
    performance_metrics: Dict[str, float] = field(default_factory=dict)
    """Performance metrics from the execution."""
    
    retry_count: int = 0
    """Number of retries that were attempted."""
    
    partial_success: bool = False
    """Whether execution was partially successful."""
    
    affected_systems: List[str] = field(default_factory=list)
    """List of systems that were affected by the execution."""
    
    warnings: List[str] = field(default_factory=list)
    """Any warnings generated during execution."""
    
    def is_complete_success(self) -> bool:
        """
        Check if execution was completely successful.
        
        Returns:
            bool: True if fully successful with no warnings.
        """
        return self.success and not self.partial_success and not self.warnings
    
    def get_error_summary(self) -> Optional[str]:
        """
        Get a summary of the error if execution failed.
        
        Returns:
            Optional[str]: Error summary or None if successful.
        """
        if not self.success and self.error_details:
            # Extract first line or up to 100 characters
            error_lines = self.error_details.split('\n')
            return error_lines[0][:100] + "..." if len(error_lines[0]) > 100 else error_lines[0]
        return None
    
    def to_dict(self) -> Dict[str, Any]:
        """
        Convert to dictionary for serialization.
        
        Returns:
            Dict[str, Any]: Dictionary representation.
        """
        return {
            "stimuli_id": self.stimuli_id,
            "execution_plan_id": self.execution_plan_id,
            "success": self.success,
            "results": self.results,
            "execution_time": self.execution_time,
            "timestamp": self.timestamp.isoformat(),
            "error_details": self.error_details,
            "performance_metrics": self.performance_metrics,
            "retry_count": self.retry_count,
            "partial_success": self.partial_success,
            "affected_systems": self.affected_systems,
            "warnings": self.warnings
        }


@dataclass
class ProcessingResult:
    """
    Overall result of stimuli processing.
    
    Aggregates all execution results and provides a complete view
    of the stimuli processing outcome.
    """
    
    stimuli_id: str
    """ID of the processed stimuli."""
    
    routing_decision: ProcessingDecision
    """The routing decision that was made."""
    
    execution_results: List[ExecutionResult]
    """List of execution results from all operations."""
    
    total_processing_time: float
    """Total time taken for all processing in seconds."""
    
    success: bool = False
    """Overall success status."""
    
    processing_stages: Dict[str, Dict[str, Any]] = field(default_factory=dict)
    """Details about each processing stage."""
    
    metadata: Dict[str, Any] = field(default_factory=dict)
    """Additional processing metadata."""
    
    created_at: datetime = field(default_factory=datetime.now)
    """Timestamp when processing started."""
    
    completed_at: Optional[datetime] = None
    """Timestamp when processing completed."""
    
    def __post_init__(self):
        """Calculate overall success if not provided."""
        if not self.success and self.execution_results:
            # Consider successful if all critical executions succeeded
            self.success = all(
                result.success or result.partial_success 
                for result in self.execution_results
            )
        
        # Set completed timestamp if not provided
        if self.completed_at is None and self.execution_results:
            self.completed_at = datetime.now()
    
    def get_failed_operations(self) -> List[ExecutionResult]:
        """
        Get list of failed execution operations.
        
        Returns:
            List[ExecutionResult]: Failed execution results.
        """
        return [
            result for result in self.execution_results 
            if not result.success and not result.partial_success
        ]
    
    def get_success_rate(self) -> float:
        """
        Calculate success rate of executions.
        
        Returns:
            float: Success rate from 0.0 to 1.0.
        """
        if not self.execution_results:
            return 0.0
            
        successful = sum(
            1 for result in self.execution_results 
            if result.success or result.partial_success
        )
        return successful / len(self.execution_results)
    
    def to_dict(self) -> Dict[str, Any]:
        """
        Convert to dictionary for serialization.
        
        Returns:
            Dict[str, Any]: Dictionary representation.
        """
        return {
            "stimuli_id": self.stimuli_id,
            "routing_decision": self.routing_decision.value,
            "execution_results": [
                result.to_dict() for result in self.execution_results
            ],
            "total_processing_time": self.total_processing_time,
            "success": self.success,
            "success_rate": self.get_success_rate(),
            "processing_stages": self.processing_stages,
            "metadata": self.metadata,
            "created_at": self.created_at.isoformat(),
            "completed_at": self.completed_at.isoformat() if self.completed_at else None
        }