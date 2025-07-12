"""
Unified Configuration Management System
=====================================

Single source of truth for all CORE system configuration.
Supports environment variables, JSON files, and runtime overrides.
"""

import os
import json
import logging
from pathlib import Path
from typing import Dict, Any, Optional, Union, List
from dataclasses import dataclass, field
from enum import Enum
import redis
from pydantic import Field, validator
from pydantic_settings import BaseSettings


class SystemMode(str, Enum):
    """System operational modes"""
    SIMPLIFIED = "simplified"  # S2 only with 3 teams
    FULL_AUTOGEN = "full_autogen"  # Complete autonomous system
    HYBRID = "hybrid"  # Both systems active


class LogLevel(str, Enum):
    """Logging levels"""
    DEBUG = "DEBUG"
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"


@dataclass
class QueueConfig:
    """Queue system configuration"""
    type: str = "redis"  # redis, file, memory
    redis_url: str = "redis://localhost:6379"
    redis_db: int = 0
    queue_prefix: str = "core_queue"
    max_retries: int = 3
    retry_delay: float = 1.0
    batch_size: int = 10
    poll_interval: float = 1.0


@dataclass
class DatabaseConfig:
    """Database configuration"""
    neo4j_uri: str = "neo4j://localhost:7687"
    neo4j_user: str = "neo4j"
    neo4j_password: str = ""
    neo4j_database: str = "neo4j"
    connection_pool_size: int = 10
    connection_timeout: float = 30.0


@dataclass
class SCBConfig:
    """SCB (Shared Contextual Bridge) configuration"""
    endpoint: str = "http://localhost:8080"
    timeout: float = 30.0
    max_retries: int = 3
    api_key: Optional[str] = None


@dataclass
class AutoGenConfig:
    """AutoGen system configuration"""
    model_name: str = "gpt-4"
    temperature: float = 0.7
    max_tokens: int = 2000
    max_rounds: int = 5
    timeout: float = 300.0
    enable_code_execution: bool = False


@dataclass
class MonitoringConfig:
    """Monitoring and metrics configuration"""
    enable_metrics: bool = True
    metrics_port: int = 9090
    health_check_interval: float = 30.0
    log_level: LogLevel = LogLevel.INFO
    enable_tracing: bool = False
    jaeger_endpoint: Optional[str] = None


@dataclass
class SecurityConfig:
    """Security configuration"""
    api_key_required: bool = True
    api_keys: List[str] = field(default_factory=list)
    rate_limit_requests: int = 100
    rate_limit_window: int = 60
    enable_cors: bool = True
    allowed_origins: List[str] = field(default_factory=lambda: ["*"])


class CoreConfig(BaseSettings):
    """
    Unified configuration for the entire CORE system.
    
    Configuration precedence (highest to lowest):
    1. Environment variables (prefixed with CORE_)
    2. JSON configuration files
    3. Default values
    """
    
    # System configuration
    system_mode: SystemMode = SystemMode.SIMPLIFIED
    debug: bool = False
    environment: str = "development"
    
    # Service configuration
    queue: QueueConfig = Field(default_factory=QueueConfig)
    database: DatabaseConfig = Field(default_factory=DatabaseConfig)
    scb: SCBConfig = Field(default_factory=SCBConfig)
    autogen: AutoGenConfig = Field(default_factory=AutoGenConfig)
    monitoring: MonitoringConfig = Field(default_factory=MonitoringConfig)
    security: SecurityConfig = Field(default_factory=SecurityConfig)
    
    # API configuration
    api_host: str = "0.0.0.0"
    api_port: int = 8000
    api_workers: int = 1
    
    # File paths
    data_dir: Path = Path("/tmp/core_data")
    log_dir: Path = Path("/tmp/core_logs")
    config_dir: Path = Path("/etc/core")
    
    model_config = {
        "env_prefix": "CORE_",
        "env_nested_delimiter": "__",
        "case_sensitive": False
    }
        
    @validator('data_dir', 'log_dir', 'config_dir', pre=True)
    def ensure_path_object(cls, v):
        return Path(v) if not isinstance(v, Path) else v
    
    def __post_init__(self):
        """Ensure directories exist"""
        for dir_path in [self.data_dir, self.log_dir]:
            dir_path.mkdir(parents=True, exist_ok=True)
    
    @classmethod
    def load_from_file(cls, config_path: Union[str, Path]) -> 'CoreConfig':
        """Load configuration from JSON file"""
        config_path = Path(config_path)
        if not config_path.exists():
            raise FileNotFoundError(f"Configuration file not found: {config_path}")
        
        with open(config_path, 'r') as f:
            config_data = json.load(f)
        
        return cls.parse_obj(config_data)
    
    def save_to_file(self, config_path: Union[str, Path]):
        """Save configuration to JSON file"""
        config_path = Path(config_path)
        config_path.parent.mkdir(parents=True, exist_ok=True)
        
        with open(config_path, 'w') as f:
            json.dump(self.dict(), f, indent=2, default=str)
    
    def get_redis_client(self) -> redis.Redis:
        """Get configured Redis client"""
        return redis.from_url(
            self.queue.redis_url,
            db=self.queue.redis_db,
            decode_responses=True
        )
    
    def validate_configuration(self) -> List[str]:
        """Validate configuration and return list of issues"""
        issues = []
        
        # Check Redis connectivity if using Redis queue
        if self.queue.type == "redis":
            try:
                client = self.get_redis_client()
                client.ping()
            except Exception as e:
                issues.append(f"Redis connection failed: {e}")
        
        # Check required directories
        for dir_name, dir_path in [
            ("data", self.data_dir),
            ("log", self.log_dir)
        ]:
            if not dir_path.exists():
                try:
                    dir_path.mkdir(parents=True, exist_ok=True)
                except Exception as e:
                    issues.append(f"Cannot create {dir_name} directory {dir_path}: {e}")
        
        # Validate API keys if security is enabled
        if self.security.api_key_required and not self.security.api_keys:
            issues.append("API key required but no keys configured")
        
        return issues


