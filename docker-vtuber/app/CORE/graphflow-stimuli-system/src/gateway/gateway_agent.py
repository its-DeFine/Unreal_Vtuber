"""
GraphFlow Gateway Agent for External Stimuli Processing.

This module implements the main gateway agent that orchestrates the GraphFlow
pipeline for processing external stimuli through categorization, analysis,
routing, and execution stages.
"""

import asyncio
import time
from typing import Any, Dict, Optional, List
from datetime import datetime
import logging
from contextlib import asynccontextmanager

from autogen_agentchat.base import TaskResult
from autogen_core import SingleThreadedAgentRuntime, AgentId, MessageContext
from autogen_core import DefaultTopicId, default_subscription

from ..config.settings import GraphFlowConfig, load_config
from ..models.stimuli import ExternalStimuli, ProcessingResult
from ..models.decisions import ExecutionResult
from ..integrations.system1_interface import System1Interface
from ..integrations.system2_interface import System2Interface
from ..utils.logging import get_structured_logger
from ..utils.metrics import MetricsCollector
from .flows.stimuli_flow import StimuliFlowManager
from .flows.decision_flow import DecisionFlowManager


class MockRuntime:
    """Mock runtime for testing when AutoGen runtime is not available."""
    
    async def start(self):
        """Mock start method."""
        pass
    
    async def stop(self):
        """Mock stop method."""
        pass
    
    async def send_message(self, message, recipient):
        """Mock send_message method."""
        pass


