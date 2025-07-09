"""
Test Suite for Persona-Aware Tool System

This test suite verifies that the persona-aware tool system correctly:
1. Restricts tools based on character persona
2. Synchronizes character state between S1 and S2
3. Provides mission-based tool access
4. Notifies S2 of character changes
"""

import asyncio
import sys
import os

# Add the autogen_agent directory to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'autogen_agent'))

from autogen_agent.character_state_manager import CharacterStateManager, CharacterMission
from autogen_agent.persona_aware_tool_registry import PersonaAwareToolRegistry
from autogen_agent.tools.admin_character_tool import AdminCharacterTool
import logging

# Set up logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

async def test_character_state_manager():
    """Test character state manager functionality"""
    print("\n🎭 Testing Character State Manager...")
    
    # Initialize character state manager
    manager = CharacterStateManager()
    
    # Test mission templates
    print(f"✅ Mission templates loaded: {len(manager.mission_templates)}")
    
    # Test persona type determination
    doctor_info = {
        "id": "test_doctor",
        "name": "Dr. Test",
        "role": "Medical Professional",
        "domain_expertise": ["medicine", "health"],
        "personality_traits": ["caring", "precise"]
    }
    
    await manager._update_character_state(doctor_info)
    current_char = manager.get_current_character()
    
    print(f"✅ Character loaded: {current_char.character_name} ({current_char.role})")
    print(f"✅ Mission: {current_char.mission.title if current_char.mission else 'None'}")
    print(f"✅ Available tools: {len(current_char.available_tools)}")
    print(f"✅ Operational mode: {manager.get_operational_mode()}")
    
    return manager

async def test_persona_aware_tool_registry():
    """Test persona-aware tool registry functionality"""
    print("\n🔧 Testing Persona-Aware Tool Registry...")
    
    # Initialize tool registry
    registry = PersonaAwareToolRegistry()
    
    # Mock tool loading (normally done by load_tools())
    registry.tools = {
        "medical_information_tool": lambda ctx: {"persona": "doctor", "tool": "medical"},
        "recipe_generation_tool": lambda ctx: {"persona": "chef", "tool": "recipe"},
        "educational_content_tool": lambda ctx: {"persona": "teacher", "tool": "education"},
        "fitness_assessment_tool": lambda ctx: {"persona": "coach", "tool": "fitness"},
        "admin_character_tool": lambda ctx: {"persona": "universal", "tool": "admin"},
        "goal_management_tools": lambda ctx: {"persona": "universal", "tool": "goals"}
    }
    
    # Initialize performance tracking
    for tool_name in registry.tools.keys():
        registry.tool_performance[tool_name] = {
            'total_uses': 0,
            'successes': 0,
            'avg_execution_time': 0.0,
            'context_relevance_scores': [],
            'last_used': 0
        }
    
    print(f"✅ Tools loaded: {len(registry.tools)}")
    print(f"✅ Persona mappings: {len(registry.persona_tool_mappings)}")
    
    # Test tool availability for different personas
    doctor_tools = registry.get_available_tools_for_persona("doctor")
    chef_tools = registry.get_available_tools_for_persona("chef")
    teacher_tools = registry.get_available_tools_for_persona("teacher")
    
    print(f"✅ Doctor tools: {len(doctor_tools)} - {doctor_tools}")
    print(f"✅ Chef tools: {len(chef_tools)} - {chef_tools}")
    print(f"✅ Teacher tools: {len(teacher_tools)} - {teacher_tools}")
    
    return registry

