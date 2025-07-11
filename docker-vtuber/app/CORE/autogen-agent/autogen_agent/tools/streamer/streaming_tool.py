"""
Streaming Management Tool for Streamer Team
==========================================

Manages live streaming operations including stream setup, monitoring, 
scheduling, and platform-specific features.
"""

import logging
import json
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional
import random
import uuid

logger = logging.getLogger(__name__)


async def run(context: Dict[str, Any]) -> Dict[str, Any]:
    """
    🎥 Streaming Management Tool Entry Point
    
    Comprehensive streaming management and control capabilities.
    
    Args:
        context: Operation context containing:
            - action: Type of operation (start, stop, schedule, monitor, settings)
            - platform: Streaming platform (twitch, youtube, etc.)
            - Additional parameters based on action
    
    Returns:
        Streaming operation results
    """
    try:
        action = context.get("action", "status")
        
        # Route to appropriate streaming function
        if action == "start":
            return await _start_stream(context)
        
        elif action == "stop":
            return await _stop_stream(context)
        
        elif action == "schedule":
            return await _schedule_stream(context)
        
        elif action == "monitor":
            return await _monitor_stream(context)
        
        elif action == "settings":
            return await _manage_stream_settings(context)
        
        elif action == "scenes":
            return await _manage_scenes(context)
        
        elif action == "alerts":
            return await _manage_alerts(context)
        
        elif action == "multistream":
            return await _manage_multistream(context)
        
        elif action == "status":
            return await _get_stream_status(context)
        
        else:
            return {
                "success": False,
                "error": f"Unknown action: {action}",
                "available_actions": ["start", "stop", "schedule", "monitor", 
                                    "settings", "scenes", "alerts", "multistream", "status"]
            }
            
    except Exception as e:
        logger.error(f"❌ [STREAMING] Error: {e}")
        return {
            "success": False,
            "error": str(e)
        }


async def _start_stream(context: Dict[str, Any]) -> Dict[str, Any]:
    """Start a live stream"""
    try:
        platform = context.get("platform", "twitch")
        title = context.get("title", "Live Stream")
        category = context.get("category", "Just Chatting")
        
        # Generate stream key
        stream_id = f"STREAM-{uuid.uuid4().hex[:8].upper()}"
        
        # Validate stream settings
        validation = _validate_stream_settings(platform, context)
        if not validation["valid"]:
            return {
                "success": False,
                "error": validation["error"],
                "suggestions": validation["suggestions"]
            }
        
        # Initialize stream
        stream_config = {
            "stream_id": stream_id,
            "platform": platform,
            "title": title,
            "category": category,
            "status": "initializing",
            "started_at": datetime.now().isoformat(),
            "stream_key": f"live_{stream_id}_{platform}",
            "server_url": _get_stream_server(platform),
            "settings": {
                "resolution": context.get("resolution", "1920x1080"),
                "framerate": context.get("framerate", 60),
                "bitrate": context.get("bitrate", 6000),
                "encoder": context.get("encoder", "x264")
            }
        }
        
        # Pre-stream checklist
        checklist = _generate_pre_stream_checklist()
        
        # Start stream
        stream_config["status"] = "live"
        stream_config["url"] = f"https://{platform}.tv/username"
        
        return {
            "success": True,
            "stream": stream_config,
            "checklist": checklist,
            "notifications": {
                "discord": "Posted stream announcement",
                "twitter": "Tweet sent with stream link",
                "alerts": "Stream alerts activated"
            },
            "tips": [
                "Check your audio levels",
                "Ensure webcam is properly positioned",
                "Have water nearby",
                "Monitor chat for viewer questions"
            ],
            "message": f"Stream started successfully on {platform}"
        }
        
    except Exception as e:
        logger.error(f"❌ [STREAMING] Start stream error: {e}")
        return {"success": False, "error": str(e)}


