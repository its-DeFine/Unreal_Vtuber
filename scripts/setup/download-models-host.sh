#!/bin/bash

echo "🚀 [HOST_DOWNLOAD] Downloading Ollama models to host machine..."

# Create local ollama data directory
OLLAMA_DATA_DIR="./ollama_models"
mkdir -p "$OLLAMA_DATA_DIR"

echo "📁 [HOST_DOWNLOAD] Using directory: $OLLAMA_DATA_DIR"

# Start temporary Ollama container to download models
echo "🔄 [HOST_DOWNLOAD] Starting temporary Ollama container..."

docker run -d \
    --name temp_ollama_download \
    -v "$PWD/$OLLAMA_DATA_DIR:/root/.ollama" \
    -p 11434:11434 \
    ollama/ollama:latest

# Wait for container to be ready
echo "⏳ [HOST_DOWNLOAD] Waiting for Ollama to start..."
sleep 10

# Download models
echo "📥 [HOST_DOWNLOAD] Downloading models..."

# Small, fast models first
docker exec temp_ollama_download ollama pull nomic-embed-text:latest
docker exec temp_ollama_download ollama pull qwen2:0.5b
docker exec temp_ollama_download ollama pull gemma2:2b
docker exec temp_ollama_download ollama pull phi3:mini

# Optional larger model (uncomment if you want it)
# docker exec temp_ollama_download ollama pull llama3.1:8b

# List downloaded models
echo "📋 [HOST_DOWNLOAD] Downloaded models:"
docker exec temp_ollama_download ollama list

# Cleanup
echo "🧹 [HOST_DOWNLOAD] Cleaning up temporary container..."
docker stop temp_ollama_download
docker rm temp_ollama_download

echo "✅ [HOST_DOWNLOAD] Models downloaded to $OLLAMA_DATA_DIR"
echo "💡 [HOST_DOWNLOAD] Update docker-compose.yml to use: $PWD/$OLLAMA_DATA_DIR:/root/.ollama" 