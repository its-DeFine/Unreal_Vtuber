#!/usr/bin/env python3
"""Test script for unified VTuber system with GraphFlow stimuli"""

import requests
import json
import time
from datetime import datetime

# Configuration
GRAPHFLOW_URL = "http://localhost:8081"
PROMETHEUS_URL = "http://localhost:9090"
GRAFANA_URL = "http://localhost:3002"
API_KEY = "test-key-12345"

# Color codes for output
GREEN = '\033[92m'
YELLOW = '\033[93m'
RED = '\033[91m'
BLUE = '\033[94m'
RESET = '\033[0m'

def print_status(message, status="INFO"):
    timestamp = datetime.now().strftime("%H:%M:%S")
    if status == "SUCCESS":
        print(f"{GREEN}[{timestamp}] ✓ {message}{RESET}")
    elif status == "ERROR":
        print(f"{RED}[{timestamp}] ✗ {message}{RESET}")
    elif status == "WARNING":
        print(f"{YELLOW}[{timestamp}] ⚠ {message}{RESET}")
    else:
        print(f"{BLUE}[{timestamp}] → {message}{RESET}")

def test_graphflow_health():
    """Test GraphFlow health endpoint"""
    print_status("Testing GraphFlow health...")
    try:
        response = requests.get(f"{GRAPHFLOW_URL}/api/v1/health")
        if response.status_code == 200:
            print_status("GraphFlow is healthy", "SUCCESS")
            return True
        else:
            print_status(f"GraphFlow health check failed: {response.status_code}", "ERROR")
            return False
    except Exception as e:
        print_status(f"Failed to connect to GraphFlow: {e}", "ERROR")
        return False

def submit_stimulus(content, source="test_script", priority="medium", metadata=None):
    """Submit a stimulus to GraphFlow"""
    headers = {
        "Authorization": f"Bearer {API_KEY}",
        "Content-Type": "application/json"
    }
    
    payload = {
        "content": content,
        "source": source,
        "priority": priority,
        "metadata": metadata or {}
    }
    
    print_status(f"Submitting stimulus: '{content[:50]}...'")
    
    try:
        response = requests.post(
            f"{GRAPHFLOW_URL}/api/v1/stimuli/submit",
            headers=headers,
            json=payload
        )
        
        if response.status_code == 200:
            result = response.json()
            print_status(f"Stimulus submitted successfully - ID: {result.get('id')}", "SUCCESS")
            return result
        else:
            print_status(f"Failed to submit stimulus: {response.status_code} - {response.text}", "ERROR")
            return None
    except Exception as e:
        print_status(f"Error submitting stimulus: {e}", "ERROR")
        return None

def check_prometheus_metrics():
    """Check if Prometheus is collecting metrics"""
    print_status("Checking Prometheus metrics...")
    try:
        response = requests.get(f"{PROMETHEUS_URL}/api/v1/targets")
        data = response.json()
        
        active_targets = data['data']['activeTargets']
        up_count = sum(1 for target in active_targets if target['health'] == 'up')
        total_count = len(active_targets)
        
        print_status(f"Prometheus targets: {up_count}/{total_count} up", 
                    "SUCCESS" if up_count > 0 else "WARNING")
        
        # Check specific targets
        for target in active_targets:
            job = target['labels']['job']
            health = target['health']
            status = "SUCCESS" if health == "up" else "WARNING"
            print_status(f"  - {job}: {health}", status)
            
        return up_count > 0
    except Exception as e:
        print_status(f"Failed to check Prometheus: {e}", "ERROR")
        return False

def check_grafana_dashboards():
    """Check if Grafana dashboards are available"""
    print_status("Checking Grafana dashboards...")
    try:
        response = requests.get(
            f"{GRAFANA_URL}/api/search?type=dash-db",
            auth=('admin', 'admin')
        )
        
        if response.status_code == 200:
            dashboards = response.json()
            print_status(f"Found {len(dashboards)} dashboards:", "SUCCESS")
            for dash in dashboards:
                print_status(f"  - {dash['title']} ({dash['uid']})")
            return True
        else:
            print_status(f"Failed to get dashboards: {response.status_code}", "ERROR")
            return False
    except Exception as e:
        print_status(f"Failed to connect to Grafana: {e}", "ERROR")
        return False

def run_stimuli_tests():
    """Run a series of test stimuli"""
    test_stimuli = [
        {
            "content": "Hello VTuber! This is a test message from the unified system.",
            "priority": "high",
            "metadata": {"test_id": "001", "type": "greeting"}
        },
        {
            "content": "What's the weather like today?",
            "priority": "medium",
            "metadata": {"test_id": "002", "type": "question"}
        },
        {
            "content": "Play some relaxing music",
            "priority": "low",
            "metadata": {"test_id": "003", "type": "command"}
        },
        {
            "content": "Tell me a joke about programming",
            "priority": "medium",
            "metadata": {"test_id": "004", "type": "entertainment"}
        },
        {
            "content": "System check: How are all services running?",
            "priority": "high",
            "metadata": {"test_id": "005", "type": "system_check"}
        }
    ]
    
    print_status("=== Running Stimuli Tests ===")
    results = []
    
    for i, stimulus in enumerate(test_stimuli, 1):
        print_status(f"\nTest {i}/{len(test_stimuli)}")
        result = submit_stimulus(
            stimulus["content"],
            priority=stimulus["priority"],
            metadata=stimulus["metadata"]
        )
        results.append(result)
        
        # Wait between submissions
        if i < len(test_stimuli):
            time.sleep(2)
    
    # Summary
    successful = sum(1 for r in results if r is not None)
    print_status(f"\n=== Test Summary: {successful}/{len(test_stimuli)} successful ===", 
                "SUCCESS" if successful == len(test_stimuli) else "WARNING")
    
    return results

def main():
    """Main test function"""
    print_status("=== VTuber Unified System Test ===")
    print_status(f"GraphFlow URL: {GRAPHFLOW_URL}")
    print_status(f"Prometheus URL: {PROMETHEUS_URL}")
    print_status(f"Grafana URL: {GRAFANA_URL}")
    print()
    
    # Run health checks
    graphflow_ok = test_graphflow_health()
    prometheus_ok = check_prometheus_metrics()
    grafana_ok = check_grafana_dashboards()
    
    print()
    
    if not graphflow_ok:
        print_status("GraphFlow is not available. Aborting tests.", "ERROR")
        return
    
    # Run stimuli tests
    results = run_stimuli_tests()
    
    print()
    print_status("=== Test Complete ===")
    print_status(f"GraphFlow: {'✓' if graphflow_ok else '✗'}")
    print_status(f"Prometheus: {'✓' if prometheus_ok else '✗'}")
    print_status(f"Grafana: {'✓' if grafana_ok else '✗'}")
    
    print()
    print_status("View live metrics at:")
    print_status(f"  - Grafana: {GRAFANA_URL} (admin/admin)")
    print_status(f"  - Prometheus: {PROMETHEUS_URL}")
    print_status(f"  - GraphFlow API: {GRAPHFLOW_URL}/api/docs")

if __name__ == "__main__":
    main()