class GraphFlowGatewayAgent:
    """
    Main gateway agent implementing GraphFlow-based stimuli processing.
    
    This agent orchestrates the entire processing pipeline from receiving
    external stimuli through categorization, analysis, routing, and execution.
    It provides integration with System1 (Avatar/Speech) and System2 (Multi-Agent)
    while maintaining monitoring, metrics, and error handling capabilities.
    """
    
    def __init__(self, config: Optional[GraphFlowConfig] = None):
        """
        Initialize gateway agent with configuration.
        
        Args:
            config: GraphFlow configuration (loads from environment if None)
        """
        self.config = config or load_config()
        self.logger = get_structured_logger("gateway_agent")
        
        # Initialize runtime for AutoGen
        self.runtime = None  # Will be initialized in start()
        
        # Initialize flow managers (runtime will be set in start())
        self.stimuli_flow_manager = StimuliFlowManager(
            config=self.config,
            runtime=None
        )
        self.decision_flow_manager = DecisionFlowManager(
            config=self.config,
            runtime=None
        )
        
        # Initialize system interfaces
        self.system1_interface = System1Interface(self.config.system1)
        self.system2_interface = System2Interface(self.config.system2)
        
        # Initialize metrics and monitoring
        self.metrics_collector = MetricsCollector(
            enabled=self.config.metrics_enabled,
            port=self.config.metrics_port
        )
        
        # Processing state
        self._active_requests = 0
        self._processing_lock = asyncio.Lock()
        self._shutdown = False
        
        self.logger.info(
            "GraphFlow Gateway Agent initialized",
            config={
                "max_concurrent_stimuli": self.config.max_concurrent_stimuli,
                "llm_provider": self.config.llm_provider,
                "llm_model": self.config.llm_model,
                "metrics_enabled": self.config.metrics_enabled
            }
        )
    
    async def start(self) -> None:
        """Start the gateway agent and initialize all components."""
        try:
            # Initialize and start the runtime
            try:
                self.runtime = SingleThreadedAgentRuntime()
                self.logger.info(f"Runtime created: {self.runtime}")
                
                if self.runtime is None:
                    self.logger.error("SingleThreadedAgentRuntime() returned None")
                    return
                
                # Set runtime for flow managers
                self.stimuli_flow_manager.runtime = self.runtime
                self.decision_flow_manager.runtime = self.runtime
                
                # Start the runtime
                await self.runtime.start()
            except Exception as e:
                self.logger.error(f"Failed to create/start runtime: {e}")
                # Create a mock runtime for now
                self.runtime = MockRuntime()
                self.stimuli_flow_manager.runtime = self.runtime
                self.decision_flow_manager.runtime = self.runtime
            
            # Initialize flow managers
            await self.stimuli_flow_manager.initialize()
            await self.decision_flow_manager.initialize()
            
            # Initialize system interfaces
            await self.system1_interface.initialize()
            try:
                await self.system2_interface.initialize()
            except Exception as e:
                self.logger.warning(f"System2 interface failed to initialize, continuing without it: {e}")
                # System2 is optional for basic operation
            
            # Start metrics collector
            if self.config.metrics_enabled:
                await self.metrics_collector.start()
            
            self.logger.info("GraphFlow Gateway Agent started successfully")
            
        except Exception as e:
            self.logger.error(
                "Failed to start GraphFlow Gateway Agent",
                error=str(e)
            )
            raise
    
    async def stop(self) -> None:
        """Stop the gateway agent and cleanup resources."""
        self._shutdown = True
        
        try:
            # Wait for active requests to complete
            timeout = 30  # seconds
            start_time = time.time()
            while self._active_requests > 0 and (time.time() - start_time) < timeout:
                await asyncio.sleep(0.1)
            
            if self._active_requests > 0:
                self.logger.warning(
                    "Forcefully stopping with active requests",
                    active_requests=self._active_requests
                )
            
            # Stop components
            await self.runtime.stop()
            await self.stimuli_flow_manager.shutdown()
            await self.decision_flow_manager.shutdown()
            await self.system1_interface.shutdown()
            await self.system2_interface.shutdown()
            
            if self.config.metrics_enabled:
                await self.metrics_collector.stop()
            
            self.logger.info("GraphFlow Gateway Agent stopped")
            
        except Exception as e:
            self.logger.error(
                "Error during shutdown",
                error=str(e)
            )
    
    @asynccontextmanager
    async def _request_context(self, stimuli_id: str):
        """Context manager for tracking active requests."""
        async with self._processing_lock:
            if self._active_requests >= self.config.max_concurrent_stimuli:
                raise RuntimeError("Maximum concurrent stimuli limit reached")
            self._active_requests += 1
        
        try:
            yield
        finally:
            async with self._processing_lock:
                self._active_requests -= 1
    
    async def process_stimuli(self, stimuli: ExternalStimuli) -> ProcessingResult:
        """
        Main entry point for stimuli processing.
        
        This method orchestrates the entire GraphFlow pipeline:
        1. Validation and preparation
        2. Categorization and analysis through stimuli flow
        3. Decision routing through decision flow
        4. Execution coordination
        5. Result aggregation and metrics
        
        Args:
            stimuli: External stimuli to process
            
        Returns:
            ProcessingResult with decisions and execution results
            
        Raises:
            ValueError: If stimuli validation fails
            RuntimeError: If processing fails or timeout occurs
        """
        if self._shutdown:
            raise RuntimeError("Gateway agent is shutting down")
        
        # Validate stimuli
        if not stimuli.validate():
            raise ValueError("Invalid stimuli data")
        
        start_time = time.time()
        
        async with self._request_context(stimuli.id):
            try:
                self.logger.info(
                    "Processing stimuli",
                    stimuli_id=stimuli.id,
                    source=stimuli.source,
                    priority=stimuli.priority.value
                )
                
                # Record metrics
                self.metrics_collector.increment_stimuli_received(
                    source=stimuli.source,
                    priority=stimuli.priority.value
                )
                
                # Process through stimuli flow (categorization + analysis)
                analyzed_stimuli = await asyncio.wait_for(
                    self.stimuli_flow_manager.process_stimuli(stimuli),
                    timeout=self.config.processing_timeout / 2  # Half timeout for analysis
                )
                
                # Process through decision flow (routing + execution planning)
                routing_decision = await asyncio.wait_for(
                    self.decision_flow_manager.process_decision(analyzed_stimuli),
                    timeout=self.config.processing_timeout / 4  # Quarter timeout for decision
                )
                
                # Store analyzed stimuli in routing decision for executor
                routing_decision.analyzed_stimuli = analyzed_stimuli
                
                # Execute the decision
                execution_results = await asyncio.wait_for(
                    self._execute_decision(routing_decision),
                    timeout=self.config.processing_timeout / 4  # Quarter timeout for execution
                )
                
                # Calculate total processing time
                processing_time = time.time() - start_time
                
                # Record metrics
                self.metrics_collector.record_processing_time(processing_time)
                self.metrics_collector.increment_stimuli_processed(
                    category=analyzed_stimuli.category.value,
                    decision=routing_decision.decision.value,
                    success=all(r.success for r in execution_results)
                )
                
                # Create processing result
                result = ProcessingResult(
                    stimuli_id=stimuli.id,
                    success=all(r.success for r in execution_results),
                    category=analyzed_stimuli.category,
                    decision=routing_decision.decision,
                    execution_results=execution_results,
                    processing_time=processing_time,
                    confidence_scores={
                        "categorization": analyzed_stimuli.confidence,
                        "routing": routing_decision.confidence_score,
                        "context": analyzed_stimuli.get_context_score()
                    },
                    metadata={
                        "reasoning": routing_decision.reasoning,
                        "override_applied": routing_decision.override_applied,
                        "analysis_timestamp": analyzed_stimuli.analysis_timestamp.isoformat()
                    }
                )
                
                self.logger.info(
                    "Stimuli processing completed",
                    stimuli_id=stimuli.id,
                    success=result.success,
                    processing_time=processing_time,
                    decision=routing_decision.decision.value
                )
                
                return result
                
            except asyncio.TimeoutError:
                self.logger.error(
                    "Stimuli processing timeout",
                    stimuli_id=stimuli.id,
                    timeout=self.config.processing_timeout
                )
                self.metrics_collector.increment_processing_errors("timeout")
                raise RuntimeError(f"Processing timeout after {self.config.processing_timeout}s")
                
            except Exception as e:
                self.logger.error(
                    "Stimuli processing failed",
                    stimuli_id=stimuli.id,
                    error=str(e),
                    error_type=type(e).__name__
                )
                self.metrics_collector.increment_processing_errors(type(e).__name__)
                raise
    
    async def _execute_decision(self, routing_decision) -> List[ExecutionResult]:
        """
        Execute the routing decision by coordinating with appropriate systems.
        
        Args:
            routing_decision: The routing decision with execution plan
            
        Returns:
            List of execution results from different systems
        """
        # Set system interfaces on executor node
        self.decision_flow_manager.executor_node.set_system_interfaces(
            self.system1_interface,
            self.system2_interface
        )
        
        # Execute through the executor node
        result = await self.decision_flow_manager.executor_node.process(routing_decision)
        
        # Return as list for consistency
        return [result]
    
    
    async def health_check(self) -> Dict[str, Any]:
        """
        Perform health check for monitoring with retry logic and timeout handling.
        
        Returns:
            Dictionary with health status information
        """
        health_status = {
            "status": "healthy",
            "timestamp": datetime.now().isoformat(),
            "active_requests": self._active_requests,
            "max_concurrent_stimuli": self.config.max_concurrent_stimuli,
            "components": {}
        }
        
        # Helper function for retryable health checks
        async def check_with_retry(check_func, component_name: str, max_retries: int = 2, timeout: float = 5.0):
            for attempt in range(max_retries + 1):
                try:
                    result = await asyncio.wait_for(check_func(), timeout=timeout)
                    return {"status": "healthy", "healthy": True, "details": result}
                except asyncio.TimeoutError:
                    if attempt == max_retries:
                        return {"status": "timeout", "healthy": False, "error": f"Health check timed out after {timeout}s"}
                    await asyncio.sleep(0.5)  # Brief delay before retry
                except Exception as e:
                    if attempt == max_retries:
                        return {"status": "unhealthy", "healthy": False, "error": str(e)}
                    await asyncio.sleep(0.5)  # Brief delay before retry
                    
        # Check System1 health with retry
        system1_result = await check_with_retry(
            self.system1_interface.get_current_status, 
            "system1"
        )
        health_status["components"]["system1"] = system1_result
        if not system1_result.get("healthy", False):
            health_status["status"] = "degraded"
        
        # Check System2 health with retry
        async def check_system2():
            status = await self.system2_interface.get_agent_status()
            return {"active_agents": len(status)} if isinstance(status, (list, dict)) else status
            
        system2_result = await check_with_retry(check_system2, "system2")
        health_status["components"]["system2"] = system2_result
        if not system2_result.get("healthy", False):
            health_status["status"] = "degraded"
        
        # Check flow managers (quick local checks)
        health_status["components"]["stimuli_flow"] = {
            "status": "healthy" if self.stimuli_flow_manager.is_initialized else "not_initialized",
            "healthy": self.stimuli_flow_manager.is_initialized
        }
        health_status["components"]["decision_flow"] = {
            "status": "healthy" if self.decision_flow_manager.is_initialized else "not_initialized", 
            "healthy": self.decision_flow_manager.is_initialized
        }
        
        # Additional runtime checks
        health_status["components"]["runtime"] = {
            "status": "healthy" if self.runtime is not None else "not_initialized",
            "healthy": self.runtime is not None
        }
        
        health_status["components"]["processing_lock"] = {
            "status": "healthy" if not self._processing_lock.locked() else "busy",
            "healthy": True,  # Lock being busy is not unhealthy
            "locked": self._processing_lock.locked()
        }
        
        return health_status
    
    async def get_metrics(self) -> Dict[str, Any]:
        """
        Get performance metrics.
        
        Returns:
            Dictionary with current metrics
        """
        return await self.metrics_collector.get_metrics()
    
    def get_status(self) -> Dict[str, Any]:
        """
        Get current gateway status.
        
        Returns:
            Dictionary with status information
        """
        return {
            "active_requests": self._active_requests,
            "shutdown_in_progress": self._shutdown,
            "config": {
                "max_concurrent_stimuli": self.config.max_concurrent_stimuli,
                "processing_timeout": self.config.processing_timeout,
                "llm_provider": self.config.llm_provider,
                "llm_model": self.config.llm_model
            }
        }


# Convenience function for creating and starting the gateway
async def create_gateway(config: Optional[GraphFlowConfig] = None) -> GraphFlowGatewayAgent:
    """
    Create and start a GraphFlow Gateway Agent.
    
    Args:
        config: Optional configuration (loads from environment if None)
        
    Returns:
        Started GraphFlowGatewayAgent instance
    """
    gateway = GraphFlowGatewayAgent(config)
    await gateway.start()
    return gateway