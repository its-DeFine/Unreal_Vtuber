"""
Test script for System2 integration components.

This script tests the AutoGenClient, AgentManager, CogneeClient,
and System2Interface implementations.
"""

import asyncio
import pytest
from datetime import datetime
from unittest.mock import Mock, AsyncMock, patch

from src.integrations.autogen_client import AutoGenClient, AgentType, TaskStatus
from src.integrations.agent_manager import AgentManager, LoadBalancingStrategy, AgentInfo
from src.integrations.cognee_client import CogneeClient, MemoryQuery, MemoryType
from src.integrations.system2_interface import System2Interface
from src.models.stimuli import AnalyzedStimuli, StimuliCategory, Priority
from src.models.system2_models import (
    AgentStatusInfo, AgentStatus, AnalysisResult, AnalysisStatus,
    MemoryResult, System2Response
)
from src.config.settings import System2Config


class TestAutoGenClient:
    """Test AutoGen client functionality."""
    
    @pytest.mark.asyncio
    async def test_submit_task(self):
        """Test task submission."""
        client = AutoGenClient("http://localhost:3100")
        
        # Mock the session
        mock_response = AsyncMock()
        mock_response.status = 200
        mock_response.json = AsyncMock(return_value={
            "task_id": "test-123",
            "status": "submitted"
        })
        
        with patch.object(client, 'ensure_session') as mock_session:
            mock_session.return_value.post.return_value.__aenter__.return_value = mock_response
            
            task_data = {
                "content": "Test task",
                "category": "test"
            }
            
            success, response = await client.submit_task(task_data)
            
            assert success is True
            assert response["task_id"] == "test-123"
    
    @pytest.mark.asyncio
    async def test_get_agents_status(self):
        """Test getting agent status."""
        client = AutoGenClient("http://localhost:3100")
        
        mock_response = AsyncMock()
        mock_response.status = 200
        mock_response.json = AsyncMock(return_value={
            "agents": [
                {
                    "id": "agent-1",
                    "is_active": True,
                    "current_task": None
                }
            ]
        })
        
        with patch.object(client, 'ensure_session') as mock_session:
            mock_session.return_value.get.return_value.__aenter__.return_value = mock_response
            
            success, agents = await client.get_agents_status()
            
            assert success is True
            assert len(agents) == 1
            assert agents[0]["agent_id"] == "agent-1"


class TestAgentManager:
    """Test agent manager functionality."""
    
    @pytest.mark.asyncio
    async def test_agent_selection(self):
        """Test agent selection strategies."""
        mock_client = AsyncMock()
        manager = AgentManager(
            mock_client,
            strategy=LoadBalancingStrategy.ROUND_ROBIN
        )
        
        # Add test agents
        manager.agents = {
            "agent-1": AgentInfo(
                agent_id="agent-1",
                agent_type=AgentType.COGNITIVE_AI,
                is_available=True
            ),
            "agent-2": AgentInfo(
                agent_id="agent-2",
                agent_type=AgentType.PROGRAMMER,
                is_available=True
            )
        }
        
        # Test round-robin selection
        agent1 = await manager.select_agent()
        agent2 = await manager.select_agent()
        agent3 = await manager.select_agent()
        
        assert agent1 in ["agent-1", "agent-2"]
        assert agent2 in ["agent-1", "agent-2"]
        assert agent3 in ["agent-1", "agent-2"]
    
    @pytest.mark.asyncio
    async def test_task_assignment(self):
        """Test task assignment and tracking."""
        mock_client = AsyncMock()
        manager = AgentManager(mock_client)
        
        manager.agents = {
            "agent-1": AgentInfo(
                agent_id="agent-1",
                agent_type=AgentType.COGNITIVE_AI,
                is_available=True
            )
        }
        
        # Assign task
        success = await manager.assign_task("task-123", "agent-1")
        assert success is True
        assert "task-123" in manager.agents["agent-1"].current_tasks
        
        # Complete task
        await manager.complete_task("task-123", success=True, response_time=1.5)
        assert "task-123" not in manager.agents["agent-1"].current_tasks
        assert manager.agents["agent-1"].metrics.successful_tasks == 1


