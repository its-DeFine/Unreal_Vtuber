#!/usr/bin/env python3
"""
Quick S2 Test with Ollama - Single Team Test
============================================

Tests a single team with a simple stimuli to verify full pipeline.
"""

import asyncio
import json
import logging
import os
import sys
from datetime import datetime

# Add the autogen agent path
sys.path.append('/home/geo/directories/autonomy/docker-vtuber/app/CORE/autogen-agent')

# Configure Ollama
os.environ["USE_OLLAMA"] = "true"
os.environ["OLLAMA_HOST"] = "http://localhost:11434"
os.environ["OLLAMA_MODEL"] = "llama3.1:8b"
os.environ["USE_TEACHABLE_AGENTS"] = "false"

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)

async def test_single_team():
    """Test a single team with Ollama"""
    
    print("\n" + "="*80)
    print("🚀 QUICK S2 OLLAMA TEST - SINGLE TEAM")
    print("="*80)
    
    try:
        from autogen_agent.core.stimuli_autogen_team import StimuliAutoGenTeam
        from autogen_agent.core.character_team_registry import get_character_team_registry, CharacterType
        
        # Create and initialize teacher team
        print("\n📚 Initializing Teacher Team...")
        team = StimuliAutoGenTeam()
        
        if team.initialize_team():
            print("✅ Teacher team initialized successfully!")
            
            # Create test stimuli
            stimuli_data = {
                "stimuli_id": "test_teacher_001",
                "content": "What are the best practices for teaching Python to beginners?",
                "source": "quick_test",
                "priority": "medium",
                "metadata": {
                    "test": True,
                    "timestamp": datetime.now().isoformat()
                }
            }
            
            print(f"\n📨 Sending stimuli: {stimuli_data['content']}")
            print("⏳ Processing (this may take 30-60 seconds with Ollama)...")
            
            # Process stimuli
            result = await team.process_stimuli_with_team(stimuli_data)
            
            if result.get("success"):
                print("\n✅ Team processed stimuli successfully!")
                print(f"\n📝 Response Summary:")
                print("-" * 60)
                
                # Extract key information
                response = result.get("response_content", "No response")
                if len(response) > 500:
                    print(response[:500] + "...")
                else:
                    print(response)
                
                print("-" * 60)
                
                # Show actions
                actions = result.get("actions", [])
                if actions:
                    print(f"\n🎯 Recommended Actions: {len(actions)}")
                    for i, action in enumerate(actions):
                        print(f"  {i+1}. {action.get('type', 'Unknown')}: {action.get('description', 'No description')}")
                
                # Show tools triggered
                tools = result.get("tools_triggered", [])
                if tools:
                    print(f"\n🔧 Tools Triggered: {', '.join(tools)}")
                
                # Show processing time
                if "processing_time" in result:
                    print(f"\n⏱️ Processing Time: {result['processing_time']:.2f} seconds")
                
            else:
                print("\n❌ Team failed to process stimuli")
                print(f"Error: {result.get('error', 'Unknown error')}")
                
        else:
            print("❌ Failed to initialize teacher team")
            
    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        
    print("\n" + "="*80)


async def main():
    """Run the quick test"""
    await test_single_team()


if __name__ == "__main__":
    asyncio.run(main())