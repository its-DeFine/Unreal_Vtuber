#!/usr/bin/env python3
"""
Test script for Ollama GPU monitoring

This script checks if Ollama is up and running by:
- Testing connection to Ollama API
- Checking running models and their VRAM usage
- Listing available models
"""

import requests
import json
import time
import sys

def test_ollama_status(ollama_url="http://localhost:11434"):
    """Test if Ollama is up and get GPU/VRAM info"""
    
    print("🔍 Testing Ollama Status\n")
    
    # Test Ollama endpoints directly
    print("1. Testing Ollama container...")
    try:
        # Check running models
        response = requests.get(f"{ollama_url}/api/ps", timeout=5)
        if response.status_code == 200:
            data = response.json()
            print("✅ Ollama /api/ps endpoint successful")
            models = data.get("models", [])
            if models:
                print(f"   Running models: {len(models)}")
                total_vram = 0
                for model in models:
                    name = model.get('name', 'unknown')
                    size_bytes = model.get('size', 0)
                    size_vram = model.get('size_vram', 0)
                    total_vram += size_vram
                    print(f"     - {name}:")
                    print(f"       Total Size: {size_bytes / (1024**3):.2f} GB")
                    print(f"       VRAM Usage: {size_vram / (1024**2):.0f} MB ({size_vram / (1024**3):.2f} GB)")
                    
                    # Show model details if available
                    details = model.get('details', {})
                    if details:
                        print(f"       Parameter Size: {details.get('parameter_size', 'N/A')}")
                        print(f"       Quantization: {details.get('quantization_level', 'N/A')}")
                        print(f"       Format: {details.get('format', 'N/A')}")
                
                print(f"\n   📊 Total VRAM in use: {total_vram / (1024**2):.0f} MB ({total_vram / (1024**3):.2f} GB)")
            else:
                print("   No models currently loaded")
                print("   💡 Tip: Load a model with: curl -X POST localhost:11434/api/generate -d '{\"model\": \"tinyllama\", \"prompt\": \"test\", \"keep_alive\": \"5m\"}'")
        
        # Check available models
        response = requests.get(f"{ollama_url}/api/tags", timeout=5)
        if response.status_code == 200:
            data = response.json()
            models = data.get("models", [])
            print(f"\n   Available models: {len(models)}")
            for model in models[:5]:  # Show first 5
                print(f"     - {model.get('name', 'unknown')}: {model.get('size', 0) / (1024**3):.1f} GB")
            if len(models) > 5:
                print(f"     ... and {len(models) - 5} more")
                
    except Exception as e:
        print(f"⚠️  Could not reach Ollama directly: {e}")
        print("   Make sure Ollama container is running on port 11434")
    
    print("\n✨ Ollama Status Check Complete!")

def load_model(ollama_url="http://localhost:11434", model_name="tinyllama"):
    """Load a model into memory to test VRAM usage"""
    print(f"\n🔄 Loading {model_name} model...")
    try:
        response = requests.post(
            f"{ollama_url}/api/generate",
            json={
                "model": model_name,
                "prompt": "Hello",
                "keep_alive": "5m"
            },
            timeout=30
        )
        if response.status_code == 200:
            print(f"✅ Model {model_name} loaded successfully")
            return True
        else:
            print(f"❌ Failed to load model: {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ Error loading model: {e}")
        return False

if __name__ == "__main__":
    # Parse command line arguments
    ollama_url = "http://localhost:11434"
    load_model_flag = False
    
    for i, arg in enumerate(sys.argv[1:]):
        if arg == "--load-model":
            load_model_flag = True
        elif not arg.startswith("--"):
            ollama_url = arg
    
    print(f"🚀 Checking Ollama status on {ollama_url}")
    print("=" * 50)
    
    # Load model if requested
    if load_model_flag:
        if load_model(ollama_url):
            time.sleep(2)  # Give model time to fully load
    
    test_ollama_status(ollama_url)
    
    # Show usage hints
    if not load_model_flag:
        print("\n💡 Tip: Use --load-model flag to automatically load tinyllama and see VRAM usage")
        print("   Example: python3 test_gpu_monitoring.py --load-model")