#!/usr/bin/env python3
"""
Demo script for the Stimuli Categorizer Node.

This script demonstrates how to use the StimuliCategorizerNode
with different types of stimuli.
"""

import asyncio
import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.models.stimuli import ExternalStimuli, Priority
from src.gateway.nodes import StimuliCategorizerNode, CategorizerConfig
from src.utils import create_llm_client


async def demo_categorizer():
    """Run a demo of the categorizer node."""
    
    # Create LLM client (using mock for demo)
    llm_client = create_llm_client("mock")
    
    # Configure the categorizer
    config = CategorizerConfig(
        confidence_threshold=0.7,
        enable_fallback=True,
        log_llm_responses=True
    )
    
    # Create the categorizer node
    categorizer = StimuliCategorizerNode(llm_client, config)
    
    # Test stimuli examples
    test_stimuli = [
        # Direct admin command
        ExternalStimuli(
            content="Set avatar hair color to purple",
            source="admin_console",
            priority=Priority.HIGH
        ),
        
        # User interaction
        ExternalStimuli(
            content="Hello! How are you doing today?",
            source="user_chat",
            metadata={"user_id": "user123"}
        ),
        
        # System notification - avatar state
        ExternalStimuli(
            content="Avatar state changed to speaking",
            source="system",
            priority=Priority.HIGH
        ),
        
        # Social media mention
        ExternalStimuli(
            content="@vtuber_ai just posted a new video!",
            source="twitter",
            metadata={"platform": "twitter", "type": "mention"}
        ),
        
        # Emergency
        ExternalStimuli(
            content="URGENT: Memory usage critical! Immediate action required!",
            source="monitoring",
            priority=Priority.CRITICAL
        ),
        
        # Autonomous trigger
        ExternalStimuli(
            content="Idle for 5 minutes, triggering autonomous behavior",
            source="autonomous",
            metadata={"idle_time": 300}
        ),
        
        # Contextual update
        ExternalStimuli(
            content="Weather update: It's sunny today",
            source="external_api",
            priority=Priority.LOW
        )
    ]
    
    print("=== Stimuli Categorizer Demo ===\n")
    
    # Process each stimuli
    for i, stimuli in enumerate(test_stimuli, 1):
        print(f"--- Test {i} ---")
        print(f"Content: {stimuli.content}")
        print(f"Source: {stimuli.source}")
        print(f"Priority: {stimuli.priority.value}")
        
        # Categorize
        result = await categorizer.process(stimuli)
        
        print(f"Category: {result.category.value}")
        print(f"Confidence: {result.confidence:.2f}")
        print(f"Method: {result.classification_metadata['classification_method']}")
        print(f"Reasoning: {result.classification_metadata['reasoning']}")
        print()
    
    # Show health check
    print("--- Health Check ---")
    health = await categorizer.health_check()
    print(f"Healthy: {health['healthy']}")
    print(f"Total Processed: {health['total_processed']}")
    print(f"LLM Success Rate: {health['llm_success_rate']:.1f}%")
    print()


async def demo_ollama_integration():
    """Demo with real Ollama integration (requires Ollama running)."""
    
    print("=== Ollama Integration Demo ===\n")
    
    try:
        # Create Ollama client
        llm_client = create_llm_client(
            "ollama",
            base_url="http://localhost:11434",
            model="llama3.2:3b"
        )
        
        # Check if Ollama is available
        if not await llm_client.health_check():
            print("❌ Ollama is not available at http://localhost:11434")
            print("Please start Ollama with: ollama serve")
            return
        
        print("✓ Connected to Ollama")
        
        # Create categorizer
        config = CategorizerConfig(
            confidence_threshold=0.8,
            llm_temperature=0.3,
            llm_timeout=15.0
        )
        
        categorizer = StimuliCategorizerNode(llm_client, config)
        
        # Test with a complex stimuli
        stimuli = ExternalStimuli(
            content="The system is experiencing high load. Users are reporting slow response times. Please investigate and optimize performance.",
            source="monitoring",
            priority=Priority.HIGH,
            metadata={"alert_type": "performance", "severity": "warning"}
        )
        
        print(f"Processing stimuli: {stimuli.content[:50]}...")
        
        result = await categorizer.process(stimuli)
        
        print(f"\nResult:")
        print(f"Category: {result.category.value}")
        print(f"Confidence: {result.confidence:.2f}")
        print(f"Reasoning: {result.classification_metadata['reasoning']}")
        
    except Exception as e:
        print(f"Error: {e}")
    finally:
        # Clean up
        if hasattr(llm_client, 'client'):
            await llm_client.client.aclose()


async def main():
    """Run all demos."""
    # Run mock demo
    await demo_categorizer()
    
    # Optionally run Ollama demo
    print("\nWould you like to test with Ollama? (requires Ollama running)")
    print("Press 'y' to test with Ollama, any other key to skip: ")
    
    # Simple input handling for demo
    # In production, use proper async input handling
    import select
    import sys
    
    # Check if input is available (with timeout)
    if sys.stdin in select.select([sys.stdin], [], [], 5)[0]:
        response = sys.stdin.readline().strip().lower()
        if response == 'y':
            await demo_ollama_integration()


if __name__ == "__main__":
    asyncio.run(main())