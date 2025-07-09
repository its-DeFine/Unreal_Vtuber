"""
Capacity Monitor for Unified Stimuli Processing

This module monitors the capacity of both System 1 (S1 Avatar) and System 2 (AutoGen) 
to determine when they can accept new stimuli for processing. This enables intelligent
batching and prevents overwhelming either system.

Key Features:
1. S1 Capacity Detection: Monitors temporary WAV files and TTS processing state
2. S2 Capacity Detection: Monitors AutoGen discussion state and team availability  
3. Real-time capacity reporting with detailed status information
4. Configurable thresholds and monitoring intervals
"""

import os
import glob
import asyncio
import logging
import aiohttp
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, List
from dataclasses import dataclass
from enum import Enum


class CapacityStatus(Enum):
    """Capacity status levels for systems"""
    AVAILABLE = "available"          # Ready to accept new stimuli
    BUSY = "busy"                   # Currently processing, cannot accept new stimuli
    OVERLOADED = "overloaded"       # Too many items in queue/processing
    ERROR = "error"                 # System error or unavailable
    UNKNOWN = "unknown"             # Status cannot be determined


@dataclass
class SystemCapacity:
    """Represents the capacity status of a system"""
    status: CapacityStatus
    current_load: int               # Current number of active tasks
    max_capacity: int               # Maximum concurrent tasks
    last_updated: datetime
    details: Dict[str, Any]         # Additional status details
    estimated_free_time: Optional[float] = None  # Estimated seconds until free


