#!/usr/bin/env python3
"""Voice-to-Change-Subject helper

Records a short clip from the default microphone, transcribes it with
OpenAI Whisper, then sends it to the NeuroSync orchestrator as a
`change_subject` event (topic = transcribed text).

Requirements:
  • python -m pip install sounddevice soundfile openai requests
  • Set OPENAI_API_KEY in environment (or via --api-key)

Usage (default 5-second capture):
    python voice_change_subject.py            # 5-second recording
    python voice_change_subject.py -d 8       # 8-second recording
    python voice_change_subject.py -e http://localhost:5001

During capture press Ctrl-C to abort.
"""

import argparse
import os
import queue
import sys
import tempfile
import time
from pathlib import Path

import requests  # type: ignore
import sounddevice as sd  # type: ignore
import soundfile as sf  # type: ignore
import openai  # type: ignore

# Optional .env support
try:
    from dotenv import load_dotenv  # type: ignore
except ImportError:
    load_dotenv = None

# ---------------------------------------------------------------------------
# Audio helpers
# ---------------------------------------------------------------------------

def record_audio(duration: float, samplerate: int = 16000, channels: int = 1) -> Path:
    """Record audio from default input and return path to temp WAV file."""
    q = queue.Queue()

    def _callback(indata, frames, time_info, status):  # noqa: D401
        if status:
            print(status, file=sys.stderr)
        q.put(indata.copy())

    temp_path = Path(tempfile.mkstemp(suffix=".wav")[1])
    with sd.InputStream(samplerate=samplerate, channels=channels, callback=_callback):
        print(f"🎙️  Recording {duration} s …")
        collected = []
        start = time.time()
        while time.time() - start < duration:
            collected.append(q.get())
        data = b"".join(collected)

    # Write to WAV
    sf.write(temp_path, b"".join(collected), samplerate)
    print(f"✅ Audio saved to {temp_path}")
    return temp_path


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(description="Speak a topic and send change_subject event")
    parser.add_argument("-d", "--duration", type=float, default=5.0, help="Recording duration in seconds (default 5)")
    parser.add_argument("-e", "--endpoint", default="http://localhost:5001", help="Orchestrator base URL")
    parser.add_argument("--api-key", help="OpenAI API key (overrides env)")
    parser.add_argument("--env-file", help="Path to .env file containing OPENAI_API_KEY")
    parser.add_argument("--model", default="whisper-1", help="OpenAI Whisper model")
    args = parser.parse_args()

    # Load .env if requested or if dotenv is available and env file exists
    if args.env_file and load_dotenv:
        load_dotenv(args.env_file)
    elif load_dotenv and Path('.env').exists():
        load_dotenv('.env')

    api_key = args.api_key or os.getenv("OPENAI_API_KEY")
    if not api_key:
        print("❌ OPENAI_API_KEY not set (env or --api-key)")
        sys.exit(1)
    openai.api_key = api_key

    wav_path = record_audio(args.duration)

    try:
        print("🧠 Transcribing with OpenAI Whisper …")
        with open(wav_path, "rb") as audio_file:
            transcription = openai.Audio.transcribe(args.model, audio_file)
            text = transcription.get("text", "").strip()
    except Exception as e:
        print(f"❌ Transcription failed: {e}")
        sys.exit(1)

    if not text:
        print("⚠️  No text detected; aborting")
        sys.exit(1)

    print(f"✅ Transcribed text: '{text}'")

    # Send to orchestrator
    payload = {
        "event_type": "change_subject",
        "payload": {"topic": text}
    }
    try:
        url = f"{args.endpoint.rstrip('/')}/orchestrator/event"
        resp = requests.post(url, json=payload, timeout=5)
        resp.raise_for_status()
        print(f"🚀 Event sent. Orchestrator response: {resp.json()}")
    except Exception as e:
        print(f"❌ Failed to send event: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main() 