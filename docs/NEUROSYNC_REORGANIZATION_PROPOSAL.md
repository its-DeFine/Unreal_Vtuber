# NeuroBridge/NeuroSync Player Reorganization Proposal

## Current Organization Issues

### **Problem Analysis**

**1. Scattered Decision Logic**
- Request routing logic mixed in main Flask app (`llm_to_face.py`)
- Orchestrator decision-making split between multiple files
- Context analysis and path selection embedded in HTTP handlers

**2. Overlapping Integration Points**
- `orchestrator_integration.py` - Wrapper layer
- `autonomous_orchestrator.py` - Core logic  
- `llm_to_face.py` - Request routing and execution
- State management spread across multiple components

**3. Provider Abstraction Gaps**
- TTS providers in `utils/tts/` with inconsistent interfaces
- LLM providers configured differently (config vs direct imports)
- No unified provider interface or registry

**4. Configuration Dispersion**
- Environment variables scattered across multiple files
- Provider configuration mixed with business logic
- No centralized configuration validation

**5. Testing and Utility Development Barriers**
- Tight coupling makes unit testing difficult
- Hard to build utilities due to scattered interfaces
- No clear extension points for new providers or behaviors

## Proposed Reorganization

### **New Directory Structure**

```
docker-vtuber/app/AVATAR/NeuroBridge/NeuroSync_Player/
├── core/
│   ├── __init__.py
│   ├── pipeline.py              # Main execution pipeline
│   ├── orchestrator.py          # Unified orchestration logic
│   ├── state_manager.py         # Centralized state management
│   └── decision_engine.py       # Decision logic abstraction
├── providers/
│   ├── __init__.py
│   ├── base.py                  # Base provider interfaces
│   ├── llm/
│   │   ├── __init__.py
│   │   ├── ollama_provider.py
│   │   ├── openai_provider.py
│   │   └── custom_provider.py
│   ├── tts/
│   │   ├── __init__.py
│   │   ├── kokoro_provider.py
│   │   ├── elevenlabs_provider.py
│   │   └── local_provider.py
│   └── animation/
│       ├── __init__.py
│       ├── neurosync_provider.py
│       └── mock_provider.py
├── config/
│   ├── __init__.py
│   ├── settings.py              # Centralized configuration
│   ├── validation.py            # Config validation
│   └── defaults.py              # Default configurations
├── api/
│   ├── __init__.py
│   ├── routes.py                # Clean route definitions
│   ├── middleware.py            # Request processing middleware
│   └── responses.py             # Response formatting
├── utils/
│   ├── __init__.py
│   ├── audio.py                 # Audio processing utilities
│   ├── sync.py                  # Synchronization utilities
│   └── logging.py               # Logging configuration
├── extensions/
│   ├── __init__.py
│   ├── game_control.py          # Game control extension
│   ├── scb_integration.py       # SCB extension
│   └── health_monitoring.py     # Health check extension
├── tests/
│   ├── unit/
│   ├── integration/
│   └── fixtures/
└── examples/
    ├── single_llm_setup.py
    ├── dual_llm_setup.py
    └── custom_provider_example.py
```

### **Core Architecture Redesign**

#### **1. Unified Pipeline Pattern**

