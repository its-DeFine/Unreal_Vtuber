#!/usr/bin/env python3
"""
LLM + TTS Real-Time Audio Streamer
Integrates LLM text generation with TTS and audio-only RTMP streaming
"""

import sys
import os
import asyncio
import logging
import json
import time
from pathlib import Path
from typing import Dict, Any, Optional
import argparse

# Add AI models service path
sys.path.append('/opt/voice_app/services/ai-models')

from audio_quality_manager import AudioQualityManager

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('/var/log/llm_tts_streamer.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class LLMTTSStreamer:
    """
    Real-time LLM + TTS to RTMP audio streaming
    """
    
    def __init__(self, stream_name: str = "voice_stream"):
        self.stream_name = stream_name
        self.audio_manager = AudioQualityManager()
        self.is_streaming = False
        
        # TTS configuration
        self.tts_config = {
            'model': 'tts_models/en/ljspeech/tacotron2-DDC',
            'voice_speed': 1.0,
            'voice_pitch': 0.0
        }
        
        logger.info(f"🎙️ [LLMTTSStreamer] Initialized for stream: {stream_name}")

    async def generate_llm_response(self, user_input: str, context: str = "") -> str:
        """
        Generate LLM response using Ollama (from Task 4)
        
        Args:
            user_input: User's text input
            context: Optional context for the conversation
            
        Returns:
            str: Generated response text
        """
        try:
            # Simulate LLM API call (would use actual Ollama integration from Task 4)
            # For now, using a simple response pattern
            
            logger.info(f"🧠 [LLMTTSStreamer] Generating LLM response for: '{user_input[:50]}...'")
            
            # Simple response generation (replace with actual Ollama call)
            if "hello" in user_input.lower():
                response = "Hello! I'm your AI assistant. How can I help you today?"
            elif "weather" in user_input.lower():
                response = "I don't have access to current weather data, but I'd be happy to help with other questions."
            elif "time" in user_input.lower():
                current_time = time.strftime("%I:%M %p")
                response = f"The current time is {current_time}."
            else:
                response = f"I understand you said: {user_input}. That's an interesting topic! Let me think about that..."
            
            logger.info(f"✅ [LLMTTSStreamer] Generated response: '{response[:50]}...'")
            return response
            
        except Exception as e:
            logger.error(f"❌ [LLMTTSStreamer] LLM generation failed: {str(e)}")
            return "I'm sorry, I'm having trouble processing that right now."

    async def text_to_speech(self, text: str) -> Optional[str]:
        """
        Convert text to speech and return audio file path
        
        Args:
            text: Text to convert to speech
            
        Returns:
            str: Path to generated audio file, or None if failed
        """
        try:
            logger.info(f"🗣️ [LLMTTSStreamer] Converting to speech: '{text[:50]}...'")
            
            # Create unique filename for this TTS output
            timestamp = int(time.time() * 1000)
            audio_file = f"/tmp/tts_output_{self.stream_name}_{timestamp}.wav"
            
            # Use Coqui TTS (from Task 4 implementation)
            tts_cmd = [
                'tts',
                '--text', text,
                '--model_name', self.tts_config['model'],
                '--out_path', audio_file
            ]
            
            # Execute TTS generation
            import subprocess
            result = subprocess.run(tts_cmd, capture_output=True, text=True, timeout=30)
            
            if result.returncode == 0 and os.path.exists(audio_file):
                logger.info(f"✅ [LLMTTSStreamer] TTS generated: {audio_file}")
                return audio_file
            else:
                logger.error(f"❌ [LLMTTSStreamer] TTS failed: {result.stderr}")
                return None
                
        except Exception as e:
            logger.error(f"❌ [LLMTTSStreamer] TTS conversion failed: {str(e)}")
            return None

    async def stream_audio_file(self, audio_file: str, quality_profiles: list = None) -> bool:
        """
        Stream audio file to RTMP with multiple quality options
        
        Args:
            audio_file: Path to audio file to stream
            quality_profiles: List of quality profiles to use
            
        Returns:
            bool: True if streaming started successfully
        """
        try:
            if quality_profiles is None:
                quality_profiles = ['medium']  # Default for TTS
            
            logger.info(f"📡 [LLMTTSStreamer] Streaming audio: {audio_file}")
            
            # Start audio transcoding with quality manager
            success = self.audio_manager.start_audio_transcoding(
                audio_file, 
                self.stream_name,
                quality_profiles
            )
            
            if success:
                logger.info(f"✅ [LLMTTSStreamer] Audio streaming started")
                return True
            else:
                logger.error("❌ [LLMTTSStreamer] Failed to start audio streaming")
                return False
                
        except Exception as e:
            logger.error(f"❌ [LLMTTSStreamer] Audio streaming failed: {str(e)}")
            return False

    async def process_user_input(self, user_input: str, 
                               stream_audio: bool = True,
                               quality_profiles: list = None) -> Dict[str, Any]:
        """
        Complete pipeline: User input → LLM → TTS → Audio streaming
        
        Args:
            user_input: User's text input
            stream_audio: Whether to stream the generated audio
            quality_profiles: Audio quality profiles to use
            
        Returns:
            dict: Processing results and metadata
        """
        start_time = time.time()
        
        try:
            logger.info(f"🔄 [LLMTTSStreamer] Processing input: '{user_input[:50]}...'")
            
            # Step 1: Generate LLM response
            llm_start = time.time()
            response_text = await self.generate_llm_response(user_input)
            llm_time = time.time() - llm_start
            
            # Step 2: Convert to speech
            tts_start = time.time()
            audio_file = await self.text_to_speech(response_text)
            tts_time = time.time() - tts_start
            
            if not audio_file:
                raise Exception("TTS generation failed")
            
            # Step 3: Stream audio (if requested)
            stream_success = False
            stream_time = 0
            
            if stream_audio:
                stream_start = time.time()
                stream_success = await self.stream_audio_file(audio_file, quality_profiles)
                stream_time = time.time() - stream_start
            
            total_time = time.time() - start_time
            
            # Build result
            result = {
                'success': True,
                'user_input': user_input,
                'llm_response': response_text,
                'audio_file': audio_file,
                'stream_success': stream_success,
                'timing': {
                    'llm_ms': round(llm_time * 1000, 2),
                    'tts_ms': round(tts_time * 1000, 2),
                    'stream_ms': round(stream_time * 1000, 2),
                    'total_ms': round(total_time * 1000, 2)
                },
                'quality_profiles': quality_profiles or ['medium'],
                'stream_name': self.stream_name
            }
            
            logger.info(f"✅ [LLMTTSStreamer] Processing complete - Total: {result['timing']['total_ms']}ms")
            return result
            
        except Exception as e:
            logger.error(f"❌ [LLMTTSStreamer] Processing failed: {str(e)}")
            return {
                'success': False,
                'error': str(e),
                'user_input': user_input,
                'timing': {'total_ms': round((time.time() - start_time) * 1000, 2)}
            }

    async def start_interactive_mode(self):
        """Start interactive mode for testing"""
        logger.info("🎙️ [LLMTTSStreamer] Starting interactive mode")
        print("\n" + "="*60)
        print("🎙️  LLM + TTS Real-Time Audio Streamer")
        print("="*60)
        print("Type your message and press Enter to generate speech")
        print("Stream URLs:")
        print(f"  Medium Quality: rtmp://localhost:1935/live/{self.stream_name}_medium")
        print(f"  High Quality:   rtmp://localhost:1935/live/{self.stream_name}_high")
        print("Type 'quit' to exit")
        print("="*60)
        
        try:
            while True:
                user_input = input("\n💬 You: ").strip()
                
                if user_input.lower() in ['quit', 'exit', 'q']:
                    break
                
                if not user_input:
                    continue
                
                print("🔄 Processing...")
                
                # Process input with audio streaming
                result = await self.process_user_input(
                    user_input, 
                    stream_audio=True,
                    quality_profiles=['medium', 'high']
                )
                
                if result['success']:
                    print(f"🤖 AI: {result['llm_response']}")
                    print(f"⏱️  Timing: LLM {result['timing']['llm_ms']}ms, "
                          f"TTS {result['timing']['tts_ms']}ms, "
                          f"Total {result['timing']['total_ms']}ms")
                    if result['stream_success']:
                        print("📡 Audio streaming started successfully")
                    else:
                        print("⚠️ Audio streaming failed")
                else:
                    print(f"❌ Error: {result.get('error', 'Unknown error')}")
                    
        except KeyboardInterrupt:
            logger.info("🛑 [LLMTTSStreamer] Interrupted by user")
        finally:
            # Cleanup
            self.audio_manager.stop_audio_transcoding()
            logger.info("✅ [LLMTTSStreamer] Cleanup complete")

    def get_streaming_stats(self) -> Dict[str, Any]:
        """Get current streaming statistics"""
        return {
            'stream_name': self.stream_name,
            'is_streaming': self.is_streaming,
            'audio_stats': self.audio_manager.get_audio_stats(),
            'tts_config': self.tts_config
        }

async def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(description='LLM + TTS Real-Time Audio Streamer')
    parser.add_argument('--stream-name', default='voice_stream', 
                       help='Stream name identifier')
    parser.add_argument('--interactive', action='store_true',
                       help='Start interactive mode')
    parser.add_argument('--text', help='Single text to process and stream')
    parser.add_argument('--quality', nargs='+', 
                       choices=['low', 'medium', 'high'],
                       default=['medium'],
                       help='Audio quality profiles')
    parser.add_argument('--log-level', choices=['DEBUG', 'INFO', 'WARNING', 'ERROR'], 
                       default='INFO', help='Logging level')
    
    args = parser.parse_args()
    
    # Set log level
    logging.getLogger().setLevel(getattr(logging, args.log_level))
    
    # Create streamer
    streamer = LLMTTSStreamer(args.stream_name)
    
    try:
        if args.interactive:
            # Interactive mode
            await streamer.start_interactive_mode()
        elif args.text:
            # Single text processing
            result = await streamer.process_user_input(
                args.text, 
                stream_audio=True,
                quality_profiles=args.quality
            )
            
            if result['success']:
                print(f"✅ Processed successfully - Total time: {result['timing']['total_ms']}ms")
                print(f"🤖 Response: {result['llm_response']}")
                print(f"📡 Audio file: {result['audio_file']}")
                if result['stream_success']:
                    print(f"📡 Streaming to: rtmp://localhost:1935/live/{args.stream_name}_*")
            else:
                print(f"❌ Processing failed: {result.get('error')}")
                sys.exit(1)
        else:
            print("Please specify --interactive or --text")
            sys.exit(1)
            
    except Exception as e:
        logger.error(f"❌ [LLMTTSStreamer] Unexpected error: {str(e)}")
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(main()) 