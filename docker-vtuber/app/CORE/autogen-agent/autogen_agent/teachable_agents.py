"""
Teachable Agents Configuration for AutoGen
Enables agents to learn from conversations and remember information across sessions
"""

import os
import logging
from typing import Dict, Any, Optional
from autogen.agentchat.contrib.teachable_agent import TeachableAgent
from autogen import ConversableAgent, UserProxyAgent
import autogen

logger = logging.getLogger(__name__)


class TeachableCognitiveAgent:
    """Enhanced cognitive agent with teachability - learns from interactions"""
    
    def __init__(self, llm_config: Dict[str, Any], teach_db_path: str = "/app/teachable_db"):
        """
        Initialize teachable cognitive agent
        
        Args:
            llm_config: LLM configuration for the agent
            teach_db_path: Path to store teaching database
        """
        self.teach_db_path = teach_db_path
        self.llm_config = llm_config
        
        # Ensure teach DB directory exists
        os.makedirs(self.teach_db_path, exist_ok=True)
        
        # Create teachable agent with enhanced system message
        self.agent = TeachableAgent(
            name="teachable_cognitive_ai",
            system_message="""You are a teachable cognitive AI agent for an autonomous system.
            
Your capabilities:
1. **Learning**: You can learn new information from conversations and remember it permanently
2. **Recall**: You can recall previously learned information when relevant
3. **Pattern Recognition**: You identify patterns in data and behaviors
4. **Self-Improvement**: You apply learned knowledge to improve your responses
5. **Knowledge Sharing**: You can share what you've learned with other agents

Important behaviors:
- When you learn something new, explicitly acknowledge it
- Proactively recall relevant past learnings
- Build upon previous knowledge to provide better insights
- Ask clarifying questions to learn more effectively
- Maintain a growth mindset

You work alongside programmer and observer agents to make intelligent decisions.""",
            llm_config=llm_config,
            teach_config={
                "verbosity": 1,  # 0 = silent, 1 = basic, 2 = verbose
                "reset_db": False,  # Don't reset on init - preserve learnings
                "path_to_db_dir": self.teach_db_path,
                "recall_threshold": 1.5,  # Threshold for recalling memories
                "max_num_retrievals": 5,  # Max memories to retrieve
            }
        )
        
        logger.info(f"✅ Teachable cognitive agent initialized with DB at {self.teach_db_path}")
    
    def get_agent(self) -> TeachableAgent:
        """Get the teachable agent instance"""
        return self.agent
    
    def get_learned_topics(self) -> Dict[str, Any]:
        """Get a summary of what the agent has learned"""
        try:
            # Access the agent's memory (this is a simplified version)
            # In practice, you'd query the vector DB
            return {
                "status": "active",
                "db_path": self.teach_db_path,
                "message": "Learning system active"
            }
        except Exception as e:
            logger.error(f"Error accessing learned topics: {e}")
            return {"status": "error", "error": str(e)}


class CodeExecutionAgent:
    """Agent capable of safely executing code in a sandboxed environment"""
    
    def __init__(self, work_dir: str = "/tmp/autogen_code_execution"):
        """
        Initialize code execution agent
        
        Args:
            work_dir: Working directory for code execution
        """
        self.work_dir = work_dir
        os.makedirs(self.work_dir, exist_ok=True)
        
        # Create user proxy agent with code execution capability
        self.agent = UserProxyAgent(
            name="code_executor",
            system_message="""You are a code execution agent that safely runs Python code.
            
Your responsibilities:
1. Execute code provided by other agents
2. Report results accurately
3. Handle errors gracefully
4. Ensure code safety
5. Provide performance metrics

Important: Only execute code that is safe and relevant to the task.""",
            code_execution_config={
                "work_dir": self.work_dir,
                "use_docker": os.getenv("USE_DOCKER_SANDBOX", "false").lower() == "true",
                "timeout": 60,  # 60 second timeout
                "last_n_messages": 3,  # Consider last 3 messages for context
            },
            human_input_mode="NEVER",  # Fully autonomous
            max_consecutive_auto_reply=10,
            is_termination_msg=lambda x: "TERMINATE" in x.get("content", ""),
        )
        
        logger.info(f"✅ Code execution agent initialized with work_dir: {self.work_dir}")
    
    def get_agent(self) -> UserProxyAgent:
        """Get the code execution agent instance"""
        return self.agent
    
    def cleanup_work_dir(self):
        """Clean up the working directory"""
        try:
            import shutil
            shutil.rmtree(self.work_dir)
            os.makedirs(self.work_dir, exist_ok=True)
            logger.info("🧹 Code execution work directory cleaned")
        except Exception as e:
            logger.error(f"Error cleaning work directory: {e}")