```python
# core/pipeline.py
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional
from dataclasses import dataclass

@dataclass
class PipelineContext:
    """Unified context object passed through pipeline stages"""
    user_input: str
    request_metadata: Dict[str, Any]
    autonomous_context: Optional[str] = None
    priority: Priority = Priority.MEDIUM
    processing_mode: str = "standard"  # standard, direct_speech, orchestrated
    provider_preferences: Dict[str, str] = None

class PipelineStage(ABC):
    """Base class for all pipeline stages"""
    
    @abstractmethod
    async def process(self, context: PipelineContext) -> PipelineContext:
        """Process the context and return modified context"""
        pass

class NeuroSyncPipeline:
    """Main pipeline orchestrating all processing stages"""
    
    def __init__(self):
        self.stages = []
        self.state_manager = StateManager()
        self.orchestrator = UnifiedOrchestrator()
        
    def add_stage(self, stage: PipelineStage):
        """Add a processing stage to the pipeline"""
        self.stages.append(stage)
        
    async def execute(self, context: PipelineContext) -> Dict[str, Any]:
        """Execute the full pipeline"""
        for stage in self.stages:
            context = await stage.process(context)
            
            # Check for interruptions at each stage
            if self.orchestrator.should_interrupt(context):
                await self.orchestrator.handle_interruption(context)
                break
                
        return context

# Built-in pipeline stages
class ContextAnalysisStage(PipelineStage):
    """Analyzes input context and sets processing mode"""
    
    async def process(self, context: PipelineContext) -> PipelineContext:
        context.processing_mode = self._determine_mode(context.user_input, context.autonomous_context)
        context.priority = self._determine_priority(context.user_input, context.autonomous_context)
        return context

class LLMProcessingStage(PipelineStage):
    """Handles LLM processing based on context"""
    
    def __init__(self, llm_registry: 'LLMRegistry'):
        self.llm_registry = llm_registry
        
    async def process(self, context: PipelineContext) -> PipelineContext:
        if context.processing_mode == "direct_speech":
            return context  # Skip LLM processing
            
        provider = self.llm_registry.get_provider(context.provider_preferences.get('llm', 'default'))
        context.llm_response = await provider.generate(context.user_input, context.request_metadata)
        return context

class TTSProcessingStage(PipelineStage):
    """Handles TTS processing"""
    
    def __init__(self, tts_registry: 'TTSRegistry'):
        self.tts_registry = tts_registry
        
    async def process(self, context: PipelineContext) -> PipelineContext:
        text_to_speak = context.llm_response if hasattr(context, 'llm_response') else context.user_input
        provider = self.tts_registry.get_provider(context.provider_preferences.get('tts', 'default'))
        context.audio_data = await provider.generate_audio(text_to_speak)
        return context

class AnimationProcessingStage(PipelineStage):
    """Handles facial animation processing"""
    
    def __init__(self, animation_registry: 'AnimationRegistry'):
        self.animation_registry = animation_registry
        
    async def process(self, context: PipelineContext) -> PipelineContext:
        provider = self.animation_registry.get_provider('default')
        context.facial_data = await provider.generate_blendshapes(context.audio_data)
        return context

class OutputStage(PipelineStage):
    """Handles synchronized output"""
    
    async def process(self, context: PipelineContext) -> PipelineContext:
        await self._execute_synchronized_output(context.audio_data, context.facial_data)
        return context
```

#### **2. Provider Registry System**

```python
# providers/base.py
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional

class BaseProvider(ABC):
    """Base interface for all providers"""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        
    @abstractmethod
    async def initialize(self) -> bool:
        """Initialize the provider"""
        pass
        
    @abstractmethod
    async def health_check(self) -> Dict[str, Any]:
        """Check provider health"""
        pass

class LLMProvider(BaseProvider):
    """Base LLM provider interface"""
    
    @abstractmethod
    async def generate(self, prompt: str, context: Dict[str, Any]) -> str:
        """Generate text response"""
        pass
        
    @abstractmethod
    def get_capabilities(self) -> Dict[str, Any]:
        """Return provider capabilities"""
        pass

class TTSProvider(BaseProvider):
    """Base TTS provider interface"""
    
    @abstractmethod
    async def generate_audio(self, text: str, voice: Optional[str] = None) -> bytes:
        """Generate audio from text"""
        pass
        
    @abstractmethod
    def get_voices(self) -> List[str]:
        """Get available voices"""
        pass

class AnimationProvider(BaseProvider):
    """Base animation provider interface"""
    
    @abstractmethod
    async def generate_blendshapes(self, audio_data: bytes) -> List[List[float]]:
        """Generate facial blendshapes from audio"""
        pass

# providers/__init__.py
class ProviderRegistry:
    """Centralized provider registry"""
    
    def __init__(self):
        self._llm_providers = {}
        self._tts_providers = {}
        self._animation_providers = {}
        
    def register_llm_provider(self, name: str, provider_class: type, config: Dict[str, Any]):
        """Register an LLM provider"""
        self._llm_providers[name] = provider_class(config)
        
    def register_tts_provider(self, name: str, provider_class: type, config: Dict[str, Any]):
        """Register a TTS provider"""
        self._tts_providers[name] = provider_class(config)
        
    def register_animation_provider(self, name: str, provider_class: type, config: Dict[str, Any]):
        """Register an animation provider"""
        self._animation_providers[name] = provider_class(config)
        
    async def initialize_all(self):
        """Initialize all registered providers"""
        for providers in [self._llm_providers, self._tts_providers, self._animation_providers]:
            for provider in providers.values():
                await provider.initialize()
                
    def get_llm_provider(self, name: str = "default") -> LLMProvider:
        return self._llm_providers.get(name)
        
    def get_tts_provider(self, name: str = "default") -> TTSProvider:
        return self._tts_providers.get(name)
        
    def get_animation_provider(self, name: str = "default") -> AnimationProvider:
        return self._animation_providers.get(name)
```

