"""
Centralized configuration system for NeuroSync Player.
"""

from dataclasses import dataclass, field
from typing import Dict, Any, Optional, List
import os
import json
from pathlib import Path


@dataclass
class LLMConfig:
    """LLM provider configuration"""
    provider: str = "ollama"
    endpoint: Optional[str] = None
    model: Optional[str] = None
    api_key: Optional[str] = None
    streaming: bool = True
    max_tokens: int = 2048
    temperature: float = 0.7
    timeout: int = 30  # seconds
    
    def to_dict(self) -> Dict[str, Any]:
        return {k: v for k, v in self.__dict__.items() if v is not None}


@dataclass 
class TTSConfig:
    """TTS provider configuration"""
    provider: str = "kokoro"
    voice: str = "af_sarah"
    endpoint: Optional[str] = None
    api_key: Optional[str] = None
    sample_rate: int = 24000
    audio_format: str = "wav"
    speed: float = 1.0
    pitch: float = 1.0
    timeout: int = 30  # seconds
    
    def to_dict(self) -> Dict[str, Any]:
        return {k: v for k, v in self.__dict__.items() if v is not None}


@dataclass
class AnimationConfig:
    """Animation provider configuration"""
    provider: str = "neurosync"
    endpoint: Optional[str] = None
    fps: int = 60
    blend_shape_count: int = 52
    smoothing: bool = True
    emotion_support: bool = True
    
    def to_dict(self) -> Dict[str, Any]:
        return {k: v for k, v in self.__dict__.items() if v is not None}


@dataclass
class OrchestrationConfig:
    """Orchestration configuration"""
    enabled: bool = True
    mode: str = "single_llm"  # single_llm, dual_llm, multi_llm
    interrupt_threshold: int = 4  # Priority level for interruptions
    decision_interval: float = 0.1  # seconds
    idle_timeout: float = 2.0  # seconds
    action_queue_size: int = 100
    enable_state_monitoring: bool = True
    enable_telemetry: bool = True
    
    def to_dict(self) -> Dict[str, Any]:
        return self.__dict__


@dataclass
class SynchronizationConfig:
    """Synchronization configuration for audio-visual alignment"""
    audio_lookahead: float = 0.05  # seconds
    blendshape_offset: float = 0.0  # seconds
    warmup_iterations: int = 2
    adaptive_sync: bool = True
    buffer_size: int = 1024
    
    def to_dict(self) -> Dict[str, Any]:
        return self.__dict__