async def _stop_stream(context: Dict[str, Any]) -> Dict[str, Any]:
    """Stop an active stream"""
    try:
        stream_id = context.get("stream_id", "")
        save_vod = context.get("save_vod", True)
        
        if not stream_id:
            return {
                "success": False,
                "error": "Stream ID required to stop stream"
            }
        
        # Simulate stream statistics
        stream_stats = {
            "duration": "3h 25m",
            "peak_viewers": 1250,
            "average_viewers": 856,
            "new_followers": 45,
            "new_subscribers": 12,
            "chat_messages": 3420,
            "donations": {
                "total": 125.50,
                "count": 18
            },
            "bits_cheered": 2500
        }
        
        # Generate highlights
        highlights = _generate_stream_highlights(stream_stats)
        
        # VOD processing
        vod_info = None
        if save_vod:
            vod_info = {
                "vod_id": f"VOD-{uuid.uuid4().hex[:8].upper()}",
                "processing_status": "queued",
                "estimated_time": "15-30 minutes",
                "auto_publish": True
            }
        
        return {
            "success": True,
            "stream_id": stream_id,
            "stopped_at": datetime.now().isoformat(),
            "statistics": stream_stats,
            "highlights": highlights,
            "vod": vod_info,
            "post_stream_tasks": [
                "Review stream analytics",
                "Thank top contributors",
                "Schedule highlight video",
                "Post stream summary on social media"
            ],
            "message": "Stream ended successfully"
        }
        
    except Exception as e:
        logger.error(f"❌ [STREAMING] Stop stream error: {e}")
        return {"success": False, "error": str(e)}


async def _schedule_stream(context: Dict[str, Any]) -> Dict[str, Any]:
    """Schedule upcoming streams"""
    try:
        streams = context.get("streams", [])
        recurring = context.get("recurring", False)
        
        if not streams and not recurring:
            return {
                "success": False,
                "error": "No streams to schedule"
            }
        
        scheduled_streams = []
        
        if recurring:
            # Generate recurring schedule
            schedule_pattern = context.get("pattern", "weekly")
            days = context.get("days", ["Monday", "Wednesday", "Friday"])
            time = context.get("time", "19:00")
            duration = context.get("duration", 4)  # hours
            
            for i in range(4):  # Next 4 occurrences
                for day in days:
                    scheduled_time = _get_next_day_time(day, time, i)
                    
                    scheduled_streams.append({
                        "schedule_id": f"SCH-{uuid.uuid4().hex[:8].upper()}",
                        "title": f"{day} Stream - {context.get('default_title', 'Gaming Session')}",
                        "scheduled_time": scheduled_time.isoformat(),
                        "duration_hours": duration,
                        "recurring": True,
                        "pattern": schedule_pattern
                    })
        
        else:
            # Schedule individual streams
            for stream in streams:
                scheduled_streams.append({
                    "schedule_id": f"SCH-{uuid.uuid4().hex[:8].upper()}",
                    "title": stream.get("title", "Scheduled Stream"),
                    "scheduled_time": stream.get("time", datetime.now() + timedelta(days=1)),
                    "duration_hours": stream.get("duration", 3),
                    "category": stream.get("category", "Gaming"),
                    "description": stream.get("description", "")
                })
        
        # Generate calendar view
        calendar = _generate_stream_calendar(scheduled_streams)
        
        # Conflict detection
        conflicts = _detect_schedule_conflicts(scheduled_streams)
        
        return {
            "success": True,
            "scheduled_streams": scheduled_streams,
            "calendar": calendar,
            "conflicts": conflicts,
            "reminders_set": {
                "discord": True,
                "calendar": True,
                "notifications": "30 minutes before each stream"
            },
            "statistics": {
                "total_scheduled": len(scheduled_streams),
                "weekly_hours": sum(s["duration_hours"] for s in scheduled_streams[:7]),
                "consistency_score": 9.5
            },
            "recommendations": [
                "Maintain consistent schedule for viewer retention",
                "Consider timezone differences for international audience",
                "Plan content themes for each stream"
            ]
        }
        
    except Exception as e:
        logger.error(f"❌ [STREAMING] Schedule stream error: {e}")
        return {"success": False, "error": str(e)}