#### **3. Unified Orchestrator**

```python
# core/orchestrator.py
from typing import Dict, Any, List, Optional
from enum import Enum

class OrchestrationMode(Enum):
    SINGLE_LLM = "single_llm"
    DUAL_LLM = "dual_llm"
    MULTI_LLM = "multi_llm"

class UnifiedOrchestrator:
    """Unified orchestrator handling both single and multi-LLM scenarios"""
    
    def __init__(self, mode: OrchestrationMode = OrchestrationMode.SINGLE_LLM):
        self.mode = mode
        self.state_manager = StateManager()
        self.decision_engine = DecisionEngine()
        self.action_queue = []
        
    async def should_interrupt(self, context: PipelineContext) -> bool:
        """Unified interruption logic"""
        current_state = self.state_manager.get_current_state()
        return self.decision_engine.should_interrupt(
            context.priority, 
            current_state,
            context.processing_mode
        )
        
    async def handle_interruption(self, context: PipelineContext):
        """Unified interruption handling"""
        await self._stop_current_processing()
        await self._clear_queues()
        self.state_manager.reset_to_idle()
        
    def route_to_llm(self, context: PipelineContext) -> str:
        """Determine which LLM should handle the request"""
        if self.mode == OrchestrationMode.SINGLE_LLM:
            return "default"
        elif self.mode == OrchestrationMode.DUAL_LLM:
            return "speech" if self._is_speech_request(context) else "environment"
        else:
            return self._multi_llm_routing(context)
            
    def _is_speech_request(self, context: PipelineContext) -> bool:
        """Determine if request is speech vs environment"""
        environment_keywords = ["scene", "hair", "color", "lighting", "appearance"]
        return not any(keyword in context.user_input.lower() for keyword in environment_keywords)
```

#### **4. Centralized Configuration**

```python
# config/settings.py
from dataclasses import dataclass, field
from typing import Dict, Any, Optional
import os

@dataclass
class LLMConfig:
    provider: str = "ollama"
    endpoint: Optional[str] = None
    model: Optional[str] = None
    api_key: Optional[str] = None
    streaming: bool = True
    
@dataclass
class TTSConfig:
    provider: str = "kokoro"
    voice: str = "af_sarah"
    endpoint: Optional[str] = None
    api_key: Optional[str] = None
    
@dataclass
class OrchestrationConfig:
    enabled: bool = True
    mode: str = "single_llm"  # single_llm, dual_llm, multi_llm
    interrupt_threshold: int = 4
    decision_interval: float = 0.1
    idle_timeout: float = 2.0
    
@dataclass
class NeuroSyncConfig:
    """Centralized configuration for the entire system"""
    
    # Core settings
    llm: LLMConfig = field(default_factory=LLMConfig)
    tts: TTSConfig = field(default_factory=TTSConfig)
    orchestration: OrchestrationConfig = field(default_factory=OrchestrationConfig)
    
    # Provider configurations
    provider_configs: Dict[str, Dict[str, Any]] = field(default_factory=dict)
    
    # Extensions
    extensions_enabled: Dict[str, bool] = field(default_factory=lambda: {
        'game_control': True,
        'scb_integration': True,
        'health_monitoring': True
    })
    
    @classmethod
    def from_environment(cls) -> 'NeuroSyncConfig':
        """Load configuration from environment variables"""
        config = cls()
        
        # LLM configuration
        config.llm.provider = os.getenv("LLM_PROVIDER", "ollama")
        config.llm.endpoint = os.getenv("OLLAMA_API_ENDPOINT")
        config.llm.model = os.getenv("OLLAMA_MODEL")
        config.llm.api_key = os.getenv("OPENAI_API_KEY")
        
        # TTS configuration
        config.tts.provider = os.getenv("TTS_PROVIDER", "kokoro")
        config.tts.voice = os.getenv("TTS_VOICE", "af_sarah")
        config.tts.endpoint = os.getenv("KOKORO_TTS_SERVER_URL")
        
        # Orchestration configuration
        config.orchestration.enabled = os.getenv("AUTONOMOUS_ORCHESTRATION_ENABLED", "true").lower() == "true"
        config.orchestration.mode = os.getenv("ORCHESTRATION_MODE", "single_llm")
        config.orchestration.interrupt_threshold = int(os.getenv("INTERRUPT_THRESHOLD", "4"))
        
        return config
        
    def validate(self) -> List[str]:
        """Validate configuration and return list of errors"""
        errors = []
        
        if self.llm.provider == "openai" and not self.llm.api_key:
            errors.append("OpenAI API key required when using OpenAI provider")
            
        if self.tts.provider == "elevenlabs" and not self.tts.api_key:
            errors.append("ElevenLabs API key required when using ElevenLabs provider")
            
        if self.orchestration.mode not in ["single_llm", "dual_llm", "multi_llm"]:
            errors.append(f"Invalid orchestration mode: {self.orchestration.mode}")
            
        return errors
```

