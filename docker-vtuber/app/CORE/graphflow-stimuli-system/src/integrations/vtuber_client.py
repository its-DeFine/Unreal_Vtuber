"""
VTuber Client for HTTP communication with the VTuber system.

This module provides a dedicated client for communicating with the VTuber
avatar system, handling all HTTP endpoints with proper error handling,
retries, and response validation.
"""

import asyncio
import aiohttp
from typing import Dict, Any, Optional, List, Literal
from datetime import datetime
import json
from urllib.parse import urljoin

from ..utils.logging import get_structured_logger
from ..utils.metrics import MetricsCollector


class VTuberClient:
    """
    HTTP client for VTuber system communication.
    
    Handles all communication with the VTuber avatar system including:
    - Speech synthesis
    - Character management
    - Mode switching
    - Status monitoring
    - Animation control
    """
    
    def __init__(self, base_url: str, timeout: float = 30.0, max_retries: int = 3):
        """
        Initialize VTuber client.
        
        Args:
            base_url: Base URL for VTuber system (e.g., http://neurosync:5001)
            timeout: Request timeout in seconds
            max_retries: Maximum number of retry attempts
        """
        self.base_url = base_url.rstrip('/')
        self.timeout = timeout
        self.max_retries = max_retries
        self.logger = get_structured_logger("vtuber_client")
        self.metrics = MetricsCollector()
        
        # HTTP session
        self.session: Optional[aiohttp.ClientSession] = None
        
        # Connection settings
        self.retry_delays = [1.0, 2.0, 4.0]  # Exponential backoff
        
    async def initialize(self) -> None:
        """Initialize the HTTP session."""
        if self.session:
            await self.session.close()
            
        timeout = aiohttp.ClientTimeout(total=self.timeout)
        connector = aiohttp.TCPConnector(
            limit=100,
            limit_per_host=30,
            ttl_dns_cache=300
        )
        
        self.session = aiohttp.ClientSession(
            timeout=timeout,
            connector=connector,
            headers={
                'User-Agent': 'GraphFlow-VTuber-Client/1.0',
                'Accept': 'application/json'
            }
        )
        
        self.logger.info("VTuber client initialized", base_url=self.base_url)
        
    async def close(self) -> None:
        """Close the HTTP session."""
        if self.session:
            await self.session.close()
            self.session = None
            
    async def speak(
        self,
        text: str,
        character_id: Optional[str] = None,
        emotion: str = "neutral",
        priority: str = "normal",
        metadata: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Trigger avatar speech with text.
        
        Args:
            text: Text to speak
            character_id: Optional character ID to use
            emotion: Emotion for speech (happy, sad, angry, neutral, etc.)
            priority: Priority level (high, normal, low)
            metadata: Additional metadata for speech control
            
        Returns:
            Response with speech job details
        """
        endpoint = "/speak"
        payload = {
            "text": text,
            "character_id": character_id,
            "emotion": emotion,
            "priority": priority,
            "metadata": metadata or {}
        }
        
        return await self._make_request("POST", endpoint, json=payload)
        
    async def get_status(self) -> Dict[str, Any]:
        """
        Get basic VTuber system status.
        
        Returns:
            Status information including availability
        """
        return await self._make_request("GET", "/status")
        
    async def get_detailed_status(self) -> Dict[str, Any]:
        """
        Get detailed VTuber system status.
        
        Returns:
            Detailed status including current state, character, queue info
        """
        return await self._make_request("GET", "/status/detailed")
        
    async def load_character(
        self,
        character_id: str,
        preset_data: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Load a character preset.
        
        Args:
            character_id: Character ID to load
            preset_data: Optional preset configuration data
            
        Returns:
            Response confirming character load
        """
        endpoint = "/character/load"
        payload = {
            "character_id": character_id,
            "preset_data": preset_data or {}
        }
        
        return await self._make_request("POST", endpoint, json=payload)
        
    async def list_characters(self) -> List[Dict[str, Any]]:
        """
        List available characters.
        
        Returns:
            List of available character configurations
        """
        response = await self._make_request("GET", "/character/list")
        return response.get("characters", [])
        
    async def get_current_character(self) -> Dict[str, Any]:
        """
        Get current active character.
        
        Returns:
            Current character information
        """
        return await self._make_request("GET", "/character/current")
        
    async def set_mode(self, mode: Literal["reactive", "autonomous"]) -> Dict[str, Any]:
        """
        Set VTuber operation mode.
        
        Args:
            mode: Operation mode (reactive or autonomous)
            
        Returns:
            Response confirming mode change
        """
        endpoint = "/mode/set"
        payload = {"mode": mode}
        
        return await self._make_request("POST", endpoint, json=payload)
        
    async def get_mode(self) -> str:
        """
        Get current operation mode.
        
        Returns:
            Current mode (reactive or autonomous)
        """
        response = await self._make_request("GET", "/mode")
        return response.get("mode", "unknown")
        
    async def trigger_animation(
        self,
        animation_name: str,
        duration: Optional[float] = None,
        parameters: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Trigger a specific animation.
        
        Args:
            animation_name: Name of animation to trigger
            duration: Optional duration override
            parameters: Animation-specific parameters
            
        Returns:
            Response with animation job details
        """
        endpoint = "/animation/trigger"
        payload = {
            "animation_name": animation_name,
            "duration": duration,
            "parameters": parameters or {}
        }
        
        return await self._make_request("POST", endpoint, json=payload)
        
    async def stop_current_action(self) -> Dict[str, Any]:
        """
        Stop current speech/animation.
        
        Returns:
            Response confirming action stopped
        """
        return await self._make_request("POST", "/action/stop")
        
    async def get_queue_status(self) -> Dict[str, Any]:
        """
        Get speech/animation queue status.
        
        Returns:
            Queue information including size and estimated wait time
        """
        return await self._make_request("GET", "/queue/status")
        
    async def clear_queue(self) -> Dict[str, Any]:
        """
        Clear the speech/animation queue.
        
        Returns:
            Response confirming queue cleared
        """
        return await self._make_request("POST", "/queue/clear")
        
    async def health_check(self) -> bool:
        """
        Perform health check on VTuber system.
        
        Returns:
            True if system is healthy, False otherwise
        """
        try:
            response = await self._make_request("GET", "/health", raise_on_error=False)
            return response.get("status") == "healthy"
        except Exception:
            return False
            
    async def _make_request(
        self,
        method: str,
        endpoint: str,
        json: Optional[Dict[str, Any]] = None,
        params: Optional[Dict[str, Any]] = None,
        raise_on_error: bool = True
    ) -> Dict[str, Any]:
        """
        Make HTTP request with retries and error handling.
        
        Args:
            method: HTTP method (GET, POST, etc.)
            endpoint: API endpoint path
            json: JSON payload for request
            params: Query parameters
            raise_on_error: Whether to raise exceptions on errors
            
        Returns:
            Response data as dictionary
            
        Raises:
            aiohttp.ClientError: On request failures (if raise_on_error=True)
        """
        if not self.session:
            raise RuntimeError("VTuber client not initialized")
            
        url = urljoin(self.base_url, endpoint)
        
        # Track metrics
        start_time = datetime.now()
        
        last_error = None
        for attempt in range(self.max_retries):
            try:
                async with self.session.request(
                    method,
                    url,
                    json=json,
                    params=params
                ) as response:
                    # Record metrics
                    duration = (datetime.now() - start_time).total_seconds()
                    self.metrics.record_http_request(
                        endpoint=endpoint,
                        method=method,
                        status_code=response.status,
                        duration=duration
                    )
                    
                    # Parse response
                    if response.content_type == 'application/json':
                        data = await response.json()
                    else:
                        text = await response.text()
                        data = {"response": text}
                        
                    # Check for errors
                    if response.status >= 400:
                        error_msg = data.get("error", f"HTTP {response.status}")
                        if raise_on_error:
                            raise aiohttp.ClientResponseError(
                                request_info=response.request_info,
                                history=response.history,
                                status=response.status,
                                message=error_msg,
                                headers=response.headers
                            )
                        else:
                            data["_error"] = error_msg
                            data["_status"] = response.status
                            
                    return data
                    
            except asyncio.TimeoutError:
                last_error = "Request timeout"
                self.logger.warning(
                    "VTuber request timeout",
                    endpoint=endpoint,
                    attempt=attempt + 1
                )
                
            except aiohttp.ClientError as e:
                last_error = str(e)
                self.logger.warning(
                    "VTuber request failed",
                    endpoint=endpoint,
                    error=str(e),
                    attempt=attempt + 1
                )
                
                if raise_on_error and attempt == self.max_retries - 1:
                    raise
                    
            except Exception as e:
                last_error = str(e)
                self.logger.error(
                    "Unexpected error in VTuber request",
                    endpoint=endpoint,
                    error=str(e),
                    attempt=attempt + 1
                )
                
                if raise_on_error:
                    raise
                    
            # Wait before retry (if not last attempt)
            if attempt < self.max_retries - 1:
                delay = self.retry_delays[min(attempt, len(self.retry_delays) - 1)]
                await asyncio.sleep(delay)
                
        # All retries failed
        if raise_on_error:
            raise aiohttp.ClientError(f"Request failed after {self.max_retries} attempts: {last_error}")
            
        return {
            "_error": f"Request failed: {last_error}",
            "_attempts": self.max_retries
        }
        
    async def validate_connection(self) -> bool:
        """
        Validate connection to VTuber system.
        
        Returns:
            True if connection is valid, False otherwise
        """
        try:
            await self.health_check()
            return True
        except Exception as e:
            self.logger.error(f"Connection validation failed: {e}")
            return False