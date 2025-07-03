"""
LLM client interfaces for intelligent stimuli categorization.

This module provides abstract and concrete implementations for LLM integration,
supporting both local (Ollama) and cloud (OpenAI) providers.
"""

import asyncio
import json
import logging
from abc import ABC, abstractmethod
from typing import Any, Dict, Optional
import httpx
from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential,
    retry_if_exception_type
)


logger = logging.getLogger(__name__)


class LLMError(Exception):
    """Base exception for LLM-related errors."""
    pass


class LLMTimeoutError(LLMError):
    """Raised when LLM request times out."""
    pass


class LLMConnectionError(LLMError):
    """Raised when connection to LLM service fails."""
    pass


class LLMClient(ABC):
    """
    Abstract base class for LLM client implementations.
    
    Provides a consistent interface for different LLM providers.
    """
    
    @abstractmethod
    async def generate(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        temperature: float = 0.3,
        max_tokens: int = 1000,
        timeout: float = 30.0
    ) -> str:
        """
        Generate text completion from the LLM.
        
        Args:
            prompt: The user prompt.
            system_prompt: Optional system prompt for context.
            temperature: Sampling temperature (0.0 to 1.0).
            max_tokens: Maximum tokens in response.
            timeout: Request timeout in seconds.
            
        Returns:
            Generated text response.
            
        Raises:
            LLMError: On various LLM-related errors.
        """
        pass
    
    @abstractmethod
    async def health_check(self) -> bool:
        """
        Check if the LLM service is available.
        
        Returns:
            True if service is healthy, False otherwise.
        """
        pass


class OllamaLLMClient(LLMClient):
    """
    LLM client implementation for Ollama (local LLM).
    
    Connects to Ollama service typically running on port 11434.
    """
    
    def __init__(
        self,
        base_url: str = "http://localhost:11434",
        model: str = "llama3.2:3b",
        default_timeout: float = 30.0
    ):
        """
        Initialize Ollama client.
        
        Args:
            base_url: Base URL for Ollama service.
            model: Model to use for generation.
            default_timeout: Default request timeout.
        """
        self.base_url = base_url.rstrip('/')
        self.model = model
        self.default_timeout = default_timeout
        self.client = httpx.AsyncClient()
        
    async def __aenter__(self):
        """Async context manager entry."""
        return self
        
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        await self.client.aclose()
    
    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        retry=retry_if_exception_type(LLMConnectionError)
    )
    async def generate(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        temperature: float = 0.3,
        max_tokens: int = 1000,
        timeout: float = None
    ) -> str:
        """
        Generate text using Ollama.
        
        Args:
            prompt: The user prompt.
            system_prompt: Optional system prompt.
            temperature: Sampling temperature.
            max_tokens: Maximum tokens (Note: Ollama uses num_predict).
            timeout: Request timeout.
            
        Returns:
            Generated text response.
            
        Raises:
            LLMTimeoutError: If request times out.
            LLMConnectionError: If connection fails.
            LLMError: For other errors.
        """
        timeout = timeout or self.default_timeout
        
        # Build the full prompt
        if system_prompt:
            full_prompt = f"{system_prompt}\n\n{prompt}"
        else:
            full_prompt = prompt
        
        payload = {
            "model": self.model,
            "prompt": full_prompt,
            "temperature": temperature,
            "options": {
                "num_predict": max_tokens,
                "stop": ["\\n\\n", "User:", "Assistant:"]
            },
            "stream": False
        }
        
        try:
            logger.debug(f"Sending request to Ollama: model={self.model}, temperature={temperature}")
            
            response = await self.client.post(
                f"{self.base_url}/api/generate",
                json=payload,
                timeout=timeout
            )
            
            if response.status_code != 200:
                error_msg = f"Ollama returned status {response.status_code}: {response.text}"
                logger.error(error_msg)
                raise LLMError(error_msg)
            
            result = response.json()
            generated_text = result.get("response", "").strip()
            
            logger.debug(f"Ollama response received: {len(generated_text)} characters")
            return generated_text
            
        except httpx.TimeoutException:
            logger.error(f"Ollama request timed out after {timeout}s")
            raise LLMTimeoutError(f"Request timed out after {timeout} seconds")
            
        except httpx.ConnectError as e:
            logger.error(f"Failed to connect to Ollama: {e}")
            raise LLMConnectionError(f"Failed to connect to Ollama at {self.base_url}")
            
        except Exception as e:
            logger.error(f"Unexpected error in Ollama generation: {e}")
            raise LLMError(f"Unexpected error: {str(e)}")
    
    async def health_check(self) -> bool:
        """
        Check if Ollama service is available.
        
        Returns:
            True if service is healthy, False otherwise.
        """
        try:
            response = await self.client.get(
                f"{self.base_url}/api/tags",
                timeout=5.0
            )
            return response.status_code == 200
            
        except Exception as e:
            logger.warning(f"Ollama health check failed: {e}")
            return False


