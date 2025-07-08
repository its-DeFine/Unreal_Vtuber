"""
System2 (Multi-Agent) Interface for GraphFlow.

This module provides the interface for integrating with System2 (multi-agent)
components, handling agent coordination, analysis tasks, and memory queries.
"""

import asyncio
from typing import Dict, Any, Optional, List
from datetime import datetime
import uuid

from ..models.stimuli import AnalyzedStimuli
from ..models.system2_models import (
    AgentStatusInfo, AgentStatus as AgentStatusEnum,
    AnalysisResult, AnalysisStatus,
    MemoryResult, EvolutionResult,
    System2Response
)
from ..config.settings import System2Config
from ..utils.logging import get_structured_logger
from .autogen_client import AutoGenClient, AgentType
from .agent_manager import AgentManager, LoadBalancingStrategy
from .cognee_client import CogneeClient, MemoryQuery, MemoryType


class System2Interface:
    """
    Interface for System2 (Multi-Agent) integration.
    
    Handles communication with:
    - AutoGen agent system
    - Cognee memory system
    - Evolution engine
    - Agent coordination
    """
    
    def __init__(self, config: System2Config):
        """
        Initialize System2 interface.
        
        Args:
            config: System2 configuration
        """
        self.config = config
        self.logger = get_structured_logger("system2_interface")
        
        # Initialize clients
        self.autogen_client = AutoGenClient(
            endpoint=config.autogen_endpoint,
            timeout=config.request_timeout,
            max_retries=config.max_retries
        )
        
        self.cognee_client = CogneeClient(
            endpoint=config.cognee_endpoint,
            api_key=config.cognee_api_key,
            timeout=config.request_timeout
        )
        
        # Initialize agent manager
        self.agent_manager = AgentManager(
            autogen_client=self.autogen_client,
            strategy=LoadBalancingStrategy(config.load_balancing_strategy),
            health_check_interval=config.health_check_interval,
            max_tasks_per_agent=config.max_tasks_per_agent
        )
        
        # Task tracking
        self._active_tasks: Dict[str, Dict[str, Any]] = {}
        self._task_lock = asyncio.Lock()
        
        self.is_initialized = False
    
    async def initialize(self) -> None:
        """Initialize the System2 interface."""
        try:
            self.logger.info("Initializing System2 interface")
            
            # Initialize agent manager (discovers agents)
            await self.agent_manager.initialize()
            
            # Verify connectivity
            if not await self.autogen_client.health_check():
                raise RuntimeError("AutoGen system health check failed")
            
            self.is_initialized = True
            self.logger.info("System2 interface initialized successfully")
            
        except Exception as e:
            self.logger.error(f"Failed to initialize System2 interface: {e}")
            await self.shutdown()
            raise
    
    async def shutdown(self) -> None:
        """Shutdown the System2 interface."""
        self.logger.info("Shutting down System2 interface")
        
        # Cancel any active tasks
        async with self._task_lock:
            for task_id in list(self._active_tasks.keys()):
                await self.autogen_client.cancel_task(task_id)
            self._active_tasks.clear()
        
        # Shutdown components
        await self.agent_manager.shutdown()
        await self.autogen_client.close()
        await self.cognee_client.close()
        
        self.is_initialized = False
    
    async def submit_for_analysis(self, stimuli: AnalyzedStimuli) -> str:
        """
        Submit stimuli to the new Stimuli-Responsive Orchestrator.
        
        Args:
            stimuli: Analyzed stimuli for agent processing
            
        Returns:
            Task ID for tracking analysis progress
        """
        if not self.is_initialized:
            raise RuntimeError("System2 interface not initialized")
        
        # Generate task ID
        task_id = str(uuid.uuid4())
        
        # Prepare payload for the new stimuli endpoint
        stimuli_data = {
            "stimuli_id": stimuli.id,
            "content": stimuli.content,
            "category": stimuli.category.value,
            "source": stimuli.source or "graphflow",
            "priority": stimuli.priority.value if hasattr(stimuli, 'priority') else "medium",
            "confidence": stimuli.confidence,
            "metadata": self._prepare_context(stimuli)
        }
        
        # Submit to the new stimuli orchestrator API
        import httpx
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{self.config.autogen_endpoint}/api/stimuli/receive",
                    json=stimuli_data,
                    timeout=30.0
                )
                
                if response.status_code == 200:
                    result = response.json()
                    
                    # Track active task
                    async with self._task_lock:
                        self._active_tasks[task_id] = {
                            "stimuli_id": stimuli.id,
                            "submitted_at": datetime.utcnow(),
                            "status": "submitted",
                            "orchestrator_response": result
                        }
                    
                    self.logger.info(
                        "Stimuli submitted to orchestrator",
                        task_id=task_id,
                        stimuli_id=stimuli.id,
                        processing_time=result.get("processing_time"),
                        tools_triggered=result.get("tools_triggered")
                    )
                    
                    return task_id
                else:
                    error_detail = response.text
                    raise RuntimeError(f"Failed to submit stimuli: HTTP {response.status_code} - {error_detail}")
                    
        except Exception as e:
            self.logger.error(
                "Failed to submit stimuli to orchestrator",
                error=str(e),
                stimuli_id=stimuli.id
            )
            raise RuntimeError(f"Failed to submit analysis: {str(e)}")
    
    async def get_agent_status(self) -> Dict[str, AgentStatusInfo]:
        """Get status of all AutoGen agents."""
        if not self.is_initialized:
            return {}
        
        # Get agent status from manager
        agent_statuses = await self.agent_manager.get_agent_status()
        
        # Convert to AgentStatusInfo objects
        result = {}
        for agent_id, status_data in agent_statuses.items():
            result[agent_id] = AgentStatusInfo(
                agent_id=agent_id,
                agent_type=status_data["agent_type"],
                status=AgentStatusEnum.ACTIVE if status_data["is_available"] else AgentStatusEnum.BUSY,
                queue_size=status_data["current_tasks"],
                performance_metrics={
                    "health_score": status_data["health_score"],
                    "success_rate": status_data["success_rate"],
                    "average_response_time": status_data["average_response_time"]
                }
            )
        
        return result
    
    async def trigger_evolution_analysis(self, stimuli: AnalyzedStimuli) -> bool:
        """Trigger evolution engine analysis if appropriate."""
        if not self.config.evolution_engine_enabled:
            return False
        
        # Check if stimuli warrants evolution analysis
        if not self._should_trigger_evolution(stimuli):
            return False
        
        context_data = {
            "stimuli_id": stimuli.id,
            "category": stimuli.category.value,
            "content": stimuli.content,
            "context_score": stimuli.get_context_score(),
            "analysis": self._prepare_context(stimuli)
        }
        
        success, evolution_id = await self.autogen_client.trigger_evolution(context_data)
        
        if success:
            self.logger.info(
                "Evolution analysis triggered",
                stimuli_id=stimuli.id,
                evolution_id=evolution_id
            )
            return True
        else:
            self.logger.warning("Evolution trigger failed")
            return False
    
    async def query_cognee_memory(self, query: str) -> List[MemoryResult]:
        """Query Cognee memory system for relevant context."""
        if not self.is_initialized:
            return []
        
        # Build memory query
        memory_query = MemoryQuery(
            query_text=query,
            memory_types=[MemoryType.EPISODIC, MemoryType.SEMANTIC, MemoryType.CONTEXTUAL],
            relevance_threshold=0.5,
            max_results=10,
            include_metadata=True
        )
        
        # Query memories
        memory_items = await self.cognee_client.query_memories(memory_query)
        
        # Convert to MemoryResult objects
        memory_results = [
            MemoryResult(
                memory_id=item.id,
                content=item.content,
                relevance=item.relevance_score,
                memory_type=item.memory_type.value,
                timestamp=item.timestamp,
                metadata=item.metadata,
                related_memories=item.related_memories
            )
            for item in memory_items
        ]
        
        self.logger.info(
            f"Memory query returned {len(memory_results)} results",
            query=query[:50]
        )
        
        return memory_results
    
    async def get_task_status(self, task_id: str) -> Dict[str, Any]:
        """Get status of a submitted analysis task."""
        async with self._task_lock:
            if task_id not in self._active_tasks:
                return {"status": "unknown", "error": "Task not found"}
        
        if not self.is_initialized:
            return {"status": "error", "error": "Interface not initialized"}
        
        success, status_data = await self.autogen_client.get_task_status(task_id)
        
        if success:
            # Update local tracking
            async with self._task_lock:
                if task_id in self._active_tasks:
                    self._active_tasks[task_id]["status"] = status_data.get("status")
            
            return status_data
        else:
            return {"status": "error", "error": status_data.get("error", "Unknown error")}
    
    async def get_task_result(self, task_id: str) -> Optional[AnalysisResult]:
        """
        Get the result of a completed task.
        
        Args:
            task_id: Task ID to retrieve result for
            
        Returns:
            AnalysisResult if available, None otherwise
        """
        async with self._task_lock:
            if task_id not in self._active_tasks:
                return None
            task_info = self._active_tasks[task_id]
        
        success, result_data = await self.autogen_client.get_task_result(task_id)
        
        if success and result_data.get("status") == "completed":
            # Update agent metrics
            processing_time = result_data.get("processing_time", 0.0)
            await self.agent_manager.complete_task(
                task_id,
                success=True,
                response_time=processing_time
            )
            
            # Create AnalysisResult
            analysis_result = AnalysisResult(
                task_id=task_id,
                stimuli_id=task_info["stimuli_id"],
                status=AnalysisStatus.COMPLETED,
                agent_id=task_info["agent_id"],
                analysis_type=result_data.get("analysis_type", "general"),
                results=result_data.get("results", {}),
                recommendations=result_data.get("recommendations", []),
                confidence_score=result_data.get("confidence", 0.0),
                processing_time=processing_time,
                metadata=result_data.get("metadata", {})
            )
            
            # Clean up task
            async with self._task_lock:
                self._active_tasks.pop(task_id, None)
            
            return analysis_result
        
        return None
    
    async def get_comprehensive_response(self, stimuli_id: str) -> System2Response:
        """
        Get comprehensive response for a stimuli including all analysis results.
        
        Args:
            stimuli_id: ID of the stimuli
            
        Returns:
            System2Response with all available results
        """
        response = System2Response(stimuli_id=stimuli_id)
        
        # Collect all task results for this stimuli
        async with self._task_lock:
            stimuli_tasks = [
                task_id for task_id, info in self._active_tasks.items()
                if info["stimuli_id"] == stimuli_id
            ]
        
        # Get analysis results
        for task_id in stimuli_tasks:
            result = await self.get_task_result(task_id)
            if result:
                response.analysis_results.append(result)
        
        # Get agent statuses
        response.agent_statuses = await self.get_agent_status()
        
        # Query relevant memories
        memory_results = await self.query_cognee_memory(
            f"context for stimuli {stimuli_id}"
        )
        response.memory_results = memory_results
        
        return response
    
    def _get_required_capabilities(self, stimuli: AnalyzedStimuli) -> List[str]:
        """Determine required agent capabilities based on stimuli."""
        capabilities = []
        
        # Category-based capabilities
        if stimuli.category.value == "DIRECT_ADMIN":
            capabilities.append("admin_commands")
        elif stimuli.category.value == "USER_INTERACTION":
            capabilities.append("conversation")
        elif stimuli.category.value == "AUTONOMOUS_TRIGGER":
            capabilities.append("autonomous_reasoning")
        
        # Context-based capabilities
        if stimuli.user_context_analysis and stimuli.user_context_analysis.engagement_level == "high":
            capabilities.append("deep_analysis")
        
        return capabilities
    
    def _prepare_context(self, stimuli: AnalyzedStimuli) -> Dict[str, Any]:
        """Prepare context information for agent processing."""
        context = {
            "category": stimuli.category.value,
            "confidence": stimuli.confidence,
            "analysis_timestamp": stimuli.analysis_timestamp.isoformat()
        }
        
        # Add system state if available
        if stimuli.system_state_analysis:
            context["system_state"] = {
                "is_speaking": stimuli.system_state_analysis.is_speaking,
                "is_idle": stimuli.system_state_analysis.is_idle,
                "availability_score": stimuli.system_state_analysis.availability_score
            }
        
        # Add user context if available
        if stimuli.user_context_analysis:
            context["user_context"] = {
                "engagement_level": stimuli.user_context_analysis.engagement_level,
                "interaction_frequency": stimuli.user_context_analysis.interaction_frequency,
                "recent_topics": stimuli.user_context_analysis.recent_topics
            }
        
        # Add environmental context if available
        if stimuli.environmental_analysis:
            context["environment"] = {
                "autonomous_mode": stimuli.environmental_analysis.autonomous_mode_active,
                "streaming_status": stimuli.environmental_analysis.streaming_status,
                "recent_activity": stimuli.environmental_analysis.recent_activity_level
            }
        
        # Add resource analysis if available
        if stimuli.resource_analysis:
            context["resources"] = {
                "cpu_availability": stimuli.resource_analysis.cpu_availability,
                "memory_availability": stimuli.resource_analysis.memory_availability,
                "processing_capacity": stimuli.resource_analysis.estimated_processing_capacity
            }
        
        return context
    
    def _should_trigger_evolution(self, stimuli: AnalyzedStimuli) -> bool:
        """Determine if stimuli should trigger evolution analysis."""
        # Trigger evolution for high-value interactions
        if stimuli.category.value in ["DIRECT_ADMIN", "USER_INTERACTION"]:
            if stimuli.confidence > 0.8 and stimuli.get_context_score() > 0.7:
                return True
        
        # Trigger for autonomous mode discoveries
        if stimuli.category.value == "AUTONOMOUS_TRIGGER":
            return True
        
        # Check user engagement
        if (stimuli.user_context_analysis and 
            stimuli.user_context_analysis.engagement_level == "high"):
            return True
        
        return False