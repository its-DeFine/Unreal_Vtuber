#!/bin/bash

# setup_ollama.sh - Setup script for Ollama local LLM support in VTuber system
# This script sets up Ollama with lightweight models optimized for VTuber interactions

set -e

echo "🤖 Setting up Ollama for VTuber Local LLM Support"
echo "=================================================="

# Check if Docker is available
if ! command -v docker &> /dev/null; then
    echo "❌ Docker is required but not installed. Please install Docker first."
    exit 1
fi

# Check if Docker Compose is available
if ! command -v docker-compose &> /dev/null; then
    echo "❌ Docker Compose is required but not installed. Please install Docker Compose first."
    exit 1
fi

# Function to check if Ollama is responding
check_ollama() {
    local retries=30
    while [ $retries -gt 0 ]; do
        if curl -s http://localhost:11434/api/tags >/dev/null 2>&1; then
            echo "✅ Ollama is responding"
            return 0
        fi
        echo "⏳ Waiting for Ollama to start... ($retries attempts remaining)"
        sleep 2
        ((retries--))
    done
    echo "❌ Ollama failed to start within timeout"
    return 1
}

# Create Ollama directory if it doesn't exist
mkdir -p ./ollama_data

# Create Docker Compose file for Ollama
cat > docker-compose.ollama.yml << 'EOF'
version: '3.8'

services:
  ollama:
    image: ollama/ollama:latest
    container_name: vtuber-ollama
    ports:
      - "11434:11434"
    volumes:
      - ./ollama_data:/root/.ollama
    environment:
      - OLLAMA_ORIGINS=*
    restart: unless-stopped
    networks:
      - vtuber-network
    deploy:
      resources:
        reservations:
          devices:
            - driver: nvidia
              count: all
              capabilities: [gpu]
    # Fallback for systems without GPU
    profiles:
      - gpu

  ollama-cpu:
    image: ollama/ollama:latest
    container_name: vtuber-ollama-cpu
    ports:
      - "11434:11434"
    volumes:
      - ./ollama_data:/root/.ollama
    environment:
      - OLLAMA_ORIGINS=*
    restart: unless-stopped
    networks:
      - vtuber-network
    profiles:
      - cpu

networks:
  vtuber-network:
    external: true
    name: docker-vt_default

EOF

echo "📝 Created Docker Compose configuration for Ollama"

# Check for GPU support
if docker run --rm --gpus all nvidia/cuda:11.0.3-base-ubuntu20.04 nvidia-smi >/dev/null 2>&1; then
    echo "🎮 GPU detected - using GPU-accelerated Ollama"
    GPU_SUPPORT=true
    PROFILE="gpu"
else
    echo "💻 No GPU detected - using CPU-only Ollama"
    GPU_SUPPORT=false
    PROFILE="cpu"
fi

# Start Ollama container
echo "🚀 Starting Ollama container..."
if [ "$GPU_SUPPORT" = true ]; then
    docker-compose -f docker-compose.ollama.yml --profile gpu up -d ollama
else
    docker-compose -f docker-compose.ollama.yml --profile cpu up -d ollama-cpu
fi

# Wait for Ollama to be ready
echo "⏳ Waiting for Ollama to start..."
if ! check_ollama; then
    echo "❌ Failed to start Ollama. Check the logs:"
    docker-compose -f docker-compose.ollama.yml logs
    exit 1
fi

echo "📦 Installing recommended lightweight models for VTuber..."

# Array of models to install (optimized for VTuber interactions)
declare -a models=(
    "llama3.2:3b"      # Fast, efficient 3B parameter model
    "phi3:mini"        # Microsoft's compact model
    "qwen2:1.5b"       # Very lightweight for quick responses
    "gemma2:2b"        # Google's efficient model
)

# Install models
for model in "${models[@]}"; do
    echo "📥 Installing $model..."
    if docker exec vtuber-ollama-${PROFILE/gpu/} ollama pull "$model"; then
        echo "✅ Successfully installed $model"
    else
        echo "⚠️ Failed to install $model (continuing with other models)"
    fi
done

# Test model functionality
echo "🧪 Testing model functionality..."
TEST_RESPONSE=$(docker exec vtuber-ollama-${PROFILE/gpu/} ollama run llama3.2:3b "Say hello in a friendly way" 2>/dev/null || echo "")

if [ -n "$TEST_RESPONSE" ]; then
    echo "✅ Model test successful!"
    echo "🤖 Test response: $TEST_RESPONSE"
