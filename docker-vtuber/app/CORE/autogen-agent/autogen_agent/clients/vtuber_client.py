import logging
from typing import Dict

try:
    import requests
except ImportError:  # pragma: no cover
    requests = None  # type: ignore


class VTuberClient:
    def __init__(self, endpoint: str = None):
        self.endpoint = endpoint.rstrip("/") if endpoint else None
        self.enabled = bool(endpoint)
        self.vtuber_activated = False  # 🎭 NEW: VTuber activation state
        
        if self.enabled:
            logging.info("🎭 [VTUBER] VTuber client using %s", endpoint)
        else:
            logging.info("🎭 [VTUBER] VTuber client disabled - standalone mode")

    def activate_vtuber(self) -> None:
        """🎭 Activate VTuber for message sending"""
        self.vtuber_activated = True
        logging.info("🎭 [VTUBER] VTuber activated - messages will now be sent")

    def deactivate_vtuber(self) -> None:
        """🎭 Deactivate VTuber to stop message sending"""
        self.vtuber_activated = False
        logging.info("🎭 [VTUBER] VTuber deactivated - messages will be logged only")

    def is_vtuber_activated(self) -> bool:
        """🎭 Check if VTuber is currently activated"""
        return self.vtuber_activated

    def post_message(self, message: str, force_send: bool = False) -> None:
        """
        Send message to VTuber endpoint only if activated or forced
        
        Args:
            message: Message to send
            force_send: If True, bypass activation check (for tool-initiated messages)
        """
        if not message:
            return
            
        # 🚫 Check activation state first
        if not force_send and not self.vtuber_activated:
            logging.debug("🚫 [VTUBER] Message blocked - VTuber not activated: %s", 
                         message[:50] + "..." if len(message) > 50 else message)
            return
            
        if not self.enabled:
            activation_status = "activated" if self.vtuber_activated or force_send else "not activated"
            logging.info("🎭 [VTUBER] Message (standalone, %s): %s", 
                        activation_status,
                        message[:100] + "..." if len(message) > 100 else message)
            return
            
        url = f"{self.endpoint}/process_text"  # Updated to correct endpoint
        if requests:
            try:
                response = requests.post(url, json={
                    "text": message,
                    "autonomous_context": True
                }, timeout=10)  # Increased timeout for better reliability
                
                if response.ok:
                    logging.info("🎭 [VTUBER] Message sent to VTuber service")
                else:
                    logging.warning("⚠️ [VTUBER] VTuber service returned HTTP %d", response.status_code)
                    
            except Exception as exc:  # pragma: no cover
                logging.warning("⚠️ [VTUBER] Failed to post message to VTuber service: %s", exc)
                logging.info("🎭 [VTUBER] Message (fallback): %s", 
                           message[:100] + "..." if len(message) > 100 else message)

    def get_status(self) -> Dict[str, any]:
        """🎭 Get VTuber client status"""
        return {
            "enabled": self.enabled,
            "activated": self.vtuber_activated,
            "endpoint": self.endpoint
        }

    def is_available(self) -> bool:
        """Check if VTuber service is available"""
        return self.endpoint is not None and self.enabled