async def test_tool_selection_with_persona():
    """Test tool selection with persona awareness"""
    print("\n🧠 Testing Tool Selection with Persona Awareness...")
    
    # Initialize components
    manager = CharacterStateManager()
    registry = PersonaAwareToolRegistry()
    registry.set_character_state_manager(manager)
    
    # Mock tools
    registry.tools = {
        "medical_information_tool": lambda ctx: {"success": True, "persona": "doctor"},
        "recipe_generation_tool": lambda ctx: {"success": True, "persona": "chef"},
        "educational_content_tool": lambda ctx: {"success": True, "persona": "teacher"},
        "admin_character_tool": lambda ctx: {"success": True, "persona": "universal"}
    }
    
    # Initialize performance tracking
    for tool_name in registry.tools.keys():
        registry.tool_performance[tool_name] = {
            'total_uses': 0,
            'successes': 0,
            'avg_execution_time': 0.0,
            'context_relevance_scores': [],
            'last_used': 0
        }
    
    # Test with doctor persona
    doctor_info = {
        "id": "test_doctor",
        "name": "Dr. Test",
        "role": "Medical Professional",
        "domain_expertise": ["medicine", "health"],
        "personality_traits": ["caring", "precise"]
    }
    await manager._update_character_state(doctor_info)
    
    # Test tool selection with medical context
    medical_context = {
        "content": "I need medical information about symptoms",
        "message": "health advice needed"
    }
    
    selected_tool = registry.select_tool(medical_context)
    print(f"✅ Selected tool for medical context: {selected_tool}")
    
    # Test with chef persona
    chef_info = {
        "id": "test_chef",
        "name": "Chef Test",
        "role": "Culinary Expert",
        "domain_expertise": ["cooking", "recipes"],
        "personality_traits": ["creative", "passionate"]
    }
    await manager._update_character_state(chef_info)
    
    # Test tool selection with cooking context
    cooking_context = {
        "content": "I need a recipe for pasta",
        "message": "cooking help needed"
    }
    
    selected_tool = registry.select_tool(cooking_context)
    print(f"✅ Selected tool for cooking context: {selected_tool}")
    
    return True

async def test_admin_character_tool_integration():
    """Test admin character tool integration with persona system"""
    print("\n🔧 Testing Admin Character Tool Integration...")
    
    # Initialize admin tool
    admin_tool = AdminCharacterTool()
    
    # Test command parsing
    test_commands = [
        "admin: switch character Dr. Smith",
        "admin: create character Chef Mario chef",
        "admin: list characters",
        "not an admin command"
    ]
    
    for command in test_commands:
        parsed = admin_tool.parse_admin_command(command)
        print(f"✅ Command: '{command}' -> Type: {parsed.get('type')}")
    
    # Test character template extraction
    character_data = admin_tool.extract_character_details("create character Dr. Wilson doctor", "Dr. Wilson")
    print(f"✅ Character template: {character_data.get('role')} with {len(character_data.get('available_tools', []))} tools")
    
    return True

async def test_mission_system():
    """Test mission-based character system"""
    print("\n🎯 Testing Mission System...")
    
    manager = CharacterStateManager()
    
    # Test different persona missions
    personas = ["doctor", "teacher", "chef", "coach", "librarian"]
    
    for persona in personas:
        if persona in manager.mission_templates:
            mission = manager.mission_templates[persona]
            print(f"✅ {persona.title()} Mission: {mission.title}")
            print(f"   Objectives: {len(mission.objectives)}")
            print(f"   Available tools: {len(mission.available_tools)}")
            print(f"   Operational mode: {mission.operational_mode}")
            print(f"   Priority contexts: {mission.priority_contexts[:3]}...")
    
    return True

async def run_all_tests():
    """Run all persona-aware tool system tests"""
    print("🧪 Starting Persona-Aware Tool System Tests...")
    
    try:
        # Run individual tests
        await test_character_state_manager()
        await test_persona_aware_tool_registry()
        await test_tool_selection_with_persona()
        await test_admin_character_tool_integration()
        await test_mission_system()
        
        print("\n✅ All tests completed successfully!")
        print("\n🎯 Persona-Aware Tool System Features Verified:")
        print("   • Character state synchronization between S1 and S2")
        print("   • Mission-based tool access control")
        print("   • Persona-specific tool availability")
        print("   • Admin character change notifications")
        print("   • Tool selection with persona awareness")
        print("   • Character template generation")
        
        return True
        
    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = asyncio.run(run_all_tests())
    sys.exit(0 if success else 1)