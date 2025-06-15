"""
GPU Monitoring Module for AutoGen Agent

Provides GPU status monitoring by querying Ollama container stats.
Falls back to mock data if Ollama is not available.
"""

import os
import time
import logging
from typing import Dict, Any, Optional
from datetime import datetime
from .ollama_monitor import OllamaMonitor

logger = logging.getLogger(__name__)

class GPUMonitor:
    """Monitors GPU status and tracks agent uptime"""
    
    def __init__(self):
        """Initialize GPU monitor with uptime tracking"""
        self.start_time = time.time()
        self.agent_id = os.getenv('AGENT_ID', 'autogen-agent-001')
        self.cycle_count = 0
        self.last_cycle_time = None
        
        # Initialize Ollama monitor if Ollama is configured
        self.use_ollama = os.getenv('USE_OLLAMA', 'false').lower() == 'true'
        self.ollama_monitor = None
        
        if self.use_ollama:
            try:
                self.ollama_monitor = OllamaMonitor()
                logger.info("🦙 Ollama monitor initialized successfully")
            except Exception as e:
                logger.warning(f"Failed to initialize Ollama monitor: {e}")
                self.ollama_monitor = None
    
    def get_uptime_seconds(self) -> float:
        """Calculate uptime in seconds since container start"""
        return time.time() - self.start_time
    
    def get_uptime_percent(self) -> float:
        """Calculate uptime percentage (mock: always high for autogen)"""
        # In production, this would calculate actual availability
        # For now, return high uptime for AutoGen agent
        return 99.5
    
    def increment_cycle_count(self):
        """Increment the autonomous loop cycle counter"""
        self.cycle_count += 1
        self.last_cycle_time = time.time()
    
    def get_mock_data(self) -> Dict[str, Any]:
        """Generate mock GPU data for testing"""
        return {
            "count": 1,
            "devices": {
                0: {
                    "device_id": 0,
                    "name": "Mock NVIDIA RTX 4090",
                    "uuid": f"GPU-MOCK-{self.agent_id}",
                    "memory": {
                        "total_mb": 24576,  # 24GB
                        "used_mb": 5500,
                        "free_mb": 19076,
                        "usage_percent": 22.4
                    },
                    "utilization": {
                        "gpu_percent": 15,
                        "memory_percent": 22
                    },
                    "temperature": 45,
                    "power_draw": 75,  # Watts
                    "power_limit": 450  # Watts
                }
            }
        }
    
    
    def get_gpu_status(self) -> Dict[str, Any]:
        """Get complete GPU status including uptime and autonomous loop info"""
        current_time = time.time()
        
        # Try to get data from Ollama first
        if self.use_ollama and self.ollama_monitor:
            try:
                # Get Ollama status
                ollama_status = self.ollama_monitor.get_ollama_status()
                
                # Update with our autonomous loop info
                ollama_status["autonomous_loop"]["active"] = self.last_cycle_time is not None
                ollama_status["autonomous_loop"]["last_cycle"] = self.last_cycle_time
                ollama_status["autonomous_loop"]["cycles_completed"] = self.cycle_count
                
                if self.last_cycle_time:
                    ollama_status["autonomous_loop"]["last_cycle_seconds_ago"] = round(current_time - self.last_cycle_time, 2)
                
                # Override agent_id and uptime with our own
                ollama_status["agent_id"] = self.agent_id
                ollama_status["uptime_seconds"] = round(self.get_uptime_seconds(), 2)
                
                return ollama_status
                
            except Exception as e:
                logger.warning(f"Failed to get Ollama status: {e}")
                # Fall through to mock data
        
        # Fallback to mock data
        uptime_seconds = self.get_uptime_seconds()
        gpu_data = self.get_mock_data()
        
        # Calculate autonomous loop info
        last_cycle_ago = None
        if self.last_cycle_time:
            last_cycle_ago = current_time - self.last_cycle_time
        
        return {
            "status": "success",
            "agent_id": self.agent_id,
            "uptime_seconds": round(uptime_seconds, 2),
            "uptime_percent": self.get_uptime_percent(),
            "timestamp": current_time,
            "gpu_available": True,
            "gpu_data": gpu_data,
            "autonomous_loop": {
                "active": self.last_cycle_time is not None,
                "last_cycle": self.last_cycle_time,
                "last_cycle_seconds_ago": round(last_cycle_ago, 2) if last_cycle_ago else None,
                "cycles_completed": self.cycle_count,
                "interval_seconds": int(os.getenv('LOOP_INTERVAL', '30'))
            },
            "system_info": {
                "source": "mock_data",
                "version": "1.0",
                "description": "AutoGen Agent GPU Monitoring (Mock)"
            }
        }
    
    def get_summary(self) -> Dict[str, Any]:
        """Get a summary of GPU status for quick checks"""
        # If using Ollama, delegate to its summary method
        if self.use_ollama and self.ollama_monitor:
            try:
                summary = self.ollama_monitor.get_summary()
                # Add our autonomous loop info
                summary["autonomous_loop_active"] = self.last_cycle_time is not None
                summary["cycles_completed"] = self.cycle_count
                return summary
            except Exception as e:
                logger.warning(f"Failed to get Ollama summary: {e}")
        
        # Fallback to standard summary
        full_status = self.get_gpu_status()
        
        # Extract key metrics
        gpu_count = full_status["gpu_data"]["count"]
        total_memory_mb = 0
        used_memory_mb = 0
        avg_gpu_util = 0
        
        if gpu_count > 0:
            for device in full_status["gpu_data"]["devices"].values():
                total_memory_mb += device["memory"]["total_mb"]
                used_memory_mb += device["memory"]["used_mb"]
                avg_gpu_util += device["utilization"]["gpu_percent"]
            
            avg_gpu_util /= gpu_count
        
        memory_usage_percent = (used_memory_mb / total_memory_mb * 100) if total_memory_mb > 0 else 0
        
        return {
            "healthy": True,
            "gpu_count": gpu_count,
            "total_memory_mb": total_memory_mb,
            "memory_usage_percent": round(memory_usage_percent, 1),
            "avg_gpu_utilization": round(avg_gpu_util, 1),
            "uptime_hours": round(full_status["uptime_seconds"] / 3600, 2),
            "autonomous_loop_active": full_status["autonomous_loop"]["active"],
            "cycles_completed": full_status["autonomous_loop"]["cycles_completed"]
        }
    
    def cleanup(self):
        """Cleanup resources"""
        # No cleanup needed for Ollama monitoring
        logger.info("GPU monitor cleanup completed")