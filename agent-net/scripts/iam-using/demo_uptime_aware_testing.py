#!/usr/bin/env python3
"""
Demonstration script showing the complete flow of uptime-aware capability testing
with mock GPU uptime data from the worker.

This script:
1. Verifies Docker services are running
2. Tests different agents with varying uptime percentages
3. Shows how job rates adjust based on agent uptime
"""

import asyncio
import subprocess
import time
import signal
import sys
import os
import requests
from datetime import datetime

# Colors for terminal output
GREEN = '\033[92m'
YELLOW = '\033[93m'
RED = '\033[91m'
BLUE = '\033[94m'
RESET = '\033[0m'

class DemoRunner:
    def __init__(self):
        self.processes = []
        
    def cleanup(self, signum=None, frame=None):
        """Clean up all processes on exit"""
        print(f"\n{RED}Cleaning up processes...{RESET}")
        for proc in self.processes:
            if proc.poll() is None:
                proc.terminate()
                proc.wait()
        sys.exit(0)
        
    async def verify_services_running(self):
        """Verify that the required services are running"""
        print(f"{BLUE}Verifying services are running...{RESET}")
        
        services_ok = True
        
        # Check if worker is accessible through gateway
        try:
            response = requests.get("http://localhost:8088/worker/health", timeout=5)
            if response.status_code == 200:
                print(f"{GREEN}✓ Worker service is accessible through gateway{RESET}")
            else:
                print(f"{YELLOW}⚠ Worker returned status {response.status_code}{RESET}")
                services_ok = False
        except Exception as e:
            print(f"{RED}✗ Cannot reach worker service: {e}{RESET}")
            print(f"{YELLOW}  Make sure docker-compose services are running{RESET}")
            services_ok = False
            
        # Check if gateway is accessible
        try:
            response = requests.get("http://localhost:8088/gateway/health", timeout=5)
            if response.status_code == 200:
                print(f"{GREEN}✓ Gateway service is accessible{RESET}")
            else:
                print(f"{YELLOW}⚠ Gateway returned status {response.status_code}{RESET}")
                services_ok = False
        except Exception as e:
            print(f"{RED}✗ Cannot reach gateway service: {e}{RESET}")
            services_ok = False
            
        return services_ok
        
    async def test_gpu_check_endpoint(self, agent_id):
        """Test the GPU check endpoint directly to verify mock data"""
        print(f"\n{BLUE}Testing GPU check endpoint for {agent_id}...{RESET}")
        
        try:
            response = requests.post(
                "http://localhost:8088/worker/gpu-check",
                json={"agent_id": agent_id},
                timeout=5
            )
            
            if response.status_code == 200:
                data = response.json()
                uptime = data.get("uptime_percent", 0)
                print(f"{GREEN}✓ GPU check successful: {agent_id} has {uptime}% uptime{RESET}")
                return uptime
            else:
                print(f"{RED}✗ GPU check failed: {response.status_code}{RESET}")
                return None
        except Exception as e:
            print(f"{RED}✗ Error testing GPU check: {e}{RESET}")
            return None
            
    async def run_uptime_aware_tests(self):
        """Run tests for each agent to show different punishment levels"""
        print(f"\n{BLUE}Running uptime-aware capability tests...{RESET}")
        print("=" * 80)
        
        agents = [
            ("agent-001", "99.5% uptime - Full job rate"),
            ("agent-002", "98.0% uptime - 50% job rate (punishment)"), 
            ("agent-003", "92.0% uptime - 10% job rate (punishment)"),
            ("agent-004", "85.0% uptime - No jobs (full punishment)"),
        ]
        
        # First verify mock data is working
        print(f"\n{YELLOW}Verifying mock data endpoints...{RESET}")
        for agent_id, description in agents:
            await self.test_gpu_check_endpoint(agent_id)
            
        print(f"\n{YELLOW}Starting job rate tests...{RESET}")
        
        for agent_id, description in agents:
            print(f"\n{YELLOW}Testing {agent_id}: {description}{RESET}")
            print("-" * 60)
            
            # Build the command to run the capability tester
            script_dir = os.path.dirname(os.path.abspath(__file__))
            tester_path = os.path.join(script_dir, 'single_orchestrator_tester.py')
            
            # Run the uptime-aware tester
            proc = subprocess.Popen(
                [
                    sys.executable,
                    tester_path,
                    '--agent', agent_id,
                    '--rate', '60',
                    '--capabilities', 'gpu-check',
                    '--gateway-url', 'http://localhost:8088',
                ],
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                universal_newlines=True
            )
            
            self.processes.append(proc)
            
            # Capture output for 15 seconds
            start_time = time.time()
            output_lines = []
            job_count = 0
            
            while time.time() - start_time < 15:
                try:
                    line = proc.stdout.readline()
                    if line:
                        print(line.rstrip())
                        output_lines.append(line.rstrip())
                        if "✅" in line or "❌" in line:
                            job_count += 1
                except:
                    break
                    
            # Terminate the process
            proc.terminate()
            proc.wait()
            self.processes.remove(proc)
            
            # Calculate actual job rate
            actual_rate = (job_count / 15) * 60
            
            print(f"\n{GREEN}Summary for {agent_id}:{RESET}")
            print(f"  Jobs sent in 15 seconds: {job_count}")
            print(f"  Actual job rate: {actual_rate:.1f} jobs/min")
            print(f"  Expected rate based on uptime: {self.get_expected_rate(agent_id)}")
            
        print(f"\n{GREEN}All tests completed!{RESET}")
        
    def get_expected_rate(self, agent_id):
        """Get expected job rate based on agent uptime"""
        expected_rates = {
            "agent-001": "60 jobs/min (100% of base rate)",
            "agent-002": "30 jobs/min (50% of base rate)",
            "agent-003": "6 jobs/min (10% of base rate)",
            "agent-004": "0 jobs/min (full punishment)"
        }
        return expected_rates.get(agent_id, "Unknown")
        
        
    async def run_demo(self):
        """Run the complete demonstration"""
        print(f"{BLUE}=== UPTIME-AWARE CAPABILITY TESTER DEMONSTRATION ==={RESET}")
        print(f"\nThis demo shows how the client-side punishment logic works:")
        print(f"- Agents with 99%+ uptime get full job rate (60 jobs/min)")
        print(f"- Agents with 95-99% uptime get 50% job rate (30 jobs/min)")
        print(f"- Agents with 90-95% uptime get 10% job rate (6 jobs/min)")
        print(f"- Agents with <90% uptime get no jobs (0 jobs/min)")
        print()
        
        # Set up signal handler
        signal.signal(signal.SIGINT, self.cleanup)
        signal.signal(signal.SIGTERM, self.cleanup)
        
        try:
            # Verify services are running
            if not await self.verify_services_running():
                print(f"\n{RED}Please start the services with:{RESET}")
                print(f"  cd /home/geo/docker-vt/agent-net")
                print(f"  docker-compose up -d")
                return
            
            # Run tests
            await self.run_uptime_aware_tests()
            
        finally:
            self.cleanup()

async def main():
    """Main entry point"""
    runner = DemoRunner()
    await runner.run_demo()

if __name__ == "__main__":
    asyncio.run(main())