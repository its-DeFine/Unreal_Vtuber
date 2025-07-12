#!/usr/bin/env python3
"""
Correct Stimuli Examples for S1 and S2 Systems
==============================================

This script demonstrates the CORRECT way to send stimuli to both S1 and S2 containers
using the real endpoints that exist, not made-up ones.
"""

import asyncio
import aiohttp
import json
import time
from datetime import datetime
from typing import Dict, Any


class CorrectStimuliSender:
    """Demonstrates correct stimuli sending patterns"""
    
    def __init__(self):
        self.session = None
        
        # Real container endpoints based on investigation
        self.s1_neurosync_api = "http://localhost:5000"  # SCB and neural processing
        self.s1_player_api = "http://localhost:5001"     # Speech and avatar control
        self.s2_autogen_api = "http://localhost:8200"    # Team processing
    
    async def __aenter__(self):
        self.session = aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=30))
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.session:
            await self.session.close()
    
    async def _send_request(self, method: str, url: str, data: Dict = None) -> Dict:
        """Send request and return response"""
        try:
            async with self.session.request(method, url, json=data) as response:
                result = await response.json()
                return {
                    "success": 200 <= response.status < 300,
                    "status_code": response.status,
                    "data": result
                }
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "data": None
            }
    
    # === S1 STIMULI METHODS ===
    
    async def send_s1_speech_stimuli(self, text: str, direct_speech: bool = True) -> Dict:
        """
        Send speech stimuli to S1 system for text-to-speech generation
        
        This is the CORRECT way to trigger speech in S1
        """
        speech_data = {
            "text": text,
            "direct_speech": direct_speech,
            "autonomous_context": {
                "source": "external_stimuli_system",
                "direct_speech": direct_speech,
                "stimuli_type": "speech_generation"
            }
        }
        
        print(f"🎤 Sending S1 Speech Stimuli: {text[:50]}...")
        result = await self._send_request("POST", f"{self.s1_player_api}/process_text", speech_data)
        
        if result["success"]:
            print(f"✅ S1 Speech stimuli accepted: {result['data'].get('status')}")
        else:
            print(f"❌ S1 Speech stimuli failed: {result.get('error')}")
        
        return result
    
    async def send_s1_avatar_control_stimuli(self, action_prompt: str) -> Dict:
        """
        Send avatar control stimuli to S1 system for character animation
        
        This is the CORRECT way to control the avatar in S1
        """
        avatar_data = {
            "prompt": action_prompt,
            "autonomous_context": {
                "source": "external_stimuli_system",
                "stimuli_type": "avatar_control"
            }
        }
        
        print(f"🎭 Sending S1 Avatar Control: {action_prompt[:50]}...")
        result = await self._send_request("POST", f"{self.s1_player_api}/game_control", avatar_data)
        
        if result["success"]:
            data = result["data"]
            print(f"✅ S1 Avatar control accepted: {data.get('commands_generated', 0)} commands generated")
        else:
            print(f"❌ S1 Avatar control failed: {result.get('error')}")
        
        return result
    
    async def send_s1_scb_directive(self, text: str, actor: str = "external_system", ttl: int = 30) -> Dict:
        """
        Send general stimuli to S1 via Shared Cognitive Blackboard
        
        This is the CORRECT way to send general directives to S1
        """
        directive_data = {
            "text": text,
            "actor": actor,
            "ttl": ttl
        }
        
        print(f"📋 Sending S1 SCB Directive: {text[:50]}...")
        result = await self._send_request("POST", f"{self.s1_neurosync_api}/scb/directive", directive_data)
        
        if result["success"]:
            print(f"✅ S1 SCB directive accepted")
        else:
            print(f"❌ S1 SCB directive failed: {result.get('error')}")
        
        return result
    
    # === S2 STIMULI METHODS ===
    
    async def send_s2_team_stimuli(self, content: str, team_preference: str = None, priority: str = "medium") -> Dict:
        """
        Send stimuli to S2 system for team processing
        
        This is the CORRECT way to trigger team processing in S2
        """
        stimuli_data = {
            "stimuli_id": f"external_stimuli_{int(time.time())}_{team_preference or 'auto'}",
            "content": content,
            "source": "external_stimuli_system",
            "priority": priority,
            "metadata": {
                "stimuli_type": "team_processing",
                "timestamp": datetime.now().isoformat()
            }
        }
        
        # Add team preference if specified
        if team_preference:
            stimuli_data["category"] = f"{team_preference}_processing"
            stimuli_data["metadata"]["team_preference"] = team_preference
        
        print(f"🤖 Sending S2 Team Stimuli ({team_preference or 'auto'}): {content[:50]}...")
        result = await self._send_request("POST", f"{self.s2_autogen_api}/api/stimuli/receive", stimuli_data)
        
        if result["success"]:
            data = result["data"]
            print(f"✅ S2 Stimuli accepted: {data.get('agent_decision', 'processed')}")
            if data.get("tools_triggered"):
                print(f"   Tools triggered: {data['tools_triggered']}")
        else:
            print(f"❌ S2 Stimuli failed: {result.get('error')}")
        
        return result
    
    # === COMBINED STIMULI SCENARIOS ===
    
    async def demo_trading_scenario(self):
        """Demonstrate a complete trading scenario with both S1 and S2"""
        print("\n💰 TRADING SCENARIO DEMO")
        print("=" * 50)
        
        # 1. Send trading analysis request to S2
        trading_request = "Analyze current Bitcoin and Ethereum market trends. Provide specific investment recommendations with risk assessment for a $10,000 portfolio."
        s2_result = await self.send_s2_team_stimuli(trading_request, "trader", "high")
        
        # Wait for S2 processing
        await asyncio.sleep(2)
        
        # 2. Send speech instruction to S1 to announce the analysis
        speech_text = "I'm analyzing the current cryptocurrency market trends. Let me provide you with detailed investment recommendations."
        s1_speech_result = await self.send_s1_speech_stimuli(speech_text, direct_speech=True)
        
        # 3. Send avatar control to show thinking/analyzing gesture
        avatar_action = "lean forward thoughtfully, touch chin, then nod confidently"
        s1_avatar_result = await self.send_s1_avatar_control_stimuli(avatar_action)
        
        return {
            "s2_analysis": s2_result,
            "s1_speech": s1_speech_result,
            "s1_avatar": s1_avatar_result
        }
    
    async def demo_education_scenario(self):
        """Demonstrate a complete education scenario"""
        print("\n📚 EDUCATION SCENARIO DEMO")
        print("=" * 50)
        
        # 1. Send education request to S2
        education_request = "Explain quantum computing principles to a beginner. Create a structured learning path with practical examples and assessment methods."
        s2_result = await self.send_s2_team_stimuli(education_request, "educator", "medium")
        
        # Wait for S2 processing
        await asyncio.sleep(2)
        
        # 2. Send welcoming speech to S1
        speech_text = "Welcome to today's quantum computing lesson! I'll guide you through the fascinating world of quantum mechanics and computing."
        s1_speech_result = await self.send_s1_speech_stimuli(speech_text, direct_speech=True)
        
        # 3. Send avatar control for teaching gestures
        avatar_action = "wave hello enthusiastically, then gesture as if explaining concepts with hands"
        s1_avatar_result = await self.send_s1_avatar_control_stimuli(avatar_action)
        
        return {
            "s2_education": s2_result,
            "s1_speech": s1_speech_result,
            "s1_avatar": s1_avatar_result
        }
    
    async def demo_streaming_scenario(self):
        """Demonstrate a streaming/content creation scenario"""
        print("\n📹 STREAMING SCENARIO DEMO")
        print("=" * 50)
        
        # 1. Send content creation request to S2
        content_request = "Create engaging streaming content about the latest technology trends. Include interactive elements and viewer engagement strategies."
        s2_result = await self.send_s2_team_stimuli(content_request, "streamer", "medium")
        
        # Wait for S2 processing
        await asyncio.sleep(2)
        
        # 2. Send energetic greeting to S1
        speech_text = "Hey everyone! Welcome back to the stream! Today we're diving into the most exciting tech trends that are changing our world!"
        s1_speech_result = await self.send_s1_speech_stimuli(speech_text, direct_speech=True)
        
        # 3. Send dynamic streaming gestures to avatar
        avatar_action = "wave energetically at camera, smile broadly, then lean in excitedly"
        s1_avatar_result = await self.send_s1_avatar_control_stimuli(avatar_action)
        
        return {
            "s2_content": s2_result,
            "s1_speech": s1_speech_result,
            "s1_avatar": s1_avatar_result
        }
    
    # === STATUS CHECKING ===
    
    async def check_system_status(self):
        """Check the status of both S1 and S2 systems"""
        print("\n📊 SYSTEM STATUS CHECK")
        print("=" * 50)
        
        # Check S1 systems
        s1_neurosync_health = await self._send_request("GET", f"{self.s1_neurosync_api}/health")
        s1_player_health = await self._send_request("GET", f"{self.s1_player_api}/health")
        
        # Check S2 system
        s2_health = await self._send_request("GET", f"{self.s2_autogen_api}/health")
        s2_stimuli_status = await self._send_request("GET", f"{self.s2_autogen_api}/api/stimuli/status")
        
        print(f"🔧 S1 NeuroSync API: {'✅ Healthy' if s1_neurosync_health['success'] else '❌ Unhealthy'}")
        print(f"🎭 S1 Player API: {'✅ Healthy' if s1_player_health['success'] else '❌ Unhealthy'}")
        print(f"🤖 S2 AutoGen API: {'✅ Healthy' if s2_health['success'] else '❌ Unhealthy'}")
        
        if s2_stimuli_status["success"]:
            stimuli_data = s2_stimuli_status["data"]
            print(f"📥 S2 Stimuli System: ✅ {stimuli_data.get('autonomous_state', 'unknown')} state")
        
        return {
            "s1_neurosync": s1_neurosync_health,
            "s1_player": s1_player_health,
            "s2_autogen": s2_health,
            "s2_stimuli": s2_stimuli_status
        }


