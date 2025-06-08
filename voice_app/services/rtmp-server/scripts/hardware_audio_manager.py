#!/usr/bin/env python3
"""
Hardware-Accelerated Audio Manager for LLM + TTS Streaming
Integrates hardware detection with audio quality management for optimal performance
"""

import os
import sys
import json
import logging
import time
from typing import Dict, Any, List, Optional
from pathlib import Path
import argparse

# Import our audio components
from audio_hardware_detector import AudioHardwareDetector
from audio_quality_manager import AudioQualityManager

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('/var/log/hardware_audio_manager.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class HardwareAudioManager:
    """
    Hardware-accelerated audio manager for LLM + TTS streaming
    Combines hardware detection with optimized audio quality management
    """
    
    def __init__(self, auto_detect: bool = True):
        self.hardware_detector = AudioHardwareDetector()
        self.audio_manager = AudioQualityManager()
        
        # Hardware-optimized profiles
        self.hw_profiles = {}
        self.current_profile = None
        self.hardware_info = {}
        
        if auto_detect:
            self.detect_and_optimize()
        
        logger.info("🔧 [HardwareAudio] Manager initialized")

    def detect_and_optimize(self) -> Dict[str, Any]:
        """Detect hardware and create optimized audio profiles"""
        try:
            logger.info("🔍 [HardwareAudio] Detecting hardware and optimizing profiles...")
            
            # Run hardware detection
            detection_results = self.hardware_detector.detect_all()
            
            if 'error' in detection_results:
                logger.error(f"❌ [HardwareAudio] Hardware detection failed: {detection_results['error']}")
                return detection_results
            
            self.hardware_info = detection_results
            
            # Create hardware-optimized audio profiles
            self.hw_profiles = self._create_hardware_optimized_profiles()
            
            # Select optimal default profile
            self.current_profile = self._select_optimal_profile()
            
            logger.info(f"✅ [HardwareAudio] Hardware detection complete, using profile: {self.current_profile}")
            return {
                'success': True,
                'hardware_info': self.hardware_info,
                'hw_profiles': list(self.hw_profiles.keys()),
                'current_profile': self.current_profile
            }
            
        except Exception as e:
            logger.error(f"❌ [HardwareAudio] Detection and optimization failed: {str(e)}")
            return {'error': str(e)}

    def _create_hardware_optimized_profiles(self) -> Dict[str, Dict]:
        """Create audio profiles optimized for detected hardware"""
        profiles = {}
        
        try:
            # Get optimal profiles from hardware detector
            optimal_profiles = self.hardware_detector.optimal_profiles
            
            # Create enhanced profiles for LLM + TTS streaming
            for profile_name, profile_config in optimal_profiles.items():
                # Add hardware-specific optimizations
                enhanced_profile = profile_config.copy()
                
                # Add FFmpeg command optimizations
                enhanced_profile['ffmpeg_params'] = self._build_hardware_ffmpeg_params(profile_config)
                
                # Add performance expectations
                enhanced_profile['expected_latency_ms'] = profile_config.get('latency_target_ms', 100)
                enhanced_profile['cpu_usage_level'] = self._estimate_cpu_usage(profile_config)
                
                # Add use case recommendations
                enhanced_profile['recommended_for'] = self._get_use_case_recommendation(profile_config)
                
                profiles[profile_name] = enhanced_profile
            
            # Add fallback profile
            profiles['fallback_safe'] = {
                'encoder': 'aac',
                'bitrate': '64k',
                'sample_rate': 22050,
                'channels': 1,
                'format': 'aac',
                'preset': 'ultrafast',
                'latency_target_ms': 150,
                'use_case': 'Emergency fallback (minimal requirements)',
                'ffmpeg_params': ['-c:a', 'aac', '-b:a', '64k', '-ar', '22050', '-ac', '1'],
                'expected_latency_ms': 150,
                'cpu_usage_level': 'low',
                'recommended_for': ['emergency', 'minimal_hardware']
            }
            
            logger.info(f"🎯 [HardwareAudio] Created {len(profiles)} hardware-optimized profiles")
            return profiles
            
        except Exception as e:
            logger.error(f"❌ [HardwareAudio] Profile creation failed: {str(e)}")
            return {}

    def _build_hardware_ffmpeg_params(self, profile_config: Dict) -> List[str]:
        """Build FFmpeg parameters optimized for hardware"""
        params = []
        
        try:
            # Audio codec
            params.extend(['-c:a', profile_config['encoder']])
            
            # Bitrate
            params.extend(['-b:a', profile_config['bitrate']])
            
            # Sample rate
            params.extend(['-ar', str(profile_config['sample_rate'])])
            
            # Channels
            params.extend(['-ac', str(profile_config['channels'])])
            
            # Quality preset
            if 'preset' in profile_config:
                params.extend(['-preset', profile_config['preset']])
            
            # Audio filters for voice optimization
            if 'audio_filters' in profile_config:
                params.extend(['-af', profile_config['audio_filters']])
            
            # Hardware-specific optimizations
            if profile_config.get('hardware_acceleration'):
                vendor = profile_config.get('vendor', '').lower()
                
                if vendor == 'intel':
                    # Intel Quick Sync optimizations
                    params.extend(['-look_ahead', '0', '-async_depth', '1'])
                elif vendor == 'nvidia':
                    # NVIDIA CUDA optimizations
                    params.extend(['-gpu', '0'])
                elif vendor == 'amd':
                    # AMD AMF optimizations
                    params.extend(['-usage', 'lowlatency'])
            
            # Low-latency optimizations for real-time TTS
            params.extend([
                '-fflags', '+genpts',
                '-avoid_negative_ts', 'make_zero',
                '-max_delay', '0'
            ])
            
            return params
            
        except Exception as e:
            logger.error(f"❌ [HardwareAudio] FFmpeg params building failed: {str(e)}")
            return ['-c:a', 'aac', '-b:a', '128k']  # Fallback

    def _estimate_cpu_usage(self, profile_config: Dict) -> str:
        """Estimate CPU usage level for a profile"""
        try:
            if profile_config.get('hardware_acceleration'):
                return 'low'  # Hardware acceleration reduces CPU load
            
            bitrate = int(profile_config['bitrate'].replace('k', ''))
            sample_rate = profile_config['sample_rate']
            
            # Estimate based on encoding complexity
            if bitrate <= 64 and sample_rate <= 22050:
                return 'low'
            elif bitrate <= 128 and sample_rate <= 44100:
                return 'medium'
            else:
                return 'high'
                
        except Exception:
            return 'medium'  # Safe default

    def _get_use_case_recommendation(self, profile_config: Dict) -> List[str]:
        """Get use case recommendations for a profile"""
        recommendations = []
        
        try:
            latency = profile_config.get('latency_target_ms', 100)
            bitrate = int(profile_config['bitrate'].replace('k', ''))
            
            if latency <= 75:
                recommendations.append('real_time_interaction')
            if bitrate >= 192:
                recommendations.append('high_quality_streaming')
            if profile_config.get('hardware_acceleration'):
                recommendations.append('high_throughput')
            if profile_config.get('channels', 2) == 1:
                recommendations.append('voice_calls')
            
            recommendations.append('tts_streaming')  # All profiles good for TTS
            
            return recommendations
            
        except Exception:
            return ['general_purpose']

    def _select_optimal_profile(self) -> str:
        """Select the optimal profile based on hardware capabilities"""
        try:
            # Priority order for profile selection
            priority_profiles = [
                'hw_intel_optimized',     # Intel hardware acceleration
                'hw_nvidia_optimized',    # NVIDIA hardware acceleration
                'hw_amd_optimized',       # AMD hardware acceleration
                'voice_standard',         # Standard software profile
                'voice_low_latency',      # Low latency fallback
                'fallback_safe'          # Emergency fallback
            ]
            
            for profile_name in priority_profiles:
                if profile_name in self.hw_profiles:
                    logger.info(f"🎯 [HardwareAudio] Selected optimal profile: {profile_name}")
                    return profile_name
            
            # Fallback to first available profile
            if self.hw_profiles:
                first_profile = list(self.hw_profiles.keys())[0]
                logger.warning(f"⚠️ [HardwareAudio] Using first available profile: {first_profile}")
                return first_profile
            
            logger.error("❌ [HardwareAudio] No profiles available!")
            return None
            
        except Exception as e:
            logger.error(f"❌ [HardwareAudio] Profile selection failed: {str(e)}")
            return None

    def start_optimized_streaming(self, input_source: str, stream_name: str,
                                profile_name: str = None) -> bool:
        """Start audio streaming with hardware-optimized settings"""
        try:
            if profile_name is None:
                profile_name = self.current_profile
            
            if profile_name not in self.hw_profiles:
                logger.error(f"❌ [HardwareAudio] Unknown profile: {profile_name}")
                return False
            
            profile = self.hw_profiles[profile_name]
            
            logger.info(f"🚀 [HardwareAudio] Starting optimized streaming with profile: {profile_name}")
            logger.info(f"🎤 [HardwareAudio] Expected latency: {profile['expected_latency_ms']}ms, "
                      f"CPU usage: {profile['cpu_usage_level']}")
            
            # Override audio manager's default profiles with hardware-optimized ones
            self.audio_manager.audio_profiles['hw_optimized'] = {
                'bitrate': profile['bitrate'],
                'sample_rate': profile['sample_rate'],
                'channels': profile['channels'],
                'format': profile['format'],
                'description': f"Hardware-optimized: {profile['use_case']}"
            }
            
            # Start streaming with hardware profile
            success = self.audio_manager.start_audio_transcoding(
                input_source, 
                stream_name, 
                ['hw_optimized']
            )
            
            if success:
                logger.info(f"✅ [HardwareAudio] Hardware-optimized streaming started successfully")
            else:
                logger.error("❌ [HardwareAudio] Failed to start hardware-optimized streaming")
            
            return success
            
        except Exception as e:
            logger.error(f"❌ [HardwareAudio] Optimized streaming failed: {str(e)}")
            return False

    def get_performance_stats(self) -> Dict[str, Any]:
        """Get performance statistics and recommendations"""
        try:
            stats = {
                'hardware_info': self.hardware_info,
                'current_profile': self.current_profile,
                'available_profiles': list(self.hw_profiles.keys()),
                'audio_stats': self.audio_manager.get_audio_stats(),
                'hardware_acceleration_available': self.hardware_info.get('hardware_acceleration_available', False),
                'recommendations': self._get_performance_recommendations()
            }
            
            return stats
            
        except Exception as e:
            logger.error(f"❌ [HardwareAudio] Stats collection failed: {str(e)}")
            return {'error': str(e)}

    def _get_performance_recommendations(self) -> List[str]:
        """Get performance recommendations based on current setup"""
        recommendations = []
        
        try:
            if not self.hardware_info.get('hardware_acceleration_available', False):
                recommendations.append("Consider hardware with audio acceleration support for better performance")
            
            if self.current_profile and 'low_latency' in self.current_profile:
                recommendations.append("Using low-latency profile - suitable for real-time interaction")
            
            if self.current_profile == 'fallback_safe':
                recommendations.append("Using fallback profile - consider hardware upgrade for better quality")
            
            audio_stats = self.audio_manager.get_audio_stats()
            if audio_stats.get('active_audio_streams', 0) > 3:
                recommendations.append("High stream count detected - monitor CPU usage")
            
            return recommendations
            
        except Exception:
            return ["Unable to generate recommendations"]

    def switch_profile(self, profile_name: str) -> bool:
        """Switch to a different audio profile"""
        try:
            if profile_name not in self.hw_profiles:
                logger.error(f"❌ [HardwareAudio] Profile not found: {profile_name}")
                return False
            
            old_profile = self.current_profile
            self.current_profile = profile_name
            
            logger.info(f"🔄 [HardwareAudio] Switched profile: {old_profile} → {profile_name}")
            return True
            
        except Exception as e:
            logger.error(f"❌ [HardwareAudio] Profile switch failed: {str(e)}")
            return False

    def benchmark_current_setup(self) -> Dict[str, Any]:
        """Benchmark current hardware setup for audio performance"""
        try:
            logger.info("⚡ [HardwareAudio] Running hardware benchmark...")
            
            # Run encoder benchmarks
            benchmark_results = self.hardware_detector.benchmark_audio_encoders()
            
            # Add system performance metrics
            import psutil
            system_metrics = {
                'cpu_percent': psutil.cpu_percent(interval=1),
                'memory_percent': psutil.virtual_memory().percent,
                'available_memory_mb': psutil.virtual_memory().available // (1024*1024)
            }
            
            benchmark_summary = {
                'timestamp': time.time(),
                'encoder_benchmarks': benchmark_results,
                'system_metrics': system_metrics,
                'current_profile': self.current_profile,
                'hardware_acceleration': self.hardware_info.get('hardware_acceleration_available', False),
                'recommendations': self._analyze_benchmark_results(benchmark_results, system_metrics)
            }
            
            logger.info("✅ [HardwareAudio] Benchmark complete")
            return benchmark_summary
            
        except Exception as e:
            logger.error(f"❌ [HardwareAudio] Benchmarking failed: {str(e)}")
            return {'error': str(e)}

    def _analyze_benchmark_results(self, benchmark_results: Dict, system_metrics: Dict) -> List[str]:
        """Analyze benchmark results and provide recommendations"""
        recommendations = []
        
        try:
            # Analyze encoder performance
            fastest_encoder = None
            fastest_time = float('inf')
            
            for encoder, results in benchmark_results.items():
                if results.get('status') == 'success':
                    encode_time = results.get('encode_time_ms', float('inf'))
                    if encode_time < fastest_time:
                        fastest_time = encode_time
                        fastest_encoder = encoder
            
            if fastest_encoder:
                recommendations.append(f"Fastest encoder: {fastest_encoder} ({fastest_time:.1f}ms)")
            
            # Analyze system resources
            if system_metrics['cpu_percent'] > 80:
                recommendations.append("High CPU usage detected - consider hardware acceleration")
            
            if system_metrics['memory_percent'] > 90:
                recommendations.append("Low memory available - consider reducing concurrent streams")
            
            if system_metrics['available_memory_mb'] < 512:
                recommendations.append("Very low memory - use low-latency profiles only")
            
            return recommendations
            
        except Exception:
            return ["Unable to analyze benchmark results"]

def main():
    """Main entry point for hardware audio manager"""
    parser = argparse.ArgumentParser(description='Hardware-Accelerated Audio Manager for LLM + TTS')
    parser.add_argument('--detect-only', action='store_true',
                       help='Only run hardware detection, do not start streaming')
    parser.add_argument('--benchmark', action='store_true',
                       help='Run performance benchmarks')
    parser.add_argument('--profile', help='Select specific audio profile')
    parser.add_argument('--input-source', help='Audio input source for streaming')
    parser.add_argument('--stream-name', help='Stream name for RTMP output')
    parser.add_argument('--log-level', choices=['DEBUG', 'INFO', 'WARNING', 'ERROR'], 
                       default='INFO', help='Logging level')
    
    args = parser.parse_args()
    
    # Set log level
    logging.getLogger().setLevel(getattr(logging, args.log_level))
    
    try:
        # Create hardware audio manager
        manager = HardwareAudioManager()
        
        if args.detect_only:
            # Just show detection results
            stats = manager.get_performance_stats()
            print("\n" + "="*60)
            print("🔧 Hardware Audio Manager - Detection Results")
            print("="*60)
            print(f"Current Profile: {stats['current_profile']}")
            print(f"Available Profiles: {', '.join(stats['available_profiles'])}")
            print(f"Hardware Acceleration: {'✅ Available' if stats['hardware_acceleration_available'] else '❌ Not Available'}")
            print("\nRecommendations:")
            for rec in stats['recommendations']:
                print(f"  • {rec}")
            print("="*60)
            
        elif args.benchmark:
            # Run benchmarks
            benchmark_results = manager.benchmark_current_setup()
            if 'error' not in benchmark_results:
                print("\n" + "="*60)
                print("⚡ Hardware Audio Benchmark Results")
                print("="*60)
                print(f"Current Profile: {benchmark_results['current_profile']}")
                print(f"CPU Usage: {benchmark_results['system_metrics']['cpu_percent']:.1f}%")
                print(f"Memory Usage: {benchmark_results['system_metrics']['memory_percent']:.1f}%")
                print("\nRecommendations:")
                for rec in benchmark_results['recommendations']:
                    print(f"  • {rec}")
                print("="*60)
            else:
                print(f"❌ Benchmark failed: {benchmark_results['error']}")
                
        elif args.input_source and args.stream_name:
            # Start optimized streaming
            profile_name = args.profile or manager.current_profile
            
            if manager.switch_profile(profile_name):
                success = manager.start_optimized_streaming(
                    args.input_source, 
                    args.stream_name,
                    profile_name
                )
                
                if success:
                    print(f"✅ Hardware-optimized streaming started with profile: {profile_name}")
                    print(f"📡 Stream URL: rtmp://localhost:1935/live/{args.stream_name}_hw_optimized")
                    
                    # Keep running
                    try:
                        while True:
                            time.sleep(1)
                    except KeyboardInterrupt:
                        print("\n🛑 Stopping hardware-optimized streaming...")
                        manager.audio_manager.stop_audio_transcoding()
                else:
                    print("❌ Failed to start hardware-optimized streaming")
                    sys.exit(1)
            else:
                print(f"❌ Failed to switch to profile: {profile_name}")
                sys.exit(1)
        else:
            print("Usage: Specify --detect-only, --benchmark, or --input-source + --stream-name")
            sys.exit(1)
            
    except Exception as e:
        logger.error(f"❌ [HardwareAudio] Unexpected error: {str(e)}")
        sys.exit(1)

if __name__ == "__main__":
    main() 