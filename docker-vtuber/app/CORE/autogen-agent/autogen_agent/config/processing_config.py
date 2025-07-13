"""
Processing Configuration Constants
=================================

Central configuration for all processing parameters to avoid magic numbers
and make the system more maintainable.
"""

class ProcessingConfig:
    """Configuration constants for queue processing and team coordination."""
    
    # Queue Consumer Settings
    DEFAULT_POLL_INTERVAL = 5.0
    MAX_RETRIES = 5
    BACKOFF_BASE_SECONDS = 2.0
    BACKOFF_MAX_SECONDS = 10.0
    PROCESSED_ITEMS_LIMIT = 100
    
    # AutoGen Team Settings
    DEFAULT_MAX_ROUNDS = 5
    GROUP_CHAT_TIMEOUT = 60.0
    TEAM_INITIALIZATION_TIMEOUT = 30.0
    
    # Character State Management
    SYNC_INTERVAL = 30
    STATE_CLEANUP_INTERVAL = 300  # 5 minutes
    MAX_IDLE_SESSIONS = 50
    
    # Stimuli Processing
    CONTENT_ANALYSIS_TIMEOUT = 10.0
    ROUTING_DECISION_TIMEOUT = 5.0
    
    # Error Handling
    MAX_ERROR_LOGS_PER_MINUTE = 10
    ERROR_COOLDOWN_SECONDS = 60
    
    # Performance Monitoring
    HEALTH_CHECK_INTERVAL = 30
    METRICS_COLLECTION_INTERVAL = 60


class LoggingConfig:
    """Configuration for logging behavior."""
    
    # Log Levels
    DEFAULT_LEVEL = "INFO"
    DEBUG_COMPONENTS = ["queue", "team", "character"]
    
    # Log Formatting
    COMPONENT_WIDTH = 8
    MESSAGE_PREFIX_EMOJI = {
        "queue": "🔄",
        "team": "🤖", 
        "character": "👤",
        "error": "❌",
        "success": "✅",
        "warning": "⚠️",
        "info": "ℹ️"
    }
    
    # Performance Logging
    SLOW_OPERATION_THRESHOLD = 5.0  # seconds
    LOG_PERFORMANCE_METRICS = True


class TeamConfig:
    """Configuration for AutoGen team behavior."""
    
    # Team Types
    VALID_TEAM_TYPES = ["trader", "educator", "streamer"]
    
    # Team Composition
    AGENTS_PER_TEAM = 4
    
    # Content Analysis Keywords
    TEAM_KEYWORDS = {
        "trader": ["market", "trading", "bitcoin", "crypto", "stock", "invest", "finance", "portfolio"],
        "educator": ["teach", "learn", "explain", "education", "lesson", "student", "course", "tutorial"],
        "streamer": ["stream", "content", "video", "audience", "engage", "gaming", "entertainment", "broadcast"]
    }
    
    # Default Team Selection
    DEFAULT_TEAM = "educator"


class FileConfig:
    """Configuration for file operations."""
    
    # Queue Files
    DEFAULT_QUEUE_FILE = "/tmp/s2_queue/s2_processing_queue.json"
    DEFAULT_PROCESSED_FILE = "/tmp/s2_queue/s2_processed_stimuli.json"
    
    # Character Files
    CHARACTERS_DIR = "/app/AVATAR/NeuroBridge/NeuroSync_Player/characters"
    
    # Log Files
    LOG_DIR = "/app/logs"
    MAX_LOG_SIZE_MB = 100
    LOG_RETENTION_DAYS = 7