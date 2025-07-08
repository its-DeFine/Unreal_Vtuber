#!/usr/bin/env python3
import asyncio
import sys
sys.path.append('/app')

async def test_cognee():
    try:
        from autogen_agent.services.cognee_direct_service import get_cognee_direct_service
        print('🧠 Testing Cognee Service...')
        
        service = await get_cognee_direct_service()
        if service:
            print('✅ Cognee Service: Available')
            
            # Test memory search
            results = await service.search('AutoGen system operational')
            print(f'🔍 Search Results: {len(results)} found')
            
            # Test adding new data
            test_data = ['Integration test successful - Cognee working perfectly']
            add_result = await service.add_data(test_data)
            print(f'📝 Data Addition: {add_result.get("success", False)}')
            
            return True
        else:
            print('❌ Cognee Service: Not Available')
            return False
    except Exception as e:
        print(f'❌ Error: {e}')
        return False

result = asyncio.run(test_cognee())
print(f'🎯 Integration Test: {"✅ PASSED" if result else "❌ FAILED"}') 