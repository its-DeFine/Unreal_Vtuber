"""
Example: Single LLM Setup using the reorganized NeuroSync architecture
"""

import asyncio
import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.append(str(Path(__file__).parent.parent))

from core.pipeline import PipelineBuilder, PipelineContext, PipelineStage, Priority
from providers import get_registry
from providers.llm.ollama_provider import OllamaProvider
from config.settings import NeuroSyncConfig, get_config
import logging


# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


# Example pipeline stages
class ContextAnalysisStage(PipelineStage):
    """Analyzes input context and sets processing mode"""
    
    def __init__(self):
        super().__init__("context_analysis")
        
    async def process(self, context: PipelineContext) -> PipelineContext:
        # Check for direct speech markers
        if context.autonomous_context and "orchestrator_speech" in context.autonomous_context:
            context.processing_mode = "direct_speech"
            context.priority = Priority.HIGH
        # Check for environment keywords
        elif any(keyword in context.user_input.lower() for keyword in ['scene', 'hair', 'color', 'lighting']):
            context.processing_mode = "orchestrated"
            context.priority = Priority.MEDIUM
        else:
            context.processing_mode = "standard"
            
        self.logger.info(f"Determined processing mode: {context.processing_mode}, priority: {context.priority.name}")
        return context


class LLMProcessingStage(PipelineStage):
    """Handles LLM processing based on context"""
    
    def __init__(self, registry):
        super().__init__("llm_processing")
        self.registry = registry
        
    async def process(self, context: PipelineContext) -> PipelineContext:
        if context.processing_mode == "direct_speech":
            # Skip LLM for direct speech
            context.llm_response = context.user_input
            self.logger.info("Skipping LLM for direct speech mode")
        else:
            # Use LLM provider
            provider = self.registry.get_llm_provider()
            self.logger.info(f"Processing with LLM provider: {provider.name}")
            
            context.llm_response = await provider.generate(
                context.user_input,
                context={'system': 'You are a helpful VTuber assistant.'}
            )
            
        return context


class MockTTSStage(PipelineStage):
    """Mock TTS stage for demonstration"""
    
    def __init__(self):
        super().__init__("tts_processing")
        
    async def process(self, context: PipelineContext) -> PipelineContext:
        text_to_speak = context.llm_response or context.user_input
        self.logger.info(f"Generating audio for: {text_to_speak[:50]}...")
        
        # Simulate TTS processing
        await asyncio.sleep(0.5)
        context.audio_data = b"mock_audio_data"
        
        return context


class MockAnimationStage(PipelineStage):
    """Mock animation stage for demonstration"""
    
    def __init__(self):
        super().__init__("animation_processing")
        
    async def process(self, context: PipelineContext) -> PipelineContext:
        if context.audio_data:
            self.logger.info("Generating facial animations...")
            
            # Simulate animation processing
            await asyncio.sleep(0.3)
            context.facial_data = [[0.0] * 52 for _ in range(60)]  # Mock 60 frames
            
        return context


class OutputStage(PipelineStage):
    """Handles synchronized output"""
    
    def __init__(self):
        super().__init__("output")
        
    async def process(self, context: PipelineContext) -> PipelineContext:
        self.logger.info("Executing synchronized output")
        
        # In real implementation, this would:
        # 1. Start audio playback
        # 2. Send facial data to Unreal Engine
        # 3. Coordinate timing
        
        return context


async def main():
    """Main function demonstrating single LLM setup"""
    
    # Load configuration
    config = NeuroSyncConfig()
    config.orchestration.mode = "single_llm"
    config.llm.provider = "ollama"
    config.llm.endpoint = "http://localhost:11434"
    config.llm.model = "llama2"
    
    # Validate configuration
    errors = config.validate()
    if errors:
        logger.error(f"Configuration errors: {errors}")
        return
        
    # Create provider registry
    registry = get_registry()
    
    # Register LLM provider
    registry.register_llm_provider(
        "default",
        OllamaProvider,
        config.llm.to_dict(),
        set_as_default=True
    )
    
    # Initialize providers
    logger.info("Initializing providers...")
    init_results = await registry.initialize_all()
    logger.info(f"Initialization results: {init_results}")
    
    if init_results['failed']:
        logger.error("Some providers failed to initialize")
        return
        
    # Build pipeline
    pipeline = (PipelineBuilder()
        .add_stage(ContextAnalysisStage())
        .add_stage(LLMProcessingStage(registry))
        .add_stage(MockTTSStage())
        .add_stage(MockAnimationStage())
        .add_stage(OutputStage())
        .with_error_handler(lambda ctx, err: logger.error(f"Pipeline error: {err}"))
        .build()
    )
    
    # Example requests
    test_requests = [
        # Standard request
        {
            "text": "Hello! How are you today?",
            "context": None
        },
        # Direct speech from orchestrator
        {
            "text": "I'm feeling great today!",
            "context": "orchestrator_speech"
        },
        # Environment-related request
        {
            "text": "Change my hair color to blue",
            "context": None
        }
    ]
    
    # Process requests
    for request in test_requests:
        logger.info(f"\n{'='*50}")
        logger.info(f"Processing request: {request['text']}")
        
        context = PipelineContext(
            user_input=request['text'],
            autonomous_context=request['context']
        )
        
        result = await pipeline.execute(context)
        
        # Log results
        logger.info(f"Processing mode: {result.processing_mode}")
        logger.info(f"LLM response: {result.llm_response[:100] if result.llm_response else 'None'}...")
        logger.info(f"Audio generated: {result.audio_data is not None}")
        logger.info(f"Animation frames: {len(result.facial_data) if result.facial_data else 0}")
        
        # Log timing
        total_time = result.get_duration("pipeline_start", "pipeline_end")
        logger.info(f"Total pipeline time: {total_time:.3f}s")
        
    # Cleanup
    await registry.shutdown_all()
    logger.info("\nPipeline demonstration completed!")


if __name__ == "__main__":
    asyncio.run(main()) 