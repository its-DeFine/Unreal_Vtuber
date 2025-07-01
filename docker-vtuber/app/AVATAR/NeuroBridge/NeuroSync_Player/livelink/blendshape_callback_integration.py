"""
Blendshape Callback Integration for Autonomous Orchestrator V2
Provides real-time feedback from blendshape streaming to orchestrator
"""

import time
import logging
from typing import List, Optional, Callable, Dict, Any
from threading import Lock

# Global orchestrator reference
_orchestrator_v2 = None
_callback_lock = Lock()


def set_orchestrator_v2(orchestrator):
    """Set the V2 orchestrator instance for callbacks"""
    global _orchestrator_v2
    with _callback_lock:
        _orchestrator_v2 = orchestrator
        logging.info("✅ Blendshape callbacks connected to Orchestrator V2")


def send_pre_encoded_data_to_unreal_with_callbacks(
    encoded_facial_data: List[bytes], 
    start_event, 
    fps: int, 
    socket_connection=None,
    speech_metadata: Dict[str, Any] = None
):
    """
    Enhanced version of send_pre_encoded_data_to_unreal with orchestrator callbacks
    This replaces the original function to provide real-time feedback
    """
    
    logger = logging.getLogger(__name__)
    
    # Notify orchestrator that blendshapes are starting
    if _orchestrator_v2:
        try:
            _orchestrator_v2.blendshape_monitor.on_blendshape_start()
            logger.info(f"[BLENDSHAPE-CALLBACK] Started streaming ({len(encoded_facial_data)} frames)")
        except Exception as e:
            logger.error(f"[BLENDSHAPE-CALLBACK] Error notifying start: {e}")
    
    # Import the original function
    try:
        from livelink.send_to_unreal import create_socket_connection
        
        own_socket = False
        if socket_connection is None:
            socket_connection = create_socket_connection()
            own_socket = True
            
        start_event.wait()
        frame_duration = 1 / fps
        start_time = time.time()
        
        total_frames = len(encoded_facial_data)
        
        for frame_index, frame_data in enumerate(encoded_facial_data):
            current_time = time.time()
            elapsed_time = current_time - start_time
            expected_time = frame_index * frame_duration
            
            if elapsed_time < expected_time:
                time.sleep(expected_time - elapsed_time)
            elif elapsed_time > expected_time + frame_duration:
                continue
                
            socket_connection.sendall(frame_data)
            
            # Notify orchestrator of progress (every 10 frames to reduce overhead)
            if _orchestrator_v2 and frame_index % 10 == 0:
                try:
                    _orchestrator_v2.blendshape_monitor.on_blendshape_frame(
                        frame_index, total_frames
                    )
                except Exception as e:
                    if frame_index == 0:  # Only log once
                        logger.error(f"[BLENDSHAPE-CALLBACK] Error notifying progress: {e}")
                        
    except KeyboardInterrupt:
        pass
    except Exception as e:
        logger.error(f"[BLENDSHAPE-CALLBACK] Streaming error: {e}")
    finally:
        # Always notify completion
        if _orchestrator_v2:
            try:
                _orchestrator_v2.blendshape_monitor.on_blendshape_complete()
                logger.info("[BLENDSHAPE-CALLBACK] Completed streaming")
            except Exception as e:
                logger.error(f"[BLENDSHAPE-CALLBACK] Error notifying completion: {e}")
                
        if 'own_socket' in locals() and own_socket and socket_connection:
            socket_connection.close()


def patch_send_to_unreal():
    """
    Patch the original send_to_unreal module to use our callback version
    This should be called during initialization
    """
    try:
        import livelink.send_to_unreal as send_to_unreal_module
        
        # Store original function
        if not hasattr(send_to_unreal_module, '_original_send_pre_encoded_data_to_unreal'):
            send_to_unreal_module._original_send_pre_encoded_data_to_unreal = \
                send_to_unreal_module.send_pre_encoded_data_to_unreal
        
        # Replace with our version
        send_to_unreal_module.send_pre_encoded_data_to_unreal = \
            send_pre_encoded_data_to_unreal_with_callbacks
            
        logging.info("✅ Patched send_to_unreal with blendshape callbacks")
        return True
        
    except Exception as e:
        logging.error(f"❌ Failed to patch send_to_unreal: {e}")
        return False


def unpatch_send_to_unreal():
    """Restore original send_to_unreal function"""
    try:
        import livelink.send_to_unreal as send_to_unreal_module
        
        if hasattr(send_to_unreal_module, '_original_send_pre_encoded_data_to_unreal'):
            send_to_unreal_module.send_pre_encoded_data_to_unreal = \
                send_to_unreal_module._original_send_pre_encoded_data_to_unreal
            logging.info("✅ Restored original send_to_unreal")
            
    except Exception as e:
        logging.error(f"❌ Failed to unpatch send_to_unreal: {e}")


# Additional utility functions for monitoring
class BlendshapeStreamMonitor:
    """Monitor for tracking multiple concurrent streams"""
    
    def __init__(self):
        self.active_streams = {}
        self.lock = Lock()
        
    def register_stream(self, stream_id: str, total_frames: int):
        """Register a new stream"""
        with self.lock:
            self.active_streams[stream_id] = {
                'start_time': time.time(),
                'total_frames': total_frames,
                'current_frame': 0,
                'completed': False
            }
            
    def update_stream(self, stream_id: str, current_frame: int):
        """Update stream progress"""
        with self.lock:
            if stream_id in self.active_streams:
                self.active_streams[stream_id]['current_frame'] = current_frame
                
    def complete_stream(self, stream_id: str):
        """Mark stream as complete"""
        with self.lock:
            if stream_id in self.active_streams:
                stream_info = self.active_streams[stream_id]
                stream_info['completed'] = True
                stream_info['duration'] = time.time() - stream_info['start_time']
                
    def get_active_streams(self) -> Dict[str, Any]:
        """Get all active streams"""
        with self.lock:
            return {k: v for k, v in self.active_streams.items() if not v['completed']}
            
    def cleanup_old_streams(self, max_age_seconds: float = 60):
        """Clean up old completed streams"""
        with self.lock:
            current_time = time.time()
            to_remove = []
            
            for stream_id, info in self.active_streams.items():
                if info['completed'] and current_time - info['start_time'] > max_age_seconds:
                    to_remove.append(stream_id)
                    
            for stream_id in to_remove:
                del self.active_streams[stream_id]


# Global stream monitor instance
stream_monitor = BlendshapeStreamMonitor() 