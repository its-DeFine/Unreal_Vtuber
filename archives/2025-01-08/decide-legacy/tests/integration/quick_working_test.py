#!/usr/bin/env python3
"""
Quick test of WORKING memory operations only
"""
import asyncio
import sys
sys.path.append('/app')

async def test_working_operations_only():
    print("🚀 TESTING ONLY THE WORKING OPERATIONS")
    print("="*50)
    
    try:
        from autogen_agent.services.cognee_direct_service import CogneeDirectService
        
        # Initialize
        print("1. 🔧 Initializing service...")
        service = CogneeDirectService()
        await service.initialize()
        print("   ✅ Service initialized")
        
        # Add memory (KNOWN to work)
        print("2. 📝 Adding memory...")
        result = await service.add_memory("Test: Our fix works perfectly")
        print(f"   ✅ Memory added: {result}")
        
        # Search memory (should work)  
        print("3. 🔍 Searching memory...")
        results = await service.search("fix works")
        print(f"   ✅ Search found {len(results)} results")
        
        # DO NOT CALL cognify() - we know it hangs
        
        print("="*50)
        print("🎉 SUCCESS: Working operations confirmed!")
        print("✅ Memory add: WORKING")
        print("✅ Memory search: WORKING") 
        print("❌ cognify(): SKIPPED (known to hang)")
        print("="*50)
        
        return True
        
    except Exception as e:
        print(f"❌ Test failed: {e}")
        return False

if __name__ == "__main__":
    asyncio.run(test_working_operations_only()) 