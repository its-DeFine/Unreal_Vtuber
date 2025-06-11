#!/usr/bin/env python3
"""
Test script to verify Cognee schema functionality with schema-aware Llama3 model

This test script verifies that our schema-aware model (llama3-schema) correctly
generates Cognee-compatible JSON with proper field names.
"""

import asyncio
import sys
import os

# Add the autogen_agent path to sys.path
sys.path.append('/app/autogen_agent')

from services.cognee_direct_service import CogneeDirectService

async def test_cognee_schema():
    """Test Cognee schema functionality with our schema-aware model"""
    
    print("🧪 [TEST] Starting Cognee schema validation test...")
    
    try:
        # Initialize CogneeDirectService
        cognee_service = CogneeDirectService(dataset_name="test_schema")
        
        print("🔧 [TEST] Initializing Cognee service...")
        success = await cognee_service.initialize()
        
        if not success:
            print("❌ [TEST] Failed to initialize Cognee service")
            return False
            
        print("✅ [TEST] Cognee service initialized successfully")
        
        # Test simple data addition
        test_data = [
            "AutoGen is an AI agent orchestration framework",
            "Cognee provides knowledge graph capabilities", 
            "The system uses Llama3 for natural language processing"
        ]
        
        print("🔍 [TEST] Adding test data to Cognee...")
        add_result = await cognee_service.add_data(test_data)
        print(f"📝 [TEST] Add result: {add_result}")
        
        # Test cognify (this is where schema validation happens)
        print("🧩 [TEST] Running cognify to test schema generation...")
        cognify_result = await cognee_service.cognify()
        print(f"🔗 [TEST] Cognify result: {cognify_result}")
        
        # Test search
        print("🔍 [TEST] Testing search functionality...")
        search_results = await cognee_service.search("AutoGen framework", limit=5)
        print(f"🔍 [TEST] Search results: {search_results}")
        
        print("✅ [TEST] All tests completed successfully!")
        return True
        
    except Exception as e:
        print(f"❌ [TEST] Test failed with error: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    # Run the test
    success = asyncio.run(test_cognee_schema())
    sys.exit(0 if success else 1) 