class TestCogneeClient:
    """Test Cognee client functionality."""
    
    @pytest.mark.asyncio
    async def test_query_memories(self):
        """Test memory querying."""
        client = CogneeClient("http://localhost:8000")
        
        mock_response = AsyncMock()
        mock_response.status = 200
        mock_response.json = AsyncMock(return_value={
            "memories": [
                {
                    "id": "mem-1",
                    "content": "Test memory",
                    "memory_type": "episodic",
                    "relevance_score": 0.9,
                    "timestamp": datetime.utcnow().isoformat(),
                    "metadata": {}
                }
            ]
        })
        
        with patch.object(client, 'ensure_session') as mock_session:
            mock_session.return_value.post.return_value.__aenter__.return_value = mock_response
            
            query = MemoryQuery(
                query_text="test query",
                memory_types=[MemoryType.EPISODIC],
                max_results=10
            )
            
            memories = await client.query_memories(query)
            
            assert len(memories) == 1
            assert memories[0].id == "mem-1"
            assert memories[0].relevance_score == 0.9


class TestSystem2Interface:
    """Test System2 interface integration."""
    
    @pytest.mark.asyncio
    async def test_submit_for_analysis(self):
        """Test submitting stimuli for analysis."""
        config = System2Config()
        interface = System2Interface(config)
        
        # Mock components
        interface.autogen_client = AsyncMock()
        interface.agent_manager = AsyncMock()
        interface.cognee_client = AsyncMock()
        interface.is_initialized = True
        
        # Mock agent selection
        interface.agent_manager.select_agent.return_value = "agent-1"
        
        # Mock task submission
        interface.autogen_client.submit_task.return_value = (True, {"task_id": "test-123"})
        
        # Create test stimuli
        stimuli = AnalyzedStimuli(
            id="stim-1",
            content="Test stimuli",
            source="test",
            category=StimuliCategory.USER_INTERACTION,
            confidence=0.9,
            priority=Priority.MEDIUM
        )
        
        # Submit for analysis
        task_id = await interface.submit_for_analysis(stimuli)
        
        assert task_id == "test-123"
        interface.agent_manager.select_agent.assert_called_once()
        interface.autogen_client.submit_task.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_query_cognee_memory(self):
        """Test memory querying through interface."""
        config = System2Config()
        interface = System2Interface(config)
        
        interface.cognee_client = AsyncMock()
        interface.is_initialized = True
        
        # Mock memory query
        mock_memory = Mock()
        mock_memory.id = "mem-1"
        mock_memory.content = "Test memory"
        mock_memory.relevance_score = 0.8
        mock_memory.memory_type = Mock(value="episodic")
        mock_memory.timestamp = datetime.utcnow()
        mock_memory.metadata = {}
        mock_memory.related_memories = []
        
        interface.cognee_client.query_memories.return_value = [mock_memory]
        
        # Query memories
        results = await interface.query_cognee_memory("test query")
        
        assert len(results) == 1
        assert results[0].memory_id == "mem-1"
        assert results[0].relevance == 0.8


# Run tests
if __name__ == "__main__":
    # Run basic smoke tests
    print("Running System2 integration tests...")
    
    async def run_tests():
        # Test AutoGen client
        print("\n1. Testing AutoGen client...")
        client = AutoGenClient("http://localhost:3100")
        print(f"   - Created client: {client.endpoint}")
        
        # Test Agent manager
        print("\n2. Testing Agent manager...")
        manager = AgentManager(client)
        print(f"   - Created manager with strategy: {manager.strategy}")
        
        # Test Cognee client
        print("\n3. Testing Cognee client...")
        cognee = CogneeClient("http://localhost:8000")
        print(f"   - Created Cognee client: {cognee.endpoint}")
        
        # Test System2 interface
        print("\n4. Testing System2 interface...")
        config = System2Config()
        interface = System2Interface(config)
        print(f"   - Created interface with AutoGen: {config.autogen_endpoint}")
        print(f"   - Cognee endpoint: {config.cognee_endpoint}")
        print(f"   - Evolution enabled: {config.evolution_engine_enabled}")
        
        print("\nAll components created successfully!")
    
    asyncio.run(run_tests())