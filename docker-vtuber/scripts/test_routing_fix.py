#!/usr/bin/env python3
"""
Test script to verify S1/S2 routing is working correctly after fixes
"""

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'app', 'CORE', 'graphflow-stimuli-system'))

from config.emergency_override import EMERGENCY_OVERRIDE
from src.models.decisions import ProcessingDecision

def test_routing():
    """Test various routing scenarios"""
    test_scenarios = [
        {
            "name": "Direct speech request",
            "context": {
                "content": "Please speak this message out loud",
                "category": "USER_INTERACTION",
                "metadata": {}
            },
            "expected": ProcessingDecision.AVATAR_AND_ANALYSIS,
            "reason": "Speech requests should go to S1"
        },
        {
            "name": "Trader character analysis",
            "context": {
                "content": "Analyze Bitcoin volatility",
                "category": "CONTEXTUAL_UPDATE",
                "metadata": {
                    "character_id": "trader",
                    "team_type": "trader"
                }
            },
            "expected": ProcessingDecision.ANALYSIS_ONLY,
            "reason": "Trader characters must go to S2 only"
        },
        {
            "name": "S2-only processing mode",
            "context": {
                "content": "Process this data",
                "metadata": {
                    "processing_mode": "s2_only"
                }
            },
            "expected": ProcessingDecision.ANALYSIS_ONLY,
            "reason": "Explicit S2-only mode"
        },
        {
            "name": "Educational content with speech",
            "context": {
                "content": "Hello, teach me about Python",
                "metadata": {
                    "team_type": "teacher"
                }
            },
            "expected": ProcessingDecision.AVATAR_AND_ANALYSIS,
            "reason": "Teacher with speech keywords should go to both"
        },
        {
            "name": "Streaming content",
            "context": {
                "content": "Create engaging weather content",
                "metadata": {
                    "team_type": "streamer",
                    "character_id": "weatherman"
                }
            },
            "expected": ProcessingDecision.AVATAR_AND_ANALYSIS,
            "reason": "Streamer content typically needs avatar"
        },
        {
            "name": "Force S2 flag",
            "context": {
                "content": "Analyze system performance",
                "metadata": {
                    "force_s2": True
                }
            },
            "expected": ProcessingDecision.ANALYSIS_ONLY,
            "reason": "Force S2 flag should override"
        },
        {
            "name": "Target systems S2",
            "context": {
                "content": "Complex analysis task",
                "metadata": {
                    "target_systems": ["s2"]
                }
            },
            "expected": ProcessingDecision.ANALYSIS_ONLY,
            "reason": "Explicit S2 targeting"
        },
        {
            "name": "Admin request",
            "context": {
                "content": "Create new character configuration",
                "category": "DIRECT_ADMIN",
                "metadata": {}
            },
            "expected": ProcessingDecision.AVATAR_AND_ANALYSIS,
            "reason": "Admin requests go to both systems"
        },
        {
            "name": "Trader with speech keyword",
            "context": {
                "content": "Speak about market trends",
                "metadata": {
                    "character_id": "trader"
                }
            },
            "expected": ProcessingDecision.ANALYSIS_ONLY,
            "reason": "Trader overrides speech keywords"
        },
        {
            "name": "Analysis-only keywords",
            "context": {
                "content": "Analyze and evaluate this data",
                "category": "CONTEXTUAL_UPDATE",
                "metadata": {}
            },
            "expected": ProcessingDecision.ANALYSIS_ONLY,
            "reason": "Pure analysis keywords without speech"
        }
    ]
    
    print("🧪 Testing S1/S2 Routing Logic")
    print("=" * 80)
    
    passed = 0
    failed = 0
    
    for scenario in test_scenarios:
        result = EMERGENCY_OVERRIDE.evaluate(scenario["context"])
        success = result == scenario["expected"]
        
        status = "✅ PASS" if success else "❌ FAIL"
        print(f"\n{status} {scenario['name']}")
        print(f"   Expected: {scenario['expected'].value}")
        print(f"   Got:      {result.value}")
        print(f"   Reason:   {scenario['reason']}")
        
        if not success:
            print(f"   Context:  {scenario['context']}")
        
        if success:
            passed += 1
        else:
            failed += 1
    
    print(f"\n{'=' * 80}")
    print(f"📊 Summary: {passed}/{len(test_scenarios)} passed ({passed/len(test_scenarios)*100:.0f}%)")
    
    if failed > 0:
        print(f"⚠️  {failed} tests failed")
        return False
    else:
        print("✅ All tests passed!")
        return True

if __name__ == "__main__":
    success = test_routing()
    sys.exit(0 if success else 1)