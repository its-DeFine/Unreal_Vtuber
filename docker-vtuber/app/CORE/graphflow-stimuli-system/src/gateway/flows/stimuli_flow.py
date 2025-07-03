"""
Stimuli Flow Manager for GraphFlow Pipeline.

This module manages the stimuli processing flow through categorization
and analysis nodes, coordinating their execution and handling state management.
"""

import asyncio
from typing import Optional, Dict, Any, List
from datetime import datetime
import uuid

from autogen_core.application import SingleThreadedAgentRuntime
from autogen_core.base import AgentId, MessageContext, CancellationToken
from autogen_core.components import DefaultTopicId, default_subscription

from ...config.settings import GraphFlowConfig
from ...models.stimuli import (
    ExternalStimuli, 
    CategorizedStimuli, 
    AnalyzedStimuli,
    StimuliCategory
)
from ...models.context import (
    SystemStateAnalysis,
    UserContextAnalysis,
    EnvironmentalAnalysis,
    ResourceAnalysis,
    ProcessingContext
)
from ...utils.logging import get_structured_logger
from ..nodes.categorizer_node import StimuliCategorizerNode
from ..nodes.analyzer_node import ContextAnalyzerNode


class StimuliFlowManager:
    """
    Manages the stimuli processing flow through GraphFlow pipeline.
    
    This manager coordinates the execution of categorization and analysis
    nodes, handles flow state management, and implements parallel processing
    where appropriate.
    """
    
    def __init__(self, config: GraphFlowConfig, runtime: SingleThreadedAgentRuntime):
        """
        Initialize the stimuli flow manager.
        
        Args:
            config: GraphFlow configuration
            runtime: AutoGen runtime for agent management
        """
        self.config = config
        self.runtime = runtime
        self.logger = get_structured_logger("stimuli_flow_manager")
        
        # Initialize nodes
        self.categorizer_node = StimuliCategorizerNode(
            config=config.categorizer,
            llm_config={
                "provider": config.llm_provider,
                "model": config.llm_model,
                "endpoint": config.llm_endpoint,
                "temperature": config.llm_temperature,
                "api_key": config.llm_api_key
            }
        )
        
        self.analyzer_node = ContextAnalyzerNode(
            config=config.analyzer
        )
        
        # Flow state management
        self._flow_states: Dict[str, Dict[str, Any]] = {}
        self._state_lock = asyncio.Lock()
        self.is_initialized = False
        
        # Performance tracking
        self._processing_times: Dict[str, Dict[str, float]] = {}
    
    async def initialize(self) -> None:
        """Initialize the flow manager and its nodes."""
        try:
            self.logger.info("Initializing stimuli flow manager")
            
            # Initialize nodes
            await self.categorizer_node.initialize()
            await self.analyzer_node.initialize()
            
            # Register nodes with runtime if needed
            # This would depend on specific AutoGen requirements
            
            self.is_initialized = True
            self.logger.info("Stimuli flow manager initialized successfully")
            
        except Exception as e:
            self.logger.error(
                "Failed to initialize stimuli flow manager",
                error=str(e)
            )
            raise
    
    async def shutdown(self) -> None:
        """Shutdown the flow manager and cleanup resources."""
        try:
            self.logger.info("Shutting down stimuli flow manager")
            
            # Shutdown nodes
            await self.categorizer_node.shutdown()
            await self.analyzer_node.shutdown()
            
            # Clear flow states
            async with self._state_lock:
                self._flow_states.clear()
                self._processing_times.clear()
            
            self.is_initialized = False
            self.logger.info("Stimuli flow manager shutdown complete")
            
        except Exception as e:
            self.logger.error(
                "Error during stimuli flow manager shutdown",
                error=str(e)
            )
    
    async def process_stimuli(self, stimuli: ExternalStimuli) -> AnalyzedStimuli:
        """
        Process stimuli through the categorization and analysis flow.
        
        This method orchestrates the flow:
        1. Initialize flow state
        2. Categorize the stimuli
        3. Analyze context (potentially in parallel)
        4. Aggregate results
        
        Args:
            stimuli: External stimuli to process
            
        Returns:
            AnalyzedStimuli with categorization and context analysis
            
        Raises:
            RuntimeError: If flow processing fails
        """
        if not self.is_initialized:
            raise RuntimeError("Stimuli flow manager not initialized")
        
        flow_id = f"flow_{stimuli.id}"
        start_time = datetime.now()
        
        try:
            # Initialize flow state
            await self._init_flow_state(flow_id, stimuli)
            
            self.logger.info(
                "Starting stimuli flow processing",
                flow_id=flow_id,
                stimuli_id=stimuli.id,
                source=stimuli.source
            )
            
            # Step 1: Categorization
            categorized_stimuli = await self._categorize_stimuli(flow_id, stimuli)
            
            # Step 2: Context Analysis
            # For deep analysis or high-priority items, run analyses in parallel
            if (self.config.analyzer.analysis_depth.value == "deep" or 
                stimuli.priority.value in ["high", "critical", "emergency"]):
                analyzed_stimuli = await self._parallel_context_analysis(
                    flow_id, categorized_stimuli
                )
            else:
                analyzed_stimuli = await self._sequential_context_analysis(
                    flow_id, categorized_stimuli
                )
            
            # Update flow state with results
            await self._update_flow_state(flow_id, {
                "status": "completed",
                "result": analyzed_stimuli,
                "end_time": datetime.now()
            })
            
            # Record processing times
            end_time = datetime.now()
            processing_time = (end_time - start_time).total_seconds()
            self._processing_times[stimuli.id] = {
                "total": processing_time,
                "categorization": self._processing_times.get(f"{stimuli.id}_cat", 0),
                "analysis": self._processing_times.get(f"{stimuli.id}_ana", 0)
            }
            
            self.logger.info(
                "Stimuli flow processing completed",
                flow_id=flow_id,
                stimuli_id=stimuli.id,
                category=analyzed_stimuli.category.value,
                confidence=analyzed_stimuli.confidence,
                context_score=analyzed_stimuli.get_context_score(),
                processing_time=processing_time
            )
            
            return analyzed_stimuli
            
        except Exception as e:
            self.logger.error(
                "Stimuli flow processing failed",
                flow_id=flow_id,
                stimuli_id=stimuli.id,
                error=str(e)
            )
            
            # Update flow state with error
            await self._update_flow_state(flow_id, {
                "status": "failed",
                "error": str(e),
                "end_time": datetime.now()
            })
            
            raise RuntimeError(f"Flow processing failed: {str(e)}")
        
        finally:
            # Cleanup flow state after a delay
            asyncio.create_task(self._cleanup_flow_state(flow_id))
    
    async def _init_flow_state(self, flow_id: str, stimuli: ExternalStimuli) -> None:
        """Initialize flow state for tracking."""
        async with self._state_lock:
            self._flow_states[flow_id] = {
                "stimuli_id": stimuli.id,
                "status": "processing",
                "start_time": datetime.now(),
                "stages": {
                    "categorization": "pending",
                    "analysis": "pending"
                }
            }
    
    async def _update_flow_state(self, flow_id: str, updates: Dict[str, Any]) -> None:
        """Update flow state with new information."""
        async with self._state_lock:
            if flow_id in self._flow_states:
                self._flow_states[flow_id].update(updates)
    
    async def _cleanup_flow_state(self, flow_id: str, delay: int = 300) -> None:
        """Cleanup flow state after a delay (default 5 minutes)."""
        await asyncio.sleep(delay)
        async with self._state_lock:
            if flow_id in self._flow_states:
                del self._flow_states[flow_id]
    
    async def _categorize_stimuli(
        self, 
        flow_id: str, 
        stimuli: ExternalStimuli
    ) -> CategorizedStimuli:
        """Categorize stimuli using the categorizer node."""
        start_time = datetime.now()
        
        try:
            await self._update_flow_state(flow_id, {
                "stages": {"categorization": "processing"}
            })
            
            categorized = await self.categorizer_node.process(stimuli)
            
            # Track processing time
            cat_time = (datetime.now() - start_time).total_seconds()
            self._processing_times[f"{stimuli.id}_cat"] = cat_time
            
            await self._update_flow_state(flow_id, {
                "stages": {"categorization": "completed"},
                "category": categorized.category.value,
                "categorization_confidence": categorized.confidence
            })
            
            return categorized
            
        except Exception as e:
            await self._update_flow_state(flow_id, {
                "stages": {"categorization": "failed"}
            })
            raise
    
    async def _sequential_context_analysis(
        self,
        flow_id: str,
        categorized_stimuli: CategorizedStimuli
    ) -> AnalyzedStimuli:
        """Perform context analysis sequentially."""
        start_time = datetime.now()
        
        try:
            await self._update_flow_state(flow_id, {
                "stages": {"analysis": "processing"}
            })
            
            analyzed = await self.analyzer_node.process(categorized_stimuli)
            
            # Track processing time
            ana_time = (datetime.now() - start_time).total_seconds()
            self._processing_times[f"{categorized_stimuli.id}_ana"] = ana_time
            
            await self._update_flow_state(flow_id, {
                "stages": {"analysis": "completed"},
                "context_score": analyzed.get_context_score()
            })
            
            return analyzed
            
        except Exception as e:
            await self._update_flow_state(flow_id, {
                "stages": {"analysis": "failed"}
            })
            raise
    
    async def _parallel_context_analysis(
        self,
        flow_id: str,
        categorized_stimuli: CategorizedStimuli
    ) -> AnalyzedStimuli:
        """
        Perform context analysis in parallel for faster processing.
        
        This method runs different analysis components concurrently:
        - System state analysis
        - User context analysis  
        - Environmental analysis
        - Resource analysis
        """
        start_time = datetime.now()
        
        try:
            await self._update_flow_state(flow_id, {
                "stages": {"analysis": "processing_parallel"}
            })
            
            # Create analysis tasks
            tasks = [
                self.analyzer_node._analyze_system_state(),
                self.analyzer_node._analyze_user_context(categorized_stimuli),
                self.analyzer_node._analyze_environmental_context(),
                self.analyzer_node._analyze_resource_availability()
            ]
            
            # Run analyses in parallel
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            # Check for exceptions
            for i, result in enumerate(results):
                if isinstance(result, Exception):
                    self.logger.warning(
                        f"Analysis component {i} failed",
                        error=str(result)
                    )
                    # Replace with default/fallback analysis
                    if i == 0:  # System state
                        results[i] = SystemStateAnalysis(
                            is_speaking=False,
                            is_idle=True,
                            is_busy=False,
                            has_errors=False,
                            queue_size=0,
                            resource_utilization={},
                            availability_score=0.5
                        )
                    elif i == 1:  # User context
                        results[i] = UserContextAnalysis(
                            interaction_frequency=0.0,
                            engagement_level="medium",
                            recent_topics=[],
                            user_preference_match=0.5,
                            historical_response_patterns={}
                        )
                    elif i == 2:  # Environmental
                        results[i] = EnvironmentalAnalysis(
                            autonomous_mode_active=False,
                            streaming_status="unknown",
                            time_of_day_factor=0.5,
                            recent_activity_level="medium",
                            external_event_context={}
                        )
                    elif i == 3:  # Resource
                        results[i] = ResourceAnalysis(
                            cpu_availability=0.5,
                            memory_availability=0.5,
                            agent_availability={},
                            system1_availability=True,
                            system2_availability=True,
                            estimated_processing_capacity=10
                        )
            
            # Create analyzed stimuli with parallel results
            analyzed = AnalyzedStimuli(
                **categorized_stimuli.__dict__,
                system_state_analysis=results[0],
                user_context_analysis=results[1],
                environmental_analysis=results[2],
                resource_analysis=results[3],
                analysis_timestamp=datetime.now(),
                processing_context=ProcessingContext(
                    flow_id=flow_id,
                    parallel_analysis=True,
                    analysis_depth=self.config.analyzer.analysis_depth.value
                )
            )
            
            # Track processing time
            ana_time = (datetime.now() - start_time).total_seconds()
            self._processing_times[f"{categorized_stimuli.id}_ana"] = ana_time
            
            await self._update_flow_state(flow_id, {
                "stages": {"analysis": "completed"},
                "context_score": analyzed.get_context_score(),
                "parallel_analysis": True
            })
            
            return analyzed
            
        except Exception as e:
            await self._update_flow_state(flow_id, {
                "stages": {"analysis": "failed"}
            })
            raise
    
    def get_flow_state(self, flow_id: str) -> Optional[Dict[str, Any]]:
        """Get current state of a flow."""
        return self._flow_states.get(flow_id)
    
    def get_active_flows(self) -> List[str]:
        """Get list of currently active flow IDs."""
        return list(self._flow_states.keys())
    
    def get_processing_metrics(self, stimuli_id: str) -> Optional[Dict[str, float]]:
        """Get processing time metrics for a stimuli."""
        return self._processing_times.get(stimuli_id)