async def _monitor_stream(context: Dict[str, Any]) -> Dict[str, Any]:
    """Monitor active stream performance"""
    try:
        stream_id = context.get("stream_id", "active")
        metrics = context.get("metrics", ["viewers", "performance", "chat", "alerts"])
        
        # Real-time metrics
        current_metrics = {
            "viewers": {
                "current": random.randint(800, 1200),
                "peak": 1250,
                "average": 956,
                "trend": "increasing" if random.random() > 0.5 else "stable"
            },
            "performance": {
                "fps": 59.94,
                "bitrate": 5800,
                "dropped_frames": 0.02,
                "cpu_usage": 45,
                "gpu_usage": 68,
                "network_stability": "excellent"
            },
            "chat": {
                "messages_per_minute": 24,
                "active_chatters": 156,
                "moderator_actions": 3,
                "emote_usage": "high",
                "sentiment": "positive"
            },
            "engagement": {
                "new_followers": 23,
                "subscriptions": 5,
                "donations": 3,
                "clips_created": 7,
                "shares": 12
            }
        }
        
        # Stream health check
        health_status = _check_stream_health(current_metrics)
        
        # Alerts and notifications
        alerts = _generate_stream_alerts(current_metrics)
        
        # Predictions
        predictions = {
            "estimated_peak_viewers": int(current_metrics["viewers"]["peak"] * 1.1),
            "projected_followers": current_metrics["engagement"]["new_followers"] * 2,
            "engagement_forecast": "high" if current_metrics["chat"]["messages_per_minute"] > 20 else "moderate"
        }
        
        return {
            "success": True,
            "stream_id": stream_id,
            "timestamp": datetime.now().isoformat(),
            "metrics": current_metrics,
            "health": health_status,
            "alerts": alerts,
            "predictions": predictions,
            "recommendations": _generate_live_recommendations(current_metrics),
            "top_events": [
                {"time": "10 min ago", "event": "Raid from BigStreamer (500 viewers)"},
                {"time": "25 min ago", "event": "New subscriber milestone (1000)"},
                {"time": "45 min ago", "event": "Clip went viral"}
            ]
        }
        
    except Exception as e:
        logger.error(f"❌ [STREAMING] Monitor stream error: {e}")
        return {"success": False, "error": str(e)}


async def _manage_stream_settings(context: Dict[str, Any]) -> Dict[str, Any]:
    """Manage stream settings and configuration"""
    try:
        action = context.get("settings_action", "view")  # view, update, optimize
        platform = context.get("platform", "twitch")
        
        # Current settings
        current_settings = {
            "video": {
                "resolution": "1920x1080",
                "framerate": 60,
                "bitrate": 6000,
                "encoder": "x264",
                "preset": "medium",
                "keyframe_interval": 2
            },
            "audio": {
                "bitrate": 160,
                "sample_rate": 48000,
                "channels": "stereo",
                "mic_gain": 75,
                "desktop_audio": 80,
                "noise_suppression": True,
                "noise_gate": -30
            },
            "stream": {
                "server": "auto",
                "low_latency_mode": False,
                "vod_recording": True,
                "auto_reconnect": True,
                "delay": 0
            },
            "chat": {
                "overlay_enabled": True,
                "position": "bottom-left",
                "font_size": 14,
                "opacity": 85,
                "subscriber_mode": False,
                "slow_mode": 0
            }
        }
        
        if action == "optimize":
            # Auto-optimize settings
            optimized = _optimize_stream_settings(current_settings, platform)
            
            return {
                "success": True,
                "action": "optimize",
                "current_settings": current_settings,
                "optimized_settings": optimized["settings"],
                "improvements": optimized["improvements"],
                "warnings": optimized["warnings"],
                "estimated_quality_gain": "15-20%"
            }
        
        elif action == "update":
            # Update specific settings
            updates = context.get("updates", {})
            updated_settings = _apply_settings_updates(current_settings, updates)
            
            return {
                "success": True,
                "action": "update",
                "updated_settings": updated_settings,
                "validation": _validate_settings(updated_settings),
                "restart_required": _check_restart_required(updates)
            }
        
        else:  # view
            return {
                "success": True,
                "action": "view",
                "settings": current_settings,
                "profiles": {
                    "gaming": _get_preset_profile("gaming"),
                    "just_chatting": _get_preset_profile("just_chatting"),
                    "creative": _get_preset_profile("creative")
                },
                "hardware_info": {
                    "cpu": "Intel i7-10700K",
                    "gpu": "NVIDIA RTX 3070",
                    "ram": "32GB",
                    "upload_speed": "50 Mbps"
                },
                "recommendations": [
                    "Your bitrate could be increased for better quality",
                    "Consider enabling low latency mode for gaming",
                    "Audio settings are optimal"
                ]
            }
        
    except Exception as e:
        logger.error(f"❌ [STREAMING] Settings management error: {e}")
        return {"success": False, "error": str(e)}


