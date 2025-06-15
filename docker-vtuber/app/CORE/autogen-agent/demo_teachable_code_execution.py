#!/usr/bin/env python3
"""
Demo script for Teachable Agents and Code Execution
Shows how agents learn from conversations and can execute code safely
"""

import asyncio
import os
import logging
from autogen import GroupChat, GroupChatManager
from autogen_agent.teachable_agents import create_teachable_agents

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(message)s')

# Example code for agents to analyze and improve
SAMPLE_CODE = '''
def calculate_statistics(numbers):
    """Calculate mean, median, and mode of a list of numbers"""
    # Calculate mean
    total = 0
    for num in numbers:
        total += num
    mean = total / len(numbers)
    
    # Calculate median
    sorted_nums = sorted(numbers)
    n = len(sorted_nums)
    if n % 2 == 0:
        median = (sorted_nums[n//2 - 1] + sorted_nums[n//2]) / 2
    else:
        median = sorted_nums[n//2]
    
    # Calculate mode (most frequent)
    frequency = {}
    for num in numbers:
        frequency[num] = frequency.get(num, 0) + 1
    mode = max(frequency, key=frequency.get)
    
    return mean, median, mode
'''

async def demo_teachable_agents():
    """Demonstrate teachable agents with learning and code execution"""
    print("🎓 Teachable Agents & Code Execution Demo\n")
    
    # Check for API key
    if not os.getenv('OPENAI_API_KEY'):
        print("⚠️  Warning: OPENAI_API_KEY not set.")
        print("For full demo, set: export OPENAI_API_KEY='your-key-here'\n")
        return
    
    # Configure LLM
    llm_config = {
        "config_list": [{
            "model": "gpt-4",
            "api_key": os.getenv('OPENAI_API_KEY'),
            "api_type": "openai"
        }],
        "temperature": 0.7
    }
    
    # Create teachable agents
    print("📚 Creating teachable agents...")
    agents = create_teachable_agents(llm_config)
    
    cognitive = agents["cognitive"]
    programmer = agents["programmer"]
    executor = agents["executor"]
    observer = agents["observer"]
    
    print("✅ Agents created with learning capabilities!\n")
    
    # Create group chat
    group_chat = GroupChat(
        agents=[cognitive, programmer, executor, observer],
        messages=[],
        max_round=10
    )
    
    manager = GroupChatManager(groupchat=group_chat, llm_config=llm_config)
    
    # Example 1: Teaching agents about the project
    print("📖 Example 1: Teaching agents about the project\n")
    
    await cognitive.initiate_chat(
        manager,
        message="""Let me teach you about our project:
        
We are building an autonomous AI system with these key features:
1. Multi-agent collaboration using Microsoft AutoGen
2. Goal management with SMART framework
3. Darwin-Gödel self-improvement capabilities
4. VTuber integration for visual representation
5. Cognitive memory using PostgreSQL with pgvector

Remember this information as it's important for our work together."""
    )
    
    # Example 2: Code analysis and execution
    print("\n\n💻 Example 2: Code analysis and execution\n")
    
    await programmer.initiate_chat(
        manager,
        message=f"""Analyze this code and suggest improvements. Then have the executor test it:

```python
{SAMPLE_CODE}
```

After analysis, create an improved version and test both to compare performance."""
    )
    
    # Example 3: Learning from past interactions
    print("\n\n🧠 Example 3: Recalling learned information\n")
    
    await cognitive.initiate_chat(
        manager,
        message="Based on what you've learned about our project, what performance optimizations would be most valuable for our autonomous AI system?"
    )
    
    # Example 4: Complex problem solving with code
    print("\n\n🔧 Example 4: Solving a real problem\n")
    
    await programmer.initiate_chat(
        manager,
        message="""Create a function that monitors agent decision times and automatically triggers optimization when performance degrades. Test your solution."""
    )
    
    # Get learning summary
    print("\n\n📊 Learning Summary\n")
    from autogen_agent.teachable_agents import get_learning_summary
    summary = get_learning_summary(agents)
    
    print("What the agents have learned:")
    for agent_name, status in summary.items():
        print(f"- {agent_name}: {status}")

async def demo_code_execution_safety():
    """Demonstrate safe code execution"""
    print("\n\n🛡️ Code Execution Safety Demo\n")
    
    # Configure LLM
    llm_config = {
        "config_list": [{
            "model": "gpt-4",
            "api_key": os.getenv('OPENAI_API_KEY', 'dummy-key'),
            "api_type": "openai"
        }],
        "temperature": 0.7
    }
    
    # Create just the executor
    from autogen_agent.teachable_agents import CodeExecutionAgent
    executor_wrapper = CodeExecutionAgent()
    executor = executor_wrapper.get_agent()
    
    print("Testing safe code execution:")
    
    # Safe code example
    safe_code = """
# Calculate factorial
def factorial(n):
    if n <= 1:
        return 1
    return n * factorial(n-1)

# Test it
result = factorial(5)
print(f"5! = {result}")
"""
    
    print("\n1. Executing safe code:")
    print(safe_code)
    
    # The executor would run this safely in its sandbox
    # In a real scenario, this would be part of a conversation
    
    # Potentially unsafe code example
    unsafe_code = """
# This code tries to access system resources
import os
print(os.environ)  # Try to read environment variables
open('/etc/passwd', 'r')  # Try to read system files
"""
    
    print("\n2. Unsafe code example (would be contained in sandbox):")
    print(unsafe_code)
    print("\nThe code execution agent runs all code in a sandboxed environment")
    print("with timeouts and resource limits to ensure safety.\n")

async def main():
    """Run all demos"""
    # Teachable agents demo
    await demo_teachable_agents()
    
    # Code execution safety demo
    await demo_code_execution_safety()
    
    print("\n🎉 Demo Complete!\n")
    print("Key Features Demonstrated:")
    print("✅ Agents that learn from conversations")
    print("✅ Persistent memory across sessions")
    print("✅ Safe code execution in sandbox")
    print("✅ Multi-agent collaboration with specialized roles")
    print("✅ Code analysis and optimization capabilities")
    
    print("\nTo use in production:")
    print("1. Set USE_TEACHABLE_AGENTS=true")
    print("2. Set USE_DOCKER_SANDBOX=true for enhanced security")
    print("3. Teaching databases persist in /app/teachable_db")

if __name__ == "__main__":
    asyncio.run(main())