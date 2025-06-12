# This software is licensed under a **dual-license model**
# For individuals and businesses earning **under $1M per year**, this software is licensed under the **MIT License**
# Businesses or organizations with **annual revenue of $1,000,000 or more** must obtain permission to use this software commercially.

from utils.neurosync.multi_part_return import get_tts_with_blendshapes
from utils.neurosync.neurosync_api_connect import send_audio_to_neurosync
from utils.tts.local_tts import call_local_tts 
from utils.tts.eleven_labs import get_elevenlabs_audio
from utils.tts.kokoro_tts import get_kokoro_audio
from config import get_tts_config
import string

def tts_worker(chunk_queue, audio_queue, USE_LOCAL_AUDIO=None, VOICE_NAME=None, USE_COMBINED_ENDPOINT=False):
    """
    Processes text chunks from chunk_queue.
    
    When USE_COMBINED_ENDPOINT is True, a single API call retrieves both audio and blendshapes.
    Otherwise, the worker generates audio using the configured TTS provider (local, elevenlabs, or kokoro)
    and then retrieves facial data separately.
    
    The results (audio_bytes, facial/blendshape data) are enqueued into audio_queue.
    
    Parameters:
      - chunk_queue: Queue holding text chunks.
      - audio_queue: Queue where the (audio_bytes, facial_data) tuple is enqueued.
      - USE_LOCAL_AUDIO (bool, optional): Legacy parameter for backward compatibility. 
        If provided, overrides TTS_PROVIDER config (True=local, False=elevenlabs).
      - VOICE_NAME (str): Voice name to use for TTS providers that support it.
      - USE_COMBINED_ENDPOINT (bool): If True, use the combined TTS+blendshapes endpoint.
    """
    # Get TTS configuration
    tts_config = get_tts_config()
    
    # Handle backward compatibility with USE_LOCAL_AUDIO parameter
    if USE_LOCAL_AUDIO is not None:
        if USE_LOCAL_AUDIO:
            tts_provider = "local"
            print("⚠️ Using legacy USE_LOCAL_AUDIO=True, defaulting to 'local' provider")
        else:
            tts_provider = "elevenlabs"
            print("⚠️ Using legacy USE_LOCAL_AUDIO=False, defaulting to 'elevenlabs' provider")
    else:
        tts_provider = tts_config["TTS_PROVIDER"]
    
    print(f"🎙️ TTS Worker started with provider: {tts_provider}")
    if VOICE_NAME:
        print(f"🎭 Voice: {VOICE_NAME}")
    
    while True:
        chunk = chunk_queue.get()
        if chunk is None:
            break

        # Skip if the chunk is empty or only punctuation/whitespace.
        if not chunk.strip() or all(c in string.punctuation or c.isspace() for c in chunk):
            chunk_queue.task_done()
            continue

        if USE_COMBINED_ENDPOINT:
            # Use the combined endpoint: one call returns both audio and blendshapes.
            audio_bytes, blendshapes = get_tts_with_blendshapes(chunk, VOICE_NAME)
            if audio_bytes and blendshapes:
                audio_queue.put((audio_bytes, blendshapes))
            else:
                print("❌ Failed to retrieve audio and blendshapes for chunk:", chunk)
        else:
            # Generate audio using the configured TTS provider.
            audio_bytes = None
            
            if tts_provider == "local":
                print(f"🎵 Generating audio with Local TTS for: '{chunk[:50]}...'")
                audio_bytes = call_local_tts(chunk)
            elif tts_provider == "elevenlabs":
                print(f"🎵 Generating audio with ElevenLabs TTS for: '{chunk[:50]}...'")
                audio_bytes = get_elevenlabs_audio(chunk, VOICE_NAME)
            elif tts_provider == "kokoro":
                print(f"🎵 Generating audio with Kokoro TTS for: '{chunk[:50]}...'")
                audio_bytes = get_kokoro_audio(chunk, VOICE_NAME)
            else:
                print(f"❌ Unknown TTS provider: {tts_provider}. Falling back to local TTS.")
                audio_bytes = call_local_tts(chunk)

            if audio_bytes:
                print(f"✅ Audio generated successfully ({len(audio_bytes)} bytes)")
                # Retrieve facial/blendshape data using the separate API.
                facial_data = send_audio_to_neurosync(audio_bytes)
                if facial_data:
                    audio_queue.put((audio_bytes, facial_data))
                    print("✅ Facial data retrieved and queued")
                else:
                    print("❌ Failed to get facial data for chunk:", chunk)
            else:
                print("❌ TTS generation failed for chunk:", chunk)

        chunk_queue.task_done()
