#!/usr/bin/env python3
"""
Test script for AutoGen agents - run this to debug agent issues
Usage: python test_agents.py
"""

import os
import sys
import logging
from pathlib import Path

# Add current directory to Python path
sys.path.insert(0, str(Path(__file__).parent))

# Import our modules
try:
    from autogen_agents import (
        create_orchestrator_agent, 
        create_content_filter_agent,
        create_speech_coordinator_agent,
        _create_autogen_llm_config,
        AUTOGEN_AVAILABLE
    )
    from persona_config import PersonaManager
except ImportError as e:
    print(f"❌ Import error: {e}")
    print("Make sure you're running this from the NeuroSync_Player directory")
    sys.exit(1)

# Set up logging
logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def test_autogen_availability():
    """Test if AutoGen is available and working"""
    print("🔍 Testing AutoGen availability...")
    print(f"AutoGen available: {AUTOGEN_AVAILABLE}")
    
    if not AUTOGEN_AVAILABLE:
        print("❌ AutoGen is not available - install with: pip install autogen")
        return False
    
    try:
        from autogen import AssistantAgent
        print("✅ AutoGen import successful")
        return True
    except ImportError as e:
        print(f"❌ AutoGen import failed: {e}")
        return False

def test_api_keys():
    """Test if required API keys are available"""
    print("\n🔑 Testing API key configuration...")
    
    api_keys = {
        "OPENAI_API_KEY": os.getenv("OPENAI_API_KEY"),
        "ANTHROPIC_API_KEY": os.getenv("ANTHROPIC_API_KEY"),
        "GROQ_API_KEY": os.getenv("GROQ_API_KEY")
    }
    
    available_keys = []
    for key, value in api_keys.items():
        if value and value.strip():
            print(f"✅ {key}: {'*' * (len(value) - 4)}{value[-4:]}")
            available_keys.append(key)
        else:
            print(f"❌ {key}: Not set")
    
    if not available_keys:
        print("⚠️ No API keys found - agents will use mock implementations")
        return False
    
    return True

def create_test_llm_config():
    """Create test LLM config based on available API keys"""
    if os.getenv("OPENAI_API_KEY"):
        return {
            "api_key": os.getenv("OPENAI_API_KEY"),
            "model": "gpt-3.5-turbo",
            "base_url": "https://api.openai.com/v1"
        }
    elif os.getenv("GROQ_API_KEY"):
        return {
            "api_key": os.getenv("GROQ_API_KEY"), 
            "model": "mixtral-8x7b-32768",
            "base_url": "https://api.groq.com/openai/v1"
        }
    elif os.getenv("ANTHROPIC_API_KEY"):
        return {
            "api_key": os.getenv("ANTHROPIC_API_KEY"),
            "model": "claude-3-haiku-20240307"
        }
    else:
        return {
            "api_key": "",
            "model": "gpt-3.5-turbo"
        }

def test_persona_config():
    """Test persona configuration"""
    print("\n👤 Testing persona configuration...")
    
    try:
        persona_manager = PersonaManager()
        persona = persona_manager.get_persona("interactive_streamer")
        
        if persona:
            print(f"✅ Persona loaded: {persona.name}")
            print(f"   - Filter threshold: {persona.filter_threshold}")
            print(f"   - Idle content types: {len(persona.idle_behavior.content_types)}")
            return persona
        else:
            print("❌ Failed to load default persona")
            return None
            
    except Exception as e:
        print(f"❌ Persona config error: {e}")
        return None