else
    echo "⚠️ Model test failed, but Ollama is running"
fi

# Create or update .env configuration
ENV_FILE=".env"
echo "📝 Updating environment configuration..."

# Backup existing .env if it exists
if [ -f "$ENV_FILE" ]; then
    cp "$ENV_FILE" "${ENV_FILE}.backup.$(date +%Y%m%d_%H%M%S)"
    echo "📋 Backed up existing .env file"
fi

# Update .env with Ollama settings
if [ ! -f "$ENV_FILE" ]; then
    echo "# VTuber Local LLM Configuration with Ollama" > "$ENV_FILE"
fi

# Remove old LLM settings and add new ones
grep -v "^LLM_PROVIDER\|^OLLAMA_\|^USE_LOCAL_LLM\|^USE_STREAMING" "$ENV_FILE" > "${ENV_FILE}.tmp" 2>/dev/null || true
cat >> "${ENV_FILE}.tmp" << EOF

# ======================================
# Local LLM Configuration with Ollama
# ======================================
LLM_PROVIDER=ollama
OLLAMA_API_ENDPOINT=http://localhost:11434
OLLAMA_MODEL=llama3.2:3b
OLLAMA_STREAMING=true
USE_STREAMING=true

# Backup models (comment/uncomment as needed)
# OLLAMA_MODEL=phi3:mini
# OLLAMA_MODEL=qwen2:1.5b
# OLLAMA_MODEL=gemma2:2b

EOF

mv "${ENV_FILE}.tmp" "$ENV_FILE"

echo "✅ Environment configuration updated!"

# Display summary
echo ""
echo "🎉 Ollama Setup Complete!"
echo "========================="
echo "🔧 Provider: Ollama"
echo "🌐 Endpoint: http://localhost:11434"
echo "🤖 Default Model: llama3.2:3b"
echo "⚡ Streaming: Enabled"
echo ""
echo "📋 Installed Models:"
for model in "${models[@]}"; do
    echo "   - $model"
done
echo ""
echo "🚀 Usage Instructions:"
echo "1. Your VTuber system is now configured to use local LLMs"
echo "2. Start your VTuber system normally - it will use Ollama automatically"
echo "3. To change models, update OLLAMA_MODEL in .env file"
echo "4. To stop Ollama: docker-compose -f docker-compose.ollama.yml down"
echo "5. To view Ollama logs: docker-compose -f docker-compose.ollama.yml logs"
echo ""
echo "💡 Tips:"
echo "   - llama3.2:3b is fastest for real-time VTuber interactions"
echo "   - phi3:mini uses less memory but may be slower"
echo "   - All models run locally for privacy and cost savings"
echo ""
echo "🔍 Test your setup by running your VTuber system!"

# Create a simple test script
cat > test_ollama.py << 'EOF'
#!/usr/bin/env python3
"""Simple test script for Ollama VTuber integration"""

import requests
import json
import sys

def test_ollama():
    try:
        # Test connection
        response = requests.get("http://localhost:11434/api/tags", timeout=5)
        if not response.ok:
            print(f"❌ Ollama connection failed: HTTP {response.status_code}")
            return False
        
        models = response.json().get('models', [])
        print(f"✅ Connected to Ollama. Available models: {len(models)}")
        
        if not models:
            print("⚠️ No models installed")
            return False
        
        # Test chat
        model_name = "llama3.2:3b"
        chat_data = {
            "model": model_name,
            "messages": [
                {"role": "system", "content": "You are a friendly VTuber AI assistant."},
                {"role": "user", "content": "Say hello!"}
            ],
            "stream": False
        }
        
        print(f"🧪 Testing chat with {model_name}...")
        response = requests.post("http://localhost:11434/api/chat", json=chat_data, timeout=30)
        
        if response.ok:
            result = response.json()
            message = result.get('message', {}).get('content', 'No response')
            print(f"✅ Chat test successful!")
            print(f"🤖 Response: {message[:100]}{'...' if len(message) > 100 else ''}")
            return True
        else:
            print(f"❌ Chat test failed: HTTP {response.status_code}")
            return False
            
    except Exception as e:
        print(f"❌ Test failed: {e}")
        return False

if __name__ == "__main__":
    print("🧪 Testing Ollama VTuber Integration")
    print("===================================")
    success = test_ollama()
    sys.exit(0 if success else 1)
EOF

chmod +x test_ollama.py
echo "🧪 Created test script: ./test_ollama.py"
echo "   Run './test_ollama.py' to test your Ollama setup" 