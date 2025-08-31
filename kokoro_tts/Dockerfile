FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Install Python dependencies
RUN pip install --no-cache-dir \
    fastapi \
    uvicorn \
    numpy

# Create FastAPI wrapper
RUN cat > /app/server.py << 'EOF'
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import numpy as np
import io
import base64

app = FastAPI()

# Initialize model (placeholder - needs actual Kokoro model code)
model = None

class TTSRequest(BaseModel):
    text: str
    speaker_id: int = 0

@app.get("/health")
def health_check():
    return {"status": "healthy"}

@app.post("/tts")
async def text_to_speech(request: TTSRequest):
    try:
        # Placeholder for actual TTS processing
        # In real implementation, load and use Kokoro model
        return {
            "audio": "base64_encoded_audio_here",
            "sample_rate": 24000
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8880)
EOF

EXPOSE 8880

CMD ["python", "/app/server.py"]