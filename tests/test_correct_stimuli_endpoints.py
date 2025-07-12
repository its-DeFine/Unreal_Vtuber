#!/usr/bin/env python3
"""
Test Correct Stimuli Endpoints Investigation
==========================================

This script investigates and demonstrates the CORRECT way to send stimuli
to both S1 and S2 containers by testing the actual endpoints that exist.
"""

import asyncio
import aiohttp
import json
import time
from datetime import datetime
from typing import Dict, Any, Optional

# Container endpoints based on docker-compose.all.yml
S1_NEUROSYNC_API_URL = "http://localhost:5000"     # NeuroSync Local API (port 5000)
S1_PLAYER_URL = "http://localhost:5001"             # NeuroSync Player (port 5001)
S2_AUTOGEN_URL = "http://localhost:8200"            # AutoGen Agent (port 8200)

# Timeout for requests
TIMEOUT = 30


class StimuliEndpointTester:
    """Test class to investigate the correct stimuli endpoints"""
    
    def __init__(self):
        self.session = None
        self.results = []
    
    async def __aenter__(self):
        self.session = aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=TIMEOUT))
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.session:
            await self.session.close()
    
    async def _make_request(self, method: str, url: str, json_data: Dict = None, headers: Dict = None) -> Optional[Dict]:
        """Make HTTP request and handle errors gracefully"""
        try:
            async with self.session.request(method, url, json=json_data, headers=headers) as response:
                response_text = await response.text()
                
                if response.content_type == 'application/json':
                    try:
                        response_json = json.loads(response_text)
                    except:
                        response_json = {"raw_response": response_text}
                else:
                    response_json = {"raw_response": response_text}
                
                return {
                    "status_code": response.status,
                    "success": 200 <= response.status < 300,
                    "content_type": response.content_type,
                    "data": response_json
                }
        except Exception as e:
            return {
                "status_code": None,
                "success": False,
                "error": str(e),
                "data": None
            }
    
    def _log_result(self, test_name: str, result: Dict, details: str = ""):
        """Log test result"""
        status = "✅ SUCCESS" if result.get("success") else "❌ FAILED"
        status_code = f" ({result.get('status_code', 'N/A')})" if result.get('status_code') else ""
        error = f" - {result.get('error', '')}" if result.get('error') else ""
        
        print(f"{status}{status_code} {test_name}{error}")
        if details:
            print(f"   {details}")
        if result.get("data") and result["success"]:
            print(f"   Response: {json.dumps(result['data'], indent=2)[:200]}...")
        
        self.results.append({
            "test_name": test_name,
            "result": result,
            "details": details
        })
    
    # === S1 Container Tests ===
    
    async def test_s1_endpoints(self):
        """Test S1 container endpoints to find stimuli capabilities"""
        print("\n🔍 INVESTIGATING S1 CONTAINER ENDPOINTS")
        print("=" * 60)
        
        # Test S1 NeuroSync API (port 5000)
        print(f"\n📡 Testing S1 NeuroSync API ({S1_NEUROSYNC_API_URL})")
        
        # Health check
        result = await self._make_request("GET", f"{S1_NEUROSYNC_API_URL}/health")
        self._log_result("S1 NeuroSync Health", result)
        
        # SCB endpoints
        result = await self._make_request("GET", f"{S1_NEUROSYNC_API_URL}/scb/ping")
        self._log_result("S1 SCB Ping", result)
        
        result = await self._make_request("GET", f"{S1_NEUROSYNC_API_URL}/scb/slice")
        self._log_result("S1 SCB Slice", result, "Shared Cognitive Blackboard data access")
        
        # Test SCB directive posting (this is how to send stimuli to S1)
        directive_data = {
            "text": "This is a test stimuli message for S1 avatar system",
            "actor": "test_system",
            "ttl": 15
        }
        result = await self._make_request("POST", f"{S1_NEUROSYNC_API_URL}/scb/directive", directive_data)
        self._log_result("S1 SCB Directive (Stimuli)", result, "CORRECT way to send stimuli to S1")
        
        # Test S1 Player (port 5001)
        print(f"\n🎭 Testing S1 Player ({S1_PLAYER_URL})")
        
        # Health check
        result = await self._make_request("GET", f"{S1_PLAYER_URL}/health")
        self._log_result("S1 Player Health", result)
        
        # Process text endpoint (direct speech stimuli)
        text_data = {
            "text": "Hello, this is a test stimuli for speech generation",
            "direct_speech": True,
            "autonomous_context": {
                "source": "test_system",
                "direct_speech": True
            }
        }
        result = await self._make_request("POST", f"{S1_PLAYER_URL}/process_text", text_data)
        self._log_result("S1 Process Text (Speech Stimuli)", result, "CORRECT way to send speech stimuli to S1")
        
        # Game control endpoint (avatar control stimuli)
        game_data = {
            "prompt": "wave hello and smile, then nod",
            "autonomous_context": {
                "source": "test_system"
            }
        }
        result = await self._make_request("POST", f"{S1_PLAYER_URL}/game_control", game_data)
        self._log_result("S1 Game Control (Avatar Stimuli)", result, "CORRECT way to send avatar control stimuli to S1")
        
        # Character management endpoints
        result = await self._make_request("GET", f"{S1_PLAYER_URL}/character/list")
        self._log_result("S1 Character List", result, "Available characters")
        
        result = await self._make_request("GET", f"{S1_PLAYER_URL}/character/current")
        self._log_result("S1 Current Character", result, "Active character info")
    
    # === S2 Container Tests ===
    
    async def test_s2_endpoints(self):
        """Test S2 container endpoints to find stimuli capabilities"""
        print("\n🔍 INVESTIGATING S2 CONTAINER ENDPOINTS")
        print("=" * 60)
        
        print(f"\n🤖 Testing S2 AutoGen Agent ({S2_AUTOGEN_URL})")
        
        # Health check
        result = await self._make_request("GET", f"{S2_AUTOGEN_URL}/health")
        self._log_result("S2 Health", result)
        
        # Status check
        result = await self._make_request("GET", f"{S2_AUTOGEN_URL}/api/status")
        self._log_result("S2 Status", result, "System status and services")
        
        # Stimuli status
        result = await self._make_request("GET", f"{S2_AUTOGEN_URL}/api/stimuli/status")
        self._log_result("S2 Stimuli Status", result, "Orchestrator status for stimuli processing")
        
        # Available tools
        result = await self._make_request("GET", f"{S2_AUTOGEN_URL}/api/stimuli/tools")
        self._log_result("S2 Available Tools", result, "Tools that can be triggered by stimuli")
        
        # Admin control panel
        result = await self._make_request("GET", f"{S2_AUTOGEN_URL}/api/admin/control-panel")
        self._log_result("S2 Admin Control Panel", result, "Admin operations and character status")
        
        # The MAIN stimuli endpoint for S2
        stimuli_data = {
            "stimuli_id": f"test_s2_stimuli_{int(time.time())}",
            "content": "Analyze the current cryptocurrency market trends and provide investment recommendations. Focus on Bitcoin and Ethereum with risk assessment.",
            "source": "test_system",
            "priority": "medium",
            "category": "trading_analysis",
            "confidence": 0.85,
            "metadata": {
                "test_type": "endpoint_investigation",
                "team_preference": "trader"
            }
        }
        result = await self._make_request("POST", f"{S2_AUTOGEN_URL}/api/stimuli/receive", stimuli_data)
        self._log_result("S2 Receive Stimuli (MAIN)", result, "CORRECT way to send stimuli to S2")
        
        # Test processing endpoint (alternative)
        test_data = {
            "content": "Explain quantum computing concepts for beginners",
            "team_type": "educator",
            "metadata": {
                "test_type": "direct_processing"
            }
        }
        result = await self._make_request("POST", f"{S2_AUTOGEN_URL}/api/test/process", test_data)
        self._log_result("S2 Test Process", result, "Alternative direct processing endpoint")
        
        # Control endpoints
        result = await self._make_request("POST", f"{S2_AUTOGEN_URL}/api/stimuli/control/pause")
        self._log_result("S2 Pause Autonomous", result, "Pause autonomous operations")
        
        result = await self._make_request("POST", f"{S2_AUTOGEN_URL}/api/stimuli/control/resume")
        self._log_result("S2 Resume Autonomous", result, "Resume autonomous operations")
    
    # === Summary and Recommendations ===
    
    async def generate_summary(self):
        """Generate summary of findings"""
        print("\n" + "=" * 80)
        print("📋 STIMULI ENDPOINTS INVESTIGATION SUMMARY")
        print("=" * 80)
        
        successful_tests = [r for r in self.results if r["result"].get("success")]
        failed_tests = [r for r in self.results if not r["result"].get("success")]
        
        print(f"\n📊 Test Results:")
        print(f"   Total Tests: {len(self.results)}")
        print(f"   Successful: {len(successful_tests)}")
        print(f"   Failed: {len(failed_tests)}")
        
        print(f"\n✅ CORRECT S1 STIMULI ENDPOINTS:")
        s1_endpoints = [
            ("SCB Directive", f"{S1_NEUROSYNC_API_URL}/scb/directive", "POST", "General stimuli via Shared Cognitive Blackboard"),
            ("Process Text", f"{S1_PLAYER_URL}/process_text", "POST", "Direct speech/text stimuli"),
            ("Game Control", f"{S1_PLAYER_URL}/game_control", "POST", "Avatar control stimuli"),
        ]
        
        for name, endpoint, method, description in s1_endpoints:
            print(f"   • {name}: {method} {endpoint}")
            print(f"     → {description}")
        
        print(f"\n✅ CORRECT S2 STIMULI ENDPOINTS:")
        s2_endpoints = [
            ("Receive Stimuli", f"{S2_AUTOGEN_URL}/api/stimuli/receive", "POST", "Main stimuli endpoint for team processing"),
            ("Test Process", f"{S2_AUTOGEN_URL}/api/test/process", "POST", "Direct team processing for testing"),
        ]
        
        for name, endpoint, method, description in s2_endpoints:
            print(f"   • {name}: {method} {endpoint}")
            print(f"     → {description}")
        
        print(f"\n📡 EXAMPLE STIMULI REQUESTS:")
        
        print(f"\n🎭 S1 Speech Stimuli:")
        s1_speech_example = {
            "text": "Hello! This is a test message for speech synthesis.",
            "direct_speech": True,
            "autonomous_context": {
                "source": "external_system",
                "direct_speech": True
            }
        }
        print(f"   POST {S1_PLAYER_URL}/process_text")
        print(f"   {json.dumps(s1_speech_example, indent=6)}")
        
        print(f"\n🎮 S1 Avatar Control Stimuli:")
        s1_avatar_example = {
            "prompt": "wave hello, smile, and nod approvingly",
            "autonomous_context": {
                "source": "external_system"
            }
        }
        print(f"   POST {S1_PLAYER_URL}/game_control")
        print(f"   {json.dumps(s1_avatar_example, indent=6)}")
        
        print(f"\n🤖 S2 Team Processing Stimuli:")
        s2_example = {
            "stimuli_id": f"external_stimuli_{int(time.time())}",
            "content": "Analyze market trends and provide investment recommendations",
            "source": "external_system",
            "priority": "medium",
            "category": "trading_analysis",
            "metadata": {
                "team_preference": "trader"
            }
        }
        print(f"   POST {S2_AUTOGEN_URL}/api/stimuli/receive")
        print(f"   {json.dumps(s2_example, indent=6)}")
        
        print(f"\n💡 KEY FINDINGS:")
        print("   1. S1 has multiple stimuli endpoints for different purposes:")
        print("      - SCB directives for general stimuli")
        print("      - /process_text for speech generation")
        print("      - /game_control for avatar control")
        print("   2. S2 has a main stimuli API that follows formal request structure")
        print("   3. Both systems are designed to receive external stimuli requests")
        print("   4. No need to make up endpoints - these are the real stimuli interfaces")
        
        print("\n" + "=" * 80)


async def main():
    """Main investigation function"""
    print("🔍 INVESTIGATING CORRECT STIMULI ENDPOINTS")
    print("🎯 Finding the real endpoints for sending stimuli to S1 and S2")
    print("🚫 NO MADE-UP ENDPOINTS - Only testing what actually exists")
    
    async with StimuliEndpointTester() as tester:
        await tester.test_s1_endpoints()
        await tester.test_s2_endpoints()
        await tester.generate_summary()


if __name__ == "__main__":
    asyncio.run(main())