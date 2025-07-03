"""
Input validation and sanitization utilities for the GraphFlow External Stimuli System.

This module provides comprehensive input validation, content sanitization,
and validation result handling as specified in FRD section 10.2.
"""

import html
import re
from dataclasses import dataclass, field
from typing import Dict, Any, List, Optional
from datetime import datetime
import json


@dataclass
class ValidationResult:
    """Result of input validation."""
    valid: bool
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    sanitized_data: Dict[str, Any] = field(default_factory=dict)
    validation_timestamp: datetime = field(default_factory=datetime.now)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert validation result to dictionary."""
        return {
            "valid": self.valid,
            "errors": self.errors,
            "warnings": self.warnings,
            "sanitized_data": self.sanitized_data,
            "validation_timestamp": self.validation_timestamp.isoformat()
        }


class InputValidator:
    """
    Validate and sanitize input data for stimuli processing.
    
    Provides comprehensive validation for:
    - Content length and format
    - Source validation
    - Metadata structure
    - Content sanitization
    - Security checks
    """
    
    # Configuration constants
    MAX_CONTENT_LENGTH = 10000
    MIN_CONTENT_LENGTH = 1
    ALLOWED_SOURCES = [
        "user_chat", 
        "admin_console", 
        "social_media", 
        "system",
        "external_api",
        "webhook",
        "test"
    ]
    ALLOWED_PRIORITIES = ["high", "medium", "low"]
    MAX_METADATA_SIZE = 5000  # Max size for metadata JSON
    
    # Regex patterns for validation
    DANGEROUS_PATTERNS = [
        r'<script[^>]*>.*?</script>',  # Script tags
        r'javascript:',                  # JavaScript URLs
        r'on\w+\s*=',                   # Event handlers
        r'<iframe[^>]*>',               # Iframes
        r'<object[^>]*>',               # Object tags
        r'<embed[^>]*>',                # Embed tags
    ]
    
    URL_PATTERN = re.compile(
        r'http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\\(\\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+'
    )
    
    EMAIL_PATTERN = re.compile(
        r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}'
    )
    
    def __init__(self, 
                 max_content_length: Optional[int] = None,
                 allowed_sources: Optional[List[str]] = None,
                 enable_strict_mode: bool = False):
        """
        Initialize input validator.
        
        Args:
            max_content_length: Override default max content length
            allowed_sources: Override default allowed sources
            enable_strict_mode: Enable stricter validation rules
        """
        self.max_content_length = max_content_length or self.MAX_CONTENT_LENGTH
        self.allowed_sources = allowed_sources or self.ALLOWED_SOURCES
        self.strict_mode = enable_strict_mode
    
    def validate_stimuli(self, stimuli_data: Dict[str, Any]) -> ValidationResult:
        """
        Comprehensive input validation for stimuli data.
        
        Args:
            stimuli_data: Raw stimuli data to validate
            
        Returns:
            ValidationResult with validation status and sanitized data
        """
        errors = []
        warnings = []
        
        # Validate required fields
        if not stimuli_data.get("content"):
            errors.append("Content is required")
        
        if not stimuli_data.get("source"):
            errors.append("Source is required")
        
        # If required fields are missing, return early
        if errors:
            return ValidationResult(
                valid=False,
                errors=errors,
                sanitized_data={}
            )
        
        # Validate content
        content = stimuli_data.get("content", "")
        content_errors, content_warnings, sanitized_content = self._validate_content(content)
        errors.extend(content_errors)
        warnings.extend(content_warnings)
        
        # Validate source
        source = stimuli_data.get("source", "")
        source_errors = self._validate_source(source)
        errors.extend(source_errors)
        
        # Validate priority if provided
        if "priority" in stimuli_data:
            priority_errors = self._validate_priority(stimuli_data["priority"])
            errors.extend(priority_errors)
        
        # Validate metadata if provided
        if "metadata" in stimuli_data:
            metadata_errors, sanitized_metadata = self._validate_metadata(
                stimuli_data["metadata"]
            )
            errors.extend(metadata_errors)
        else:
            sanitized_metadata = {}
        
        # Validate processing options if provided
        if "processing_options" in stimuli_data:
            options_errors = self._validate_processing_options(
                stimuli_data["processing_options"]
            )
            errors.extend(options_errors)
        
        # Check for suspicious patterns in strict mode
        if self.strict_mode:
            suspicious_patterns = self._check_suspicious_patterns(content)
            if suspicious_patterns:
                warnings.append(f"Suspicious patterns detected: {suspicious_patterns}")
        
        # Build sanitized data
        sanitized_data = {
            "content": sanitized_content,
            "source": source,
            "timestamp": datetime.now().isoformat()
        }
        
        # Add optional fields if valid
        if "priority" in stimuli_data and not priority_errors:
            sanitized_data["priority"] = stimuli_data["priority"]
        
        if "metadata" in stimuli_data and not metadata_errors:
            sanitized_data["metadata"] = sanitized_metadata
        
        if "processing_options" in stimuli_data and not options_errors:
            sanitized_data["processing_options"] = stimuli_data["processing_options"]
        
        return ValidationResult(
            valid=len(errors) == 0,
            errors=errors,
            warnings=warnings,
            sanitized_data=sanitized_data
        )
    
    def _validate_content(self, content: str) -> tuple[List[str], List[str], str]:
        """
        Validate and sanitize content.
        
        Args:
            content: Raw content string
            
        Returns:
            Tuple of (errors, warnings, sanitized_content)
        """
        errors = []
        warnings = []
        
        # Check content length
        if len(content) < self.MIN_CONTENT_LENGTH:
            errors.append(f"Content too short (minimum {self.MIN_CONTENT_LENGTH} characters)")
        elif len(content) > self.max_content_length:
            errors.append(f"Content exceeds maximum length of {self.max_content_length}")
        
        # Check for empty content after stripping
        if not content.strip():
            errors.append("Content cannot be empty or whitespace only")
        
        # Sanitize content
        sanitized_content = self._sanitize_content(content)
        
        # Check if content was significantly modified during sanitization
        if len(sanitized_content) < len(content) * 0.5:
            warnings.append("Content was heavily sanitized (>50% removed)")
        
        # Check for potential issues
        if self._contains_excessive_caps(content):
            warnings.append("Content contains excessive capitalization")
        
        if self._contains_excessive_punctuation(content):
            warnings.append("Content contains excessive punctuation")
        
        return errors, warnings, sanitized_content
    
    def _validate_source(self, source: str) -> List[str]:
        """
        Validate source identifier.
        
        Args:
            source: Source identifier
            
        Returns:
            List of validation errors
        """
        errors = []
        
        if not source:
            errors.append("Source cannot be empty")
        elif source not in self.allowed_sources:
            errors.append(
                f"Invalid source '{source}'. Allowed sources: {', '.join(self.allowed_sources)}"
            )
        
        return errors
    
    def _validate_priority(self, priority: str) -> List[str]:
        """
        Validate priority level.
        
        Args:
            priority: Priority level
            
        Returns:
            List of validation errors
        """
        errors = []
        
        if priority not in self.ALLOWED_PRIORITIES:
            errors.append(
                f"Invalid priority '{priority}'. "
                f"Allowed priorities: {', '.join(self.ALLOWED_PRIORITIES)}"
            )
        
        return errors
    
    def _validate_metadata(self, metadata: Any) -> tuple[List[str], Dict[str, Any]]:
        """
        Validate and sanitize metadata.
        
        Args:
            metadata: Metadata object
            
        Returns:
            Tuple of (errors, sanitized_metadata)
        """
        errors = []
        
        if not isinstance(metadata, dict):
            errors.append("Metadata must be a dictionary/object")
            return errors, {}
        
        # Check metadata size
        try:
            metadata_json = json.dumps(metadata)
            if len(metadata_json) > self.MAX_METADATA_SIZE:
                errors.append(
                    f"Metadata size exceeds maximum of {self.MAX_METADATA_SIZE} bytes"
                )
        except (TypeError, ValueError) as e:
            errors.append(f"Metadata is not JSON serializable: {str(e)}")
            return errors, {}
        
        # Sanitize metadata values
        sanitized_metadata = {}
        for key, value in metadata.items():
            if isinstance(value, str):
                sanitized_metadata[key] = self._sanitize_content(value, minimal=True)
            else:
                sanitized_metadata[key] = value
        
        return errors, sanitized_metadata
    
    def _validate_processing_options(self, options: Any) -> List[str]:
        """
        Validate processing options.
        
        Args:
            options: Processing options
            
        Returns:
            List of validation errors
        """
        errors = []
        
        if not isinstance(options, dict):
            errors.append("Processing options must be a dictionary/object")
            return errors
        
        # Validate specific options
        if "force_avatar" in options and not isinstance(options["force_avatar"], bool):
            errors.append("force_avatar must be a boolean")
        
        if "bypass_analysis" in options and not isinstance(options["bypass_analysis"], bool):
            errors.append("bypass_analysis must be a boolean")
        
        if "timeout" in options:
            timeout = options["timeout"]
            if not isinstance(timeout, (int, float)):
                errors.append("timeout must be a number")
            elif timeout <= 0:
                errors.append("timeout must be positive")
            elif timeout > 300:  # 5 minutes max
                errors.append("timeout cannot exceed 300 seconds")
        
        return errors
    
    def _sanitize_content(self, content: str, minimal: bool = False) -> str:
        """
        Sanitize input content.
        
        Args:
            content: Raw content to sanitize
            minimal: Use minimal sanitization (for metadata)
            
        Returns:
            Sanitized content
        """
        if not content:
            return ""
        
        # HTML escape
        sanitized = html.escape(content)
        
        if not minimal:
            # Remove dangerous patterns
            for pattern in self.DANGEROUS_PATTERNS:
                sanitized = re.sub(pattern, '', sanitized, flags=re.IGNORECASE)
            
            # Remove control characters
            sanitized = ''.join(char for char in sanitized if ord(char) >= 32 or char in '\n\r\t')
            
            # Normalize whitespace
            sanitized = ' '.join(sanitized.split())
        
        return sanitized.strip()
    
    def _check_suspicious_patterns(self, content: str) -> List[str]:
        """
        Check for suspicious patterns in content.
        
        Args:
            content: Content to check
            
        Returns:
            List of suspicious patterns found
        """
        patterns_found = []
        
        # Check for SQL injection patterns
        sql_patterns = [
            r'\b(union|select|insert|update|delete|drop)\b.*\b(from|where|table)\b',
            r';\s*(delete|drop|exec|execute)',
            r'--\s*$',
            r'/\*.*\*/',
        ]
        
        for pattern in sql_patterns:
            if re.search(pattern, content, re.IGNORECASE):
                patterns_found.append("SQL injection pattern")
                break
        
        # Check for command injection patterns
        cmd_patterns = [
            r'[;&|].*\b(rm|del|format|shutdown|reboot)\b',
            r'\$\(.*\)',
            r'`.*`',
        ]
        
        for pattern in cmd_patterns:
            if re.search(pattern, content):
                patterns_found.append("Command injection pattern")
                break
        
        # Check for excessive URLs
        urls = self.URL_PATTERN.findall(content)
        if len(urls) > 5:
            patterns_found.append(f"Excessive URLs ({len(urls)})")
        
        return patterns_found
    
    def _contains_excessive_caps(self, content: str) -> bool:
        """Check if content contains excessive capitalization."""
        if len(content) < 10:
            return False
        
        words = content.split()
        if not words:
            return False
        
        caps_words = sum(1 for word in words if word.isupper() and len(word) > 1)
        return caps_words / len(words) > 0.5
    
    def _contains_excessive_punctuation(self, content: str) -> bool:
        """Check if content contains excessive punctuation."""
        if len(content) < 10:
            return False
        
        punctuation_count = sum(1 for char in content if char in '!?.')
        return punctuation_count / len(content) > 0.1
    
    def validate_api_key(self, api_key: str) -> ValidationResult:
        """
        Validate API key format.
        
        Args:
            api_key: API key to validate
            
        Returns:
            ValidationResult
        """
        errors = []
        
        if not api_key:
            errors.append("API key is required")
        elif len(api_key) < 32:
            errors.append("API key too short")
        elif not re.match(r'^[a-zA-Z0-9_-]+$', api_key):
            errors.append("API key contains invalid characters")
        
        return ValidationResult(
            valid=len(errors) == 0,
            errors=errors,
            sanitized_data={"api_key": api_key} if not errors else {}
        )