#### **5. Clean API Layer**

```python
# api/routes.py
from flask import Flask, request, jsonify
from core.pipeline import NeuroSyncPipeline, PipelineContext

class NeuroSyncAPI:
    """Clean API layer with minimal business logic"""
    
    def __init__(self, pipeline: NeuroSyncPipeline):
        self.pipeline = pipeline
        self.app = Flask(__name__)
        self._register_routes()
        
    def _register_routes(self):
        
        @self.app.route("/process", methods=['POST'])
        async def process_text():
            """Unified text processing endpoint"""
            data = request.get_json()
            
            context = PipelineContext(
                user_input=data.get('text', ''),
                request_metadata=data,
                autonomous_context=data.get('autonomous_context'),
                provider_preferences=data.get('providers', {})
            )
            
            result = await self.pipeline.execute(context)
            return jsonify(self._format_response(result))
            
        @self.app.route("/providers", methods=['GET'])
        def list_providers():
            """List available providers"""
            return jsonify(self.pipeline.get_provider_status())
            
        @self.app.route("/health", methods=['GET'])
        async def health_check():
            """System health check"""
            return jsonify(await self.pipeline.health_check())
```

## Benefits of Reorganization

### **1. Improved Readability**
- **Clear separation of concerns** with dedicated modules
- **Unified interfaces** making the system easier to understand
- **Centralized configuration** in one location
- **Logical directory structure** following standard patterns

### **2. Enhanced Extensibility**
- **Provider registry system** for easy addition of new providers
- **Pipeline pattern** allowing custom processing stages
- **Extension system** for optional features
- **Clean interfaces** for building utilities

### **3. Better Testing**
- **Isolated components** can be unit tested independently
- **Mock providers** for testing without external dependencies
- **Pipeline stages** can be tested in isolation
- **Configuration validation** ensures correct setup

### **4. Utility Development**
- **Clear extension points** for building on top of the system
- **Provider abstraction** allows easy swapping of implementations
- **Unified orchestrator** provides consistent decision-making
- **Configuration system** supports different deployment scenarios

### **5. Maintenance Benefits**
- **Centralized logic** reduces duplication
- **Consistent error handling** across components
- **Simplified debugging** with clear data flow
- **Version compatibility** easier to maintain

## Migration Strategy

### **Phase 1: Core Infrastructure** (Week 1-2)
1. Create new directory structure
2. Implement base provider interfaces
3. Create centralized configuration system
4. Build provider registry

### **Phase 2: Pipeline Implementation** (Week 3-4)
1. Implement pipeline pattern
2. Create built-in pipeline stages
3. Migrate existing providers to new interfaces
4. Build unified orchestrator

### **Phase 3: API Migration** (Week 5-6)
1. Create clean API layer
2. Migrate existing endpoints
3. Add comprehensive testing
4. Update documentation

### **Phase 4: Extension System** (Week 7-8)
1. Implement extension framework
2. Migrate game control and SCB integration
3. Add health monitoring
4. Create utility examples

## Example Usage After Reorganization

