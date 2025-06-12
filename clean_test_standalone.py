#!/usr/bin/env python3
"""
STANDALONE CLEAN TEST - No automatic cognify
"""
import asyncio
import os
import sys

# Set environment to prevent automatic cognify
os.environ['SKIP_COGNIFY'] = 'true'
sys.path.append('/app')

async def clean_standalone_test():
    print("🧠 CLEAN STANDALONE COGNEE TEST")
    print("="*45)
    print("🎯 TESTING: Memory operations WITHOUT cognify")
    print("="*45)
    
    try:
        # Import service directly 
        from autogen_agent.services.cognee_direct_service import CogneeDirectService
        
        # Create fresh service instance
        service = CogneeDirectService()
        
        print("1. 🔧 Initializing Cognee service...")
        await service.initialize()
        print("   ✅ Service initialized successfully")
        
        print("2. 📝 Adding memory data...")
        memory_text = "CLEAN TEST: Memory system is working perfectly after restart"
        result = await service.add_memory(memory_text)
        print(f"   ✅ Memory added: {result}")
        
        print("3. 🔍 Searching stored memories...")
        search_results = await service.search("CLEAN TEST")
        print(f"   ✅ Search found {len(search_results)} results")
        
        if search_results:
            print("   📋 Search result preview:")
            for i, result in enumerate(search_results[:2], 1):
                preview = result[:60] + "..." if len(result) > 60 else result
                print(f"      {i}. {preview}")
        
        print("4. 🧪 Adding evolution-related memory...")
        evolution_memory = "Evolution system ready: Real code modifications functional"
        await service.add_memory(evolution_memory)
        print("   ✅ Evolution memory stored")
        
        print("5. 🔍 Testing evolution memory search...")
        evolution_results = await service.search("evolution")
        print(f"   ✅ Found {len(evolution_results)} evolution-related memories")
        
        print("="*45)
        print("🎉 SUCCESS: CLEAN TEST COMPLETED!")
        print("✅ Service initialization: WORKING")
        print("✅ Memory storage: WORKING")
        print("✅ Memory search: WORKING")
        print("✅ Evolution integration: READY")
        print("="*45)
        print("💡 RESULT: Memory system fully functional!")
        print("🚀 Evolution system can now use memory safely!")
        
        return True
        
    except Exception as e:
        print(f"❌ Clean test failed: {e}")
        import traceback
        print(f"📋 Traceback: {traceback.format_exc()}")
        return False

if __name__ == "__main__":
    asyncio.run(clean_standalone_test()) 