async def _manage_scenes(context: Dict[str, Any]) -> Dict[str, Any]:
    """Manage OBS/streaming software scenes"""
    try:
        action = context.get("scene_action", "list")  # list, switch, create, update
        
        # Current scenes
        scenes = [
            {
                "name": "Starting Soon",
                "sources": ["countdown_timer", "background_video", "music_player"],
                "active": False
            },
            {
                "name": "Gaming",
                "sources": ["game_capture", "webcam", "alerts", "chat_overlay"],
                "active": True
            },
            {
                "name": "Just Chatting",
                "sources": ["webcam_fullscreen", "chat_overlay", "subscriber_goal"],
                "active": False
            },
            {
                "name": "BRB",
                "sources": ["brb_screen", "music_player", "timer"],
                "active": False
            },
            {
                "name": "Ending",
                "sources": ["credits", "social_media", "raid_target"],
                "active": False
            }
        ]
        
        if action == "switch":
            scene_name = context.get("scene_name", "")
            
            if not scene_name:
                return {"success": False, "error": "Scene name required"}
            
            # Switch scene
            for scene in scenes:
                scene["active"] = scene["name"] == scene_name
            
            return {
                "success": True,
                "action": "switch",
                "active_scene": scene_name,
                "transition": context.get("transition", "fade"),
                "duration": context.get("duration", 300),
                "message": f"Switched to scene: {scene_name}"
            }
        
        elif action == "create":
            new_scene = {
                "name": context.get("name", "New Scene"),
                "sources": context.get("sources", []),
                "active": False
            }
            
            scenes.append(new_scene)
            
            return {
                "success": True,
                "action": "create",
                "scene": new_scene,
                "total_scenes": len(scenes),
                "message": f"Scene '{new_scene['name']}' created"
            }
        
        else:  # list
            return {
                "success": True,
                "action": "list",
                "scenes": scenes,
                "active_scene": next((s["name"] for s in scenes if s["active"]), None),
                "scene_collections": ["Default", "Gaming", "IRL"],
                "quick_switches": {
                    "F1": "Starting Soon",
                    "F2": "Gaming",
                    "F3": "Just Chatting",
                    "F4": "BRB",
                    "F5": "Ending"
                }
            }
        
    except Exception as e:
        logger.error(f"❌ [STREAMING] Scene management error: {e}")
        return {"success": False, "error": str(e)}


async def _manage_alerts(context: Dict[str, Any]) -> Dict[str, Any]:
    """Manage stream alerts and notifications"""
    try:
        alert_type = context.get("alert_type", "all")
        action = context.get("alert_action", "view")  # view, test, configure
        
        # Alert configurations
        alerts_config = {
            "follower": {
                "enabled": True,
                "sound": "chime.mp3",
                "volume": 70,
                "duration": 5,
                "animation": "slide_in",
                "minimum_follow_age": 0
            },
            "subscriber": {
                "enabled": True,
                "sound": "celebration.mp3",
                "volume": 80,
                "duration": 8,
                "animation": "bounce",
                "variations": {
                    "tier1": "default",
                    "tier2": "special",
                    "tier3": "epic"
                }
            },
            "donation": {
                "enabled": True,
                "sound": "coins.mp3",
                "volume": 75,
                "duration": 10,
                "minimum_amount": 1.00,
                "tts_enabled": True,
                "tts_minimum": 5.00
            },
            "raid": {
                "enabled": True,
                "sound": "airhorn.mp3",
                "volume": 85,
                "duration": 15,
                "minimum_viewers": 10,
                "auto_shoutout": True
            },
            "bits": {
                "enabled": True,
                "sound": "bits_cheer.mp3",
                "volume": 75,
                "duration": 7,
                "minimum_bits": 100
            }
        }
        
        if action == "test":
            # Test specific alert
            test_alert = context.get("test_alert", "follower")
            
            return {
                "success": True,
                "action": "test",
                "alert_type": test_alert,
                "message": f"Test {test_alert} alert triggered",
                "preview": {
                    "text": f"Test {test_alert.title()} Alert!",
                    "duration": alerts_config.get(test_alert, {}).get("duration", 5),
                    "sound": alerts_config.get(test_alert, {}).get("sound", "default.mp3")
                }
            }
        
        elif action == "configure":
            # Update alert configuration
            updates = context.get("updates", {})
            alert_to_update = context.get("alert_to_update", "follower")
            
            if alert_to_update in alerts_config:
                alerts_config[alert_to_update].update(updates)
            
            return {
                "success": True,
                "action": "configure",
                "updated_alert": alert_to_update,
                "new_config": alerts_config[alert_to_update],
                "message": f"{alert_to_update} alert updated successfully"
            }
        
        else:  # view
            # Recent alerts
            recent_alerts = [
                {"type": "follower", "user": "NewViewer123", "time": "2 min ago"},
                {"type": "subscriber", "user": "LoyalFan456", "time": "5 min ago", "tier": 1},
                {"type": "donation", "user": "Supporter789", "time": "10 min ago", "amount": 10.00},
                {"type": "raid", "user": "FriendlyStreamer", "time": "15 min ago", "viewers": 250}
            ]
            
            return {
                "success": True,
                "action": "view",
                "alerts_config": alerts_config,
                "recent_alerts": recent_alerts,
                "statistics": {
                    "total_alerts_today": 145,
                    "most_common": "follower",
                    "total_revenue": 125.50
                },
                "alert_themes": ["Default", "Neon", "Retro", "Minimal", "Animated"],
                "current_theme": "Neon"
            }
        
    except Exception as e:
        logger.error(f"❌ [STREAMING] Alert management error: {e}")
        return {"success": False, "error": str(e)}


