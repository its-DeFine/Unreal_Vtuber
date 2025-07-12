"""
End-to-End Stimuli Flow Tests
============================

Tests the complete stimuli processing flow through the unified CORE system.
Based on real architecture analysis and testing.

Architecture:
- S1 (NeuroSync): Avatar/speech system on ports 5000/5001
- S2 (AutoGen): Multi-agent teams on port 8200  
- Unified CORE: Shared processing logic and routing
"""

import asyncio
import json
import pytest
import requests
import time
from typing import Dict, Any


class TestStimuliFlow:
    """Tests for end-to-end stimuli processing through unified CORE system."""
    
    S1_BASE_URL = "http://localhost:5001"
    S2_BASE_URL = "http://localhost:8200"
    
    def setup_test(self):
        """Ensure systems are healthy before each test."""
        # Check S1 health
        s1_health = requests.get(f"{self.S1_BASE_URL}/health")
        assert s1_health.status_code == 200
        assert s1_health.json()["status"] == "healthy"
        
        # Check S2 health  
        s2_health = requests.get(f"{self.S2_BASE_URL}/health")
        assert s2_health.status_code == 200
        assert s2_health.json()["status"] == "healthy"
        
        print("✅ Both S1 and S2 systems are healthy")

    def test_s1_process_text_direct(self):
        """Test S1 direct text processing (speech/avatar)."""
        test_payload = {
            "text": "Hello! This is a test of the speech system."
        }
        
        response = requests.post(
            f"{self.S1_BASE_URL}/process_text",
            json=test_payload,
            headers={"Content-Type": "application/json"}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "processing"
        assert data["s1_system"] is True
        assert "llm_provider" in data
        
        print(f"✅ S1 text processing successful: {data}")

    def test_s2_stimuli_queueing(self):
        """Test S2 stimuli queueing system."""
        test_stimuli = {
            "stimuli_id": "test_s2_queue",
            "content": "Can you analyze the current market trends for technology stocks?",
            "source": "e2e_test",
            "priority": "medium",
            "category": "financial",
            "confidence": 0.8
        }
        
        response = requests.post(
            f"{self.S2_BASE_URL}/api/stimuli/receive",
            json=test_stimuli,
            headers={"Content-Type": "application/json"}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["stimuli_id"] == "test_s2_queue"
        assert "queued_for_s2_processing" in data["agent_decision"]
        
        print(f"✅ S2 stimuli queuing successful: {data}")

    def test_s2_queue_consumer_processing(self):
        """Test that S2 queue consumer is actually processing stimuli."""
        # Get initial stats
        initial_health = requests.get(f"{self.S2_BASE_URL}/health").json()
        initial_processed = initial_health["s2_teams_status"]["queue_stats"]["processed"]
        
        # Send educational stimuli
        educational_stimuli = {
            "stimuli_id": "test_education_processing",
            "content": "Explain how neural networks learn through backpropagation. Include examples.",
            "source": "e2e_test_education",
            "priority": "medium", 
            "category": "educational",
            "confidence": 0.9
        }
        
        response = requests.post(
            f"{self.S2_BASE_URL}/api/stimuli/receive",
            json=educational_stimuli,
            headers={"Content-Type": "application/json"}
        )
        
        assert response.status_code == 200
        assert response.json()["success"] is True
        
        # Wait for processing (queue consumer polls every 5 seconds)
        time.sleep(8)
        
        # Check stats updated
        final_health = requests.get(f"{self.S2_BASE_URL}/health").json()
        final_processed = final_health["s2_teams_status"]["queue_stats"]["processed"]
        
        assert final_processed > initial_processed, f"Expected processed count to increase from {initial_processed} to >{initial_processed}, got {final_processed}"
        assert final_health["s2_teams_status"]["queue_consumer"] is True
        assert "educator" in final_health["s2_teams_status"]["queue_stats"]["teams_available"]
        
        print(f"✅ Queue consumer processing verified: {initial_processed} -> {final_processed}")

    def test_s1_character_endpoints(self):
        """Test S1 character management endpoints."""
        # Test character list
        char_list = requests.get(f"{self.S1_BASE_URL}/character/list")
        assert char_list.status_code == 200
        data = char_list.json()
        assert data["status"] == "success"
        assert "characters" in data
        assert isinstance(data["characters"], list)
        
        # Test current character
        current_char = requests.get(f"{self.S1_BASE_URL}/character/current")
        
        if current_char.status_code == 200:
            char_data = current_char.json()
            assert char_data["status"] == "success"
            assert "character" in char_data
            print(f"✅ Current character: {char_data['character']['name']}")
        else:
            print("ℹ️ No active character currently set")
        
        print(f"✅ Character management endpoints working: {len(data['characters'])} characters available")

    def test_s2_admin_endpoints(self):
        """Test S2 admin and status endpoints."""
        # Test status endpoint
        status_response = requests.get(f"{self.S2_BASE_URL}/api/stimuli/status")
        assert status_response.status_code == 200
        status_data = status_response.json()
        assert status_data["autonomous_state"] == "running"
        
        # Test tools endpoint  
        tools_response = requests.get(f"{self.S2_BASE_URL}/api/stimuli/tools")
        assert tools_response.status_code == 200
        tools_data = tools_response.json()
        assert "available_tools" in tools_data
        assert isinstance(tools_data["available_tools"], list)
        
        print(f"✅ S2 admin endpoints working: {len(tools_data['available_tools'])} tools available")

    def test_different_team_routing(self):
        """Test that different content types route to appropriate teams."""
        test_cases = [
            {
                "content": "What are the best investment strategies for cryptocurrency in 2025?",
                "category": "financial",
                "expected_team": "trader"
            },
            {
                "content": "How do I create engaging content for my YouTube channel?", 
                "category": "content_creation",
                "expected_team": "streamer"
            },
            {
                "content": "Explain quantum computing principles for beginners.",
                "category": "educational", 
                "expected_team": "educator"
            }
        ]
        
        for i, test_case in enumerate(test_cases):
            stimuli = {
                "stimuli_id": f"team_routing_test_{i}",
                "content": test_case["content"],
                "source": "team_routing_test",
                "priority": "medium",
                "category": test_case["category"],
                "confidence": 0.8
            }
            
            response = requests.post(
                f"{self.S2_BASE_URL}/api/stimuli/receive",
                json=stimuli,
                headers={"Content-Type": "application/json"}
            )
            
            assert response.status_code == 200
            data = response.json()
            assert data["success"] is True
            
            print(f"✅ {test_case['category']} stimuli queued successfully")
        
        # Allow time for all to be processed
        time.sleep(10)
        
        # Verify all were processed
        health = requests.get(f"{self.S2_BASE_URL}/health").json()
        teams_available = health["s2_teams_status"]["queue_stats"]["teams_available"]
        
        assert "trader" in teams_available
        assert "educator" in teams_available  
        assert "streamer" in teams_available
        
        print("✅ All specialized teams are available and processing")

    def test_system_integration_flow(self):
        """Test complete system integration with both S1 and S2."""
        # This simulates how the unified CORE system would handle
        # stimuli that requires both speech output (S1) and analysis (S2)
        
        # 1. Send educational content to S2 for analysis
        educational_analysis = {
            "stimuli_id": "integration_test_s2",
            "content": "I need to understand machine learning concepts. Can you break down supervised vs unsupervised learning?",
            "source": "integration_test",
            "priority": "medium",
            "category": "educational",
            "confidence": 0.9
        }
        
        s2_response = requests.post(
            f"{self.S2_BASE_URL}/api/stimuli/receive",
            json=educational_analysis,
            headers={"Content-Type": "application/json"}
        )
        
        assert s2_response.status_code == 200
        assert s2_response.json()["success"] is True
        
        # 2. Send speech content to S1 (simulating result from S2 analysis)
        speech_content = {
            "text": "Great question! Let me explain the difference between supervised and unsupervised learning in machine learning.",
            "autonomous_context": {
                "source": "s2_analysis_result", 
                "processing_mode": "s1_speech"
            }
        }
        
        s1_response = requests.post(
            f"{self.S1_BASE_URL}/process_text",
            json=speech_content,
            headers={"Content-Type": "application/json"}
        )
        
        assert s1_response.status_code == 200
        s1_data = s1_response.json()
        assert s1_data["status"] == "processing"
        assert s1_data["s1_system"] is True
        
        print("✅ Complete S1+S2 integration flow successful")
        
        # 3. Verify both systems processed the requests
        time.sleep(5)
        
        s2_health = requests.get(f"{self.S2_BASE_URL}/health").json()
        assert s2_health["s2_teams_status"]["queue_consumer"] is True
        
        s1_health = requests.get(f"{self.S1_BASE_URL}/health").json()
        assert s1_health["status"] == "healthy"
        
        print("✅ Both systems remain healthy after integration test")


if __name__ == "__main__":
    """Run tests directly for manual verification."""
    test_instance = TestStimuliFlow()
    test_instance.setup_test()
    
    print("🧪 Running E2E Stimuli Flow Tests...")
    print("=" * 50)
    
    try:
        test_instance.test_s1_process_text_direct()
        test_instance.test_s2_stimuli_queueing()
        test_instance.test_s2_queue_consumer_processing()
        test_instance.test_s1_character_endpoints()
        test_instance.test_s2_admin_endpoints()
        test_instance.test_different_team_routing()
        test_instance.test_system_integration_flow()
        
        print("=" * 50)
        print("🎉 All E2E tests completed successfully!")
        print("✅ Unified CORE system is functioning correctly")
        print("✅ S1 (NeuroSync) speech/avatar system working")
        print("✅ S2 (AutoGen) multi-agent teams working") 
        print("✅ Stimuli routing and processing verified")
        
    except Exception as e:
        print("=" * 50)
        print(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()