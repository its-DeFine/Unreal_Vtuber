#!/bin/bash

echo "🚀 [OLLAMA_INIT] Starting Ollama model initialization..."

# Start Ollama server in background
echo "🔄 [OLLAMA_INIT] Starting Ollama server..."
ollama serve &

# Wait for Ollama service to be ready (simpler approach)
echo "⏳ [OLLAMA_INIT] Waiting for Ollama service to start..."
sleep 10

# Test if Ollama is responding with a simple command
echo "✅ [OLLAMA_INIT] Testing Ollama availability..."
while ! ollama list >/dev/null 2>&1; do
    echo "⏳ [OLLAMA_INIT] Ollama not ready yet, waiting..."
    sleep 5
done

echo "✅ [OLLAMA_INIT] Ollama service is ready"

# Pull embedding model first (smaller, more reliable)
echo "📥 [OLLAMA_INIT] Pulling embedding model: nomic-embed-text:latest..."
ollama pull nomic-embed-text:latest
if [ $? -eq 0 ]; then
    echo "✅ [OLLAMA_INIT] Embedding model pulled successfully"
else
    echo "❌ [OLLAMA_INIT] Failed to pull embedding model"
fi

# Pull a reliable LLM model (try multiple options)
echo "📥 [OLLAMA_INIT] Pulling LLM model..."

# Try llama3.1:8b first (good balance of capability and size)
echo "📥 [OLLAMA_INIT] Attempting to pull llama3.1:8b..."
timeout 300 ollama pull llama3.1:8b
if [ $? -eq 0 ]; then
    echo "✅ [OLLAMA_INIT] llama3.1:8b pulled successfully"
    echo "LLM_MODEL=llama3.1:8b" > /tmp/ollama_model.env
else
    echo "⚠️ [OLLAMA_INIT] llama3.1:8b failed, trying llama3:8b..."
    
    # Fallback to llama3:8b
    timeout 300 ollama pull llama3:8b
    if [ $? -eq 0 ]; then
        echo "✅ [OLLAMA_INIT] llama3:8b pulled successfully"
        echo "LLM_MODEL=llama3:8b" > /tmp/ollama_model.env
    else
        echo "⚠️ [OLLAMA_INIT] llama3:8b failed, trying smaller but more reliable model..."
        
        # Final fallback to a more reliable smaller model
        timeout 180 ollama pull llama3:latest
        if [ $? -eq 0 ]; then
            echo "✅ [OLLAMA_INIT] llama3:latest pulled successfully"
            echo "LLM_MODEL=llama3:latest" > /tmp/ollama_model.env
        else
            echo "❌ [OLLAMA_INIT] All model pulls failed, keeping llama3.2:3b"
            echo "LLM_MODEL=llama3.2:3b" > /tmp/ollama_model.env
        fi
    fi
fi

# List available models
echo "📋 [OLLAMA_INIT] Available models:"
ollama list

echo "🎉 [OLLAMA_INIT] Initialization complete!"

# Keep the process running (wait for the background ollama serve process)
echo "🔄 [OLLAMA_INIT] Keeping Ollama server running..."
wait 