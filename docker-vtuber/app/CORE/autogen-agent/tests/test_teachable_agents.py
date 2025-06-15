"""
Test suite for teachable agents and code execution
"""

import pytest
import asyncio
import os
import tempfile
import shutil
from unittest.mock import Mock, patch, MagicMock

# Set test environment
os.environ['USE_TEACHABLE_AGENTS'] = 'true'
os.environ['USE_DOCKER_SANDBOX'] = 'false'

from autogen_agent.teachable_agents import (
    TeachableCognitiveAgent,
    CodeExecutionAgent,
    TeachableProgrammerAgent,
    create_teachable_agents,
    get_learning_summary
)


class TestTeachableAgents:
    """Test teachable agent functionality"""
    
    @pytest.fixture
    def llm_config(self):
        """Create test LLM config"""
        return {
            "config_list": [{
                "model": "gpt-4",
                "api_key": "test-key",
                "api_type": "openai"
            }],
            "temperature": 0.7
        }
    
    @pytest.fixture
    def temp_teach_db(self):
        """Create temporary teaching database directory"""
        temp_dir = tempfile.mkdtemp()
        yield temp_dir
        shutil.rmtree(temp_dir)
    
    def test_teachable_cognitive_agent_creation(self, llm_config, temp_teach_db):
        """Test creation of teachable cognitive agent"""
        agent_wrapper = TeachableCognitiveAgent(
            llm_config=llm_config,
            teach_db_path=temp_teach_db
        )
        
        assert agent_wrapper.agent is not None
        assert agent_wrapper.agent.name == "teachable_cognitive_ai"
        assert os.path.exists(temp_teach_db)
    
    def test_teachable_programmer_agent_creation(self, llm_config, temp_teach_db):
        """Test creation of teachable programmer agent"""
        agent_wrapper = TeachableProgrammerAgent(
            llm_config=llm_config,
            teach_db_path=temp_teach_db
        )
        
        assert agent_wrapper.agent is not None
        assert agent_wrapper.agent.name == "teachable_programmer"
        assert os.path.exists(temp_teach_db)
    
    def test_code_execution_agent_creation(self):
        """Test creation of code execution agent"""
        with tempfile.TemporaryDirectory() as temp_dir:
            agent_wrapper = CodeExecutionAgent(work_dir=temp_dir)
            
            assert agent_wrapper.agent is not None
            assert agent_wrapper.agent.name == "code_executor"
            assert agent_wrapper.agent._code_execution_config is not None
            assert agent_wrapper.agent._code_execution_config["work_dir"] == temp_dir
    
    def test_code_execution_config(self):
        """Test code execution configuration"""
        agent_wrapper = CodeExecutionAgent()
        
        config = agent_wrapper.agent._code_execution_config
        assert config["timeout"] == 60
        assert config["last_n_messages"] == 3
        assert config["use_docker"] is False  # Based on env var
    
    def test_create_all_teachable_agents(self, llm_config):
        """Test creating all teachable agents at once"""
        agents = create_teachable_agents(llm_config)
        
        assert "cognitive" in agents
        assert "programmer" in agents
        assert "executor" in agents
        assert "observer" in agents
        
        # Check wrappers are included
        assert "cognitive_wrapper" in agents
        assert "programmer_wrapper" in agents
        assert "executor_wrapper" in agents
    
    def test_learning_summary(self, llm_config):
        """Test getting learning summary"""
        agents = create_teachable_agents(llm_config)
        summary = get_learning_summary(agents)
        
        assert "cognitive" in summary
        assert "programmer" in summary
        assert "executor" in summary
        
        # Check status
        assert summary["cognitive"]["status"] == "active"
        assert summary["programmer"]["status"] == "active"
        assert summary["executor"]["status"] == "active"
    
    def test_work_dir_cleanup(self):
        """Test code execution work directory cleanup"""
        with tempfile.TemporaryDirectory() as base_dir:
            work_dir = os.path.join(base_dir, "test_work")
            agent_wrapper = CodeExecutionAgent(work_dir=work_dir)
            
            # Create some test files
            test_file = os.path.join(work_dir, "test.py")
            with open(test_file, 'w') as f:
                f.write("print('test')")
            
            assert os.path.exists(test_file)
            
            # Clean up
            agent_wrapper.cleanup_work_dir()
            
            assert not os.path.exists(test_file)
            assert os.path.exists(work_dir)  # Directory recreated
    
    @patch('autogen_agent.teachable_agents.TeachableAgent')
    def test_teachable_config_params(self, mock_teachable, llm_config):
        """Test that teachable agents are configured correctly"""
        # Create cognitive agent
        cognitive = TeachableCognitiveAgent(llm_config)
        
        # Check TeachableAgent was called with correct params
        mock_teachable.assert_called()
        call_kwargs = mock_teachable.call_args[1]
        
        assert call_kwargs["name"] == "teachable_cognitive_ai"
        assert "teach_config" in call_kwargs
        
        teach_config = call_kwargs["teach_config"]
        assert teach_config["verbosity"] == 1
        assert teach_config["reset_db"] is False
        assert teach_config["recall_threshold"] == 1.5
        assert teach_config["max_num_retrievals"] == 5


class TestCodeExecution:
    """Test code execution functionality"""
    
    def test_code_execution_safety(self):
        """Test that code execution has safety measures"""
        executor = CodeExecutionAgent()
        
        # Check safety settings
        assert executor.agent._human_input_mode == "NEVER"  # Fully autonomous
        assert executor.agent._max_consecutive_auto_reply == 10  # Limited replies
        
        # Check termination condition exists
        assert executor.agent._is_termination_msg is not None
        
        # Test termination detection
        assert executor.agent._is_termination_msg({"content": "TERMINATE"}) is True
        assert executor.agent._is_termination_msg({"content": "Continue"}) is False
    
    def test_docker_sandbox_config(self):
        """Test Docker sandbox configuration"""
        # Test with Docker enabled
        os.environ['USE_DOCKER_SANDBOX'] = 'true'
        executor = CodeExecutionAgent()
        
        assert executor.agent._code_execution_config["use_docker"] is True
        
        # Reset
        os.environ['USE_DOCKER_SANDBOX'] = 'false'


class TestIntegration:
    """Integration tests for teachable agents with AutoGen"""
    
    @pytest.mark.asyncio
    async def test_teachable_agent_in_conversation(self, llm_config):
        """Test that teachable agents can participate in conversations"""
        agents = create_teachable_agents(llm_config)
        
        # Get the cognitive agent
        cognitive = agents["cognitive"]
        
        # Check it has the required methods for AutoGen
        assert hasattr(cognitive, "generate_reply")
        assert hasattr(cognitive, "receive")
        assert hasattr(cognitive, "send")
    
    def test_learning_persistence(self, llm_config, temp_teach_db):
        """Test that learning persists across agent recreations"""
        # Create first instance
        agent1 = TeachableCognitiveAgent(
            llm_config=llm_config,
            teach_db_path=temp_teach_db
        )
        
        # Simulate some learning (in real use, this would happen through conversations)
        # For now, just verify the DB path is set correctly
        
        # Create second instance with same DB
        agent2 = TeachableCognitiveAgent(
            llm_config=llm_config,
            teach_db_path=temp_teach_db
        )
        
        # Both should use the same teaching database
        assert agent1.teach_db_path == agent2.teach_db_path
        assert os.path.exists(temp_teach_db)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])