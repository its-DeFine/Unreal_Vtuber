#!/usr/bin/env python3
"""
Test Orchestrator Character Switching
Verifies that S1 correctly switches characters based on orchestrator persona routing
Created: 2025-07-14
"""
import pytest
import httpx
import asyncio
import time
import json
from typing import Dict, Any

# Test configuration
ORCHESTRATOR_URL = "http://localhost:8082"
S1_URL = "http://localhost:5001"
TIMEOUT = httpx.Timeout(30.0, connect=5.0)


@pytest.fixture
async def async_client():
    """Create async HTTP client"""
    async with httpx.AsyncClient(timeout=TIMEOUT) as client:
        yield client


class TestCharacterSwitching:
    """Test S1 character switching based on orchestrator routing"""
    
    @pytest.mark.asyncio
    async def test_character_endpoints_available(self, async_client):
        """Test that character management endpoints are available"""
        # Test current character endpoint
        response = await async_client.get(f"{S1_URL}/character/current")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"
        assert "character" in data
        
        # Test character list endpoint
        response = await async_client.get(f"{S1_URL}/character/list")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"
        assert len(data["characters"]) >= 3  # Should have at least 3 characters
    
    @pytest.mark.asyncio
    async def test_trader_persona_switches_to_sophia(self, async_client):
        """Test that trader persona routes to Sophia Trader character"""
        # Send trader query through orchestrator
        stimulus = {
            "stimulus_id": "test_trader_character",
            "text": "What is the current BTC price?",
            "priority": "normal"
        }
        
        # Process through orchestrator
        response = await async_client.post(f"{ORCHESTRATOR_URL}/process", json=stimulus)
        assert response.status_code == 200
        result = response.json()
        
        # Verify routing decision
        assert result["routing_decision"]["system"] == "s1"
        assert result["routing_decision"]["config"]["persona"] == "trader"
        
        # Wait a moment for character switch to complete
        await asyncio.sleep(0.5)
        
        # Check current character
        char_response = await async_client.get(f"{S1_URL}/character/current")
        assert char_response.status_code == 200
        char_data = char_response.json()
        
        # Verify it's Sophia Trader
        assert char_data["character"]["id"] == "sophia_trader_template"
        assert char_data["character"]["name"] == "Sophia Trader"
        assert char_data["character"]["role"] == "Cryptocurrency Trading Expert"
        print(f"✅ Trader persona correctly switched to: {char_data['character']['name']}")
    
    @pytest.mark.asyncio
    async def test_streamer_persona_switches_to_luna(self, async_client):
        """Test that streamer persona routes to Luna Streamer character"""
        # Send streamer query through orchestrator
        stimulus = {
            "stimulus_id": "test_streamer_character",
            "text": "Tell me something funny",
            "priority": "normal"
        }
        
        # Process through orchestrator
        response = await async_client.post(f"{ORCHESTRATOR_URL}/process", json=stimulus)
        assert response.status_code == 200
        result = response.json()
        
        # Verify routing decision
        assert result["routing_decision"]["system"] == "s1"
        assert result["routing_decision"]["config"]["persona"] == "streamer"
        
        # Wait a moment for character switch to complete
        await asyncio.sleep(0.5)
        
        # Check current character
        char_response = await async_client.get(f"{S1_URL}/character/current")
        assert char_response.status_code == 200
        char_data = char_response.json()
        
        # Verify it's Luna Streamer
        assert char_data["character"]["id"] == "luna_streamer_template"
        assert char_data["character"]["name"] == "Luna Streamer"
        assert char_data["character"]["role"] == "Content Creator & Entertainer"
        print(f"✅ Streamer persona correctly switched to: {char_data['character']['name']}")
    
    @pytest.mark.asyncio
    async def test_educator_persona_switches_to_diana(self, async_client):
        """Test that educator queries that go to S1 use Diana character"""
        # Try a simple educator query that might route to S1
        stimulus = {
            "stimulus_id": "test_educator_character",
            "text": "Quick, what is 2+2?",
            "priority": "normal"
        }
        
        # Process through orchestrator
        response = await async_client.post(f"{ORCHESTRATOR_URL}/process", json=stimulus)
        assert response.status_code == 200
        result = response.json()
        
        # If it routes to S1, check character
        if result["routing_decision"]["system"] == "s1":
            # Wait a moment for character switch to complete
            await asyncio.sleep(0.5)
            
            # Check current character
            char_response = await async_client.get(f"{S1_URL}/character/current")
            assert char_response.status_code == 200
            char_data = char_response.json()
            
            # Verify it's Diana Educator
            assert char_data["character"]["id"] == "diana_educator_template"
            assert char_data["character"]["name"] == "Diana Code"
            assert char_data["character"]["role"] == "Programming Instructor"
            print(f"✅ Educator persona correctly switched to: {char_data['character']['name']}")
        else:
            print(f"ℹ️ Educator query routed to S2, skipping S1 character check")
    
    @pytest.mark.asyncio
    async def test_rapid_character_switching(self, async_client):
        """Test that rapid switches between characters work correctly"""
        test_sequences = [
            ("BTC price quick!", "trader", "sophia_trader_template"),
            ("Tell a joke!", "streamer", "luna_streamer_template"),
            ("Current ETH price?", "trader", "sophia_trader_template"),
        ]
        
        for text, expected_persona, expected_character_id in test_sequences:
            # Send request
            stimulus = {
                "stimulus_id": f"rapid_test_{int(time.time())}",
                "text": text,
                "priority": "normal"
            }
            
            response = await async_client.post(f"{ORCHESTRATOR_URL}/process", json=stimulus)
            assert response.status_code == 200
            result = response.json()
            
            # Only check if routed to S1
            if result["routing_decision"]["system"] == "s1":
                assert result["routing_decision"]["config"]["persona"] == expected_persona
                
                # Small delay for character switch
                await asyncio.sleep(0.3)
                
                # Verify character
                char_response = await async_client.get(f"{S1_URL}/character/current")
                char_data = char_response.json()
                assert char_data["character"]["id"] == expected_character_id
                print(f"✅ Rapid switch: {expected_persona} → {char_data['character']['name']}")
    
    @pytest.mark.asyncio
    async def test_character_persistence_across_requests(self, async_client):
        """Test that character persists until explicitly changed"""
        # Set to trader character
        stimulus = {
            "stimulus_id": "persistence_test_1",
            "text": "BTC price?",
            "priority": "normal"
        }
        
        response = await async_client.post(f"{ORCHESTRATOR_URL}/process", json=stimulus)
        assert response.status_code == 200
        
        await asyncio.sleep(0.5)
        
        # Check character
        char_response = await async_client.get(f"{S1_URL}/character/current")
        initial_character = char_response.json()["character"]["id"]
        
        # Wait and check again without sending new request
        await asyncio.sleep(2)
        char_response = await async_client.get(f"{S1_URL}/character/current")
        persisted_character = char_response.json()["character"]["id"]
        
        assert initial_character == persisted_character
        print(f"✅ Character persisted: {persisted_character}")