def test_agent_creation(persona_config):
    """Test creating individual agents"""
    print("\n🤖 Testing agent creation...")
    
    llm_config = create_test_llm_config()
    results = {}
    
    # Test orchestrator agent
    print("Creating orchestrator agent...")
    try:
        agent = create_orchestrator_agent(persona_config, llm_config)
        if agent:
            agent_type = type(agent).__name__
            is_mock = "Mock" in agent_type
            results["orchestrator"] = {"success": True, "type": agent_type, "is_mock": is_mock}
            print(f"✅ Orchestrator: {agent_type} {'(Mock)' if is_mock else ''}")
        else:
            results["orchestrator"] = {"success": False, "error": "None returned"}
            print("❌ Orchestrator: None returned")
    except Exception as e:
        results["orchestrator"] = {"success": False, "error": str(e)}
        print(f"❌ Orchestrator error: {e}")
    
    # Test content filter agent
    print("Creating content filter agent...")
    try:
        agent = create_content_filter_agent(persona_config, llm_config)
        if agent:
            agent_type = type(agent).__name__
            is_mock = "Mock" in agent_type
            results["content_filter"] = {"success": True, "type": agent_type, "is_mock": is_mock}
            print(f"✅ Content Filter: {agent_type} {'(Mock)' if is_mock else ''}")
        else:
            results["content_filter"] = {"success": False, "error": "None returned"}
            print("❌ Content Filter: None returned")
    except Exception as e:
        results["content_filter"] = {"success": False, "error": str(e)}
        print(f"❌ Content Filter error: {e}")
    
    # Test speech coordinator agent
    print("Creating speech coordinator agent...")
    try:
        agent = create_speech_coordinator_agent(llm_config)
        if agent:
            agent_type = type(agent).__name__
            is_mock = "Mock" in agent_type
            results["speech_coordinator"] = {"success": True, "type": agent_type, "is_mock": is_mock}
            print(f"✅ Speech Coordinator: {agent_type} {'(Mock)' if is_mock else ''}")
        else:
            results["speech_coordinator"] = {"success": False, "error": "None returned"}
            print("❌ Speech Coordinator: None returned")
    except Exception as e:
        results["speech_coordinator"] = {"success": False, "error": str(e)}
        print(f"❌ Speech Coordinator error: {e}")
    
    return results

def test_agent_response(persona_config):
    """Test if agents can generate responses"""
    print("\n💬 Testing agent responses...")
    
    llm_config = create_test_llm_config()
    
    # Test orchestrator response
    orchestrator = create_orchestrator_agent(persona_config, llm_config)
    if orchestrator:
        try:
            response = orchestrator.generate_reply(
                messages=[{"role": "user", "content": "Test: say hello briefly"}]
            )
            if response:
                print(f"✅ Orchestrator response: {response[:100]}...")
            else:
                print("❌ Orchestrator returned None response")
        except Exception as e:
            print(f"❌ Orchestrator response error: {e}")
    else:
        print("❌ No orchestrator agent to test")

def print_troubleshooting_tips(api_keys_available, agent_results):
    """Print troubleshooting recommendations"""
    print("\n🔧 Troubleshooting Tips:")
    
    if not api_keys_available:
        print("1. Create a .env file in the docker-vtuber directory with:")
        print("   OPENAI_API_KEY=your_key_here")
        print("   ANTHROPIC_API_KEY=your_key_here")
        print("   GROQ_API_KEY=your_key_here")
    
    mock_agents = [name for name, result in agent_results.items() 
                   if result.get("success") and result.get("is_mock")]
    if mock_agents:
        print(f"2. Mock agents detected: {', '.join(mock_agents)}")
        print("   This means API keys are missing or invalid")
    
    failed_agents = [name for name, result in agent_results.items() 
                     if not result.get("success")]
    if failed_agents:
        print(f"3. Failed agents: {', '.join(failed_agents)}")
        print("   Check error messages above for specific issues")
    
    print("4. Test the system with:")
    print("   docker restart neurosync_s1")
    print("   curl -X POST http://localhost:5001/orchestrator/v3/agents/test")

def main():
    """Main test function"""
    print("🚀 AutoGen Agent Test Suite")
    print("=" * 50)
    
    # Test AutoGen availability
    if not test_autogen_availability():
        return
    
    # Test API keys
    api_keys_available = test_api_keys()
    
    # Test persona config
    persona_config = test_persona_config()
    if not persona_config:
        return
    
    # Test agent creation
    agent_results = test_agent_creation(persona_config)
    
    # Test agent responses (if API keys available)
    if api_keys_available:
        test_agent_response(persona_config)
    
    # Print summary and troubleshooting
    print("\n📊 Test Summary:")
    successful_agents = len([r for r in agent_results.values() if r.get("success")])
    total_agents = len(agent_results)
    print(f"Agents created successfully: {successful_agents}/{total_agents}")
    
    print_troubleshooting_tips(api_keys_available, agent_results)
    
    print("\n✅ Test complete!")

if __name__ == "__main__":
    main() 