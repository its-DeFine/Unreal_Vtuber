"""
Agent Manager for GraphFlow.

This module provides agent coordination, load balancing, and health monitoring
for the AutoGen agent system integration.
"""

import asyncio
from typing import Dict, Any, Optional, List, Set
from datetime import datetime, timedelta
from collections import defaultdict
import random
from enum import Enum
from dataclasses import dataclass, field

from ..utils.logging import get_structured_logger
from .autogen_client import AutoGenClient, AgentType, TaskStatus


@dataclass
class AgentMetrics:
    """Metrics for individual agent performance."""
    total_tasks: int = 0
    successful_tasks: int = 0
    failed_tasks: int = 0
    total_response_time: float = 0.0
    last_task_time: Optional[datetime] = None
    error_count: int = 0
    consecutive_errors: int = 0
    
    @property
    def success_rate(self) -> float:
        """Calculate agent success rate."""
        if self.total_tasks == 0:
            return 1.0
        return self.successful_tasks / self.total_tasks
    
    @property
    def average_response_time(self) -> float:
        """Calculate average response time."""
        if self.total_tasks == 0:
            return 0.0
        return self.total_response_time / self.total_tasks
    
    @property
    def health_score(self) -> float:
        """Calculate overall health score (0-1)."""
        # Factors: success rate, error rate, response time
        success_factor = self.success_rate
        
        # Penalty for consecutive errors
        error_penalty = max(0, 1 - (self.consecutive_errors * 0.2))
        
        # Response time factor (penalize if > 5 seconds)
        time_factor = max(0, 1 - (self.average_response_time / 10))
        
        # Recent activity factor
        if self.last_task_time:
            minutes_since_last = (datetime.utcnow() - self.last_task_time).seconds / 60
            activity_factor = max(0, 1 - (minutes_since_last / 30))  # Penalty after 30 min
        else:
            activity_factor = 0.5
        
        # Weighted average
        return (
            success_factor * 0.4 +
            error_penalty * 0.3 +
            time_factor * 0.2 +
            activity_factor * 0.1
        )


@dataclass
class AgentInfo:
    """Information about an agent."""
    agent_id: str
    agent_type: AgentType
    is_available: bool = True
    current_tasks: Set[str] = field(default_factory=set)
    metrics: AgentMetrics = field(default_factory=AgentMetrics)
    last_health_check: Optional[datetime] = None
    capabilities: List[str] = field(default_factory=list)


class LoadBalancingStrategy(Enum):
    """Load balancing strategies for agent selection."""
    ROUND_ROBIN = "round_robin"
    LEAST_LOADED = "least_loaded"
    BEST_PERFORMANCE = "best_performance"
    WEIGHTED_RANDOM = "weighted_random"