### **Simple Single LLM Setup**
```python
# examples/single_llm_setup.py
from core.pipeline import NeuroSyncPipeline
from config.settings import NeuroSyncConfig
from providers import ProviderRegistry

# Load configuration
config = NeuroSyncConfig.from_environment()
config.orchestration.mode = "single_llm"

# Create provider registry
registry = ProviderRegistry()
registry.register_llm_provider("default", OllamaProvider, config.llm)
registry.register_tts_provider("default", KokoroProvider, config.tts)

# Create and configure pipeline
pipeline = NeuroSyncPipeline()
pipeline.add_stage(ContextAnalysisStage())
pipeline.add_stage(LLMProcessingStage(registry))
pipeline.add_stage(TTSProcessingStage(registry))
pipeline.add_stage(AnimationProcessingStage(registry))
pipeline.add_stage(OutputStage())

# Start API
api = NeuroSyncAPI(pipeline)
api.app.run(host='0.0.0.0', port=5001)
```

### **Advanced Dual LLM Setup**
```python
# examples/dual_llm_setup.py
config.orchestration.mode = "dual_llm"

# Register multiple LLM providers
registry.register_llm_provider("speech", OllamaProvider, speech_config)
registry.register_llm_provider("environment", OpenAIProvider, env_config)

# Custom routing logic
class DualLLMStage(LLMProcessingStage):
    async def process(self, context):
        provider_name = "speech" if self._is_speech_request(context) else "environment"
        provider = self.llm_registry.get_provider(provider_name)
        context.llm_response = await provider.generate(context.user_input, context.request_metadata)
        return context

pipeline.add_stage(DualLLMStage(registry))
```

This reorganization would significantly improve the codebase's maintainability, extensibility, and readability while providing clear patterns for building utilities and extensions on top of the system.

## Implementation Progress

### **Completed Components** ✅

1. **Base Provider Interfaces** (`providers/base.py`)
   - Abstract base classes for LLM, TTS, and Animation providers
   - Standardized interfaces with health checks and capabilities
   - Provider status management and error handling

2. **Provider Registry System** (`providers/__init__.py`)
   - Centralized registry for managing all providers
   - Singleton pattern for global access
   - Automatic initialization and shutdown
   - Health check aggregation

3. **Centralized Configuration** (`config/settings.py`)
   - Comprehensive configuration dataclasses
   - Environment variable loading
   - JSON file support
   - Configuration validation
   - Multi-LLM routing configuration

4. **Pipeline Pattern** (`core/pipeline.py`)
   - Flexible pipeline architecture
   - Conditional and parallel stage support
   - Error handling and hooks
   - Timing and performance tracking
   - Pipeline builder for easy construction

5. **Example Implementation** (`providers/llm/ollama_provider.py`)
   - Complete Ollama LLM provider
   - Streaming support
   - Health checks
   - Proper error handling

6. **Working Example** (`examples/single_llm_setup.py`)
   - Demonstrates complete pipeline setup
   - Shows different processing modes
   - Includes timing and logging

### **Next Steps** 🚀

1. **Migrate Existing Providers**
   - Port Kokoro TTS provider to new interface
   - Port ElevenLabs TTS provider
   - Port NeuroSync animation provider
   - Create OpenAI LLM provider

2. **Implement Core Components**
   - Create unified orchestrator (`core/orchestrator.py`)
   - Implement state manager (`core/state_manager.py`)
   - Build decision engine (`core/decision_engine.py`)

3. **API Layer**
   - Create clean Flask routes (`api/routes.py`)
   - Implement request/response formatting
   - Add middleware for logging/metrics

4. **Migration Tools**
   - Create compatibility layer for existing code
   - Build migration scripts
   - Provide backwards compatibility

5. **Testing Suite**
   - Unit tests for all components
   - Integration tests for pipeline
   - Performance benchmarks

6. **Documentation**
   - API documentation
   - Provider implementation guide
   - Migration guide for existing code

### **Benefits Already Visible**

1. **Clean Separation** - Each component has a single responsibility
2. **Easy Configuration** - Change providers/modes without code changes
3. **Extensibility** - Add new providers by implementing interfaces
4. **Performance Tracking** - Built-in timing for optimization
5. **Error Handling** - Consistent error management across system

The reorganization is progressing well and already showing significant improvements in code organization and maintainability! 