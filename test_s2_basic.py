#!/usr/bin/env python3
"""
Basic S2 System Test
===================

Simple test to verify S2 system functionality and measure basic performance.
Focuses on API response times and team processing verification.
"""

import requests
import time
import json
import asyncio
from datetime import datetime
import uuid

class BasicS2Tester:
    def __init__(self, api_url="http://localhost:8200"):
        self.api_url = api_url
        self.test_results = []
    
    def test_api_health(self):
        """Test API health endpoint."""
        start_time = time.time()
        try:
            response = requests.get(f"{self.api_url}/health", timeout=10)
            response_time = time.time() - start_time
            
            if response.status_code == 200:
                health_data = response.json()
                print(f"✅ API Health: {response_time:.3f}s")
                print(f"   Status: {health_data.get('status')}")
                print(f"   S2 Teams: {health_data.get('s2_teams_status', {}).get('teams_available', [])}")
                return True, response_time, health_data
            else:
                print(f"❌ API Health failed: {response.status_code}")
                return False, response_time, None
        except Exception as e:
            response_time = time.time() - start_time
            print(f"❌ API Health error: {e}")
            return False, response_time, None
    
    def test_tools_endpoint(self):
        """Test tools availability endpoint."""
        start_time = time.time()
        try:
            response = requests.get(f"{self.api_url}/api/stimuli/tools", timeout=10)
            response_time = time.time() - start_time
            
            if response.status_code == 200:
                tools_data = response.json()
                tool_count = tools_data.get('tool_count', 0)
                print(f"✅ Tools Endpoint: {response_time:.3f}s")
                print(f"   Available Tools: {tool_count}")
                return True, response_time, tools_data
            else:
                print(f"❌ Tools endpoint failed: {response.status_code}")
                return False, response_time, None
        except Exception as e:
            response_time = time.time() - start_time
            print(f"❌ Tools endpoint error: {e}")
            return False, response_time, None
    
    def test_stimuli_processing(self, team_type="trader", content="Test market analysis"):
        """Test basic stimuli processing."""
        stimuli_id = f"test_{uuid.uuid4().hex[:8]}"
        
        payload = {
            "stimuli_id": stimuli_id,
            "content": content,
            "source": "basic_test",
            "priority": "medium",
            "metadata": {
                "team_preference": team_type,
                "processing_mode": "s2_only"
            }
        }
        
        # Measure API response time
        start_time = time.time()
        try:
            response = requests.post(
                f"{self.api_url}/api/stimuli/receive",
                json=payload,
                timeout=30
            )
            api_response_time = time.time() - start_time
            
            if response.status_code == 200:
                response_data = response.json()
                print(f"✅ Stimuli API: {api_response_time:.3f}s")
                print(f"   Stimuli ID: {stimuli_id}")
                print(f"   Decision: {response_data.get('agent_decision', 'unknown')}")
                print(f"   Processing Time: {response_data.get('processing_time', 0):.3f}s")
                
                # Wait a bit to see if we can observe processing
                print(f"   ⏳ Waiting for team processing...")
                time.sleep(15)  # Give time for S2 processing
                
                return True, api_response_time, response_data, stimuli_id
            else:
                print(f"❌ Stimuli processing failed: {response.status_code} - {response.text}")
                return False, api_response_time, None, None
        except Exception as e:
            api_response_time = time.time() - start_time
            print(f"❌ Stimuli processing error: {e}")
            return False, api_response_time, None, None
    
    def run_comprehensive_test(self):
        """Run comprehensive S2 system test."""
        print("🚀 Starting Basic S2 System Test")
        print("=" * 50)
        
        results = {
            'timestamp': datetime.now().isoformat(),
            'tests': []
        }
        
        # Test 1: API Health
        print("\n1. Testing API Health...")
        health_success, health_time, health_data = self.test_api_health()
        results['tests'].append({
            'test': 'api_health',
            'success': health_success,
            'response_time': health_time,
            'data': health_data
        })
        
        # Test 2: Tools Endpoint
        print("\n2. Testing Tools Endpoint...")
        tools_success, tools_time, tools_data = self.test_tools_endpoint()
        results['tests'].append({
            'test': 'tools_endpoint',
            'success': tools_success,
            'response_time': tools_time,
            'data': tools_data
        })
        
        # Test 3: Team Processing Tests
        teams_to_test = ['trader', 'educator', 'streamer']
        test_contents = {
            'trader': 'Analyze Bitcoin market trends for trading opportunities',
            'educator': 'Create a lesson plan for Python programming basics',
            'streamer': 'Generate content ideas for gaming livestream'
        }
        
        for team in teams_to_test:
            print(f"\n3.{teams_to_test.index(team)+1}. Testing {team.title()} Team...")
            content = test_contents.get(team, f"Test {team} processing")
            success, response_time, response_data, stimuli_id = self.test_stimuli_processing(team, content)
            
            results['tests'].append({
                'test': f'{team}_team_processing',
                'success': success,
                'api_response_time': response_time,
                'stimuli_id': stimuli_id,
                'data': response_data
            })
        
        # Calculate summary
        total_tests = len(results['tests'])
        successful_tests = sum(1 for test in results['tests'] if test['success'])
        success_rate = successful_tests / total_tests if total_tests > 0 else 0
        
        print("\n" + "=" * 50)
        print("📊 TEST SUMMARY")
        print("=" * 50)
        print(f"Total Tests: {total_tests}")
        print(f"Successful: {successful_tests}")
        print(f"Success Rate: {success_rate:.1%}")
        
        # Response time analysis
        api_times = [test['response_time'] for test in results['tests'] if 'response_time' in test and test['success']]
        if api_times:
            avg_response_time = sum(api_times) / len(api_times)
            max_response_time = max(api_times)
            print(f"Average API Response: {avg_response_time:.3f}s")
            print(f"Max API Response: {max_response_time:.3f}s")
        
        # Team-specific results
        team_tests = [test for test in results['tests'] if 'team_processing' in test['test']]
        if team_tests:
            print(f"\nTeam Processing Results:")
            for test in team_tests:
                team_name = test['test'].replace('_team_processing', '').title()
                status = "✅" if test['success'] else "❌"
                response_time = test.get('api_response_time', 0)
                print(f"  {status} {team_name}: {response_time:.3f}s API response")
        
        # Issues found
        issues = []
        if tools_data and tools_data.get('tool_count', 0) == 0:
            issues.append("No tools available - tool system may not be initialized")
        
        failed_tests = [test for test in results['tests'] if not test['success']]
        if failed_tests:
            issues.append(f"{len(failed_tests)} test(s) failed")
        
        if issues:
            print(f"\n⚠️ Issues Found:")
            for issue in issues:
                print(f"  - {issue}")
        
        print("=" * 50)
        
        # Save results
        with open('s2_basic_test_results.json', 'w') as f:
            json.dump(results, f, indent=2)
        print(f"📁 Results saved to: s2_basic_test_results.json")
        
        return results

if __name__ == '__main__':
    tester = BasicS2Tester()
    results = tester.run_comprehensive_test() 