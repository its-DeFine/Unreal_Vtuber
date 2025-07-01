"""
Main pipeline system for NeuroSync Player.
Provides a unified execution path for all processing modes.
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, List, Callable
from dataclasses import dataclass, field
import asyncio
import logging
from enum import Enum
import time


logger = logging.getLogger(__name__)


class Priority(Enum):
    """Action priority levels"""
    LOW = 1
    MEDIUM = 2
    HIGH = 3
    URGENT = 4
    CRITICAL = 5


@dataclass
class PipelineContext:
    """Unified context object passed through pipeline stages"""
    user_input: str
    request_metadata: Dict[str, Any] = field(default_factory=dict)
    autonomous_context: Optional[str] = None
    priority: Priority = Priority.MEDIUM
    processing_mode: str = "standard"  # standard, direct_speech, orchestrated
    provider_preferences: Dict[str, str] = field(default_factory=dict)
    
    # Results from various stages
    llm_response: Optional[str] = None
    audio_data: Optional[bytes] = None
    facial_data: Optional[List[List[float]]] = None
    
    # Timing information
    timestamps: Dict[str, float] = field(default_factory=dict)
    
    # Additional context
    session_id: Optional[str] = None
    interrupt_requested: bool = False
    error: Optional[Exception] = None
    
    def add_timestamp(self, stage_name: str) -> None:
        """Add timestamp for a stage"""
        self.timestamps[stage_name] = time.time()
        
    def get_duration(self, start_stage: str, end_stage: str) -> Optional[float]:
        """Get duration between two stages"""
        if start_stage in self.timestamps and end_stage in self.timestamps:
            return self.timestamps[end_stage] - self.timestamps[start_stage]
        return None


class PipelineStage(ABC):
    """Base class for all pipeline stages"""
    
    def __init__(self, name: str):
        self.name = name
        self.logger = logging.getLogger(f"{__name__}.{name}")
        
    @abstractmethod
    async def process(self, context: PipelineContext) -> PipelineContext:
        """
        Process the context and return modified context.
        Should handle errors gracefully and set context.error if needed.
        """
        pass
        
    async def __call__(self, context: PipelineContext) -> PipelineContext:
        """Execute the stage with logging and timing"""
        self.logger.debug(f"Starting stage: {self.name}")
        context.add_timestamp(f"{self.name}_start")
        
        try:
            result = await self.process(context)
            context.add_timestamp(f"{self.name}_end")
            duration = context.get_duration(f"{self.name}_start", f"{self.name}_end")
            self.logger.debug(f"Completed stage: {self.name} (duration: {duration:.3f}s)")
            return result
        except Exception as e:
            self.logger.error(f"Error in stage {self.name}: {e}")
            context.error = e
            context.add_timestamp(f"{self.name}_error")
            raise


class ConditionalStage(PipelineStage):
    """A stage that only executes if a condition is met"""
    
    def __init__(self, name: str, stage: PipelineStage, condition: Callable[[PipelineContext], bool]):
        super().__init__(name)
        self.stage = stage
        self.condition = condition
        
    async def process(self, context: PipelineContext) -> PipelineContext:
        if self.condition(context):
            return await self.stage.process(context)
        else:
            self.logger.debug(f"Skipping stage {self.name} - condition not met")
            return context


class ParallelStage(PipelineStage):
    """A stage that executes multiple stages in parallel"""
    
    def __init__(self, name: str, stages: List[PipelineStage]):
        super().__init__(name)
        self.stages = stages
        
    async def process(self, context: PipelineContext) -> PipelineContext:
        # Create tasks for all stages
        tasks = [stage.process(context) for stage in self.stages]
        
        # Wait for all to complete
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Check for errors
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                self.logger.error(f"Error in parallel stage {self.stages[i].name}: {result}")
                context.error = result
                
        return context


class NeuroSyncPipeline:
    """Main pipeline orchestrating all processing stages"""
    
    def __init__(self, state_manager=None, orchestrator=None):
        self.stages: List[PipelineStage] = []
        self.state_manager = state_manager
        self.orchestrator = orchestrator
        self.logger = logging.getLogger(__name__)
        self._before_hooks: List[Callable] = []
        self._after_hooks: List[Callable] = []
        self._error_handlers: List[Callable] = []
        
    def add_stage(self, stage: PipelineStage) -> 'NeuroSyncPipeline':
        """Add a processing stage to the pipeline"""
        self.stages.append(stage)
        return self
        
    def add_conditional_stage(self, 
                            stage: PipelineStage,
                            condition: Callable[[PipelineContext], bool],
                            name: Optional[str] = None) -> 'NeuroSyncPipeline':
        """Add a stage that only executes if condition is met"""
        conditional_name = name or f"conditional_{stage.name}"
        conditional_stage = ConditionalStage(conditional_name, stage, condition)
        self.stages.append(conditional_stage)
        return self
        
    def add_parallel_stages(self, 
                          stages: List[PipelineStage],
                          name: str = "parallel") -> 'NeuroSyncPipeline':
        """Add stages that execute in parallel"""
        parallel_stage = ParallelStage(name, stages)
        self.stages.append(parallel_stage)
        return self
        
    def add_before_hook(self, hook: Callable[[PipelineContext], None]) -> 'NeuroSyncPipeline':
        """Add a hook to run before pipeline execution"""
        self._before_hooks.append(hook)
        return self
        
    def add_after_hook(self, hook: Callable[[PipelineContext], None]) -> 'NeuroSyncPipeline':
        """Add a hook to run after pipeline execution"""
        self._after_hooks.append(hook)
        return self
        
    def add_error_handler(self, handler: Callable[[PipelineContext, Exception], None]) -> 'NeuroSyncPipeline':
        """Add an error handler"""
        self._error_handlers.append(handler)
        return self
        
    async def execute(self, context: PipelineContext) -> PipelineContext:
        """Execute the full pipeline"""
        self.logger.info(f"Starting pipeline execution for mode: {context.processing_mode}")
        context.add_timestamp("pipeline_start")
        
        # Run before hooks
        for hook in self._before_hooks:
            try:
                await hook(context) if asyncio.iscoroutinefunction(hook) else hook(context)
            except Exception as e:
                self.logger.error(f"Error in before hook: {e}")
                
        try:
            # Execute stages
            for stage in self.stages:
                # Check for interruption
                if context.interrupt_requested:
                    self.logger.info("Pipeline interrupted by request")
                    break
                    
                if self.orchestrator and await self._should_interrupt(context):
                    self.logger.info("Pipeline interrupted by orchestrator")
                    await self._handle_interruption(context)
                    break
                    
                # Execute stage
                context = await stage(context)
                
                # Stop if error occurred
                if context.error:
                    raise context.error
                    
        except Exception as e:
            self.logger.error(f"Pipeline error: {e}")
            context.error = e
            
            # Run error handlers
            for handler in self._error_handlers:
                try:
                    await handler(context, e) if asyncio.iscoroutinefunction(handler) else handler(context, e)
                except Exception as handler_error:
                    self.logger.error(f"Error in error handler: {handler_error}")
                    
        finally:
            # Run after hooks
            for hook in self._after_hooks:
                try:
                    await hook(context) if asyncio.iscoroutinefunction(hook) else hook(context)
                except Exception as e:
                    self.logger.error(f"Error in after hook: {e}")
                    
        context.add_timestamp("pipeline_end")
        duration = context.get_duration("pipeline_start", "pipeline_end")
        self.logger.info(f"Pipeline execution completed in {duration:.3f}s")
        
        return context
        
    async def _should_interrupt(self, context: PipelineContext) -> bool:
        """Check if pipeline should be interrupted"""
        if self.orchestrator and hasattr(self.orchestrator, 'should_interrupt'):
            return await self.orchestrator.should_interrupt(context)
        return False
        
    async def _handle_interruption(self, context: PipelineContext) -> None:
        """Handle pipeline interruption"""
        if self.orchestrator and hasattr(self.orchestrator, 'handle_interruption'):
            await self.orchestrator.handle_interruption(context)
            
    def get_stage_names(self) -> List[str]:
        """Get names of all stages"""
        return [stage.name for stage in self.stages]
        
    def clear_stages(self) -> 'NeuroSyncPipeline':
        """Clear all stages"""
        self.stages.clear()
        return self
        
    def insert_stage(self, index: int, stage: PipelineStage) -> 'NeuroSyncPipeline':
        """Insert a stage at specific index"""
        self.stages.insert(index, stage)
        return self
        
    def remove_stage(self, name: str) -> 'NeuroSyncPipeline':
        """Remove a stage by name"""
        self.stages = [s for s in self.stages if s.name != name]
        return self


# Pipeline builder for convenience
class PipelineBuilder:
    """Builder pattern for creating pipelines"""
    
    def __init__(self):
        self.pipeline = NeuroSyncPipeline()
        
    def with_state_manager(self, state_manager) -> 'PipelineBuilder':
        """Set state manager"""
        self.pipeline.state_manager = state_manager
        return self
        
    def with_orchestrator(self, orchestrator) -> 'PipelineBuilder':
        """Set orchestrator"""
        self.pipeline.orchestrator = orchestrator
        return self
        
    def add_stage(self, stage: PipelineStage) -> 'PipelineBuilder':
        """Add a stage"""
        self.pipeline.add_stage(stage)
        return self
        
    def add_stages(self, *stages: PipelineStage) -> 'PipelineBuilder':
        """Add multiple stages"""
        for stage in stages:
            self.pipeline.add_stage(stage)
        return self
        
    def add_conditional(self,
                       stage: PipelineStage,
                       condition: Callable[[PipelineContext], bool]) -> 'PipelineBuilder':
        """Add conditional stage"""
        self.pipeline.add_conditional_stage(stage, condition)
        return self
        
    def add_parallel(self, *stages: PipelineStage, name: str = "parallel") -> 'PipelineBuilder':
        """Add parallel stages"""
        self.pipeline.add_parallel_stages(list(stages), name)
        return self
        
    def with_error_handler(self, handler: Callable) -> 'PipelineBuilder':
        """Add error handler"""
        self.pipeline.add_error_handler(handler)
        return self
        
    def with_hooks(self, 
                   before: Optional[Callable] = None,
                   after: Optional[Callable] = None) -> 'PipelineBuilder':
        """Add hooks"""
        if before:
            self.pipeline.add_before_hook(before)
        if after:
            self.pipeline.add_after_hook(after)
        return self
        
    def build(self) -> NeuroSyncPipeline:
        """Build the pipeline"""
        return self.pipeline 