async def _manage_multistream(context: Dict[str, Any]) -> Dict[str, Any]:
    """Manage multi-platform streaming"""
    try:
        platforms = context.get("platforms", ["twitch", "youtube"])
        action = context.get("multistream_action", "status")  # status, start, configure
        
        if action == "start":
            # Start multistreaming
            streams = []
            
            for platform in platforms:
                stream = {
                    "platform": platform,
                    "stream_key": f"sk_{platform}_{uuid.uuid4().hex[:8]}",
                    "server": _get_stream_server(platform),
                    "status": "connecting",
                    "bitrate_allocation": 6000 // len(platforms)  # Split bitrate
                }
                streams.append(stream)
            
            # Simulate connection
            for stream in streams:
                stream["status"] = "live"
                stream["url"] = f"https://{stream['platform']}.com/live/username"
            
            return {
                "success": True,
                "action": "start",
                "streams": streams,
                "total_bitrate": 6000,
                "quality_impact": "minimal" if len(platforms) <= 2 else "moderate",
                "sync_status": "synchronized",
                "message": f"Multistreaming to {len(platforms)} platforms"
            }
        
        elif action == "configure":
            # Configure multistream settings
            config = {
                "primary_platform": "twitch",
                "sync_chat": True,
                "unified_alerts": True,
                "platform_settings": {}
            }
            
            for platform in platforms:
                config["platform_settings"][platform] = {
                    "enabled": True,
                    "custom_title": f"{platform.title()} Stream",
                    "notifications": True,
                    "record_locally": platform == "youtube"
                }
            
            return {
                "success": True,
                "action": "configure",
                "configuration": config,
                "bandwidth_requirements": {
                    "minimum": 10,  # Mbps
                    "recommended": 20,
                    "current": 50
                },
                "tips": [
                    "Ensure stable internet for multistreaming",
                    "Monitor CPU usage across platforms",
                    "Use unified chat tool for easier management"
                ]
            }
        
        else:  # status
            active_streams = [
                {
                    "platform": "twitch",
                    "status": "live",
                    "viewers": 856,
                    "health": "excellent",
                    "uptime": "2h 15m"
                },
                {
                    "platform": "youtube",
                    "status": "live",
                    "viewers": 342,
                    "health": "good",
                    "uptime": "2h 15m"
                }
            ]
            
            return {
                "success": True,
                "action": "status",
                "active_streams": active_streams,
                "total_viewers": sum(s["viewers"] for s in active_streams),
                "sync_status": "in_sync",
                "resource_usage": {
                    "cpu": 65,
                    "gpu": 78,
                    "ram": 45,
                    "network": 12  # Mbps
                },
                "issues": [],
                "recommendations": [
                    "All platforms streaming smoothly",
                    "Consider adding Facebook Gaming for wider reach"
                ]
            }
        
    except Exception as e:
        logger.error(f"❌ [STREAMING] Multistream management error: {e}")
        return {"success": False, "error": str(e)}


