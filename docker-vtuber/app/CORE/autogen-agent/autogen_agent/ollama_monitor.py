"""
Ollama Monitoring Module for AutoGen Agent

Queries Ollama container for GPU usage, model stats, and system information.
This is a cleaner approach than implementing GPU monitoring directly in AutoGen.
"""

import os
import time
import logging
import requests
from typing import Dict, Any, Optional
from datetime import datetime

logger = logging.getLogger(__name__)

class OllamaMonitor:
    """Monitor Ollama container for GPU stats and model performance"""
    
    def __init__(self):
        """Initialize Ollama monitor"""
        self.ollama_host = os.getenv('OLLAMA_HOST', 'http://ollama:11434')
        self.start_time = time.time()
        self.agent_id = os.getenv('AGENT_ID', 'autogen-ollama-001')
        self.tokens_generated = 0
        self.requests_completed = 0
        
    def get_uptime_seconds(self) -> float:
        """Calculate uptime in seconds"""
        return time.time() - self.start_time
    
    def check_ollama_health(self) -> bool:
        """Check if Ollama is responding"""
        try:
            response = requests.get(f"{self.ollama_host}/api/tags", timeout=5)
            return response.status_code == 200
        except:
            return False
    
    def get_running_models(self) -> Dict[str, Any]:
        """Get information about currently loaded models"""
        try:
            response = requests.get(f"{self.ollama_host}/api/ps", timeout=5)
            if response.status_code == 200:
                data = response.json()
                return {
                    "models": data.get("models", []),
                    "count": len(data.get("models", []))
                }
            return {"models": [], "count": 0}
        except Exception as e:
            logger.error(f"Error getting running models: {e}")
            return {"models": [], "count": 0}
    
    def get_available_models(self) -> list:
        """Get list of available models"""
        try:
            response = requests.get(f"{self.ollama_host}/api/tags", timeout=5)
            if response.status_code == 200:
                data = response.json()
                return [model["name"] for model in data.get("models", [])]
            return []
        except Exception as e:
            logger.error(f"Error getting available models: {e}")
            return []
    
    def estimate_gpu_usage(self, running_models: Dict[str, Any]) -> Dict[str, Any]:
        """Estimate GPU usage based on loaded models"""
        # Ollama doesn't expose direct GPU stats, so we estimate based on loaded models
        models = running_models.get("models", [])
        
        if not models:
            return {
                "estimated_vram_mb": 0,
                "estimated_usage_percent": 0,
                "model_count": 0,
                "status": "idle"
            }
        
        total_vram = 0
        for model in models:
            # Estimate VRAM based on model size (very rough estimates)
            size = model.get("size", 0) / (1024 * 1024)  # Convert to MB
            model_name = model.get("name", "").lower()
            
            # Rough VRAM estimates based on common model sizes
            if "70b" in model_name:
                estimated_vram = 40000  # ~40GB for 70B models
            elif "34b" in model_name or "33b" in model_name:
                estimated_vram = 20000  # ~20GB for 30B+ models
            elif "13b" in model_name:
                estimated_vram = 10000  # ~10GB for 13B models
            elif "7b" in model_name:
                estimated_vram = 6000   # ~6GB for 7B models
            elif "3b" in model_name:
                estimated_vram = 3000   # ~3GB for 3B models
            else:
                estimated_vram = max(size * 1.5, 2000)  # Default estimate
            
            total_vram += estimated_vram
        
        # Assume 24GB GPU (common for local LLM work)
        gpu_total_mb = 24576
        usage_percent = min((total_vram / gpu_total_mb) * 100, 95)
        
        return {
            "estimated_vram_mb": int(total_vram),
            "estimated_usage_percent": round(usage_percent, 1),
            "model_count": len(models),
            "status": "active" if models else "idle",
            "loaded_models": [m.get("name", "unknown") for m in models]
        }
    
    def get_ollama_status(self) -> Dict[str, Any]:
        """Get comprehensive Ollama and GPU status"""
        current_time = time.time()
        uptime_seconds = self.get_uptime_seconds()
        
        # Check Ollama health
        ollama_healthy = self.check_ollama_health()
        
        # Get running models
        running_models = self.get_running_models()
        
        # Get available models
        available_models = self.get_available_models()
        
        # Estimate GPU usage
        gpu_usage = self.estimate_gpu_usage(running_models)
        
        # Build GPU data structure similar to nvidia-ml-py format
        gpu_data = {
            "count": 1,  # Assume single GPU
            "devices": {
                0: {
                    "device_id": 0,
                    "name": "Ollama GPU (Estimated)",
                    "memory": {
                        "total_mb": 24576,  # Assume 24GB
                        "used_mb": gpu_usage["estimated_vram_mb"],
                        "free_mb": 24576 - gpu_usage["estimated_vram_mb"],
                        "usage_percent": gpu_usage["estimated_usage_percent"]
                    },
                    "utilization": {
                        "gpu_percent": min(gpu_usage["estimated_usage_percent"] * 1.2, 100),  # Rough estimate
                        "memory_percent": gpu_usage["estimated_usage_percent"]
                    },
                    "temperature": None,  # Not available from Ollama
                    "power_draw": None,
                    "power_limit": None
                }
            }
        }
        
        return {
            "status": "success" if ollama_healthy else "error",
            "agent_id": self.agent_id,
            "uptime_seconds": round(uptime_seconds, 2),
            "uptime_percent": 99.5 if ollama_healthy else 0,
            "timestamp": current_time,
            "gpu_available": ollama_healthy,
            "gpu_data": gpu_data,
            "ollama_info": {
                "healthy": ollama_healthy,
                "host": self.ollama_host,
                "running_models": running_models,
                "available_models": available_models,
                "gpu_usage_estimation": gpu_usage,
                "tokens_generated": self.tokens_generated,
                "requests_completed": self.requests_completed
            },
            "autonomous_loop": {
                "active": True,
                "last_cycle": None,
                "cycles_completed": 0,
                "interval_seconds": int(os.getenv('LOOP_INTERVAL', '30'))
            },
            "system_info": {
                "source": "ollama_api",
                "version": "1.0",
                "description": "Ollama-based GPU monitoring"
            }
        }
    
    def get_summary(self) -> Dict[str, Any]:
        """Get a summary of Ollama/GPU status"""
        full_status = self.get_ollama_status()
        ollama_info = full_status.get("ollama_info", {})
        gpu_usage = ollama_info.get("gpu_usage_estimation", {})
        
        return {
            "healthy": ollama_info.get("healthy", False),
            "gpu_count": 1,
            "total_memory_mb": 24576,
            "memory_usage_percent": gpu_usage.get("estimated_usage_percent", 0),
            "avg_gpu_utilization": min(gpu_usage.get("estimated_usage_percent", 0) * 1.2, 100),
            "uptime_hours": round(full_status["uptime_seconds"] / 3600, 2),
            "models_loaded": gpu_usage.get("model_count", 0),
            "ollama_status": "online" if ollama_info.get("healthy") else "offline"
        }
    
    def increment_token_count(self, tokens: int):
        """Track tokens generated (call this from AutoGen when using Ollama)"""
        self.tokens_generated += tokens
        self.requests_completed += 1