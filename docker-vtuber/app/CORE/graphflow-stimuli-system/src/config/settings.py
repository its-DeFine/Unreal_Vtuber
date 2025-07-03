"""
Configuration management for GraphFlow External Stimuli System.

This module provides comprehensive configuration through dataclasses with
validation, environment variable loading, and sensible defaults.
"""

import os
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any
from enum import Enum
import json
import logging
from pathlib import Path


class ContextAnalysisDepth(str, Enum):
    """Depth levels for context analysis."""
    MINIMAL = "minimal"
    STANDARD = "standard"
    DEEP = "deep"


class Priority(str, Enum):
    """Priority levels for stimuli processing."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    EMERGENCY = "emergency"


class StimuliCategory(str, Enum):
    """Categories for external stimuli classification."""
    DIRECT_ADMIN = "direct_admin"
    USER_INTERACTION = "user_interaction"
    SYSTEM_NOTIFICATION = "system_notification"
    SOCIAL_MEDIA = "social_media"
    AUTONOMOUS_TRIGGER = "autonomous_trigger"
    EMERGENCY = "emergency"
    CONTEXTUAL_UPDATE = "contextual_update"


class ProcessingDecision(str, Enum):
    """Processing decision types."""
    AVATAR_AND_ANALYSIS = "avatar_and_analysis"
    ANALYSIS_ONLY = "analysis_only"
    LOG_ONLY = "log_only"
    EMERGENCY_OVERRIDE = "emergency_override"


@dataclass
class System1Config:
    """Configuration for System1 (Avatar/Speech) integration."""
    vtuber_endpoint: str = field(
        default_factory=lambda: os.getenv("SYSTEM1_VTUBER_ENDPOINT", "http://neurosync:5001")
    )
    tts_endpoint: str = field(
        default_factory=lambda: os.getenv("SYSTEM1_TTS_ENDPOINT", "http://neurosync:5001/tts")
    )
    connection_timeout: float = field(
        default_factory=lambda: float(os.getenv("SYSTEM1_CONNECTION_TIMEOUT", "5.0"))
    )
    request_timeout: float = field(
        default_factory=lambda: float(os.getenv("SYSTEM1_REQUEST_TIMEOUT", "30.0"))
    )
    max_retries: int = field(
        default_factory=lambda: int(os.getenv("SYSTEM1_MAX_RETRIES", "3"))
    )
    retry_delay: float = field(
        default_factory=lambda: float(os.getenv("SYSTEM1_RETRY_DELAY", "1.0"))
    )
    character_presets: Dict[str, str] = field(default_factory=dict)
    
    def __post_init__(self):
        """Load character presets from environment if available."""
        presets = os.getenv("SYSTEM1_CHARACTER_PRESETS")
        if presets:
            try:
                self.character_presets = json.loads(presets)
            except json.JSONDecodeError:
                logging.warning("Failed to parse SYSTEM1_CHARACTER_PRESETS from environment")


@dataclass
class System2Config:
    """Configuration for System2 (Multi-Agent) integration."""
    autogen_endpoint: str = field(
        default_factory=lambda: os.getenv("SYSTEM2_AUTOGEN_ENDPOINT", "http://autogen-agent:3100")
    )
    cognee_endpoint: str = field(
        default_factory=lambda: os.getenv("SYSTEM2_COGNEE_ENDPOINT", "http://cognee:8000")
    )
    cognee_api_key: Optional[str] = field(
        default_factory=lambda: os.getenv("SYSTEM2_COGNEE_API_KEY", None)
    )
    evolution_engine_enabled: bool = field(
        default_factory=lambda: os.getenv("SYSTEM2_EVOLUTION_ENGINE_ENABLED", "true").lower() == "true"
    )
    connection_timeout: float = field(
        default_factory=lambda: float(os.getenv("SYSTEM2_CONNECTION_TIMEOUT", "5.0"))
    )
    request_timeout: float = field(
        default_factory=lambda: float(os.getenv("SYSTEM2_REQUEST_TIMEOUT", "60.0"))
    )
    max_concurrent_agents: int = field(
        default_factory=lambda: int(os.getenv("SYSTEM2_MAX_CONCURRENT_AGENTS", "10"))
    )
    max_retries: int = field(
        default_factory=lambda: int(os.getenv("SYSTEM2_MAX_RETRIES", "3"))
    )
    load_balancing_strategy: str = field(
        default_factory=lambda: os.getenv("SYSTEM2_LOAD_BALANCING", "best_performance")
    )
    health_check_interval: int = field(
        default_factory=lambda: int(os.getenv("SYSTEM2_HEALTH_CHECK_INTERVAL", "60"))
    )
    max_tasks_per_agent: int = field(
        default_factory=lambda: int(os.getenv("SYSTEM2_MAX_TASKS_PER_AGENT", "10"))
    )
    agent_config: Dict[str, Any] = field(default_factory=dict)
    
    def __post_init__(self):
        """Load agent configuration from environment if available."""
        agent_config = os.getenv("SYSTEM2_AGENT_CONFIG")
        if agent_config:
            try:
                self.agent_config = json.loads(agent_config)
            except json.JSONDecodeError:
                logging.warning("Failed to parse SYSTEM2_AGENT_CONFIG from environment")


@dataclass
class ExternalAPIConfig:
    """Configuration for external API integration."""
    enabled: bool = field(
        default_factory=lambda: os.getenv("EXTERNAL_API_ENABLED", "true").lower() == "true"
    )
    host: str = field(
        default_factory=lambda: os.getenv("EXTERNAL_API_HOST", "0.0.0.0")
    )
    port: int = field(
        default_factory=lambda: int(os.getenv("EXTERNAL_API_PORT", "8080"))
    )
    api_key_required: bool = field(
        default_factory=lambda: os.getenv("EXTERNAL_API_KEY_REQUIRED", "true").lower() == "true"
    )
    api_keys_file: str = field(
        default_factory=lambda: os.getenv("EXTERNAL_API_KEYS_FILE", "config/api_keys.json")
    )
    rate_limit_enabled: bool = field(
        default_factory=lambda: os.getenv("EXTERNAL_RATE_LIMIT_ENABLED", "true").lower() == "true"
    )
    rate_limit_requests: int = field(
        default_factory=lambda: int(os.getenv("EXTERNAL_RATE_LIMIT_REQUESTS", "100"))
    )
    rate_limit_period: int = field(
        default_factory=lambda: int(os.getenv("EXTERNAL_RATE_LIMIT_PERIOD", "3600"))
    )
    allowed_sources: List[str] = field(default_factory=list)
    cors_enabled: bool = field(
        default_factory=lambda: os.getenv("EXTERNAL_CORS_ENABLED", "true").lower() == "true"
    )
    cors_origins: List[str] = field(default_factory=list)
    
    def __post_init__(self):
        """Load allowed sources and CORS origins from environment."""
        sources = os.getenv("EXTERNAL_ALLOWED_SOURCES", "user_chat,admin_console,social_media,system")
        self.allowed_sources = [s.strip() for s in sources.split(",")]
        
        origins = os.getenv("EXTERNAL_CORS_ORIGINS", "*")
        self.cors_origins = [o.strip() for o in origins.split(",")]


@dataclass
class CategorizerConfig:
    """Configuration for stimuli categorizer node."""
    confidence_threshold: float = field(
        default_factory=lambda: float(os.getenv("CATEGORIZER_CONFIDENCE_THRESHOLD", "0.8"))
    )
    fallback_category: str = field(
        default_factory=lambda: os.getenv("CATEGORIZER_FALLBACK_CATEGORY", "CONTEXTUAL_UPDATE")
    )
    use_llm: bool = field(
        default_factory=lambda: os.getenv("CATEGORIZER_USE_LLM", "true").lower() == "true"
    )
    llm_timeout: float = field(
        default_factory=lambda: float(os.getenv("CATEGORIZER_LLM_TIMEOUT", "5.0"))
    )
    cache_enabled: bool = field(
        default_factory=lambda: os.getenv("CATEGORIZER_CACHE_ENABLED", "true").lower() == "true"
    )
    cache_ttl: int = field(
        default_factory=lambda: int(os.getenv("CATEGORIZER_CACHE_TTL", "300"))
    )
    keyword_patterns: Dict[str, List[str]] = field(default_factory=dict)
    
    def __post_init__(self):
        """Load keyword patterns from environment if available."""
        patterns = os.getenv("CATEGORIZER_KEYWORD_PATTERNS")
        if patterns:
            try:
                self.keyword_patterns = json.loads(patterns)
            except json.JSONDecodeError:
                logging.warning("Failed to parse CATEGORIZER_KEYWORD_PATTERNS from environment")


@dataclass
class AnalyzerConfig:
    """Configuration for context analyzer node."""
    analysis_depth: ContextAnalysisDepth = field(
        default_factory=lambda: ContextAnalysisDepth(
            os.getenv("ANALYZER_DEPTH", "standard")
        )
    )
    include_user_history: bool = field(
        default_factory=lambda: os.getenv("ANALYZER_INCLUDE_USER_HISTORY", "true").lower() == "true"
    )
    history_window_size: int = field(
        default_factory=lambda: int(os.getenv("ANALYZER_HISTORY_WINDOW_SIZE", "100"))
    )
    include_environmental_context: bool = field(
        default_factory=lambda: os.getenv("ANALYZER_INCLUDE_ENVIRONMENTAL", "true").lower() == "true"
    )
    resource_check_interval: float = field(
        default_factory=lambda: float(os.getenv("ANALYZER_RESOURCE_CHECK_INTERVAL", "5.0"))
    )
    cache_enabled: bool = field(
        default_factory=lambda: os.getenv("ANALYZER_CACHE_ENABLED", "true").lower() == "true"
    )
    cache_ttl: int = field(
        default_factory=lambda: int(os.getenv("ANALYZER_CACHE_TTL", "60"))
    )


@dataclass
class RouterConfig:
    """Configuration for decision router node."""
    enable_emergency_override: bool = field(
        default_factory=lambda: os.getenv("ROUTER_ENABLE_EMERGENCY_OVERRIDE", "true").lower() == "true"
    )
    decision_timeout: float = field(
        default_factory=lambda: float(os.getenv("ROUTER_DECISION_TIMEOUT", "2.0"))
    )
    use_ml_routing: bool = field(
        default_factory=lambda: os.getenv("ROUTER_USE_ML_ROUTING", "false").lower() == "true"
    )
    ml_model_path: Optional[str] = field(
        default_factory=lambda: os.getenv("ROUTER_ML_MODEL_PATH")
    )
    fallback_decision: str = field(
        default_factory=lambda: os.getenv("ROUTER_FALLBACK_DECISION", "ANALYSIS_ONLY")
    )
    decision_logging_enabled: bool = field(
        default_factory=lambda: os.getenv("ROUTER_DECISION_LOGGING", "true").lower() == "true"
    )
    custom_rules_path: Optional[str] = field(
        default_factory=lambda: os.getenv("ROUTER_CUSTOM_RULES_PATH")
    )


@dataclass
class ExecutorConfig:
    """Configuration for execution coordinator node."""
    parallel_execution: bool = field(
        default_factory=lambda: os.getenv("EXECUTOR_PARALLEL_EXECUTION", "true").lower() == "true"
    )
    max_parallel_tasks: int = field(
        default_factory=lambda: int(os.getenv("EXECUTOR_MAX_PARALLEL_TASKS", "5"))
    )
    execution_timeout: float = field(
        default_factory=lambda: float(os.getenv("EXECUTOR_EXECUTION_TIMEOUT", "30.0"))
    )
    retry_failed_executions: bool = field(
        default_factory=lambda: os.getenv("EXECUTOR_RETRY_FAILED", "true").lower() == "true"
    )
    max_retry_attempts: int = field(
        default_factory=lambda: int(os.getenv("EXECUTOR_MAX_RETRY_ATTEMPTS", "3"))
    )
    retry_delay: float = field(
        default_factory=lambda: float(os.getenv("EXECUTOR_RETRY_DELAY", "2.0"))
    )
    emergency_override_path: str = field(
        default_factory=lambda: os.getenv("EXECUTOR_EMERGENCY_OVERRIDE_PATH", "config/emergency_override.py")
    )
    success_threshold: float = field(
        default_factory=lambda: float(os.getenv("EXECUTOR_SUCCESS_THRESHOLD", "0.9"))
    )


@dataclass
class SecurityConfig:
    """Security configuration settings."""
    enable_authentication: bool = field(
        default_factory=lambda: os.getenv("SECURITY_ENABLE_AUTH", "true").lower() == "true"
    )
    auth_token_expiry: int = field(
        default_factory=lambda: int(os.getenv("SECURITY_TOKEN_EXPIRY", "3600"))
    )
    enable_encryption: bool = field(
        default_factory=lambda: os.getenv("SECURITY_ENABLE_ENCRYPTION", "true").lower() == "true"
    )
    encryption_key_path: Optional[str] = field(
        default_factory=lambda: os.getenv("SECURITY_ENCRYPTION_KEY_PATH")
    )
    enable_audit_logging: bool = field(
        default_factory=lambda: os.getenv("SECURITY_ENABLE_AUDIT", "true").lower() == "true"
    )
    audit_log_path: str = field(
        default_factory=lambda: os.getenv("SECURITY_AUDIT_LOG_PATH", "logs/audit.log")
    )
    allowed_ips: List[str] = field(default_factory=list)
    blocked_ips: List[str] = field(default_factory=list)
    
    def __post_init__(self):
        """Load IP lists from environment."""
        allowed = os.getenv("SECURITY_ALLOWED_IPS", "")
        if allowed:
            self.allowed_ips = [ip.strip() for ip in allowed.split(",")]
            
        blocked = os.getenv("SECURITY_BLOCKED_IPS", "")
        if blocked:
            self.blocked_ips = [ip.strip() for ip in blocked.split(",")]


@dataclass
class ErrorHandlingConfig:
    """Error handling configuration."""
    circuit_breaker_enabled: bool = field(
        default_factory=lambda: os.getenv("ERROR_CIRCUIT_BREAKER_ENABLED", "true").lower() == "true"
    )
    circuit_breaker_threshold: int = field(
        default_factory=lambda: int(os.getenv("ERROR_CIRCUIT_BREAKER_THRESHOLD", "5"))
    )
    circuit_breaker_timeout: float = field(
        default_factory=lambda: float(os.getenv("ERROR_CIRCUIT_BREAKER_TIMEOUT", "60.0"))
    )
    graceful_degradation: bool = field(
        default_factory=lambda: os.getenv("ERROR_GRACEFUL_DEGRADATION", "true").lower() == "true"
    )
    error_reporting_enabled: bool = field(
        default_factory=lambda: os.getenv("ERROR_REPORTING_ENABLED", "true").lower() == "true"
    )
    error_reporting_endpoint: Optional[str] = field(
        default_factory=lambda: os.getenv("ERROR_REPORTING_ENDPOINT")
    )
    max_error_log_size: int = field(
        default_factory=lambda: int(os.getenv("ERROR_MAX_LOG_SIZE", "10485760"))  # 10MB
    )


@dataclass
class GraphFlowConfig:
    """Main configuration for GraphFlow gateway agent."""
    # Core settings
    max_concurrent_stimuli: int = field(
        default_factory=lambda: int(os.getenv("GRAPHFLOW_MAX_CONCURRENT_STIMULI", "50"))
    )
    processing_timeout: float = field(
        default_factory=lambda: float(os.getenv("GRAPHFLOW_PROCESSING_TIMEOUT", "30.0"))
    )
    retry_attempts: int = field(
        default_factory=lambda: int(os.getenv("GRAPHFLOW_RETRY_ATTEMPTS", "3"))
    )
    
    # LLM settings
    llm_provider: str = field(
        default_factory=lambda: os.getenv("GRAPHFLOW_LLM_PROVIDER", "ollama")
    )
    llm_model: str = field(
        default_factory=lambda: os.getenv("GRAPHFLOW_LLM_MODEL", "llama3.2:3b")
    )
    llm_endpoint: str = field(
        default_factory=lambda: os.getenv("GRAPHFLOW_LLM_ENDPOINT", "http://ollama:11434")
    )
    llm_temperature: float = field(
        default_factory=lambda: float(os.getenv("GRAPHFLOW_LLM_TEMPERATURE", "0.3"))
    )
    llm_api_key: Optional[str] = field(
        default_factory=lambda: os.getenv("GRAPHFLOW_LLM_API_KEY")
    )
    
    # Decision thresholds
    categorization_confidence_threshold: float = field(
        default_factory=lambda: float(os.getenv("GRAPHFLOW_CATEGORIZATION_THRESHOLD", "0.8"))
    )
    context_analysis_depth: ContextAnalysisDepth = field(
        default_factory=lambda: ContextAnalysisDepth(
            os.getenv("GRAPHFLOW_CONTEXT_ANALYSIS_DEPTH", "standard")
        )
    )
    
    # Integration settings
    system1: System1Config = field(default_factory=System1Config)
    system2: System2Config = field(default_factory=System2Config)
    external_apis: ExternalAPIConfig = field(default_factory=ExternalAPIConfig)
    
    # Node configurations
    categorizer: CategorizerConfig = field(default_factory=CategorizerConfig)
    analyzer: AnalyzerConfig = field(default_factory=AnalyzerConfig)
    router: RouterConfig = field(default_factory=RouterConfig)
    executor: ExecutorConfig = field(default_factory=ExecutorConfig)
    
    # Security and error handling
    security: SecurityConfig = field(default_factory=SecurityConfig)
    error_handling: ErrorHandlingConfig = field(default_factory=ErrorHandlingConfig)
    
    # Monitoring
    metrics_enabled: bool = field(
        default_factory=lambda: os.getenv("GRAPHFLOW_METRICS_ENABLED", "true").lower() == "true"
    )
    metrics_port: int = field(
        default_factory=lambda: int(os.getenv("GRAPHFLOW_METRICS_PORT", "9090"))
    )
    detailed_logging: bool = field(
        default_factory=lambda: os.getenv("GRAPHFLOW_DETAILED_LOGGING", "true").lower() == "true"
    )
    performance_tracking: bool = field(
        default_factory=lambda: os.getenv("GRAPHFLOW_PERFORMANCE_TRACKING", "true").lower() == "true"
    )
    log_level: str = field(
        default_factory=lambda: os.getenv("GRAPHFLOW_LOG_LEVEL", "INFO")
    )
    
    # Database settings
    redis_url: str = field(
        default_factory=lambda: os.getenv("REDIS_URL", "redis://redis:6379")
    )
    postgres_url: str = field(
        default_factory=lambda: os.getenv("POSTGRES_URL", "postgresql://postgres:password@postgres:5432/graphflow")
    )
    
    def validate(self) -> List[str]:
        """Validate configuration and return list of errors."""
        errors = []
        
        # Validate core settings
        if self.max_concurrent_stimuli <= 0:
            errors.append("max_concurrent_stimuli must be positive")
        if self.processing_timeout <= 0:
            errors.append("processing_timeout must be positive")
        if self.retry_attempts < 0:
            errors.append("retry_attempts must be non-negative")
            
        # Validate LLM settings
        if self.llm_provider not in ["ollama", "openai", "azure"]:
            errors.append(f"Unsupported LLM provider: {self.llm_provider}")
        if self.llm_temperature < 0 or self.llm_temperature > 2:
            errors.append("llm_temperature must be between 0 and 2")
            
        # Validate thresholds
        if not 0 <= self.categorization_confidence_threshold <= 1:
            errors.append("categorization_confidence_threshold must be between 0 and 1")
            
        # Validate node configurations
        if not 0 <= self.categorizer.confidence_threshold <= 1:
            errors.append("categorizer.confidence_threshold must be between 0 and 1")
        if self.categorizer.fallback_category not in [e.value for e in StimuliCategory]:
            errors.append(f"Invalid fallback category: {self.categorizer.fallback_category}")
            
        # Validate router fallback decision
        if self.router.fallback_decision not in [e.value for e in ProcessingDecision]:
            errors.append(f"Invalid fallback decision: {self.router.fallback_decision}")
            
        return errors


def load_config(config_path: Optional[str] = None) -> GraphFlowConfig:
    """
    Load configuration from environment variables and optional config file.
    
    Args:
        config_path: Optional path to configuration file
        
    Returns:
        GraphFlowConfig instance with loaded settings
        
    Raises:
        ValueError: If configuration validation fails
    """
    # Load environment variables from file if specified
    if config_path and Path(config_path).exists():
        with open(config_path, 'r') as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#') and '=' in line:
                    key, value = line.split('=', 1)
                    os.environ[key.strip()] = value.strip()
    
    # Create configuration instance
    config = GraphFlowConfig()
    
    # Validate configuration
    errors = config.validate()
    if errors:
        raise ValueError(f"Configuration validation failed: {'; '.join(errors)}")
    
    return config


def save_config(config: GraphFlowConfig, output_path: str) -> None:
    """
    Save configuration to file for debugging/documentation.
    
    Args:
        config: Configuration instance to save
        output_path: Path to save configuration
    """
    import json
    from dataclasses import asdict
    
    config_dict = asdict(config)
    
    # Convert enums to strings
    def convert_enums(obj):
        if isinstance(obj, Enum):
            return obj.value
        elif isinstance(obj, dict):
            return {k: convert_enums(v) for k, v in obj.items()}
        elif isinstance(obj, list):
            return [convert_enums(v) for v in obj]
        return obj
    
    config_dict = convert_enums(config_dict)
    
    with open(output_path, 'w') as f:
        json.dump(config_dict, f, indent=2, default=str)


# Example usage and testing
if __name__ == "__main__":
    # Load configuration
    config = load_config()
    
    # Print configuration summary
    print(f"GraphFlow Configuration Summary:")
    print(f"  Max Concurrent Stimuli: {config.max_concurrent_stimuli}")
    print(f"  LLM Provider: {config.llm_provider}")
    print(f"  LLM Model: {config.llm_model}")
    print(f"  System1 Endpoint: {config.system1.vtuber_endpoint}")
    print(f"  System2 Endpoint: {config.system2.autogen_endpoint}")
    print(f"  External API Enabled: {config.external_apis.enabled}")
    print(f"  Metrics Enabled: {config.metrics_enabled}")
    
    # Validate configuration
    errors = config.validate()
    if errors:
        print(f"\nConfiguration errors: {errors}")
    else:
        print("\nConfiguration is valid!")