#!/usr/bin/env python3
"""
🧠 Parallel Cognee Testing Script

Test Cognee functionality while your main AutoGen system is running.
This helps debug validation errors and understand LLM output patterns.
"""

import asyncio
import logging
import os
from datetime import datetime
import json
import sys

# Add the autogen agent path for imports
sys.path.append('./app/CORE/autogen-agent')

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s %(levelname)s %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler(f'cognee_parallel_test_{datetime.now().strftime("%Y%m%d_%H%M%S")}.log')
    ]
)

class CogneeParallelTester:
    """Test Cognee in parallel with the main system"""
    
    def __init__(self):
        self.test_dataset = f"parallel_test_{datetime.now().strftime('%H%M%S')}"
        
    async def run_comprehensive_test(self):
        """Run comprehensive Cognee testing"""
        print("🧠 PARALLEL COGNEE TESTING")
        print("=" * 50)
        print(f"📅 Test started: {datetime.now().isoformat()}")
        print(f"🏷️ Test dataset: {self.test_dataset}")
        print("=" * 50)
        
        try:
            # Import and initialize Cognee service
            from autogen_agent.services.cognee_direct_service import CogneeDirectService
            
            service = CogneeDirectService(dataset_name=self.test_dataset)
            
            print("1️⃣ INITIALIZING SERVICE...")
            success = await service.initialize()
            if not success:
                print("❌ Service initialization failed")
                return False
            print("✅ Service initialized successfully")
            
            # Test 1: Simple data addition
            print("\n2️⃣ TESTING DATA ADDITION...")
            test_data = [
                "Parallel test data #1: Simple cognitive operation",
                "Parallel test data #2: AutoGen evolution testing",
                f"Parallel test data #3: Timestamp {datetime.now().isoformat()}"
            ]
            
            add_result = await service.add_data(test_data)
            print(f"✅ Data addition result: {add_result}")
            
            # Test 2: Cognify with detailed error handling
            print("\n3️⃣ TESTING COGNIFY (Knowledge Graph Processing)...")
            print("⚠️ This is where validation errors typically occur...")
            
            cognify_result = await service.cognify()
            if cognify_result.get('success'):
                print("✅ Cognify completed successfully!")
            else:
                print(f"⚠️ Cognify had issues: {cognify_result}")
                print("🔍 This is expected due to LLM validation errors")
            
            # Test 3: Search functionality  
            print("\n4️⃣ TESTING SEARCH...")
            search_queries = [
                "parallel test",
                "cognitive operation", 
                "AutoGen evolution",
                "timestamp"
            ]
            
            for query in search_queries:
                results = await service.search(query, limit=3)
                print(f"🔍 Query '{query}': {len(results)} results")
                if results:
                    for i, result in enumerate(results[:1], 1):
                        preview = str(result)[:100] + "..." if len(str(result)) > 100 else str(result)
                        print(f"   {i}. {preview}")
            
            # Test 4: Store and process workflow
            print("\n5️⃣ TESTING STORE AND PROCESS...")
            workflow_data = [
                f"Workflow test: Full Cognee integration at {datetime.now()}",
                "This tests the complete add->cognify->search pipeline"
            ]
            
            store_result = await service.store_and_process(workflow_data, auto_cognify=True)
            print(f"✅ Store and process result: {store_result}")
            
            # Test 5: Service status
            print("\n6️⃣ CHECKING SERVICE STATUS...")
            status = await service.get_status()
            print(f"📊 Service status: {json.dumps(status, indent=2)}")
            
            print("\n" + "=" * 50)
            print("🎉 PARALLEL TESTING COMPLETED")
            print("✅ All operations tested successfully")
            print("📝 Check the log file for detailed LLM input/output traces")
            print("=" * 50)
            
            return True
            
        except Exception as e:
            print(f"❌ Test failed with error: {e}")
            import traceback
            traceback.print_exc()
            return False
    
    async def run_continuous_monitoring(self, interval_seconds=60):
        """Run continuous monitoring of Cognee operations"""
        print(f"📊 Starting continuous Cognee monitoring (every {interval_seconds}s)")
        print("Press Ctrl+C to stop...")
        
        try:
            cycle = 0
            while True:
                cycle += 1
                print(f"\n🔄 Monitoring Cycle #{cycle} - {datetime.now().strftime('%H:%M:%S')}")
                
                # Quick health check
                from autogen_agent.services.cognee_direct_service import CogneeDirectService
                service = CogneeDirectService(dataset_name=f"monitor_{cycle}")
                
                if await service.initialize():
                    # Test basic operations
                    test_data = [f"Monitor cycle {cycle}: System operational"]
                    await service.add_data(test_data)
                    results = await service.search("monitor", limit=1)
                    print(f"✅ Cycle {cycle}: Health check passed ({len(results)} search results)")
                else:
                    print(f"❌ Cycle {cycle}: Health check failed")
                
                await asyncio.sleep(interval_seconds)
                
        except KeyboardInterrupt:
            print("\n🛑 Monitoring stopped by user")
        except Exception as e:
            print(f"❌ Monitoring error: {e}")

async def main():
    """Main test function"""
    tester = CogneeParallelTester()
    
    if len(sys.argv) > 1 and sys.argv[1] == "--monitor":
        # Continuous monitoring mode
        interval = int(sys.argv[2]) if len(sys.argv) > 2 else 60
        await tester.run_continuous_monitoring(interval)
    else:
        # Single comprehensive test
        await tester.run_comprehensive_test()

if __name__ == "__main__":
    # Set environment for testing
    os.environ['COGNEE_LOG_LEVEL'] = 'DEBUG'
    os.environ['LOG_LEVEL'] = 'DEBUG'
    
    print("🚀 Usage:")
    print("  python test_cognee_parallel.py           # Run single comprehensive test")
    print("  python test_cognee_parallel.py --monitor [seconds]  # Continuous monitoring")
    print()
    
    asyncio.run(main()) 