class CapacityMonitor:
    """
    Monitors capacity for both S1 and S2 systems to enable intelligent stimuli consolidation
    """
    
    def __init__(self, 
                 s1_endpoint: str = "http://neurosync:5001",
                 s1_temp_dir: str = "/tmp",
                 s2_max_concurrent: int = 1,
                 monitoring_interval: float = 2.0):
        """
        Initialize capacity monitor
        
        Args:
            s1_endpoint: S1 Avatar endpoint URL
            s1_temp_dir: Directory where S1 stores temporary WAV files
            s2_max_concurrent: Maximum concurrent S2 discussions
            monitoring_interval: How often to check capacity (seconds)
        """
        self.s1_endpoint = s1_endpoint
        self.s1_temp_dir = s1_temp_dir
        self.s2_max_concurrent = s2_max_concurrent
        self.monitoring_interval = monitoring_interval
        
        # Current capacity states
        self.s1_capacity: Optional[SystemCapacity] = None
        self.s2_capacity: Optional[SystemCapacity] = None
        
        # Monitoring state
        self.monitoring_active = False
        self.monitor_task: Optional[asyncio.Task] = None
        
        # S2 tracking
        self.s2_active_discussions: List[Dict[str, Any]] = []
        self.s2_last_activity: Optional[datetime] = None
        
        logging.info("🔍 [CAPACITY_MONITOR] Initialized with S1 endpoint: %s", s1_endpoint)
    
    async def start_monitoring(self):
        """Start continuous capacity monitoring"""
        if self.monitoring_active:
            logging.warning("⚠️ [CAPACITY_MONITOR] Monitoring already active")
            return
        
        self.monitoring_active = True
        self.monitor_task = asyncio.create_task(self._monitoring_loop())
        logging.info("🎯 [CAPACITY_MONITOR] Started continuous monitoring")
    
    async def stop_monitoring(self):
        """Stop capacity monitoring"""
        self.monitoring_active = False
        
        if self.monitor_task and not self.monitor_task.done():
            self.monitor_task.cancel()
            try:
                await self.monitor_task
            except asyncio.CancelledError:
                pass
        
        logging.info("🛑 [CAPACITY_MONITOR] Stopped monitoring")
    
    async def _monitoring_loop(self):
        """Main monitoring loop"""
        while self.monitoring_active:
            try:
                # Check both systems concurrently
                s1_task = asyncio.create_task(self._check_s1_capacity())
                s2_task = asyncio.create_task(self._check_s2_capacity())
                
                s1_capacity, s2_capacity = await asyncio.gather(s1_task, s2_task)
                
                self.s1_capacity = s1_capacity
                self.s2_capacity = s2_capacity
                
                # Log capacity changes
                self._log_capacity_changes()
                
                await asyncio.sleep(self.monitoring_interval)
                
            except Exception as e:
                logging.error("❌ [CAPACITY_MONITOR] Error in monitoring loop: %s", e)
                await asyncio.sleep(self.monitoring_interval)
    
    async def _check_s1_capacity(self) -> SystemCapacity:
        """Check S1 Avatar capacity by monitoring temp WAV files and API status"""
        try:
            current_load = 0
            details = {}
            
            # Method 1: Check for temporary WAV files
            wav_patterns = [
                f"{self.s1_temp_dir}/*.wav",
                f"{self.s1_temp_dir}/temp_*.wav", 
                f"{self.s1_temp_dir}/tts_*.wav",
                "/tmp/*.wav",
                "/tmp/temp_*.wav",
                "/tmp/tts_*.wav"
            ]
            
            temp_files = []
            for pattern in wav_patterns:
                temp_files.extend(glob.glob(pattern))
            
            # Filter recent files (created in last 30 seconds)
            recent_files = []
            cutoff_time = datetime.now().timestamp() - 30
            
            for file_path in temp_files:
                try:
                    if os.path.getctime(file_path) > cutoff_time:
                        recent_files.append(file_path)
                except (OSError, FileNotFoundError):
                    continue
            
            current_load += len(recent_files)
            details["temp_wav_files"] = len(recent_files)
            details["temp_file_paths"] = recent_files[:5]  # First 5 for debugging
            
            # Method 2: Check S1 API status (if available)
            api_status = await self._check_s1_api_status()
            if api_status:
                details.update(api_status)
                if api_status.get("is_processing", False):
                    current_load += 1
            
            # Determine capacity status
            if current_load == 0:
                status = CapacityStatus.AVAILABLE
            elif current_load <= 2:  # Allow up to 2 concurrent items
                status = CapacityStatus.BUSY
            else:
                status = CapacityStatus.OVERLOADED
            
            # Estimate free time based on typical TTS processing time
            estimated_free_time = None
            if current_load > 0:
                estimated_free_time = current_load * 3.0  # ~3 seconds per item
            
            return SystemCapacity(
                status=status,
                current_load=current_load,
                max_capacity=2,  # S1 can handle ~2 concurrent TTS requests
                last_updated=datetime.now(),
                details=details,
                estimated_free_time=estimated_free_time
            )
            
        except Exception as e:
            logging.error("❌ [CAPACITY_MONITOR] Error checking S1 capacity: %s", e)
            return SystemCapacity(
                status=CapacityStatus.ERROR,
                current_load=0,
                max_capacity=2,
                last_updated=datetime.now(),
                details={"error": str(e)}
            )
    
    async def _check_s1_api_status(self) -> Optional[Dict[str, Any]]:
        """Check S1 status via API if available"""
        try:
            status_url = f"{self.s1_endpoint}/status"
            timeout = aiohttp.ClientTimeout(total=2.0)
            
            async with aiohttp.ClientSession(timeout=timeout) as session:
                async with session.get(status_url) as response:
                    if response.status == 200:
                        data = await response.json()
                        return {
                            "api_available": True,
                            "is_processing": data.get("is_processing", False),
                            "queue_size": data.get("queue_size", 0),
                            "last_activity": data.get("last_activity")
                        }
        except:
            # S1 API might not have status endpoint, that's okay
            pass
        
        return {"api_available": False}
    
    async def _check_s2_capacity(self) -> SystemCapacity:
        """Check S2 (AutoGen) capacity by monitoring discussion state"""
        try:
            current_load = len(self.s2_active_discussions)
            details = {
                "active_discussions": current_load,
                "last_activity": self.s2_last_activity.isoformat() if self.s2_last_activity else None
            }
            
            # Check if discussions are stale (older than 5 minutes)
            if self.s2_last_activity:
                stale_time = datetime.now() - timedelta(minutes=5)
                if self.s2_last_activity < stale_time:
                    # Clear stale discussions
                    self.s2_active_discussions.clear()
                    current_load = 0
                    details["cleared_stale_discussions"] = True
            
            # Determine capacity status
            if current_load == 0:
                status = CapacityStatus.AVAILABLE
            elif current_load < self.s2_max_concurrent:
                status = CapacityStatus.BUSY
            else:
                status = CapacityStatus.OVERLOADED
            
            # Estimate free time based on typical AutoGen discussion time
            estimated_free_time = None
            if current_load > 0:
                estimated_free_time = current_load * 15.0  # ~15 seconds per discussion
            
            return SystemCapacity(
                status=status,
                current_load=current_load,
                max_capacity=self.s2_max_concurrent,
                last_updated=datetime.now(),
                details=details,
                estimated_free_time=estimated_free_time
            )
            
        except Exception as e:
            logging.error("❌ [CAPACITY_MONITOR] Error checking S2 capacity: %s", e)
            return SystemCapacity(
                status=CapacityStatus.ERROR,
                current_load=0,
                max_capacity=self.s2_max_concurrent,
                last_updated=datetime.now(),
                details={"error": str(e)}
            )
    
    def register_s2_discussion_start(self, discussion_id: str, metadata: Optional[Dict[str, Any]] = None):
        """Register that an S2 discussion has started"""
        discussion = {
            "id": discussion_id,
            "started_at": datetime.now(),
            "metadata": metadata or {}
        }
        
        self.s2_active_discussions.append(discussion)
        self.s2_last_activity = datetime.now()
        
        logging.info("📝 [CAPACITY_MONITOR] S2 discussion started: %s", discussion_id)
    
    def register_s2_discussion_end(self, discussion_id: str):
        """Register that an S2 discussion has ended"""
        self.s2_active_discussions = [
            d for d in self.s2_active_discussions 
            if d["id"] != discussion_id
        ]
        self.s2_last_activity = datetime.now()
        
        logging.info("✅ [CAPACITY_MONITOR] S2 discussion ended: %s", discussion_id)
    
    def get_combined_capacity(self) -> Dict[str, Any]:
        """Get combined capacity status for both systems"""
        if not self.s1_capacity or not self.s2_capacity:
            return {
                "overall_status": "unknown",
                "can_accept_stimuli": False,
                "reason": "Capacity monitoring not initialized"
            }
        
        # Determine overall capacity
        s1_available = self.s1_capacity.status in [CapacityStatus.AVAILABLE, CapacityStatus.BUSY]
        s2_available = self.s2_capacity.status in [CapacityStatus.AVAILABLE, CapacityStatus.BUSY]
        
        can_accept_stimuli = s1_available or s2_available
        
        # Determine overall status
        if self.s1_capacity.status == CapacityStatus.AVAILABLE and self.s2_capacity.status == CapacityStatus.AVAILABLE:
            overall_status = "fully_available"
        elif can_accept_stimuli:
            overall_status = "partially_available"
        else:
            overall_status = "unavailable"
        
        return {
            "overall_status": overall_status,
            "can_accept_stimuli": can_accept_stimuli,
            "s1_capacity": {
                "status": self.s1_capacity.status.value,
                "current_load": self.s1_capacity.current_load,
                "max_capacity": self.s1_capacity.max_capacity,
                "estimated_free_time": self.s1_capacity.estimated_free_time
            },
            "s2_capacity": {
                "status": self.s2_capacity.status.value,
                "current_load": self.s2_capacity.current_load,
                "max_capacity": self.s2_capacity.max_capacity,
                "estimated_free_time": self.s2_capacity.estimated_free_time
            },
            "recommendations": self._get_capacity_recommendations()
        }
    
    def _get_capacity_recommendations(self) -> Dict[str, Any]:
        """Get recommendations based on current capacity"""
        recommendations = {
            "preferred_system": None,
            "max_batch_size": 0,
            "wait_time": 0,
            "actions": []
        }
        
        if not self.s1_capacity or not self.s2_capacity:
            return recommendations
        
        # Determine preferred system
        if self.s1_capacity.status == CapacityStatus.AVAILABLE:
            if self.s2_capacity.status == CapacityStatus.AVAILABLE:
                recommendations["preferred_system"] = "both"
                recommendations["max_batch_size"] = 3
            else:
                recommendations["preferred_system"] = "s1"
                recommendations["max_batch_size"] = 2
        elif self.s2_capacity.status == CapacityStatus.AVAILABLE:
            recommendations["preferred_system"] = "s2"
            recommendations["max_batch_size"] = 1
        else:
            # Both busy, calculate wait time
            s1_wait = self.s1_capacity.estimated_free_time or 0
            s2_wait = self.s2_capacity.estimated_free_time or 0
            recommendations["wait_time"] = min(s1_wait, s2_wait)
            recommendations["preferred_system"] = "s1" if s1_wait <= s2_wait else "s2"
        
        # Add action recommendations
        if recommendations["preferred_system"]:
            recommendations["actions"].append(f"Process with {recommendations['preferred_system']}")
        
        if recommendations["wait_time"] > 0:
            recommendations["actions"].append(f"Wait {recommendations['wait_time']:.1f}s for capacity")
        
        return recommendations
    
    def _log_capacity_changes(self):
        """Log significant capacity changes"""
        if not hasattr(self, '_last_logged_status'):
            self._last_logged_status = {}
        
        current_status = {
            "s1": self.s1_capacity.status.value if self.s1_capacity else "unknown",
            "s2": self.s2_capacity.status.value if self.s2_capacity else "unknown"
        }
        
        if current_status != self._last_logged_status:
            logging.info("📊 [CAPACITY_MONITOR] Status: S1=%s, S2=%s", 
                        current_status["s1"], current_status["s2"])
            self._last_logged_status = current_status
    
    def get_detailed_status(self) -> Dict[str, Any]:
        """Get detailed status for debugging and monitoring"""
        return {
            "monitoring_active": self.monitoring_active,
            "s1_capacity": {
                "status": self.s1_capacity.status.value if self.s1_capacity else "unknown",
                "details": self.s1_capacity.details if self.s1_capacity else {},
                "last_updated": self.s1_capacity.last_updated.isoformat() if self.s1_capacity else None
            },
            "s2_capacity": {
                "status": self.s2_capacity.status.value if self.s2_capacity else "unknown", 
                "details": self.s2_capacity.details if self.s2_capacity else {},
                "last_updated": self.s2_capacity.last_updated.isoformat() if self.s2_capacity else None
            },
            "s2_discussions": [
                {
                    "id": d["id"],
                    "started_at": d["started_at"].isoformat(),
                    "duration": (datetime.now() - d["started_at"]).total_seconds()
                }
                for d in self.s2_active_discussions
            ],
            "combined_capacity": self.get_combined_capacity()
        }


