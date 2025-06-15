#!/usr/bin/env python3
"""
Test script for Autonomous Statistics Evolution & Persistence System
Tests database persistence, conversation storage, and evolution tracking
"""

import asyncio
import aiohttp
import json
import time
from datetime import datetime, timedelta

BASE_URL = "http://localhost:8200"

async def test_statistics_persistence():
    """Test statistics collection and persistence"""
    print("\n🧪 Testing Statistics Persistence...")
    
    async with aiohttp.ClientSession() as session:
        # Get initial statistics
        async with session.get(f"{BASE_URL}/api/statistics") as resp:
            initial_stats = await resp.json()
            print(f"Initial statistics: {json.dumps(initial_stats, indent=2)}")
        
        # Wait for a few decision cycles
        print("⏳ Waiting for decision cycles...")
        await asyncio.sleep(65)  # Wait for ~2 cycles
        
        # Get updated statistics
        async with session.get(f"{BASE_URL}/api/statistics") as resp:
            updated_stats = await resp.json()
            print(f"\nUpdated statistics: {json.dumps(updated_stats, indent=2)}")
            
        # Get detailed statistics
        async with session.get(f"{BASE_URL}/api/statistics/detailed") as resp:
            if resp.status == 200:
                detailed_stats = await resp.json()
                print(f"\n📊 Detailed statistics available:")
                print(f"  - Total cycles: {detailed_stats['summary']['total_cycles']}")
                print(f"  - Success rate: {detailed_stats['summary']['success_rate']:.2%}")
                print(f"  - Avg decision time: {detailed_stats['summary']['avg_decision_time']:.2f}s")
                
                if detailed_stats.get('tools'):
                    print("\n🔧 Tool Usage Statistics:")
                    for tool in detailed_stats['tools'][:5]:
                        print(f"  - {tool['tool_name']}: {tool['usage_count']} uses, {tool.get('success_rate', 0):.2%} success")
            else:
                print(f"❌ Failed to get detailed statistics: {resp.status}")

async def test_tool_usage_tracking():
    """Test tool usage tracking and reporting"""
    print("\n\n🧪 Testing Tool Usage Tracking...")
    
    async with aiohttp.ClientSession() as session:
        # Get tool usage report
        async with session.get(f"{BASE_URL}/api/tools/usage?limit=10") as resp:
            if resp.status == 200:
                usage_data = await resp.json()
                print(f"\n🔧 Tool Usage Report:")
                
                if usage_data.get('most_used'):
                    print("\nMost Used Tools:")
                    for tool in usage_data['most_used']:
                        print(f"  - {tool['tool_name']}: {tool['usage_count']} uses")
                        
                if usage_data.get('success_rates'):
                    print("\nSuccess Rates:")
                    for tool_name, rate in list(usage_data['success_rates'].items())[:5]:
                        print(f"  - {tool_name}: {rate:.2%}")
                        
                if usage_data.get('avg_execution_times'):
                    print("\nAverage Execution Times:")
                    for tool_name, time in list(usage_data['avg_execution_times'].items())[:5]:
                        print(f"  - {tool_name}: {time:.3f}s")
            else:
                print(f"❌ Failed to get tool usage report: {resp.status}")

async def test_conversation_storage():
    """Test conversation storage and retrieval"""
    print("\n\n🧪 Testing Conversation Storage...")
    
    async with aiohttp.ClientSession() as session:
        # Get stored conversations
        async with session.get(f"{BASE_URL}/api/conversations?limit=5") as resp:
            if resp.status == 200:
                conv_data = await resp.json()
                print(f"\n💬 Stored Conversations: {conv_data['total']} total")
                
                for conv in conv_data['conversations']:
                    print(f"\n📝 Conversation {conv['id']}:")
                    print(f"  - Iteration: {conv['iteration']}")
                    print(f"  - Agents: {', '.join(conv['agents'])}")
                    print(f"  - Duration: {conv['duration']:.2f}s")
                    print(f"  - Tools triggered: {', '.join(conv['tools_triggered']) if conv['tools_triggered'] else 'None'}")
            else:
                print(f"❌ Failed to get conversations: {resp.status}")

async def test_evolution_history():
    """Test evolution history tracking"""
    print("\n\n🧪 Testing Evolution History...")
    
    async with aiohttp.ClientSession() as session:
        # Get evolution history
        async with session.get(f"{BASE_URL}/api/evolution/history") as resp:
            if resp.status == 200:
                history_data = await resp.json()
                print(f"\n🧬 Evolution History:")
                print(f"  - Total modifications: {len(history_data['modifications'])}")
                print(f"  - Successful improvements: {history_data['total_improvements']}")
                print(f"  - Average improvement: {history_data['avg_improvement']:.2f}%")
                print(f"  - Risk breakdown: {json.dumps(history_data['risk_breakdown'], indent=4)}")
                
                if history_data['modifications']:
                    print("\n📋 Recent Modifications:")
                    for mod in history_data['modifications'][:3]:
                        print(f"\n  - ID: {mod['id']}")
                        print(f"    Target: {mod['target_file']}")
                        print(f"    Type: {mod['modification_type']}")
                        print(f"    Status: {mod['status']}")
                        if mod.get('actual_improvement'):
                            print(f"    Actual improvement: {mod['actual_improvement']:.2f}%")
            else:
                print(f"❌ Failed to get evolution history: {resp.status}")

async def test_custom_report():
    """Test custom report generation"""
    print("\n\n🧪 Testing Custom Report Generation...")
    
    async with aiohttp.ClientSession() as session:
        # Generate comprehensive report for last 24h
        report_request = {
            "type": "comprehensive",
            "timeframe": "24h",
            "filters": {}
        }
        
        async with session.post(f"{BASE_URL}/api/reports/generate", json=report_request) as resp:
            if resp.status == 200:
                report = await resp.json()
                print(f"\n📊 Custom Report Generated:")
                print(f"  - Report type: {report.get('report_type')}")
                print(f"  - Timeframe: {report.get('timeframe')}")
                print(f"  - Generated at: {report.get('generated_at')}")
                
                if report.get('summary'):
                    print(f"\n📈 Summary:")
                    summary = report['summary']
                    print(f"  - Total cycles: {summary.get('total_cycles', 0)}")
                    print(f"  - Success rate: {summary.get('success_rate', 0):.2%}")
                    print(f"  - Tools executed: {summary.get('total_tools_executed', 0)}")
            else:
                print(f"❌ Failed to generate report: {resp.status}")

async def test_database_connectivity():
    """Test database connectivity"""
    print("\n🧪 Testing Database Connectivity...")
    
    async with aiohttp.ClientSession() as session:
        async with session.get(f"{BASE_URL}/api/test-db") as resp:
            db_status = await resp.json()
            print(f"Database status: {json.dumps(db_status, indent=2)}")

async def main():
    """Run all tests"""
    print("=" * 60)
    print("🚀 Autonomous Statistics Evolution & Persistence Tests")
    print("=" * 60)
    
    # Test database connectivity first
    await test_database_connectivity()
    
    # Run all tests
    await test_statistics_persistence()
    await test_tool_usage_tracking()
    await test_conversation_storage()
    await test_evolution_history()
    await test_custom_report()
    
    print("\n" + "=" * 60)
    print("✅ All tests completed!")
    print("=" * 60)

if __name__ == "__main__":
    asyncio.run(main())