class TeachableProgrammerAgent:
    """Programmer agent with teachability for learning coding patterns"""
    
    def __init__(self, llm_config: Dict[str, Any], teach_db_path: str = "/app/teachable_programmer_db"):
        """Initialize teachable programmer agent"""
        self.teach_db_path = teach_db_path
        os.makedirs(self.teach_db_path, exist_ok=True)
        
        self.agent = TeachableAgent(
            name="teachable_programmer",
            system_message="""You are a teachable programmer agent specializing in code generation and optimization.
            
Your enhanced capabilities:
1. **Pattern Learning**: Learn successful code patterns and reuse them
2. **Error Learning**: Remember past errors and how to fix them
3. **Optimization Memory**: Recall effective optimization techniques
4. **Library Knowledge**: Build knowledge about libraries and best practices
5. **Code Style**: Learn and maintain consistent coding styles

Key behaviors:
- Learn from successful code implementations
- Remember common bug fixes and apply them proactively
- Build a library of code snippets and patterns
- Share coding knowledge with other agents
- Continuously improve code quality based on learnings

You generate, review, and optimize code while learning from each interaction.""",
            llm_config=llm_config,
            teach_config={
                "verbosity": 1,
                "reset_db": False,
                "path_to_db_dir": self.teach_db_path,
                "recall_threshold": 1.2,  # Lower threshold for code patterns
                "max_num_retrievals": 10,  # More retrievals for code examples
            }
        )
        
        logger.info(f"✅ Teachable programmer agent initialized with DB at {self.teach_db_path}")
    
    def get_agent(self) -> TeachableAgent:
        """Get the teachable programmer agent instance"""
        return self.agent


def create_teachable_agents(llm_config: Dict[str, Any]) -> Dict[str, Any]:
    """
    Create all teachable agents for the system
    
    Returns:
        Dictionary containing all agent instances
    """
    logger.info("🎓 Creating teachable agents...")
    
    # Create teachable cognitive agent
    cognitive = TeachableCognitiveAgent(llm_config)
    
    # Create teachable programmer agent
    programmer = TeachableProgrammerAgent(llm_config)
    
    # Create code execution agent
    executor = CodeExecutionAgent()
    
    # Standard observer agent (not teachable for now)
    observer = ConversableAgent(
        name="observer_agent",
        system_message="""You are an observer agent that monitors system behavior and provides insights.
        
Your role:
1. Observe agent interactions and decisions
2. Identify patterns and potential issues
3. Provide performance feedback
4. Suggest improvements
5. Maintain system health awareness

Work with the teachable agents to help them learn from observations.""",
        llm_config=llm_config,
        human_input_mode="NEVER",
    )
    
    agents = {
        "cognitive": cognitive.get_agent(),
        "programmer": programmer.get_agent(),
        "executor": executor.get_agent(),
        "observer": observer,
        "cognitive_wrapper": cognitive,
        "programmer_wrapper": programmer,
        "executor_wrapper": executor
    }
    
    logger.info("✅ All teachable agents created successfully")
    return agents


def save_agent_learnings(agents: Dict[str, Any]):
    """Save what agents have learned (useful for backups)"""
    try:
        # The teachable agents automatically persist their learning
        # This is just for explicit saves if needed
        logger.info("💾 Agent learnings are automatically persisted")
    except Exception as e:
        logger.error(f"Error saving agent learnings: {e}")


def get_learning_summary(agents: Dict[str, Any]) -> Dict[str, Any]:
    """Get a summary of what all agents have learned"""
    summary = {}
    
    try:
        if "cognitive_wrapper" in agents:
            summary["cognitive"] = agents["cognitive_wrapper"].get_learned_topics()
        
        if "programmer_wrapper" in agents:
            summary["programmer"] = agents["programmer_wrapper"].get_learned_topics()
        
        summary["executor"] = {
            "status": "active",
            "work_dir": agents["executor_wrapper"].work_dir if "executor_wrapper" in agents else "unknown"
        }
        
    except Exception as e:
        logger.error(f"Error getting learning summary: {e}")
        summary["error"] = str(e)
    
    return summary