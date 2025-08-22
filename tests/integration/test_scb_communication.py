"""
Test SCB (Semantic Communication Bus) S1-S2 Bidirectional Communication
Verifies that S1 (Avatar) and S2 (Thinking) systems can exchange messages
"""

import pytest
import asyncio
import aiohttp
import json
import time
from typing import Dict, Any, List
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

# SCB Gateway configuration
SCB_GATEWAY_URL = "http://localhost:5002"  # Adjust based on your setup
SCB_API_KEY = None  # Set if using authentication


class SCBTester:
    """Test harness for SCB communication"""
    
    def __init__(self, gateway_url: str = SCB_GATEWAY_URL):
        self.gateway_url = gateway_url
        self.session = None
        self.messages_sent = []
        self.messages_received = []
    
    async def __aenter__(self):
        """Async context manager entry"""
        self.session = aiohttp.ClientSession()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit"""
        if self.session:
            await self.session.close()
    
    async def send_s1_to_s2(self, message: str, metadata: Dict[str, Any] = None) -> bool:
        """
        Send message from S1 (Avatar) to S2 (Thinking)
        
        Args:
            message: Text message to send
            metadata: Optional metadata
        
        Returns:
            True if successful
        """
        try:
            event = {
                "type": "s1_message",
                "text": message,
                "metadata": metadata or {
                    "timestamp": datetime.utcnow().isoformat(),
                    "source": "s1_avatar",
                    "agent_id": "test_agent_001"
                }
            }
            
            headers = {"Content-Type": "application/json"}
            if SCB_API_KEY:
                headers["X-SCB-Key"] = SCB_API_KEY
            
            # Send to S2 team slice
            async with self.session.post(
                f"{self.gateway_url}/scb/team/s2_thinking/event",
                json=event,
                headers=headers
            ) as response:
                if response.status == 200:
                    self.messages_sent.append(event)
                    logger.info(f"S1→S2: Sent message: {message[:50]}...")
                    return True
                else:
                    error = await response.text()
                    logger.error(f"S1→S2: Failed to send: {response.status} - {error}")
                    return False
        
        except Exception as e:
            logger.error(f"S1→S2: Error sending message: {e}")
            return False
    
    async def send_s2_to_s1(self, message: str, metadata: Dict[str, Any] = None) -> bool:
        """
        Send message from S2 (Thinking) to S1 (Avatar)
        
        Args:
            message: Text message to send
            metadata: Optional metadata
        
        Returns:
            True if successful
        """
        try:
            event = {
                "type": "s2_response",
                "text": message,
                "metadata": metadata or {
                    "timestamp": datetime.utcnow().isoformat(),
                    "source": "s2_thinking",
                    "agent_id": "test_agent_001"
                }
            }
            
            headers = {"Content-Type": "application/json"}
            if SCB_API_KEY:
                headers["X-SCB-Key"] = SCB_API_KEY
            
            # Send to S1 team slice
            async with self.session.post(
                f"{self.gateway_url}/scb/team/s1_avatar/event",
                json=event,
                headers=headers
            ) as response:
                if response.status == 200:
                    self.messages_sent.append(event)
                    logger.info(f"S2→S1: Sent message: {message[:50]}...")
                    return True
                else:
                    error = await response.text()
                    logger.error(f"S2→S1: Failed to send: {response.status} - {error}")
                    return False
        
        except Exception as e:
            logger.error(f"S2→S1: Error sending message: {e}")
            return False
    
    async def get_s1_messages(self, token_budget: int = 1000) -> List[Dict[str, Any]]:
        """
        Get messages from S1 team slice
        
        Args:
            token_budget: Maximum tokens to retrieve
        
        Returns:
            List of messages
        """
        try:
            headers = {}
            if SCB_API_KEY:
                headers["X-SCB-Key"] = SCB_API_KEY
            
            async with self.session.get(
                f"{self.gateway_url}/scb/team/s1_avatar/slice",
                params={"tokens": token_budget},
                headers=headers
            ) as response:
                if response.status == 200:
                    data = await response.json()
                    messages = data.get("window", [])
                    logger.info(f"Retrieved {len(messages)} S1 messages")
                    return messages
                else:
                    logger.error(f"Failed to get S1 messages: {response.status}")
                    return []
        
        except Exception as e:
            logger.error(f"Error getting S1 messages: {e}")
            return []
    
    async def get_s2_messages(self, token_budget: int = 1000) -> List[Dict[str, Any]]:
        """
        Get messages from S2 team slice
        
        Args:
            token_budget: Maximum tokens to retrieve
        
        Returns:
            List of messages
        """
        try:
            headers = {}
            if SCB_API_KEY:
                headers["X-SCB-Key"] = SCB_API_KEY
            
            async with self.session.get(
                f"{self.gateway_url}/scb/team/s2_thinking/slice",
                params={"tokens": token_budget},
                headers=headers
            ) as response:
                if response.status == 200:
                    data = await response.json()
                    messages = data.get("window", [])
                    logger.info(f"Retrieved {len(messages)} S2 messages")
                    return messages
                else:
                    logger.error(f"Failed to get S2 messages: {response.status}")
                    return []
        
        except Exception as e:
            logger.error(f"Error getting S2 messages: {e}")
            return []
    
    async def send_global_summary(self, summary: str) -> bool:
        """
        Send summary to global SCB slice
        
        Args:
            summary: Summary text (will be truncated to 50 chars)
        
        Returns:
            True if successful
        """
        try:
            # Truncate to 50 characters as per SCB spec
            truncated = summary[:50]
            
            payload = {"summary": truncated}
            
            headers = {"Content-Type": "application/json"}
            if SCB_API_KEY:
                headers["X-SCB-Key"] = SCB_API_KEY
            
            async with self.session.post(
                f"{self.gateway_url}/scb/global/summary",
                json=payload,
                headers=headers
            ) as response:
                if response.status == 200:
                    logger.info(f"Sent global summary: {truncated}")
                    return True
                else:
                    logger.error(f"Failed to send global summary: {response.status}")
                    return False
        
        except Exception as e:
            logger.error(f"Error sending global summary: {e}")
            return False
    
    async def test_health(self) -> bool:
        """Test SCB Gateway health"""
        try:
            async with self.session.get(f"{self.gateway_url}/health") as response:
                if response.status == 200:
                    data = await response.json()
                    logger.info(f"SCB Gateway health: {data}")
                    return True
                else:
                    logger.error(f"SCB Gateway unhealthy: {response.status}")
                    return False
        except Exception as e:
            logger.error(f"Cannot reach SCB Gateway: {e}")
            return False


@pytest.mark.asyncio
async def test_scb_health():
    """Test SCB Gateway is healthy"""
    async with SCBTester() as tester:
        assert await tester.test_health(), "SCB Gateway is not healthy"


@pytest.mark.asyncio
async def test_s1_to_s2_communication():
    """Test S1 can send messages to S2"""
    async with SCBTester() as tester:
        # Send message from S1 to S2
        message = "Hello from S1 Avatar system! Testing communication."
        success = await tester.send_s1_to_s2(message)
        assert success, "Failed to send message from S1 to S2"
        
        # Wait a moment for processing
        await asyncio.sleep(1)
        
        # Verify message arrived in S2 slice
        s2_messages = await tester.get_s2_messages()
        
        # Check if our message is in S2
        found = False
        for msg in s2_messages:
            if "Hello from S1 Avatar" in msg.get("text", ""):
                found = True
                break
        
        assert found, "S1 message not found in S2 slice"


@pytest.mark.asyncio
async def test_s2_to_s1_communication():
    """Test S2 can send messages to S1"""
    async with SCBTester() as tester:
        # Send message from S2 to S1
        message = "Response from S2 Thinking system! Processing complete."
        success = await tester.send_s2_to_s1(message)
        assert success, "Failed to send message from S2 to S1"
        
        # Wait a moment for processing
        await asyncio.sleep(1)
        
        # Verify message arrived in S1 slice
        s1_messages = await tester.get_s1_messages()
        
        # Check if our message is in S1
        found = False
        for msg in s1_messages:
            if "Response from S2 Thinking" in msg.get("text", ""):
                found = True
                break
        
        assert found, "S2 message not found in S1 slice"


@pytest.mark.asyncio
async def test_bidirectional_conversation():
    """Test full bidirectional conversation between S1 and S2"""
    async with SCBTester() as tester:
        # S1 sends initial message
        s1_msg = "S1: What is the current system status?"
        assert await tester.send_s1_to_s2(s1_msg), "S1 initial message failed"
        
        await asyncio.sleep(1)
        
        # S2 responds
        s2_msg = "S2: System status is operational. All services running."
        assert await tester.send_s2_to_s1(s2_msg), "S2 response failed"
        
        await asyncio.sleep(1)
        
        # S1 acknowledges
        s1_ack = "S1: Acknowledged. Proceeding with normal operations."
        assert await tester.send_s1_to_s2(s1_ack), "S1 acknowledgment failed"
        
        await asyncio.sleep(1)
        
        # Verify conversation in both slices
        s1_messages = await tester.get_s1_messages()
        s2_messages = await tester.get_s2_messages()
        
        # Check S1 slice has S2's response
        s1_has_s2_response = any("System status is operational" in msg.get("text", "") for msg in s1_messages)
        assert s1_has_s2_response, "S2 response not in S1 slice"
        
        # Check S2 slice has S1's messages
        s2_has_s1_question = any("What is the current system status" in msg.get("text", "") for msg in s2_messages)
        s2_has_s1_ack = any("Acknowledged" in msg.get("text", "") for msg in s2_messages)
        
        assert s2_has_s1_question, "S1 question not in S2 slice"
        assert s2_has_s1_ack, "S1 acknowledgment not in S2 slice"


@pytest.mark.asyncio
async def test_global_summary():
    """Test global summary functionality"""
    async with SCBTester() as tester:
        summary = "System operational. S1-S2 communication verified."
        assert await tester.send_global_summary(summary), "Failed to send global summary"


@pytest.mark.asyncio
async def test_concurrent_messages():
    """Test handling concurrent messages from both systems"""
    async with SCBTester() as tester:
        # Send multiple messages concurrently
        tasks = [
            tester.send_s1_to_s2("S1 Message 1"),
            tester.send_s2_to_s1("S2 Message 1"),
            tester.send_s1_to_s2("S1 Message 2"),
            tester.send_s2_to_s1("S2 Message 2"),
            tester.send_s1_to_s2("S1 Message 3"),
        ]
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Check all messages were sent successfully
        for i, result in enumerate(results):
            assert result is True, f"Message {i+1} failed to send"
        
        await asyncio.sleep(2)
        
        # Verify messages in slices
        s1_messages = await tester.get_s1_messages()
        s2_messages = await tester.get_s2_messages()
        
        assert len(s1_messages) > 0, "No messages in S1 slice"
        assert len(s2_messages) > 0, "No messages in S2 slice"


async def run_all_tests():
    """Run all SCB communication tests"""
    print("=" * 60)
    print("SCB S1-S2 COMMUNICATION TEST SUITE")
    print("=" * 60)
    
    tests = [
        ("Health Check", test_scb_health),
        ("S1 to S2 Communication", test_s1_to_s2_communication),
        ("S2 to S1 Communication", test_s2_to_s1_communication),
        ("Bidirectional Conversation", test_bidirectional_conversation),
        ("Global Summary", test_global_summary),
        ("Concurrent Messages", test_concurrent_messages),
    ]
    
    passed = 0
    failed = 0
    
    for test_name, test_func in tests:
        print(f"\n🧪 Testing: {test_name}")
        try:
            await test_func()
            print(f"✅ {test_name}: PASSED")
            passed += 1
        except AssertionError as e:
            print(f"❌ {test_name}: FAILED - {e}")
            failed += 1
        except Exception as e:
            print(f"❌ {test_name}: ERROR - {e}")
            failed += 1
    
    print("\n" + "=" * 60)
    print(f"RESULTS: {passed} passed, {failed} failed")
    print("=" * 60)
    
    return failed == 0


if __name__ == "__main__":
    # Configure logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # Run tests
    success = asyncio.run(run_all_tests())
    exit(0 if success else 1)