async def main():
    """Main demonstration function"""
    print("🎯 CORRECT STIMULI SENDING DEMONSTRATION")
    print("🔗 Using REAL endpoints that actually exist")
    print("🚫 NO made-up endpoints - only legitimate stimuli interfaces")
    print("=" * 80)
    
    async with CorrectStimuliSender() as stimuli_sender:
        # Check system status first
        await stimuli_sender.check_system_status()
        
        # Demonstrate different scenarios
        scenarios = [
            stimuli_sender.demo_trading_scenario,
            stimuli_sender.demo_education_scenario,
            stimuli_sender.demo_streaming_scenario
        ]
        
        for scenario in scenarios:
            try:
                await scenario()
                await asyncio.sleep(3)  # Wait between scenarios
            except Exception as e:
                print(f"❌ Scenario failed: {e}")
        
        print("\n" + "=" * 80)
        print("✅ DEMONSTRATION COMPLETE")
        print("💡 These are the CORRECT ways to send stimuli to S1 and S2 systems")
        print("📋 Summary of correct endpoints:")
        print("   S1 Speech: POST http://localhost:5001/process_text")
        print("   S1 Avatar: POST http://localhost:5001/game_control")
        print("   S1 SCB: POST http://localhost:5000/scb/directive")
        print("   S2 Teams: POST http://localhost:8200/api/stimuli/receive")
        print("=" * 80)


if __name__ == "__main__":
    asyncio.run(main())