# Global capacity monitor instance
global_capacity_monitor: Optional[CapacityMonitor] = None


def get_capacity_monitor() -> Optional[CapacityMonitor]:
    """Get the global capacity monitor instance"""
    return global_capacity_monitor


def initialize_capacity_monitor(**kwargs) -> CapacityMonitor:
    """Initialize the global capacity monitor"""
    global global_capacity_monitor
    
    if global_capacity_monitor:
        logging.warning("⚠️ [CAPACITY_MONITOR] Monitor already initialized")
        return global_capacity_monitor
    
    global_capacity_monitor = CapacityMonitor(**kwargs)
    logging.info("✅ [CAPACITY_MONITOR] Global monitor initialized")
    return global_capacity_monitor


def get_current_capacity(self) -> float:
    """Get current system capacity as percentage"""
    # Get combined capacity
    combined = self.get_combined_capacity()
    
    # Calculate overall capacity percentage
    if combined["overall_status"] == "fully_available":
        return 100.0
    elif combined["overall_status"] == "partially_available":
        # Calculate based on load
        s1_cap = combined["s1_capacity"]
        s2_cap = combined["s2_capacity"]
        
        s1_percent = (1 - s1_cap["current_load"] / s1_cap["max_capacity"]) * 100 if s1_cap["max_capacity"] > 0 else 0
        s2_percent = (1 - s2_cap["current_load"] / s2_cap["max_capacity"]) * 100 if s2_cap["max_capacity"] > 0 else 0
        
        # Average of both systems
        return (s1_percent + s2_percent) / 2
    else:
        return 0.0


# Add method to CapacityMonitor class
CapacityMonitor.get_current_capacity = get_current_capacity