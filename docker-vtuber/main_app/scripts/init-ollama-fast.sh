#!/bin/bash

echo "🚀 [OLLAMA_FAST_INIT] Starting Fast Ollama model initialization..."

# Start Ollama server in background
echo "🔄 [OLLAMA_FAST_INIT] Starting Ollama server..."
ollama serve &

# Wait a bit for startup
sleep 5

# Test if Ollama is responding
echo "✅ [OLLAMA_FAST_INIT] Testing Ollama availability..."
while ! ollama list >/dev/null 2>&1; do
    echo "⏳ [OLLAMA_FAST_INIT] Ollama not ready yet, waiting..."
    sleep 3
done

echo "✅ [OLLAMA_FAST_INIT] Ollama service is ready"

# Try to pull smallest working models first (in order of preference)
echo "📥 [OLLAMA_FAST_INIT] Pulling small, fast models..."

# Option 1: Try very small embedding model (usually <100MB)
echo "📥 [OLLAMA_FAST_INIT] Attempting nomic-embed-text (small embedding model)..."
if timeout 60 ollama pull nomic-embed-text:latest; then
    echo "✅ [OLLAMA_FAST_INIT] Embedding model pulled successfully"
else
    echo "⚠️ [OLLAMA_FAST_INIT] Embedding model failed or timed out"
fi

# Option 2: Try very small LLM models (phi3, gemma2, etc.)
echo "📥 [OLLAMA_FAST_INIT] Attempting small LLM models..."

SMALL_MODELS=("phi3:mini" "gemma2:2b" "tinyllama" "qwen2:0.5b")

for model in "${SMALL_MODELS[@]}"; do
    echo "📥 [OLLAMA_FAST_INIT] Trying $model..."
    if timeout 120 ollama pull "$model"; then
        echo "✅ [OLLAMA_FAST_INIT] Successfully pulled $model"
        LLM_MODEL="$model"
        break
    else
        echo "⚠️ [OLLAMA_FAST_INIT] $model failed or timed out, trying next..."
    fi
done

# Fallback: If no models work, use the existing ones or create minimal setup
if [ -z "$LLM_MODEL" ]; then
    echo "⚠️ [OLLAMA_FAST_INIT] No new models downloaded, checking existing..."
    EXISTING_MODELS=$(ollama list | grep -v "NAME" | awk '{print $1}' | head -1)
    if [ ! -z "$EXISTING_MODELS" ]; then
        LLM_MODEL="$EXISTING_MODELS"
        echo "✅ [OLLAMA_FAST_INIT] Using existing model: $LLM_MODEL"
    else
        echo "❌ [OLLAMA_FAST_INIT] No models available, will use basic configuration"
        LLM_MODEL="llama3.2:3b"  # Keep existing config
    fi
fi

# Show final status
echo "📋 [OLLAMA_FAST_INIT] Final model configuration:"
echo "   LLM Model: $LLM_MODEL"

# List all available models
echo "📋 [OLLAMA_FAST_INIT] Available models:"
ollama list

echo "🎉 [OLLAMA_FAST_INIT] Fast initialization complete!"

# Keep server running
wait 