# Global configuration instance
_config: Optional[CoreConfig] = None


def get_config() -> CoreConfig:
    """Get the global configuration instance"""
    global _config
    if _config is None:
        raise RuntimeError("Configuration not initialized. Call initialize_config() first.")
    return _config


def initialize_config(
    config_file: Optional[Union[str, Path]] = None,
    **overrides
) -> CoreConfig:
    """
    Initialize the global configuration.
    
    Args:
        config_file: Optional path to JSON configuration file
        **overrides: Configuration overrides
    
    Returns:
        Initialized configuration instance
    """
    global _config
    
    if config_file:
        _config = CoreConfig.load_from_file(config_file)
    else:
        _config = CoreConfig()
    
    # Apply overrides
    if overrides:
        config_dict = _config.dict()
        config_dict.update(overrides)
        _config = CoreConfig.parse_obj(config_dict)
    
    # Validate configuration
    issues = _config.validate_configuration()
    if issues:
        logging.warning(f"Configuration validation issues: {issues}")
    
    # Setup logging
    logging.basicConfig(
        level=getattr(logging, _config.monitoring.log_level.value),
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    return _config


def reload_config():
    """Reload configuration from environment and files"""
    global _config
    if _config is not None:
        _config = CoreConfig()


# Environment-specific configuration loaders
def load_development_config() -> CoreConfig:
    """Load development configuration"""
    return initialize_config(
        system_mode=SystemMode.SIMPLIFIED,
        debug=True,
        environment="development",
        monitoring=MonitoringConfig(log_level=LogLevel.DEBUG),
        security=SecurityConfig(api_key_required=False)
    )


def load_production_config() -> CoreConfig:
    """Load production configuration"""
    config_file = os.getenv("CORE_CONFIG_FILE", "/etc/core/production.json")
    return initialize_config(
        config_file=config_file if Path(config_file).exists() else None,
        environment="production",
        debug=False,
        monitoring=MonitoringConfig(
            log_level=LogLevel.INFO,
            enable_metrics=True,
            enable_tracing=True
        ),
        security=SecurityConfig(
            api_key_required=True,
            rate_limit_requests=1000
        )
    )


def load_test_config() -> CoreConfig:
    """Load test configuration"""
    return initialize_config(
        system_mode=SystemMode.SIMPLIFIED,
        debug=True,
        environment="test",
        queue=QueueConfig(type="memory"),
        database=DatabaseConfig(neo4j_uri="neo4j://localhost:7688"),
        monitoring=MonitoringConfig(
            log_level=LogLevel.DEBUG,
            enable_metrics=False
        ),
        security=SecurityConfig(api_key_required=False)
    )


if __name__ == "__main__":
    # Example usage
    config = load_development_config()
    print("Configuration loaded successfully!")
    print(f"System mode: {config.system_mode}")
    print(f"Queue type: {config.queue.type}")
    print(f"API endpoint: {config.api_host}:{config.api_port}")