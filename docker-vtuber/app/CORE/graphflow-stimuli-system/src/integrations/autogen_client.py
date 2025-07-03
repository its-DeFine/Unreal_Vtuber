"""
AutoGen HTTP Client for GraphFlow.

This module provides the HTTP client for communicating with the AutoGen
agent system, handling agent interactions, task management, and evolution engine.
"""

import asyncio
import aiohttp
from typing import Dict, Any, Optional, List, Tuple
from datetime import datetime
import json
from enum import Enum

from ..utils.logging import get_structured_logger


class AgentType(Enum):
    """Available agent types in the AutoGen system."""
    COGNITIVE_AI = "cognitive_ai_agent"
    PROGRAMMER = "programmer_agent"
    OBSERVER = "observer_agent"


class TaskStatus(Enum):
    """Task status enumeration."""
    SUBMITTED = "submitted"
    QUEUED = "queued"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class AutoGenClient:
    """
    HTTP client for AutoGen agent system communication.
    
    Provides methods for:
    - Task submission and management
    - Agent status monitoring
    - Evolution engine triggers
    - Response parsing and error handling
    """
    
    def __init__(self, endpoint: str, timeout: float = 30.0, max_retries: int = 3):
        """
        Initialize AutoGen client.
        
        Args:
            endpoint: Base URL for AutoGen API (e.g., http://autogen-agent:3100)
            timeout: Request timeout in seconds
            max_retries: Maximum number of retry attempts
        """
        self.endpoint = endpoint.rstrip('/')
        self.timeout = timeout
        self.max_retries = max_retries
        self.logger = get_structured_logger("autogen_client")
        
        # Session management
        self.session: Optional[aiohttp.ClientSession] = None
        self._session_lock = asyncio.Lock()
        
        # Request tracking
        self._active_requests: Dict[str, datetime] = {}
        
    async def ensure_session(self) -> aiohttp.ClientSession:
        """Ensure HTTP session is available."""
        async with self._session_lock:
            if self.session is None or self.session.closed:
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
                        "User-Agent": "GraphFlow/1.0",
                        "Accept": "application/json"
                    }
                )
            return self.session
    
    async def close(self) -> None:
        """Close the HTTP session."""
        async with self._session_lock:
            if self.session and not self.session.closed:
                await self.session.close()
                self.session = None
    
    async def submit_task(
        self, 
        task_data: Dict[str, Any],
        priority: str = "medium"
    ) -> Tuple[bool, Dict[str, Any]]:
        """
        Submit a task to AutoGen agents.
        
        Args:
            task_data: Task payload including content and metadata
            priority: Task priority (high, medium, low)
            
        Returns:
            Tuple of (success, response_data)
        """
        session = await self.ensure_session()
        url = f"{self.endpoint}/api/v1/tasks/submit"
        
        # Add priority to task data
        task_data["priority"] = priority
        task_data["submitted_at"] = datetime.utcnow().isoformat()
        
        for attempt in range(self.max_retries):
            try:
                async with session.post(
                    url,
                    json=task_data,
                    headers={"Content-Type": "application/json"}
                ) as response:
                    response_data = await response.json()
                    
                    if response.status == 200:
                        self.logger.info(
                            "Task submitted successfully",
                            task_id=response_data.get("task_id"),
                            attempt=attempt + 1
                        )
                        return True, response_data
                    else:
                        self.logger.warning(
                            f"Task submission failed: {response.status}",
                            error=response_data.get("error"),
                            attempt=attempt + 1
                        )
                        
                        # Don't retry on client errors
                        if 400 <= response.status < 500:
                            return False, response_data
                            
            except asyncio.TimeoutError:
                self.logger.error(f"Task submission timeout (attempt {attempt + 1})")
            except aiohttp.ClientError as e:
                self.logger.error(f"Task submission error: {e} (attempt {attempt + 1})")
            except Exception as e:
                self.logger.error(f"Unexpected error: {e}")
                return False, {"error": str(e)}
            
            # Exponential backoff
            if attempt < self.max_retries - 1:
                await asyncio.sleep(2 ** attempt)
        
        return False, {"error": "Max retries exceeded"}
    
    async def get_agents_status(self) -> Tuple[bool, List[Dict[str, Any]]]:
        """
        Get status of all AutoGen agents.
        
        Returns:
            Tuple of (success, list of agent status dicts)
        """
        session = await self.ensure_session()
        url = f"{self.endpoint}/api/v1/agents/status"
        
        try:
            async with session.get(url) as response:
                if response.status == 200:
                    data = await response.json()
                    agents = data.get("agents", [])
                    
                    # Enrich agent data
                    for agent in agents:
                        agent["status_timestamp"] = datetime.utcnow().isoformat()
                        agent["health"] = self._calculate_agent_health(agent)
                    
                    return True, agents
                else:
                    error_data = await response.json()
                    self.logger.error(
                        f"Failed to get agent status: {response.status}",
                        error=error_data.get("error")
                    )
                    return False, []
                    
        except Exception as e:
            self.logger.error(f"Agent status error: {e}")
            return False, []
    
    async def get_task_status(self, task_id: str) -> Tuple[bool, Dict[str, Any]]:
        """
        Get status of a specific task.
        
        Args:
            task_id: ID of the task to check
            
        Returns:
            Tuple of (success, task status dict)
        """
        session = await self.ensure_session()
        url = f"{self.endpoint}/api/v1/tasks/{task_id}/status"
        
        try:
            async with session.get(url) as response:
                if response.status == 200:
                    data = await response.json()
                    return True, data
                elif response.status == 404:
                    return False, {"error": "Task not found"}
                else:
                    error_data = await response.json()
                    return False, error_data
                    
        except Exception as e:
            self.logger.error(f"Task status error: {e}")
            return False, {"error": str(e)}
    
    async def get_task_result(self, task_id: str) -> Tuple[bool, Dict[str, Any]]:
        """
        Get result of a completed task.
        
        Args:
            task_id: ID of the task
            
        Returns:
            Tuple of (success, task result dict)
        """
        session = await self.ensure_session()
        url = f"{self.endpoint}/api/v1/tasks/{task_id}/result"
        
        try:
            async with session.get(url) as response:
                if response.status == 200:
                    data = await response.json()
                    return True, data
                elif response.status == 404:
                    return False, {"error": "Task not found"}
                elif response.status == 425:  # Too Early
                    return False, {"error": "Task not completed"}
                else:
                    error_data = await response.json()
                    return False, error_data
                    
        except Exception as e:
            self.logger.error(f"Task result error: {e}")
            return False, {"error": str(e)}
    
    async def cancel_task(self, task_id: str) -> bool:
        """
        Cancel an active task.
        
        Args:
            task_id: ID of the task to cancel
            
        Returns:
            Success status
        """
        session = await self.ensure_session()
        url = f"{self.endpoint}/api/v1/tasks/{task_id}/cancel"
        
        try:
            async with session.post(url) as response:
                if response.status == 200:
                    self.logger.info(f"Task {task_id} cancelled successfully")
                    return True
                else:
                    error_data = await response.json()
                    self.logger.warning(
                        f"Failed to cancel task: {response.status}",
                        error=error_data.get("error")
                    )
                    return False
                    
        except Exception as e:
            self.logger.error(f"Task cancellation error: {e}")
            return False
    
    async def trigger_evolution(
        self, 
        context_data: Dict[str, Any]
    ) -> Tuple[bool, Optional[str]]:
        """
        Trigger evolution engine analysis.
        
        Args:
            context_data: Context data for evolution analysis
            
        Returns:
            Tuple of (success, evolution_id or None)
        """
        session = await self.ensure_session()
        url = f"{self.endpoint}/api/v1/evolution/trigger"
        
        payload = {
            "context": context_data,
            "timestamp": datetime.utcnow().isoformat(),
            "source": "graphflow"
        }
        
        try:
            async with session.post(
                url,
                json=payload,
                headers={"Content-Type": "application/json"}
            ) as response:
                if response.status == 200:
                    data = await response.json()
                    evolution_id = data.get("evolution_id")
                    self.logger.info(
                        "Evolution triggered successfully",
                        evolution_id=evolution_id
                    )
                    return True, evolution_id
                else:
                    error_data = await response.json()
                    self.logger.warning(
                        f"Evolution trigger failed: {response.status}",
                        error=error_data.get("error")
                    )
                    return False, None
                    
        except Exception as e:
            self.logger.error(f"Evolution trigger error: {e}")
            return False, None
    
    async def send_agent_message(
        self,
        agent_id: str,
        message: Dict[str, Any]
    ) -> Tuple[bool, Optional[Dict[str, Any]]]:
        """
        Send a direct message to a specific agent.
        
        Args:
            agent_id: Target agent ID
            message: Message payload
            
        Returns:
            Tuple of (success, response or None)
        """
        session = await self.ensure_session()
        url = f"{self.endpoint}/api/v1/agents/{agent_id}/message"
        
        try:
            async with session.post(
                url,
                json=message,
                headers={"Content-Type": "application/json"}
            ) as response:
                if response.status == 200:
                    data = await response.json()
                    return True, data
                else:
                    error_data = await response.json()
                    self.logger.warning(
                        f"Agent message failed: {response.status}",
                        agent_id=agent_id,
                        error=error_data.get("error")
                    )
                    return False, None
                    
        except Exception as e:
            self.logger.error(f"Agent message error: {e}")
            return False, None
    
    async def health_check(self) -> bool:
        """
        Perform health check on AutoGen system.
        
        Returns:
            True if system is healthy
        """
        session = await self.ensure_session()
        url = f"{self.endpoint}/health"
        
        try:
            async with session.get(url, timeout=5.0) as response:
                if response.status == 200:
                    data = await response.json()
                    return data.get("status") == "healthy"
                else:
                    return False
                    
        except Exception:
            return False
    
    def _calculate_agent_health(self, agent_data: Dict[str, Any]) -> str:
        """
        Calculate agent health score.
        
        Args:
            agent_data: Agent status data
            
        Returns:
            Health status (healthy, degraded, unhealthy)
        """
        if not agent_data.get("is_active"):
            return "unhealthy"
        
        # Check error rate
        error_rate = agent_data.get("error_rate", 0)
        if error_rate > 0.1:  # >10% errors
            return "unhealthy"
        elif error_rate > 0.05:  # >5% errors
            return "degraded"
        
        # Check response time
        avg_response_time = agent_data.get("avg_response_time", 0)
        if avg_response_time > 10:  # >10 seconds
            return "degraded"
        
        # Check task queue
        queue_size = agent_data.get("queue_size", 0)
        if queue_size > 100:
            return "degraded"
        
        return "healthy"
    
    async def batch_submit_tasks(
        self,
        tasks: List[Dict[str, Any]]
    ) -> List[Tuple[bool, Dict[str, Any]]]:
        """
        Submit multiple tasks in batch.
        
        Args:
            tasks: List of task data dicts
            
        Returns:
            List of (success, response) tuples
        """
        # Submit tasks concurrently with rate limiting
        semaphore = asyncio.Semaphore(5)  # Max 5 concurrent submissions
        
        async def submit_with_limit(task_data):
            async with semaphore:
                return await self.submit_task(task_data)
        
        results = await asyncio.gather(
            *[submit_with_limit(task) for task in tasks],
            return_exceptions=True
        )
        
        # Convert exceptions to failure results
        processed_results = []
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                processed_results.append((False, {"error": str(result)}))
            else:
                processed_results.append(result)
        
        return processed_results