class OpenAILLMClient(LLMClient):
    """
    LLM client implementation for OpenAI API.
    
    This is a stub implementation for future OpenAI integration.
    """
    
    def __init__(
        self,
        api_key: str,
        model: str = "gpt-3.5-turbo",
        base_url: Optional[str] = None,
        default_timeout: float = 30.0
    ):
        """
        Initialize OpenAI client.
        
        Args:
            api_key: OpenAI API key.
            model: Model to use for generation.
            base_url: Optional custom base URL.
            default_timeout: Default request timeout.
        """
        self.api_key = api_key
        self.model = model
        self.base_url = base_url or "https://api.openai.com/v1"
        self.default_timeout = default_timeout
        
        # Note: In production, use the official OpenAI Python client
        logger.warning("OpenAILLMClient is a stub implementation")
    
    async def generate(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        temperature: float = 0.3,
        max_tokens: int = 1000,
        timeout: float = None
    ) -> str:
        """
        Generate text using OpenAI API.
        
        This is a stub implementation.
        """
        raise NotImplementedError("OpenAI client is not yet implemented")
    
    async def health_check(self) -> bool:
        """
        Check if OpenAI service is available.
        
        This is a stub implementation.
        """
        raise NotImplementedError("OpenAI client is not yet implemented")


class MockLLMClient(LLMClient):
    """
    Mock LLM client for testing purposes.
    
    Returns predefined responses based on input patterns.
    """
    
    def __init__(self, responses: Optional[Dict[str, str]] = None):
        """
        Initialize mock client.
        
        Args:
            responses: Optional mapping of patterns to responses.
        """
        self.responses = responses or {}
        self.default_response = "This is a mock LLM response."
        self.healthy = True
    
    async def generate(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        temperature: float = 0.3,
        max_tokens: int = 1000,
        timeout: float = None
    ) -> str:
        """
        Generate mock response.
        
        Returns predefined response based on prompt content.
        """
        # Simulate processing delay
        await asyncio.sleep(0.1)
        
        # Check for matching patterns
        prompt_lower = prompt.lower()
        for pattern, response in self.responses.items():
            if pattern.lower() in prompt_lower:
                return response
        
        # Default categorization based on keywords
        if "admin" in prompt_lower or "set" in prompt_lower:
            return json.dumps({
                "category": "DIRECT_ADMIN",
                "confidence": 0.9,
                "reasoning": "Contains administrative keywords"
            })
        elif "hello" in prompt_lower or "how are you" in prompt_lower:
            return json.dumps({
                "category": "USER_INTERACTION",
                "confidence": 0.95,
                "reasoning": "Typical user greeting"
            })
        elif "speaking" in prompt_lower or "idle" in prompt_lower:
            return json.dumps({
                "category": "SYSTEM_NOTIFICATION",
                "confidence": 0.99,
                "reasoning": "Avatar state notification"
            })
        elif "emergency" in prompt_lower or "urgent" in prompt_lower:
            return json.dumps({
                "category": "EMERGENCY",
                "confidence": 0.98,
                "reasoning": "Emergency keywords detected"
            })
        
        return json.dumps({
            "category": "CONTEXTUAL_UPDATE",
            "confidence": 0.5,
            "reasoning": "No specific patterns matched"
        })
    
    async def health_check(self) -> bool:
        """Check mock service health."""
        return self.healthy
    
    def set_healthy(self, healthy: bool):
        """Set mock service health status."""
        self.healthy = healthy


def create_llm_client(
    provider: str = "ollama",
    **kwargs
) -> LLMClient:
    """
    Factory function to create LLM client instances.
    
    Args:
        provider: LLM provider ("ollama", "openai", "mock").
        **kwargs: Provider-specific configuration.
        
    Returns:
        LLMClient instance.
        
    Raises:
        ValueError: If provider is not supported.
    """
    providers = {
        "ollama": OllamaLLMClient,
        "openai": OpenAILLMClient,
        "mock": MockLLMClient
    }
    
    if provider not in providers:
        raise ValueError(f"Unsupported LLM provider: {provider}")
    
    return providers[provider](**kwargs)