@dataclass
class NeuroSyncConfig:
    """Main configuration for the entire NeuroSync system"""
    
    # Core component configs
    llm: LLMConfig = field(default_factory=LLMConfig)
    tts: TTSConfig = field(default_factory=TTSConfig)
    animation: AnimationConfig = field(default_factory=AnimationConfig)
    orchestration: OrchestrationConfig = field(default_factory=OrchestrationConfig)
    synchronization: SynchronizationConfig = field(default_factory=SynchronizationConfig)
    
    # Provider-specific configurations
    provider_configs: Dict[str, Dict[str, Any]] = field(default_factory=dict)
    
    # System configuration
    system: Dict[str, Any] = field(default_factory=lambda: {
        'log_level': 'INFO',
        'enable_metrics': True,
        'metrics_port': 9090,
        'health_check_interval': 30,  # seconds
        'max_workers': 4
    })
    
    # Extensions configuration
    extensions_enabled: Dict[str, bool] = field(default_factory=lambda: {
        'game_control': True,
        'scb_integration': True,
        'health_monitoring': True,
        'telemetry': True
    })
    
    # Multi-LLM routing configuration (for dual/multi LLM modes)
    llm_routing: Dict[str, Any] = field(default_factory=lambda: {
        'speech_llm': 'default',
        'environment_llm': 'environment',
        'environment_keywords': [
            'scene', 'hair', 'color', 'lighting', 'appearance',
            'background', 'setting', 'environment', 'visual'
        ],
        'custom_routes': {}  # Custom routing rules
    })
    
    @classmethod
    def from_environment(cls) -> 'NeuroSyncConfig':
        """Load configuration from environment variables"""
        config = cls()
        
        # LLM configuration
        config.llm.provider = os.getenv("LLM_PROVIDER", config.llm.provider)
        config.llm.endpoint = os.getenv("OLLAMA_API_ENDPOINT", config.llm.endpoint)
        config.llm.model = os.getenv("OLLAMA_MODEL", config.llm.model)
        config.llm.api_key = os.getenv("OPENAI_API_KEY", config.llm.api_key)
        config.llm.streaming = os.getenv("LLM_STREAMING", "true").lower() == "true"
        config.llm.max_tokens = int(os.getenv("LLM_MAX_TOKENS", str(config.llm.max_tokens)))
        config.llm.temperature = float(os.getenv("LLM_TEMPERATURE", str(config.llm.temperature)))
        
        # TTS configuration
        config.tts.provider = os.getenv("TTS_PROVIDER", config.tts.provider)
        config.tts.voice = os.getenv("TTS_VOICE", config.tts.voice)
        config.tts.endpoint = os.getenv("KOKORO_TTS_SERVER_URL", config.tts.endpoint)
        config.tts.api_key = os.getenv("ELEVENLABS_API_KEY", config.tts.api_key)
        
        # Animation configuration
        config.animation.provider = os.getenv("ANIMATION_PROVIDER", config.animation.provider)
        config.animation.endpoint = os.getenv("NEUROSYNC_API_ENDPOINT", config.animation.endpoint)
        
        # Orchestration configuration
        config.orchestration.enabled = os.getenv("AUTONOMOUS_ORCHESTRATION_ENABLED", "true").lower() == "true"
        config.orchestration.mode = os.getenv("ORCHESTRATION_MODE", config.orchestration.mode)
        config.orchestration.interrupt_threshold = int(os.getenv("INTERRUPT_THRESHOLD", str(config.orchestration.interrupt_threshold)))
        
        # System configuration
        config.system['log_level'] = os.getenv("LOG_LEVEL", config.system['log_level'])
        config.system['enable_metrics'] = os.getenv("ENABLE_METRICS", "true").lower() == "true"
        
        return config
        
    @classmethod
    def from_file(cls, file_path: str) -> 'NeuroSyncConfig':
        """Load configuration from JSON file"""
        with open(file_path, 'r') as f:
            data = json.load(f)
            
        config = cls()
        
        # Load component configs
        if 'llm' in data:
            config.llm = LLMConfig(**data['llm'])
        if 'tts' in data:
            config.tts = TTSConfig(**data['tts'])
        if 'animation' in data:
            config.animation = AnimationConfig(**data['animation'])
        if 'orchestration' in data:
            config.orchestration = OrchestrationConfig(**data['orchestration'])
        if 'synchronization' in data:
            config.synchronization = SynchronizationConfig(**data['synchronization'])
            
        # Load other configs
        if 'provider_configs' in data:
            config.provider_configs = data['provider_configs']
        if 'system' in data:
            config.system.update(data['system'])
        if 'extensions_enabled' in data:
            config.extensions_enabled.update(data['extensions_enabled'])
        if 'llm_routing' in data:
            config.llm_routing.update(data['llm_routing'])
            
        return config
        
    def to_dict(self) -> Dict[str, Any]:
        """Convert configuration to dictionary"""
        return {
            'llm': self.llm.to_dict(),
            'tts': self.tts.to_dict(),
            'animation': self.animation.to_dict(),
            'orchestration': self.orchestration.to_dict(),
            'synchronization': self.synchronization.to_dict(),
            'provider_configs': self.provider_configs,
            'system': self.system,
            'extensions_enabled': self.extensions_enabled,
            'llm_routing': self.llm_routing
        }
        
    def save(self, file_path: str) -> None:
        """Save configuration to JSON file"""
        Path(file_path).parent.mkdir(parents=True, exist_ok=True)
        with open(file_path, 'w') as f:
            json.dump(self.to_dict(), f, indent=2)
            
    def validate(self) -> List[str]:
        """
        Validate configuration and return list of errors.
        Returns empty list if configuration is valid.
        """
        errors = []
        
        # Validate LLM configuration
        if self.llm.provider == "openai" and not self.llm.api_key:
            errors.append("OpenAI API key required when using OpenAI provider")
        if self.llm.provider == "ollama" and not self.llm.endpoint:
            self.llm.endpoint = "http://localhost:11434"  # Set default
            
        # Validate TTS configuration  
        if self.tts.provider == "elevenlabs" and not self.tts.api_key:
            errors.append("ElevenLabs API key required when using ElevenLabs provider")
        if self.tts.provider == "kokoro" and not self.tts.endpoint:
            self.tts.endpoint = "http://localhost:9000"  # Set default
            
        # Validate orchestration configuration
        valid_modes = ["single_llm", "dual_llm", "multi_llm"]
        if self.orchestration.mode not in valid_modes:
            errors.append(f"Invalid orchestration mode: {self.orchestration.mode}. Must be one of {valid_modes}")
            
        # Validate multi-LLM configuration
        if self.orchestration.mode in ["dual_llm", "multi_llm"]:
            if not self.llm_routing.get('speech_llm'):
                errors.append("speech_llm must be configured for dual/multi LLM mode")
            if not self.llm_routing.get('environment_llm'):
                errors.append("environment_llm must be configured for dual/multi LLM mode")
                
        # Validate system configuration
        valid_log_levels = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
        if self.system['log_level'] not in valid_log_levels:
            errors.append(f"Invalid log level: {self.system['log_level']}")
            
        return errors
        
    def merge_with_env(self) -> None:
        """Merge current configuration with environment variables"""
        env_config = self.from_environment()
        
        # Merge configs (environment takes precedence)
        if os.getenv("LLM_PROVIDER"):
            self.llm = env_config.llm
        if os.getenv("TTS_PROVIDER"):
            self.tts = env_config.tts
        if os.getenv("ORCHESTRATION_MODE"):
            self.orchestration = env_config.orchestration
            
            
# Singleton configuration instance
_config_instance = None


def get_config() -> NeuroSyncConfig:
    """Get the singleton configuration instance"""
    global _config_instance
    if _config_instance is None:
        # Try loading from file first
        config_file = os.getenv("NEUROSYNC_CONFIG_FILE", "config/neurosync.json")
        if os.path.exists(config_file):
            _config_instance = NeuroSyncConfig.from_file(config_file)
            _config_instance.merge_with_env()
        else:
            # Fall back to environment
            _config_instance = NeuroSyncConfig.from_environment()
            
    return _config_instance


def reload_config() -> NeuroSyncConfig:
    """Reload configuration from file/environment"""
    global _config_instance
    _config_instance = None
    return get_config() 