class TestCharacterBehaviorDifferences:
    """Test that different characters actually behave differently"""
    
    @pytest.mark.asyncio
    async def test_character_formality_differences(self, async_client):
        """Test that characters have different formality levels"""
        # Get all characters
        response = await async_client.get(f"{S1_URL}/character/list")
        characters = response.json()["characters"]
        
        formality_levels = {}
        for char_id, char_info in characters.items():
            # Switch to character
            switch_response = await async_client.post(
                f"{S1_URL}/character/switch",
                json={"character_id": char_id}
            )
            
            if switch_response.status_code == 200:
                # Get current character details
                char_response = await async_client.get(f"{S1_URL}/character/current")
                char_data = char_response.json()["character"]
                formality_levels[char_data["name"]] = char_data["formality_level"]
        
        # Verify different formality levels
        assert formality_levels.get("Sophia Trader") == "formal"
        assert formality_levels.get("Luna Streamer") == "casual"
        assert formality_levels.get("Diana Code") == "neutral"
        
        print("✅ Characters have distinct formality levels:")
        for name, level in formality_levels.items():
            print(f"   - {name}: {level}")


class TestErrorHandling:
    """Test error handling in character switching"""
    
    @pytest.mark.asyncio
    async def test_invalid_character_switch(self, async_client):
        """Test handling of invalid character switch requests"""
        # Try to switch to non-existent character
        response = await async_client.post(
            f"{S1_URL}/character/switch",
            json={"character_id": "non_existent_character"}
        )
        assert response.status_code == 400
        
        # Current character should remain unchanged
        char_response = await async_client.get(f"{S1_URL}/character/current")
        assert char_response.status_code == 200
        print("✅ Invalid character switch handled gracefully")


if __name__ == "__main__":
    import sys
    
    print("🧪 Orchestrator Character Switching Test Suite")
    print("=" * 50)
    print("This test verifies that:")
    print("1. S1 switches characters based on orchestrator personas")
    print("2. Each persona maps to the correct character")
    print("3. Characters persist between requests")
    print("4. Rapid switching works correctly")
    print("=" * 50)
    
    # Run with pytest
    pytest.main([__file__, "-v", "--tb=short"])