#!/usr/bin/env python3
"""
S2 Character Teams Demonstration
================================

Shows the current state of S1/S2 integration with character-specific teams.
"""

import json
import time
import requests
import subprocess
from datetime import datetime
from typing import Dict, List, Tuple

class S1S2Tester:
    def __init__(self):
        self.s1_base_url = "http://localhost:5001"
        self.s2_queue_file = "/tmp/s2_processing_queue.json"
        self.results = {
            "s1": [],
            "s2": [],
            "summary": {}
        }
    
    def test_s1_health(self) -> bool:
        """Test S1 health endpoint"""
        try:
            resp = requests.get(f"{self.s1_base_url}/health", timeout=5)
            return resp.status_code == 200
        except:
            return False
    
    def test_s1_process_text(self, text: str, character_type: str) -> bool:
        """Test S1 process_text endpoint"""
        try:
            payload = {
                "text": text,
                "direct_speech": True,
                "autonomous_context": {
                    "source": "s2_character_test",
                    "character_type": character_type,
                    "timestamp": datetime.now().isoformat()
                }
            }
            resp = requests.post(f"{self.s1_base_url}/process_text", json=payload, timeout=10)
            return resp.status_code == 200
        except:
            return False
    
    def send_s2_stimuli(self, character_id: str, team_type: str, prompt: str) -> Dict:
        """Send stimuli to S2 queue and check processing"""
        # Clear queue first
        subprocess.run([
            "docker", "exec", "autogen_agent", "bash", "-c",
            "echo '[]' > /tmp/s2_processing_queue.json"
        ])
        
        # Create stimuli
        stimuli = {
            "prompt": prompt,
            "timestamp": datetime.now().isoformat(),
            "source": f"character_test_{team_type}",
            "processing_mode": "s2_only",
            "metadata": {
                "character_id": character_id,
                "team_type": team_type,
                "test_id": f"test_{int(time.time())}"
            }
        }
        
        # Send to queue
        cmd = f"echo '{json.dumps([stimuli])}' > /tmp/s2_processing_queue.json"
        subprocess.run(["docker", "exec", "autogen_agent", "bash", "-c", cmd])
        
        # Wait for processing
        time.sleep(15)
        
        # Check logs for indicators
        logs = subprocess.run(
            ["docker", "logs", "autogen_agent", "--tail", "300"],
            capture_output=True,
            text=True
        )
        
        # Define success indicators per team
        team_indicators = {
            "trader": ["market", "risk", "portfolio", "trading", "financial"],
            "streamer": ["content", "engagement", "social", "streaming", "audience"],
            "teacher": ["learning", "curriculum", "educational", "assessment", "student"],
            "default": ["system", "optimization", "performance", "resource", "efficiency"]
        }
        
        indicators_found = []
        for indicator in team_indicators.get(team_type, []):
            if indicator.lower() in logs.stdout.lower():
                indicators_found.append(indicator)
        
        # Check if queue was processed
        queue_check = subprocess.run(
            ["docker", "exec", "autogen_agent", "cat", "/tmp/s2_processing_queue.json"],
            capture_output=True,
            text=True
        )
        queue_cleared = queue_check.stdout.strip() == "[]"
        
        return {
            "success": len(indicators_found) > 0,
            "indicators_found": indicators_found,
            "queue_cleared": queue_cleared,
            "team_detected": team_type in logs.stdout.lower()
        }
    
    def run_comprehensive_test(self):
        """Run comprehensive test of all systems"""
        print("🚀 S2 Character Teams Comprehensive Test")
        print("=" * 80)
        print(f"Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        
        # Test configurations
        test_scenarios = [
            {
                "name": "Financial Expert",
                "character_id": "dr._house_doctor_template",
                "team_type": "trader",
                "s1_prompt": "Market analysis update",
                "s2_prompt": "Analyze Bitcoin volatility and suggest portfolio diversification strategies"
            },
            {
                "name": "Content Creator",
                "character_id": "weatherman_template",
                "team_type": "streamer",
                "s1_prompt": "Weather forecast for streaming",
                "s2_prompt": "Create engaging weather content with interactive elements for social media"
            },
            {
                "name": "Educator",
                "character_id": "emma_teacher_template",
                "team_type": "teacher",
                "s1_prompt": "Teaching methodology",
                "s2_prompt": "Design adaptive learning curriculum for Python programming beginners"
            },
            {
                "name": "System Optimizer",
                "character_id": "secretary_template",
                "team_type": "default",
                "s1_prompt": "System performance report",
                "s2_prompt": "Analyze system bottlenecks and recommend optimization strategies"
            }
        ]
        
        # Test S1 Health
        print("🏥 Testing S1 (NeuroSync) Health...")
        s1_healthy = self.test_s1_health()
        print(f"   {'✅' if s1_healthy else '❌'} Health check: {'PASSED' if s1_healthy else 'FAILED'}\n")
        
        # Run tests for each scenario
        for i, scenario in enumerate(test_scenarios, 1):
            print(f"{'='*80}")
            print(f"📋 Test {i}/4: {scenario['name']} ({scenario['team_type'].upper()} Team)")
            print(f"{'='*80}")
            
            # Test S1
            print(f"\n🎮 S1 Test - {scenario['character_id']}")
            if s1_healthy:
                s1_success = self.test_s1_process_text(
                    scenario["s1_prompt"], 
                    scenario["team_type"]
                )
                self.results["s1"].append({
                    "scenario": scenario["name"],
                    "success": s1_success
                })
                print(f"   {'✅' if s1_success else '❌'} Process text: {'SUCCESS' if s1_success else 'FAILED'}")
            else:
                print("   ⚠️  S1 not available")
            
            # Test S2
            print(f"\n🤖 S2 Test - {scenario['team_type']} team")
            s2_result = self.send_s2_stimuli(
                scenario["character_id"],
                scenario["team_type"],
                scenario["s2_prompt"]
            )
            
            self.results["s2"].append({
                "scenario": scenario["name"],
                "team": scenario["team_type"],
                **s2_result
            })
            
            print(f"   {'✅' if s2_result['success'] else '❌'} Specialized processing: "
                  f"{'DETECTED' if s2_result['success'] else 'NOT DETECTED'}")
            if s2_result["indicators_found"]:
                print(f"   📌 Indicators found: {', '.join(s2_result['indicators_found'])}")
            print(f"   📁 Queue cleared: {'YES' if s2_result['queue_cleared'] else 'NO'}")
            
            time.sleep(3)
        
        # Generate summary
        self.generate_summary()
    
    def generate_summary(self):
        """Generate test summary"""
        print(f"\n{'='*80}")
        print("📊 TEST SUMMARY")
        print(f"{'='*80}\n")
        
        # S1 Summary
        s1_success = sum(1 for r in self.results["s1"] if r["success"])
        s1_total = len(self.results["s1"])
        
        print("🎮 S1 (NeuroSync) Results:")
        for result in self.results["s1"]:
            status = "✅" if result["success"] else "❌"
            print(f"   {status} {result['scenario']}")
        if s1_total > 0:
            print(f"\n   Success Rate: {s1_success}/{s1_total} ({s1_success/s1_total*100:.0f}%)")
        
        # S2 Summary
        s2_success = sum(1 for r in self.results["s2"] if r["success"])
        s2_total = len(self.results["s2"])
        
        print("\n🤖 S2 (Specialized Teams) Results:")
        for result in self.results["s2"]:
            status = "✅" if result["success"] else "❌"
            print(f"   {status} {result['scenario']} ({result['team'].upper()} team)")
            if result["indicators_found"]:
                print(f"      Indicators: {', '.join(result['indicators_found'][:3])}")
        
        print(f"\n   Success Rate: {s2_success}/{s2_total} ({s2_success/s2_total*100:.0f}%)")
        
        # Queue processing status
        queue_issues = sum(1 for r in self.results["s2"] if not r["queue_cleared"])
        if queue_issues > 0:
            print(f"\n   ⚠️  Queue Processing Issue: {queue_issues}/{s2_total} not cleared")
            print("      (Orchestrator handling instead of queue consumer)")
        
        # Overall assessment
        print(f"\n{'='*80}")
        print("🎯 OVERALL ASSESSMENT")
        print(f"{'='*80}")
        
        if s1_success == s1_total and s2_success >= s2_total * 0.75:
            print("\n✅ EXCELLENT: Both systems performing well!")
            print("   - S1 fully operational")
            print(f"   - S2 showing {s2_success}/{s2_total} specialized team behaviors")
        elif s2_success >= s2_total * 0.5:
            print("\n⚠️  GOOD: Systems partially operational")
            print(f"   - S1: {s1_success}/{s1_total} working")
            print(f"   - S2: {s2_success}/{s2_total} teams showing specialization")
        else:
            print("\n❌ NEEDS ATTENTION: Systems require debugging")
        
        # Architecture note
        print("\n📋 Current Architecture:")
        print("   S1: NeuroSync with /process_text endpoint")
        print("   S2: Character-based team selection with specialized tools")
        print("   Issue: Queue consumer not polling (orchestrator processing instead)")
        
        # Recommendations
        print("\n💡 Recommendations:")
        if queue_issues > 0:
            print("   1. Debug queue consumer service startup")
        if s2_success < s2_total:
            teams_failing = [r["team"] for r in self.results["s2"] if not r["success"]]
            print(f"   2. Investigate {', '.join(set(teams_failing))} team configurations")
        print("   3. Add more detailed team activation logging")

if __name__ == "__main__":
    tester = S1S2Tester()
    tester.run_comprehensive_test()