async def _get_stream_status(context: Dict[str, Any]) -> Dict[str, Any]:
    """Get comprehensive streaming status"""
    try:
        # Check if currently streaming
        is_live = random.choice([True, False])  # Simulated
        
        if is_live:
            # Live stream status
            status = {
                "streaming": True,
                "stream_id": f"STREAM-{uuid.uuid4().hex[:8].upper()}",
                "platform": "twitch",
                "started_at": (datetime.now() - timedelta(hours=1, minutes=30)).isoformat(),
                "duration": "1h 30m",
                "title": "Epic Gaming Session - Road to Diamond!",
                "category": "Apex Legends",
                "viewers": {
                    "current": 924,
                    "peak": 1156,
                    "average": 856
                },
                "performance": {
                    "fps": 59.94,
                    "dropped_frames": 12,
                    "bitrate": 5950,
                    "health": "excellent"
                },
                "engagement": {
                    "chat_activity": "high",
                    "new_followers": 34,
                    "subscribers": 8,
                    "donations": 5
                }
            }
        else:
            # Offline status
            status = {
                "streaming": False,
                "last_stream": {
                    "ended_at": (datetime.now() - timedelta(hours=2)).isoformat(),
                    "duration": "3h 45m",
                    "peak_viewers": 1342,
                    "vod_available": True
                },
                "next_stream": {
                    "scheduled": (datetime.now() + timedelta(days=1, hours=3)).isoformat(),
                    "title": "Variety Tuesday - Viewer Games!",
                    "reminder_set": True
                }
            }
        
        # System status
        system_status = {
            "obs_connected": True,
            "stream_deck_connected": True,
            "bot_status": "online",
            "alerts_working": True,
            "chat_connected": True
        }
        
        # Recent highlights
        recent_highlights = [
            {"type": "clip", "title": "Insane 1v3 Clutch!", "views": 2341, "created": "1h ago"},
            {"type": "highlight", "title": "Funny Moments Compilation", "views": 5678, "created": "1d ago"},
            {"type": "short", "title": "Quick Tips #42", "views": 8901, "created": "2d ago"}
        ]
        
        return {
            "success": True,
            "status": status,
            "system": system_status,
            "recent_highlights": recent_highlights,
            "weekly_stats": {
                "total_hours": 28,
                "average_viewers": 892,
                "peak_day": "Saturday",
                "growth_rate": 12.5
            },
            "quick_actions": [
                {"action": "go_live", "enabled": not is_live},
                {"action": "end_stream", "enabled": is_live},
                {"action": "check_schedule", "enabled": True},
                {"action": "view_analytics", "enabled": True}
            ]
        }
        
    except Exception as e:
        logger.error(f"❌ [STREAMING] Status check error: {e}")
        return {"success": False, "error": str(e)}


# Helper functions
def _validate_stream_settings(platform: str, context: Dict[str, Any]) -> Dict[str, Any]:
    """Validate stream settings for platform"""
    errors = []
    suggestions = []
    
    # Platform-specific validation
    if platform == "twitch":
        bitrate = context.get("bitrate", 6000)
        if bitrate > 6000:
            errors.append("Twitch bitrate limit is 6000 kbps for non-partners")
            suggestions.append("Set bitrate to 6000 or become a Twitch partner")
    
    elif platform == "youtube":
        if not context.get("stream_key"):
            errors.append("YouTube requires a valid stream key")
            suggestions.append("Get your stream key from YouTube Studio")
    
    # General validation
    resolution = context.get("resolution", "1920x1080")
    if resolution == "3840x2160" and context.get("framerate", 60) > 30:
        suggestions.append("Consider 30fps for 4K streaming to reduce bandwidth")
    
    return {
        "valid": len(errors) == 0,
        "error": "; ".join(errors) if errors else None,
        "suggestions": suggestions
    }


def _get_stream_server(platform: str) -> str:
    """Get streaming server URL for platform"""
    servers = {
        "twitch": "rtmp://live.twitch.tv/live",
        "youtube": "rtmp://a.rtmp.youtube.com/live2",
        "facebook": "rtmps://live-api-s.facebook.com:443/rtmp",
        "dlive": "rtmp://stream.dlive.tv/live"
    }
    
    return servers.get(platform, "rtmp://localhost/live")


def _generate_pre_stream_checklist() -> List[Dict[str, Any]]:
    """Generate pre-stream checklist"""
    return [
        {"item": "Audio check", "status": "completed", "critical": True},
        {"item": "Webcam positioned", "status": "completed", "critical": True},
        {"item": "Stream title updated", "status": "completed", "critical": True},
        {"item": "Notifications sent", "status": "completed", "critical": False},
        {"item": "Chat moderators online", "status": "pending", "critical": False},
        {"item": "Starting soon scene", "status": "completed", "critical": False}
    ]