class AgentManager:
    """
    Manages agent coordination, load balancing, and health monitoring.
    
    Responsibilities:
    - Track agent availability and health
    - Distribute tasks using load balancing
    - Monitor agent performance metrics
    - Handle agent failures and recovery
    """
    
    def __init__(
        self,
        autogen_client: AutoGenClient,
        strategy: LoadBalancingStrategy = LoadBalancingStrategy.BEST_PERFORMANCE,
        health_check_interval: int = 60,
        max_tasks_per_agent: int = 10
    ):
        """
        Initialize agent manager.
        
        Args:
            autogen_client: AutoGen client instance
            strategy: Load balancing strategy
            health_check_interval: Seconds between health checks
            max_tasks_per_agent: Maximum concurrent tasks per agent
        """
        self.client = autogen_client
        self.strategy = strategy
        self.health_check_interval = health_check_interval
        self.max_tasks_per_agent = max_tasks_per_agent
        self.logger = get_structured_logger("agent_manager")
        
        # Agent tracking
        self.agents: Dict[str, AgentInfo] = {}
        self._agent_lock = asyncio.Lock()
        
        # Task tracking
        self.task_assignments: Dict[str, str] = {}  # task_id -> agent_id
        self._task_lock = asyncio.Lock()
        
        # Round-robin index
        self._round_robin_index = 0
        
        # Health check task
        self._health_check_task: Optional[asyncio.Task] = None
        
        # Performance tracking
        self.global_metrics = {
            "total_tasks": 0,
            "successful_tasks": 0,
            "failed_tasks": 0,
            "total_response_time": 0.0
        }
    
    async def initialize(self) -> None:
        """Initialize agent manager and discover agents."""
        self.logger.info("Initializing agent manager")
        
        # Discover available agents
        await self._discover_agents()
        
        # Start health monitoring
        self._health_check_task = asyncio.create_task(self._health_monitor_loop())
        
        self.logger.info(
            f"Agent manager initialized with {len(self.agents)} agents",
            strategy=self.strategy.value
        )
    
    async def shutdown(self) -> None:
        """Shutdown agent manager."""
        self.logger.info("Shutting down agent manager")
        
        # Cancel health monitoring
        if self._health_check_task:
            self._health_check_task.cancel()
            try:
                await self._health_check_task
            except asyncio.CancelledError:
                pass
        
        # Clear agent data
        async with self._agent_lock:
            self.agents.clear()
        
        async with self._task_lock:
            self.task_assignments.clear()
    
    async def select_agent(
        self,
        task_type: Optional[str] = None,
        required_capabilities: Optional[List[str]] = None
    ) -> Optional[str]:
        """
        Select an agent for task assignment.
        
        Args:
            task_type: Type of task (optional)
            required_capabilities: Required agent capabilities (optional)
            
        Returns:
            Selected agent ID or None if no suitable agent
        """
        async with self._agent_lock:
            # Filter available agents
            available_agents = [
                agent for agent in self.agents.values()
                if agent.is_available and len(agent.current_tasks) < self.max_tasks_per_agent
            ]
            
            # Filter by capabilities if specified
            if required_capabilities:
                available_agents = [
                    agent for agent in available_agents
                    if all(cap in agent.capabilities for cap in required_capabilities)
                ]
            
            if not available_agents:
                self.logger.warning("No available agents for task assignment")
                return None
            
            # Apply load balancing strategy
            if self.strategy == LoadBalancingStrategy.ROUND_ROBIN:
                selected = self._select_round_robin(available_agents)
            elif self.strategy == LoadBalancingStrategy.LEAST_LOADED:
                selected = self._select_least_loaded(available_agents)
            elif self.strategy == LoadBalancingStrategy.BEST_PERFORMANCE:
                selected = self._select_best_performance(available_agents)
            else:  # WEIGHTED_RANDOM
                selected = self._select_weighted_random(available_agents)
            
            if selected:
                self.logger.info(
                    f"Selected agent {selected.agent_id} for task",
                    strategy=self.strategy.value,
                    current_load=len(selected.current_tasks),
                    health_score=selected.metrics.health_score
                )
                return selected.agent_id
            
            return None
    
    async def assign_task(self, task_id: str, agent_id: str) -> bool:
        """
        Assign a task to an agent.
        
        Args:
            task_id: Task ID
            agent_id: Agent ID
            
        Returns:
            Success status
        """
        async with self._agent_lock:
            if agent_id not in self.agents:
                self.logger.error(f"Agent {agent_id} not found")
                return False
            
            agent = self.agents[agent_id]
            if len(agent.current_tasks) >= self.max_tasks_per_agent:
                self.logger.warning(f"Agent {agent_id} at maximum capacity")
                return False
            
            agent.current_tasks.add(task_id)
        
        async with self._task_lock:
            self.task_assignments[task_id] = agent_id
        
        self.global_metrics["total_tasks"] += 1
        return True
    
    async def complete_task(
        self,
        task_id: str,
        success: bool,
        response_time: float
    ) -> None:
        """
        Mark a task as completed and update metrics.
        
        Args:
            task_id: Task ID
            success: Whether task was successful
            response_time: Task execution time in seconds
        """
        async with self._task_lock:
            agent_id = self.task_assignments.pop(task_id, None)
        
        if not agent_id:
            self.logger.warning(f"No agent assignment found for task {task_id}")
            return
        
        async with self._agent_lock:
            if agent_id in self.agents:
                agent = self.agents[agent_id]
                agent.current_tasks.discard(task_id)
                
                # Update metrics
                agent.metrics.total_tasks += 1
                agent.metrics.total_response_time += response_time
                agent.metrics.last_task_time = datetime.utcnow()
                
                if success:
                    agent.metrics.successful_tasks += 1
                    agent.metrics.consecutive_errors = 0
                    self.global_metrics["successful_tasks"] += 1
                else:
                    agent.metrics.failed_tasks += 1
                    agent.metrics.error_count += 1
                    agent.metrics.consecutive_errors += 1
                    self.global_metrics["failed_tasks"] += 1
                
                self.global_metrics["total_response_time"] += response_time
                
                self.logger.info(
                    f"Task {task_id} completed",
                    agent_id=agent_id,
                    success=success,
                    response_time=response_time,
                    agent_health=agent.metrics.health_score
                )
    
    async def get_agent_status(self) -> Dict[str, Dict[str, Any]]:
        """
        Get current status of all agents.
        
        Returns:
            Dictionary of agent statuses
        """
        async with self._agent_lock:
            status = {}
            for agent_id, agent in self.agents.items():
                status[agent_id] = {
                    "agent_type": agent.agent_type.value,
                    "is_available": agent.is_available,
                    "current_tasks": len(agent.current_tasks),
                    "health_score": agent.metrics.health_score,
                    "success_rate": agent.metrics.success_rate,
                    "average_response_time": agent.metrics.average_response_time,
                    "total_tasks": agent.metrics.total_tasks,
                    "capabilities": agent.capabilities,
                    "last_health_check": agent.last_health_check.isoformat() if agent.last_health_check else None
                }
            return status
    
    async def get_global_metrics(self) -> Dict[str, Any]:
        """Get global performance metrics."""
        metrics = self.global_metrics.copy()
        
        # Calculate rates
        if metrics["total_tasks"] > 0:
            metrics["success_rate"] = metrics["successful_tasks"] / metrics["total_tasks"]
            metrics["average_response_time"] = metrics["total_response_time"] / metrics["total_tasks"]
        else:
            metrics["success_rate"] = 0.0
            metrics["average_response_time"] = 0.0
        
        # Add agent summary
        async with self._agent_lock:
            metrics["total_agents"] = len(self.agents)
            metrics["available_agents"] = sum(1 for a in self.agents.values() if a.is_available)
            metrics["healthy_agents"] = sum(1 for a in self.agents.values() if a.metrics.health_score > 0.7)
        
        return metrics
    
    async def _discover_agents(self) -> None:
        """Discover available agents from AutoGen."""
        success, agents_data = await self.client.get_agents_status()
        
        if not success:
            self.logger.error("Failed to discover agents")
            return
        
        async with self._agent_lock:
            # Clear existing agents
            self.agents.clear()
            
            # Add discovered agents
            for agent_data in agents_data:
                agent_id = agent_data.get("id")
                agent_type_str = agent_data.get("type", "").lower()
                
                # Map to AgentType
                agent_type = AgentType.COGNITIVE_AI  # default
                if "cognitive" in agent_type_str:
                    agent_type = AgentType.COGNITIVE_AI
                elif "programmer" in agent_type_str:
                    agent_type = AgentType.PROGRAMMER
                elif "observer" in agent_type_str:
                    agent_type = AgentType.OBSERVER
                
                agent_info = AgentInfo(
                    agent_id=agent_id,
                    agent_type=agent_type,
                    is_available=agent_data.get("is_active", False),
                    capabilities=agent_data.get("capabilities", [])
                )
                
                self.agents[agent_id] = agent_info
                
                self.logger.info(
                    f"Discovered agent {agent_id}",
                    agent_type=agent_type.value,
                    capabilities=agent_info.capabilities
                )
    
    async def _health_monitor_loop(self) -> None:
        """Background task for health monitoring."""
        while True:
            try:
                await asyncio.sleep(self.health_check_interval)
                await self._perform_health_checks()
            except asyncio.CancelledError:
                break
            except Exception as e:
                self.logger.error(f"Health monitor error: {e}")
    
    async def _perform_health_checks(self) -> None:
        """Perform health checks on all agents."""
        success, agents_data = await self.client.get_agents_status()
        
        if not success:
            self.logger.warning("Health check failed to get agent status")
            return
        
        async with self._agent_lock:
            # Update agent availability
            agent_ids = {agent["id"] for agent in agents_data}
            
            for agent_data in agents_data:
                agent_id = agent_data["id"]
                
                if agent_id in self.agents:
                    agent = self.agents[agent_id]
                    agent.is_available = agent_data.get("is_active", False)
                    agent.last_health_check = datetime.utcnow()
                    
                    # Check for unhealthy agents
                    if agent.metrics.health_score < 0.3:
                        self.logger.warning(
                            f"Agent {agent_id} is unhealthy",
                            health_score=agent.metrics.health_score,
                            consecutive_errors=agent.metrics.consecutive_errors
                        )
                else:
                    # New agent discovered
                    await self._discover_agents()
                    break
            
            # Mark missing agents as unavailable
            for agent_id, agent in self.agents.items():
                if agent_id not in agent_ids:
                    agent.is_available = False
                    self.logger.warning(f"Agent {agent_id} not found in health check")
    
    def _select_round_robin(self, agents: List[AgentInfo]) -> Optional[AgentInfo]:
        """Select agent using round-robin strategy."""
        if not agents:
            return None
        
        selected = agents[self._round_robin_index % len(agents)]
        self._round_robin_index += 1
        return selected
    
    def _select_least_loaded(self, agents: List[AgentInfo]) -> Optional[AgentInfo]:
        """Select agent with least current tasks."""
        return min(agents, key=lambda a: len(a.current_tasks))
    
    def _select_best_performance(self, agents: List[AgentInfo]) -> Optional[AgentInfo]:
        """Select agent with best performance metrics."""
        return max(agents, key=lambda a: a.metrics.health_score)
    
    def _select_weighted_random(self, agents: List[AgentInfo]) -> Optional[AgentInfo]:
        """Select agent using weighted random based on health score."""
        if not agents:
            return None
        
        # Calculate weights based on health scores
        weights = [max(0.1, agent.metrics.health_score) for agent in agents]
        total_weight = sum(weights)
        
        if total_weight == 0:
            return random.choice(agents)
        
        # Weighted random selection
        r = random.uniform(0, total_weight)
        cumulative = 0
        
        for agent, weight in zip(agents, weights):
            cumulative += weight
            if r <= cumulative:
                return agent
        
        return agents[-1]  # Fallback