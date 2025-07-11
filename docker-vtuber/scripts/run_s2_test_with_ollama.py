#!/usr/bin/env python3
"""
Run S2 Tests with Ollama Configuration
======================================

This script configures Ollama and runs the comprehensive S2 tests.
"""

import os
import subprocess
import sys

# Set Ollama configuration
os.environ["USE_OLLAMA"] = "true"
os.environ["OLLAMA_HOST"] = "http://localhost:11434"
os.environ["OLLAMA_MODEL"] = "llama3.1:8b"  # Using the available model
os.environ["USE_TEACHABLE_AGENTS"] = "false"  # Start with standard agents

# Also set for any other components that might need it
os.environ["AUTOGEN_USE_OLLAMA"] = "true"

print("🦙 Ollama Configuration:")
print(f"  USE_OLLAMA: {os.environ['USE_OLLAMA']}")
print(f"  OLLAMA_HOST: {os.environ['OLLAMA_HOST']}")
print(f"  OLLAMA_MODEL: {os.environ['OLLAMA_MODEL']}")
print(f"  USE_TEACHABLE_AGENTS: {os.environ['USE_TEACHABLE_AGENTS']}")
print()

# Run the comprehensive test
script_path = os.path.join(os.path.dirname(__file__), "comprehensive_s2_test.py")
print(f"🚀 Running comprehensive S2 test with Ollama enabled...")
print("="*80)

# Run the test script
result = subprocess.run([sys.executable, script_path], capture_output=False)

sys.exit(result.returncode)