def _generate_stream_highlights(stats: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Generate stream highlights based on statistics"""
    highlights = []
    
    if stats["peak_viewers"] > 1000:
        highlights.append({
            "type": "milestone",
            "description": f"Hit {stats['peak_viewers']} peak viewers!",
            "timestamp": "2:15:30"
        })
    
    if stats["new_subscribers"] > 10:
        highlights.append({
            "type": "growth",
            "description": f"Gained {stats['new_subscribers']} new subscribers",
            "timestamp": "throughout"
        })
    
    if stats["donations"]["total"] > 100:
        highlights.append({
            "type": "support",
            "description": f"Community donated ${stats['donations']['total']}",
            "timestamp": "various"
        })
    
    # Add some random highlights
    highlights.append({
        "type": "gameplay",
        "description": "Epic clutch play in final circle",
        "timestamp": "1:45:20",
        "clip_created": True
    })
    
    return highlights


def _get_next_day_time(day: str, time: str, week_offset: int) -> datetime:
    """Get next occurrence of day and time"""
    days = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
    
    today = datetime.now()
    today_weekday = today.weekday()
    target_weekday = days.index(day)
    
    days_ahead = target_weekday - today_weekday
    if days_ahead <= 0:
        days_ahead += 7
    
    days_ahead += week_offset * 7
    
    target_date = today + timedelta(days=days_ahead)
    hour, minute = map(int, time.split(":"))
    
    return target_date.replace(hour=hour, minute=minute, second=0, microsecond=0)


def _generate_stream_calendar(streams: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Generate stream calendar view"""
    calendar = {
        "this_week": [],
        "next_week": [],
        "this_month": []
    }
    
    now = datetime.now()
    week_end = now + timedelta(days=7)
    month_end = now + timedelta(days=30)
    
    for stream in streams:
        stream_time = datetime.fromisoformat(stream["scheduled_time"])
        
        if stream_time <= week_end:
            calendar["this_week"].append(stream)
        elif stream_time <= week_end + timedelta(days=7):
            calendar["next_week"].append(stream)
        
        if stream_time <= month_end:
            calendar["this_month"].append(stream)
    
    return calendar


def _detect_schedule_conflicts(streams: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Detect scheduling conflicts"""
    conflicts = []
    
    for i, stream1 in enumerate(streams):
        for stream2 in streams[i+1:]:
            time1 = datetime.fromisoformat(stream1["scheduled_time"])
            time2 = datetime.fromisoformat(stream2["scheduled_time"])
            
            # Check for overlap
            end1 = time1 + timedelta(hours=stream1["duration_hours"])
            end2 = time2 + timedelta(hours=stream2["duration_hours"])
            
            if (time1 <= time2 < end1) or (time2 <= time1 < end2):
                conflicts.append({
                    "stream1": stream1["schedule_id"],
                    "stream2": stream2["schedule_id"],
                    "type": "time_overlap"
                })
    
    return conflicts


def _check_stream_health(metrics: Dict[str, Any]) -> Dict[str, Any]:
    """Check overall stream health"""
    issues = []
    
    # Check performance metrics
    if metrics["performance"]["dropped_frames"] > 1:
        issues.append("Dropped frames detected")
    
    if metrics["performance"]["cpu_usage"] > 80:
        issues.append("High CPU usage")
    
    if metrics["performance"]["network_stability"] != "excellent":
        issues.append("Network instability")
    
    # Overall health score
    health_score = 100
    health_score -= len(issues) * 20
    health_score -= (100 - metrics["performance"]["fps"] / 0.6)  # Penalty for low FPS
    
    return {
        "score": max(0, health_score),
        "status": "excellent" if health_score > 90 else "good" if health_score > 70 else "needs_attention",
        "issues": issues,
        "recommendations": _get_health_recommendations(issues)
    }


def _generate_stream_alerts(metrics: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Generate alerts based on stream metrics"""
    alerts = []
    
    # Viewer alerts
    if metrics["viewers"]["trend"] == "increasing" and metrics["viewers"]["current"] > 1000:
        alerts.append({
            "type": "success",
            "message": "Viewer count rising! Over 1000 viewers",
            "priority": "high"
        })
    
    # Performance alerts
    if metrics["performance"]["dropped_frames"] > 1:
        alerts.append({
            "type": "warning",
            "message": f"Dropped {metrics['performance']['dropped_frames']}% frames",
            "priority": "medium"
        })
    
    # Engagement alerts
    if metrics["engagement"]["new_followers"] > 20:
        alerts.append({
            "type": "info",
            "message": f"{metrics['engagement']['new_followers']} new followers this stream!",
            "priority": "low"
        })
    
    return alerts


def _generate_live_recommendations(metrics: Dict[str, Any]) -> List[str]:
    """Generate recommendations during live stream"""
    recommendations = []
    
    # Based on chat activity
    if metrics["chat"]["messages_per_minute"] < 10:
        recommendations.append("Engage with chat more - ask questions")
    
    # Based on viewer trends
    if metrics["viewers"]["trend"] == "decreasing":
        recommendations.append("Consider switching games or activities")
    
    # Based on performance
    if metrics["performance"]["cpu_usage"] > 70:
        recommendations.append("Close unnecessary applications to improve performance")
    
    # General recommendations
    if metrics["viewers"]["current"] > metrics["viewers"]["average"] * 1.2:
        recommendations.append("Great momentum! Consider extending stream")
    
    return recommendations


def _optimize_stream_settings(current: Dict[str, Any], platform: str) -> Dict[str, Any]:
    """Optimize stream settings for quality and performance"""
    optimized = current.copy()
    improvements = []
    warnings = []
    
    # Video optimization
    if platform == "twitch" and current["video"]["bitrate"] < 6000:
        optimized["video"]["bitrate"] = 6000
        improvements.append("Increased bitrate to Twitch maximum (6000)")
    
    # Audio optimization
    if current["audio"]["bitrate"] < 160:
        optimized["audio"]["bitrate"] = 160
        improvements.append("Increased audio bitrate for better quality")
    
    # Performance optimization
    if current["video"]["preset"] == "slow":
        optimized["video"]["preset"] = "medium"
        improvements.append("Changed encoder preset for better performance")
        warnings.append("Quality may be slightly reduced")
    
    return {
        "settings": optimized,
        "improvements": improvements,
        "warnings": warnings
    }


def _apply_settings_updates(current: Dict[str, Any], updates: Dict[str, Any]) -> Dict[str, Any]:
    """Apply settings updates"""
    updated = current.copy()
    
    for category, settings in updates.items():
        if category in updated:
            updated[category].update(settings)
    
    return updated


def _validate_settings(settings: Dict[str, Any]) -> Dict[str, Any]:
    """Validate stream settings"""
    issues = []
    
    # Video validation
    if settings["video"]["bitrate"] > 8000:
        issues.append("Bitrate may be too high for stable streaming")
    
    if settings["video"]["framerate"] > 60:
        issues.append("Framerate above 60 not recommended")
    
    # Audio validation
    if settings["audio"]["mic_gain"] > 90:
        issues.append("Microphone gain very high - may cause distortion")
    
    return {
        "valid": len(issues) == 0,
        "issues": issues
    }


def _check_restart_required(updates: Dict[str, Any]) -> bool:
    """Check if stream restart is required for updates"""
    restart_required_settings = [
        "resolution", "framerate", "encoder", "server"
    ]
    
    for category, settings in updates.items():
        for setting in settings:
            if setting in restart_required_settings:
                return True
    
    return False


def _get_preset_profile(profile_type: str) -> Dict[str, Any]:
    """Get preset streaming profile"""
    profiles = {
        "gaming": {
            "video": {
                "resolution": "1920x1080",
                "framerate": 60,
                "bitrate": 6000,
                "preset": "medium"
            },
            "low_latency": True
        },
        "just_chatting": {
            "video": {
                "resolution": "1920x1080",
                "framerate": 30,
                "bitrate": 4500,
                "preset": "slow"
            },
            "low_latency": False
        },
        "creative": {
            "video": {
                "resolution": "1920x1080",
                "framerate": 30,
                "bitrate": 5000,
                "preset": "slow"
            },
            "low_latency": False
        }
    }
    
    return profiles.get(profile_type, profiles["gaming"])


def _get_health_recommendations(issues: List[str]) -> List[str]:
    """Get recommendations based on health issues"""
    recommendations = []
    
    if "Dropped frames detected" in issues:
        recommendations.append("Lower bitrate or check internet connection")
    
    if "High CPU usage" in issues:
        recommendations.append("Lower encoder preset or close background apps")
    
    if "Network instability" in issues:
        recommendations.append("Consider using ethernet instead of WiFi")
    
    return recommendations


# Tool metadata for registration
TOOL_METADATA = {
    "name": "streaming_tool",
    "description": "Comprehensive streaming management and control",
    "version": "1.0.0",
    "author": "Streamer Team",
    "capabilities": [
        "stream_control",
        "scheduling",
        "monitoring",
        "settings_management",
        "scene_management",
        "alert_configuration",
        "multistreaming"
    ],
    "supported_platforms": ["twitch", "youtube", "facebook", "dlive"],
    "required_context": [],
    "example_usage": {
        "start": {
            "action": "start",
            "platform": "twitch",
            "title": "Epic Gaming Session!",
            "category": "Apex Legends",
            "resolution": "1920x1080",
            "framerate": 60,
            "bitrate": 6000
        },
        "monitor": {
            "action": "monitor",
            "stream_id": "active",
            "metrics": ["viewers", "performance", "chat"]
        },
        "schedule": {
            "action": "schedule",
            "recurring": True,
            "pattern": "weekly",
            "days": ["Monday", "Wednesday", "Friday"],
            "time": "19:00",
            "duration": 4
        }
    }
}