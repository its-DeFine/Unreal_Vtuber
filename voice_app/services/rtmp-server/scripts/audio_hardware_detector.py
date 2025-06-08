#!/usr/bin/env python3
"""
Audio Hardware Acceleration Detector for LLM + TTS Streaming
Detects and optimizes audio encoding hardware capabilities for real-time voice processing
"""

import os
import sys
import logging
import subprocess
import platform
import json
from typing import Dict, List, Optional, Any, Tuple
from pathlib import Path
import argparse

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('/var/log/audio_hardware_detector.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class AudioHardwareDetector:
    """
    Audio hardware acceleration detector for voice/TTS streaming
    Focuses on audio encoding acceleration rather than video
    """
    
    def __init__(self):
        self.detected_hardware = {}
        self.audio_encoders = {}
        self.optimal_profiles = {}
        self.system_info = {}
        
        logger.info("🔍 [AudioHW] Initializing audio hardware detection")

    def detect_system_info(self) -> Dict[str, Any]:
        """Detect basic system information"""
        try:
            self.system_info = {
                'platform': platform.system(),
                'architecture': platform.machine(),
                'processor': platform.processor(),
                'cpu_count': os.cpu_count(),
                'python_version': platform.python_version()
            }
            
            # Get detailed CPU info
            if self.system_info['platform'] == 'Linux':
                try:
                    with open('/proc/cpuinfo', 'r') as f:
                        cpuinfo = f.read()
                    
                    # Extract CPU model
                    for line in cpuinfo.split('\n'):
                        if 'model name' in line:
                            self.system_info['cpu_model'] = line.split(':')[1].strip()
                            break
                except Exception:
                    pass
            
            logger.info(f"💻 [AudioHW] System: {self.system_info['platform']} {self.system_info['architecture']}")
            logger.info(f"💻 [AudioHW] CPU: {self.system_info.get('cpu_model', 'Unknown')} ({self.system_info['cpu_count']} cores)")
            
            return self.system_info
            
        except Exception as e:
            logger.error(f"❌ [AudioHW] Failed to detect system info: {str(e)}")
            return {}

    def detect_ffmpeg_audio_encoders(self) -> Dict[str, Any]:
        """Detect available FFmpeg audio encoders with hardware acceleration"""
        try:
            logger.info("🔍 [AudioHW] Detecting FFmpeg audio encoders...")
            
            # Get FFmpeg encoders
            result = subprocess.run(['ffmpeg', '-encoders'], capture_output=True, text=True)
            if result.returncode != 0:
                logger.error("❌ [AudioHW] FFmpeg not available")
                return {}
            
            encoders_output = result.stdout
            
            # Audio encoders of interest for voice/TTS
            audio_encoders = {
                'software': {
                    'aac': {'name': 'aac', 'desc': 'AAC (Advanced Audio Coding)', 'quality': 'high'},
                    'libfdk_aac': {'name': 'libfdk_aac', 'desc': 'Fraunhofer FDK AAC', 'quality': 'highest'},
                    'mp3': {'name': 'libmp3lame', 'desc': 'MP3 (MPEG audio layer 3)', 'quality': 'medium'},
                    'opus': {'name': 'libopus', 'desc': 'Opus codec', 'quality': 'high', 'latency': 'low'}
                },
                'hardware': {},
                'optimized': {}
            }
            
            # Check which encoders are available
            for category, encoders in audio_encoders.items():
                if category == 'hardware':  # Will detect hardware-specific ones
                    continue
                    
                for encoder_key, encoder_info in list(encoders.items()):
                    if encoder_info['name'] in encoders_output:
                        logger.info(f"✅ [AudioHW] Found audio encoder: {encoder_info['name']} - {encoder_info['desc']}")
                    else:
                        logger.warning(f"⚠️ [AudioHW] Missing audio encoder: {encoder_info['name']}")
                        del encoders[encoder_key]
            
            # Detect hardware-accelerated audio processing
            self._detect_hardware_audio_acceleration(audio_encoders, encoders_output)
            
            self.audio_encoders = audio_encoders
            return audio_encoders
            
        except Exception as e:
            logger.error(f"❌ [AudioHW] Failed to detect audio encoders: {str(e)}")
            return {}

    def _detect_hardware_audio_acceleration(self, audio_encoders: Dict, ffmpeg_output: str):
        """Detect hardware-specific audio acceleration"""
        try:
            # Intel Quick Sync Audio (if available)
            if 'qsv' in ffmpeg_output:
                audio_encoders['hardware']['qsv_aac'] = {
                    'name': 'aac_qsv',
                    'desc': 'Intel Quick Sync AAC',
                    'quality': 'high',
                    'latency': 'low',
                    'vendor': 'intel'
                }
                logger.info("✅ [AudioHW] Intel Quick Sync audio acceleration detected")
            
            # NVIDIA audio processing (NVENC companion)
            if 'nvenc' in ffmpeg_output or 'cuda' in ffmpeg_output:
                # NVIDIA doesn't have dedicated audio encoders, but CUDA can accelerate audio filters
                audio_encoders['optimized']['cuda_filters'] = {
                    'name': 'cuda_audio_filters',
                    'desc': 'NVIDIA CUDA Audio Filters',
                    'quality': 'high',
                    'latency': 'low',
                    'vendor': 'nvidia'
                }
                logger.info("✅ [AudioHW] NVIDIA CUDA audio processing detected")
            
            # AMD audio acceleration (rare, but check)
            if 'amf' in ffmpeg_output:
                audio_encoders['hardware']['amf_aac'] = {
                    'name': 'aac_amf',
                    'desc': 'AMD AMF AAC',
                    'quality': 'high',
                    'latency': 'medium',
                    'vendor': 'amd'
                }
                logger.info("✅ [AudioHW] AMD AMF audio acceleration detected")
                
        except Exception as e:
            logger.error(f"❌ [AudioHW] Hardware acceleration detection failed: {str(e)}")

    def detect_audio_devices(self) -> Dict[str, List]:
        """Detect available audio input/output devices"""
        try:
            logger.info("🔍 [AudioHW] Detecting audio devices...")
            
            # Use FFmpeg to detect audio devices
            result = subprocess.run(['ffmpeg', '-f', 'alsa', '-list_devices', 'true', '-i', 'dummy'], 
                                 capture_output=True, text=True)
            
            devices = {
                'input': [],
                'output': []
            }
            
            # Parse device list from stderr (FFmpeg outputs device list to stderr)
            lines = result.stderr.split('\n')
            current_type = None
            
            for line in lines:
                if 'Input' in line and 'device' in line:
                    current_type = 'input'
                elif 'Output' in line and 'device' in line:
                    current_type = 'output'
                elif current_type and '[alsa' in line:
                    # Extract device info
                    if 'card' in line:
                        device_info = line.strip()
                        devices[current_type].append(device_info)
            
            logger.info(f"🎤 [AudioHW] Found {len(devices['input'])} input devices")
            logger.info(f"🔊 [AudioHW] Found {len(devices['output'])} output devices")
            
            return devices
            
        except Exception as e:
            logger.error(f"❌ [AudioHW] Audio device detection failed: {str(e)}")
            return {'input': [], 'output': []}

    def benchmark_audio_encoders(self) -> Dict[str, Dict]:
        """Benchmark available audio encoders for performance"""
        try:
            logger.info("⚡ [AudioHW] Benchmarking audio encoders...")
            
            benchmark_results = {}
            
            # Create test audio file (1 second of silence for quick test)
            test_audio = "/tmp/test_audio_benchmark.wav"
            subprocess.run([
                'ffmpeg', '-y', '-f', 'lavfi', '-i', 'anullsrc=duration=1:sample_rate=44100:channels=2',
                test_audio
            ], capture_output=True)
            
            # Test available encoders
            for category, encoders in self.audio_encoders.items():
                if category == 'optimized':  # Skip complex optimized tests for now
                    continue
                    
                for encoder_key, encoder_info in encoders.items():
                    try:
                        encoder_name = encoder_info['name']
                        output_file = f"/tmp/benchmark_{encoder_key}.aac"
                        
                        # Benchmark encoding speed
                        start_time = time.time()
                        result = subprocess.run([
                            'ffmpeg', '-y', '-i', test_audio,
                            '-c:a', encoder_name, '-b:a', '128k',
                            output_file
                        ], capture_output=True, text=True, timeout=10)
                        
                        encode_time = time.time() - start_time
                        
                        if result.returncode == 0:
                            # Get file size for compression efficiency
                            file_size = os.path.getsize(output_file) if os.path.exists(output_file) else 0
                            
                            benchmark_results[encoder_key] = {
                                'encode_time_ms': round(encode_time * 1000, 2),
                                'file_size_bytes': file_size,
                                'compression_ratio': round(file_size / os.path.getsize(test_audio), 3),
                                'performance_score': round(1000 / (encode_time * 1000), 2),  # Higher is better
                                'status': 'success'
                            }
                            
                            logger.info(f"✅ [AudioHW] {encoder_key}: {encode_time*1000:.1f}ms, "
                                      f"size: {file_size} bytes")
                            
                            # Cleanup
                            if os.path.exists(output_file):
                                os.remove(output_file)
                        else:
                            benchmark_results[encoder_key] = {
                                'status': 'failed',
                                'error': result.stderr
                            }
                            logger.warning(f"⚠️ [AudioHW] {encoder_key} benchmark failed")
                            
                    except Exception as e:
                        benchmark_results[encoder_key] = {
                            'status': 'error',
                            'error': str(e)
                        }
                        logger.error(f"❌ [AudioHW] {encoder_key} benchmark error: {str(e)}")
            
            # Cleanup test file
            if os.path.exists(test_audio):
                os.remove(test_audio)
            
            return benchmark_results
            
        except Exception as e:
            logger.error(f"❌ [AudioHW] Benchmarking failed: {str(e)}")
            return {}

    def generate_optimal_profiles(self) -> Dict[str, Dict]:
        """Generate optimal audio profiles based on detected hardware"""
        try:
            logger.info("🎯 [AudioHW] Generating optimal audio profiles...")
            
            profiles = {}
            
            # Determine best encoder for each quality level
            best_encoders = self._select_best_encoders()
            
            # Generate profiles optimized for voice/TTS content
            profiles['voice_low_latency'] = {
                'encoder': best_encoders.get('low_latency', 'aac'),
                'bitrate': '64k',
                'sample_rate': 22050,
                'channels': 1,  # Mono for voice
                'format': 'aac',
                'preset': 'ultrafast',
                'latency_target_ms': 50,
                'use_case': 'Real-time TTS, mobile/poor connection',
                'audio_filters': 'highpass=f=80,lowpass=f=8000'  # Voice frequency range
            }
            
            profiles['voice_standard'] = {
                'encoder': best_encoders.get('balanced', 'aac'),
                'bitrate': '128k',
                'sample_rate': 44100,
                'channels': 2,  # Stereo
                'format': 'aac',
                'preset': 'fast',
                'latency_target_ms': 100,
                'use_case': 'Standard TTS streaming',
                'audio_filters': 'highpass=f=60,lowpass=f=15000'
            }
            
            profiles['voice_high_quality'] = {
                'encoder': best_encoders.get('high_quality', 'libfdk_aac'),
                'bitrate': '256k',
                'sample_rate': 48000,
                'channels': 2,  # Stereo
                'format': 'aac',
                'preset': 'medium',
                'latency_target_ms': 150,
                'use_case': 'High-quality voice streaming',
                'audio_filters': 'highpass=f=40,lowpass=f=20000'
            }
            
            # Add hardware-accelerated profiles if available
            if self.audio_encoders.get('hardware'):
                for hw_encoder_key, hw_encoder_info in self.audio_encoders['hardware'].items():
                    profile_name = f"hw_{hw_encoder_info['vendor']}_optimized"
                    profiles[profile_name] = {
                        'encoder': hw_encoder_info['name'],
                        'bitrate': '192k',
                        'sample_rate': 48000,
                        'channels': 2,
                        'format': 'aac',
                        'preset': 'fast',
                        'latency_target_ms': 75,
                        'use_case': f"Hardware-accelerated ({hw_encoder_info['vendor']})",
                        'hardware_acceleration': True,
                        'vendor': hw_encoder_info['vendor']
                    }
            
            self.optimal_profiles = profiles
            
            logger.info(f"🎯 [AudioHW] Generated {len(profiles)} optimal audio profiles")
            for profile_name, profile in profiles.items():
                logger.info(f"  ✓ {profile_name}: {profile['encoder']} @ {profile['bitrate']} "
                          f"({profile['latency_target_ms']}ms target)")
            
            return profiles
            
        except Exception as e:
            logger.error(f"❌ [AudioHW] Profile generation failed: {str(e)}")
            return {}

    def _select_best_encoders(self) -> Dict[str, str]:
        """Select best encoders based on benchmarks and availability"""
        best = {
            'low_latency': 'aac',      # Default fallback
            'balanced': 'aac',         # Default fallback  
            'high_quality': 'aac'      # Default fallback
        }
        
        # Prefer hardware acceleration if available
        if self.audio_encoders.get('hardware'):
            hw_encoder = list(self.audio_encoders['hardware'].keys())[0]
            best['low_latency'] = self.audio_encoders['hardware'][hw_encoder]['name']
        
        # Prefer high-quality software encoders
        software_encoders = self.audio_encoders.get('software', {})
        
        if 'libfdk_aac' in software_encoders:
            best['high_quality'] = 'libfdk_aac'
        if 'opus' in software_encoders:
            best['low_latency'] = 'libopus'  # Opus has very low latency
        if 'aac' in software_encoders:
            best['balanced'] = 'aac'  # Native AAC is well-balanced
        
        return best

    def save_hardware_profile(self, output_file: str = None) -> str:
        """Save detected hardware profile to JSON file"""
        try:
            if output_file is None:
                output_file = "/var/log/audio_hardware_profile.json"
            
            profile_data = {
                'timestamp': time.time(),
                'system_info': self.system_info,
                'audio_encoders': self.audio_encoders,
                'optimal_profiles': self.optimal_profiles,
                'benchmark_results': getattr(self, 'benchmark_results', {}),
                'recommendations': {
                    'primary_profile': 'voice_standard',
                    'fallback_profile': 'voice_low_latency',
                    'hardware_available': len(self.audio_encoders.get('hardware', {})) > 0
                }
            }
            
            with open(output_file, 'w') as f:
                json.dump(profile_data, f, indent=2)
            
            logger.info(f"💾 [AudioHW] Hardware profile saved: {output_file}")
            return output_file
            
        except Exception as e:
            logger.error(f"❌ [AudioHW] Failed to save hardware profile: {str(e)}")
            return ""

    def detect_all(self) -> Dict[str, Any]:
        """Run complete hardware detection and optimization"""
        logger.info("🚀 [AudioHW] Starting complete audio hardware detection...")
        
        try:
            # Step 1: System info
            self.detect_system_info()
            
            # Step 2: Audio encoders
            self.detect_ffmpeg_audio_encoders()
            
            # Step 3: Audio devices
            audio_devices = self.detect_audio_devices()
            
            # Step 4: Benchmark (optional, can be time-consuming)
            # self.benchmark_results = self.benchmark_audio_encoders()
            
            # Step 5: Generate optimal profiles
            self.generate_optimal_profiles()
            
            # Step 6: Save profile
            profile_file = self.save_hardware_profile()
            
            summary = {
                'system_info': self.system_info,
                'audio_encoders_count': {
                    'software': len(self.audio_encoders.get('software', {})),
                    'hardware': len(self.audio_encoders.get('hardware', {})),
                    'optimized': len(self.audio_encoders.get('optimized', {}))
                },
                'audio_devices_count': {
                    'input': len(audio_devices.get('input', [])),
                    'output': len(audio_devices.get('output', []))
                },
                'optimal_profiles_count': len(self.optimal_profiles),
                'hardware_acceleration_available': len(self.audio_encoders.get('hardware', {})) > 0,
                'profile_file': profile_file,
                'recommended_profile': 'voice_standard'
            }
            
            logger.info("✅ [AudioHW] Audio hardware detection complete!")
            logger.info(f"📊 [AudioHW] Summary: {summary['audio_encoders_count']['software']} software + "
                      f"{summary['audio_encoders_count']['hardware']} hardware encoders, "
                      f"{summary['optimal_profiles_count']} optimized profiles")
            
            return summary
            
        except Exception as e:
            logger.error(f"❌ [AudioHW] Detection failed: {str(e)}")
            return {'error': str(e)}

def main():
    """Main entry point for audio hardware detection"""
    parser = argparse.ArgumentParser(description='Audio Hardware Acceleration Detector for LLM + TTS')
    parser.add_argument('--benchmark', action='store_true',
                       help='Run encoder benchmarking (takes extra time)')
    parser.add_argument('--output', help='Output file for hardware profile JSON')
    parser.add_argument('--log-level', choices=['DEBUG', 'INFO', 'WARNING', 'ERROR'], 
                       default='INFO', help='Logging level')
    
    args = parser.parse_args()
    
    # Set log level
    logging.getLogger().setLevel(getattr(logging, args.log_level))
    
    try:
        detector = AudioHardwareDetector()
        
        # Run detection
        results = detector.detect_all()
        
        # Optionally run benchmarks
        if args.benchmark:
            logger.info("⚡ [AudioHW] Running encoder benchmarks...")
            detector.benchmark_results = detector.benchmark_audio_encoders()
        
        # Save with custom output file if specified
        if args.output:
            detector.save_hardware_profile(args.output)
        
        # Print summary
        if 'error' not in results:
            print("\n" + "="*60)
            print("🎤 Audio Hardware Detection Summary")
            print("="*60)
            print(f"Platform: {results['system_info']['platform']} {results['system_info']['architecture']}")
            print(f"Audio Encoders: {results['audio_encoders_count']['software']} software, "
                  f"{results['audio_encoders_count']['hardware']} hardware")
            print(f"Audio Devices: {results['audio_devices_count']['input']} input, "
                  f"{results['audio_devices_count']['output']} output")
            print(f"Optimal Profiles: {results['optimal_profiles_count']}")
            print(f"Hardware Acceleration: {'✅ Available' if results['hardware_acceleration_available'] else '❌ Not Available'}")
            print(f"Recommended Profile: {results['recommended_profile']}")
            print(f"Profile Saved: {results['profile_file']}")
            print("="*60)
        else:
            print(f"❌ Detection failed: {results['error']}")
            sys.exit(1)
            
    except Exception as e:
        logger.error(f"❌ [AudioHW] Unexpected error: {str(e)}")
        sys.exit(1)

if __name__ == "__main__":
    import time
    main() 