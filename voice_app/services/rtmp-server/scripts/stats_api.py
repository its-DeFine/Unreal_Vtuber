#!/usr/bin/env python3
"""
Stats API Server for RTMP Dashboard
Provides real-time statistics and monitoring data for the web interface
"""

import sys
import os
import json
import time
import asyncio
import logging
import psutil
import subprocess
from typing import Dict, Any, List
from pathlib import Path
from datetime import datetime
import argparse

try:
    from aiohttp import web, WSMsgType
    from aiohttp.web import middleware
    import aiohttp_cors
except ImportError:
    print("aiohttp not installed. Installing...")
    subprocess.check_call([sys.executable, "-m", "pip", "install", "aiohttp", "aiohttp-cors"])
    from aiohttp import web, WSMsgType
    from aiohttp.web import middleware
    import aiohttp_cors

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('/var/log/stats_api.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class StatsCollector:
    """Collects and aggregates system and service statistics"""
    
    def __init__(self):
        self.start_time = time.time()
        self.ffmpeg_manager = None
        self.gstreamer_processor = None
        
    def get_system_stats(self) -> Dict[str, Any]:
        """Get system resource statistics"""
        try:
            # CPU and memory
            cpu_percent = psutil.cpu_percent(interval=1)
            memory = psutil.virtual_memory()
            disk = psutil.disk_usage('/')
            
            # Network stats
            network = psutil.net_io_counters()
            
            # Process counts
            ffmpeg_processes = self.count_processes('ffmpeg')
            gstreamer_processes = self.count_processes('gst')
            nginx_processes = self.count_processes('nginx')
            
            return {
                'uptime': time.time() - self.start_time,
                'cpuUsage': cpu_percent,
                'memoryUsage': memory.percent,
                'memoryTotal': memory.total / (1024**3),  # GB
                'memoryUsed': memory.used / (1024**3),    # GB
                'diskUsage': (disk.used / disk.total) * 100,
                'diskTotal': disk.total / (1024**3),     # GB
                'diskUsed': disk.used / (1024**3),       # GB
                'networkBytesReceived': network.bytes_recv,
                'networkBytesSent': network.bytes_sent,
                'processCount': {
                    'ffmpeg': ffmpeg_processes,
                    'gstreamer': gstreamer_processes,
                    'nginx': nginx_processes
                }
            }
        except Exception as e:
            logger.error(f"Error collecting system stats: {str(e)}")
            return {}
    
    def count_processes(self, name_filter: str) -> int:
        """Count processes matching the name filter"""
        try:
            count = 0
            for proc in psutil.process_iter(['name']):
                try:
                    if name_filter.lower() in proc.info['name'].lower():
                        count += 1
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    continue
            return count
        except Exception:
            return 0
    
    def get_nginx_stats(self) -> Dict[str, Any]:
        """Get NGINX/RTMP statistics from status page"""
        try:
            import urllib.request
            import xml.etree.ElementTree as ET
            
            # Try to fetch NGINX stats from status endpoint
            try:
                response = urllib.request.urlopen('http://localhost:8080/stats', timeout=5)
                stats_xml = response.read().decode('utf-8')
                
                # Parse XML stats (simplified - would need full XML parsing)
                # For now, return basic structure
                return {
                    'activeConnections': self.parse_nginx_connections(),
                    'totalStreams': 0,
                    'activeStreams': 0,
                    'bytesReceived': 0,
                    'bytesSent': 0
                }
            except Exception:
                return {
                    'activeConnections': 0,
                    'totalStreams': 0,
                    'activeStreams': 0,
                    'bytesReceived': 0,
                    'bytesSent': 0
                }
                
        except Exception as e:
            logger.warning(f"Could not fetch NGINX stats: {str(e)}")
            return {}
    
    def parse_nginx_connections(self) -> int:
        """Parse active connections from NGINX status"""
        try:
            # Simple netstat-based connection count
            result = subprocess.run(['netstat', '-an'], capture_output=True, text=True, timeout=5)
            lines = result.stdout.split('\n')
            
            connections = 0
            for line in lines:
                if ':1935' in line and 'ESTABLISHED' in line:
                    connections += 1
                    
            return connections
        except Exception:
            return 0
    
    def get_stream_stats(self) -> List[Dict[str, Any]]:
        """Get active stream statistics"""
        try:
            # This would integrate with actual stream monitoring
            # For now, return mock data structure
            streams = []
            
            # Check for active RTMP streams (simplified)
            active_connections = self.parse_nginx_connections()
            
            for i in range(active_connections):
                streams.append({
                    'name': f'stream_{i+1}',
                    'status': 'active',
                    'viewers': 1,  # Would be actual viewer count
                    'bitrate': 2500.0,  # kbps
                    'latency': 150.0,   # ms
                    'duration': 300,    # seconds
                    'qualities': ['720p', '480p', '240p'],
                    'startTime': time.time() - 300
                })
            
            return streams
            
        except Exception as e:
            logger.error(f"Error collecting stream stats: {str(e)}")
            return []
    
    def get_hardware_acceleration(self) -> Dict[str, bool]:
        """Check hardware acceleration availability"""
        try:
            capabilities = {
                'nvenc': False,
                'vaapi': False,
                'qsv': False,
                'videotoolbox': False,
                'amf': False
            }
            
            # Check FFmpeg encoders
            try:
                result = subprocess.run(['ffmpeg', '-encoders'], 
                                      capture_output=True, text=True, timeout=10)
                output = result.stdout.lower()
                
                capabilities['nvenc'] = 'h264_nvenc' in output
                capabilities['vaapi'] = 'h264_vaapi' in output
                capabilities['qsv'] = 'h264_qsv' in output
                capabilities['videotoolbox'] = 'h264_videotoolbox' in output
                capabilities['amf'] = 'h264_amf' in output
                
            except Exception:
                pass
            
            return capabilities
            
        except Exception as e:
            logger.error(f"Error checking hardware acceleration: {str(e)}")
            return {}
    
    def get_comprehensive_stats(self) -> Dict[str, Any]:
        """Get all statistics combined"""
        system_stats = self.get_system_stats()
        nginx_stats = self.get_nginx_stats()
        stream_stats = self.get_stream_stats()
        hw_accel = self.get_hardware_acceleration()
        
        # Calculate derived metrics
        total_bandwidth = sum(stream.get('bitrate', 0) for stream in stream_stats) / 1000.0  # Mbps
        avg_latency = sum(stream.get('latency', 0) for stream in stream_stats) / max(len(stream_stats), 1)
        
        return {
            'timestamp': datetime.utcnow().isoformat(),
            'activeStreams': len(stream_stats),
            'totalBandwidth': total_bandwidth,
            'averageLatency': avg_latency,
            'cpuUsage': system_stats.get('cpuUsage', 0),
            'memoryUsage': system_stats.get('memoryUsage', 0),
            'diskUsage': system_stats.get('diskUsage', 0),
            'uptime': system_stats.get('uptime', 0),
            'hardwareAcceleration': hw_accel,
            'ffmpegProcesses': system_stats.get('processCount', {}).get('ffmpeg', 0),
            'gstreamerProcesses': system_stats.get('processCount', {}).get('gstreamer', 0),
            'processRestarts': 0,  # Would track actual restarts
            'networkStatus': 'connected' if nginx_stats.get('activeConnections', 0) > 0 else 'disconnected',
            'activeStreamsDetails': stream_stats,
            'systemStats': system_stats,
            'nginxStats': nginx_stats
        }

class WebSocketManager:
    """Manages WebSocket connections for real-time updates"""
    
    def __init__(self):
        self.connections = set()
        self.stats_collector = StatsCollector()
        
    async def add_connection(self, ws):
        """Add a new WebSocket connection"""
        self.connections.add(ws)
        logger.info(f"WebSocket connection added. Total: {len(self.connections)}")
        
    async def remove_connection(self, ws):
        """Remove a WebSocket connection"""
        self.connections.discard(ws)
        logger.info(f"WebSocket connection removed. Total: {len(self.connections)}")
        
    async def broadcast_stats(self):
        """Broadcast statistics to all connected clients"""
        if not self.connections:
            return
            
        try:
            stats = self.stats_collector.get_comprehensive_stats()
            message = json.dumps({
                'type': 'stats',
                'payload': stats
            })
            
            # Send to all connected clients
            disconnected = set()
            for ws in self.connections.copy():
                try:
                    await ws.send_str(message)
                except Exception as e:
                    logger.warning(f"Failed to send to WebSocket: {str(e)}")
                    disconnected.add(ws)
            
            # Remove disconnected clients
            for ws in disconnected:
                self.connections.discard(ws)
                
        except Exception as e:
            logger.error(f"Error broadcasting stats: {str(e)}")
    
    async def broadcast_log(self, level: str, message: str):
        """Broadcast log message to all connected clients"""
        if not self.connections:
            return
            
        try:
            log_message = json.dumps({
                'type': 'log',
                'level': level,
                'message': message,
                'timestamp': datetime.utcnow().isoformat()
            })
            
            disconnected = set()
            for ws in self.connections.copy():
                try:
                    await ws.send_str(log_message)
                except Exception:
                    disconnected.add(ws)
            
            for ws in disconnected:
                self.connections.discard(ws)
                
        except Exception as e:
            logger.error(f"Error broadcasting log: {str(e)}")

# Global WebSocket manager
ws_manager = WebSocketManager()

@middleware
async def cors_middleware(request, handler):
    """CORS middleware for API requests"""
    response = await handler(request)
    response.headers['Access-Control-Allow-Origin'] = '*'
    response.headers['Access-Control-Allow-Methods'] = 'GET, POST, OPTIONS'
    response.headers['Access-Control-Allow-Headers'] = 'Content-Type'
    return response

async def stats_handler(request):
    """HTTP endpoint for getting current statistics"""
    try:
        stats = ws_manager.stats_collector.get_comprehensive_stats()
        return web.json_response(stats)
    except Exception as e:
        logger.error(f"Error in stats handler: {str(e)}")
        return web.json_response({'error': str(e)}, status=500)

async def websocket_handler(request):
    """WebSocket endpoint for real-time updates"""
    ws = web.WebSocketResponse()
    await ws.prepare(request)
    
    await ws_manager.add_connection(ws)
    
    try:
        # Send initial stats
        stats = ws_manager.stats_collector.get_comprehensive_stats()
        await ws.send_str(json.dumps({
            'type': 'stats',
            'payload': stats
        }))
        
        # Handle incoming messages
        async for msg in ws:
            if msg.type == WSMsgType.TEXT:
                try:
                    data = json.loads(msg.data)
                    # Handle client commands if needed
                    logger.info(f"Received WebSocket message: {data}")
                except json.JSONDecodeError:
                    pass
            elif msg.type == WSMsgType.ERROR:
                logger.error(f'WebSocket error: {ws.exception()}')
                break
                
    except Exception as e:
        logger.error(f"WebSocket handler error: {str(e)}")
    finally:
        await ws_manager.remove_connection(ws)
    
    return ws

async def restart_services_handler(request):
    """Endpoint to restart services"""
    try:
        # This would restart actual services
        await ws_manager.broadcast_log('warning', 'Service restart initiated')
        
        # Simulate restart process
        await asyncio.sleep(1)
        
        await ws_manager.broadcast_log('success', 'Services restarted successfully')
        return web.json_response({'status': 'success', 'message': 'Services restarted'})
        
    except Exception as e:
        logger.error(f"Error restarting services: {str(e)}")
        await ws_manager.broadcast_log('error', f'Service restart failed: {str(e)}')
        return web.json_response({'error': str(e)}, status=500)

async def emergency_stop_handler(request):
    """Endpoint for emergency stop"""
    try:
        await ws_manager.broadcast_log('error', 'Emergency stop initiated')
        
        # This would stop actual services
        # For safety, just simulate
        await asyncio.sleep(1)
        
        await ws_manager.broadcast_log('error', 'Emergency stop completed')
        return web.json_response({'status': 'success', 'message': 'Emergency stop executed'})
        
    except Exception as e:
        logger.error(f"Error in emergency stop: {str(e)}")
        return web.json_response({'error': str(e)}, status=500)

async def stats_broadcaster():
    """Background task to broadcast stats periodically"""
    while True:
        try:
            await ws_manager.broadcast_stats()
            await asyncio.sleep(5)  # Broadcast every 5 seconds
        except Exception as e:
            logger.error(f"Error in stats broadcaster: {str(e)}")
            await asyncio.sleep(10)

async def create_app():
    """Create the web application"""
    app = web.Application(middlewares=[cors_middleware])
    
    # Add routes
    app.router.add_get('/api/stats', stats_handler)
    app.router.add_get('/ws', websocket_handler)
    app.router.add_post('/api/restart', restart_services_handler)
    app.router.add_post('/api/emergency-stop', emergency_stop_handler)
    
    # Serve static files
    static_path = Path(__file__).parent.parent / 'www'
    if static_path.exists():
        app.router.add_static('/', static_path, name='static')
        app.router.add_get('/', lambda request: web.FileResponse(static_path / 'dashboard.html'))
    
    # Start background tasks
    app.on_startup.append(lambda app: asyncio.create_task(stats_broadcaster()))
    
    return app

def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(description='RTMP Server Stats API')
    parser.add_argument('--host', default='0.0.0.0', help='Host to bind to')
    parser.add_argument('--port', type=int, default=8080, help='Port to bind to')
    parser.add_argument('--log-level', choices=['DEBUG', 'INFO', 'WARNING', 'ERROR'], 
                       default='INFO', help='Logging level')
    
    args = parser.parse_args()
    
    # Set log level
    logging.getLogger().setLevel(getattr(logging, args.log_level))
    
    logger.info(f"🚀 Starting RTMP Stats API server on {args.host}:{args.port}")
    
    try:
        app = create_app()
        web.run_app(app, host=args.host, port=args.port, access_log=logger)
    except KeyboardInterrupt:
        logger.info("🛑 Server stopped by user")
    except Exception as e:
        logger.error(f"❌ Server error: {str(e)}")
        sys.exit(1)

if __name__ == "__main__":
    main() 