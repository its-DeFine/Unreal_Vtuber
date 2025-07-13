#!/usr/bin/env python3
"""
Autonomy UI - Bottle Web Application
Serves the responsive UI for the autonomous agent system with real API integration
"""

import os
import json
import asyncio
import aiohttp
from datetime import datetime
from bottle import Bottle, run, request, response, static_file, abort
from bottle import HTTPResponse, HTTPError
import threading
import time
import logging

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

app = Bottle()

# Configuration
CONFIG = {
    'AUTOGEN_URL': os.getenv('AUTOGEN_URL', 'http://autogen-agent:8000'),
    'GRAPHFLOW_URL': os.getenv('GRAPHFLOW_URL', 'http://graphflow-gateway:8080'),
    'NEUROSYNC_URL': os.getenv('NEUROSYNC_URL', 'http://neurosync:5001'),
    'NEUROSYNC_LOCAL_URL': os.getenv('NEUROSYNC_LOCAL_URL', 'http://neurosync-local:5000'),
    'UI_PORT': int(os.getenv('UI_PORT', '3000')),
    'UI_HOST': os.getenv('UI_HOST', '0.0.0.0'),
    'API_TIMEOUT': int(os.getenv('API_TIMEOUT', '10')),
    'DEBUG': os.getenv('DEBUG', 'false').lower() == 'true'
}

# API Client
class APIClient:
    def __init__(self):
        self.session = None
        self.timeout = aiohttp.ClientTimeout(total=CONFIG['API_TIMEOUT'])
    
    async def get_session(self):
        if self.session is None or self.session.closed:
            self.session = aiohttp.ClientSession(timeout=self.timeout)
        return self.session
    
    async def make_request(self, method, url, **kwargs):
        """Make HTTP request with error handling"""
        try:
            session = await self.get_session()
            async with session.request(method, url, **kwargs) as resp:
                if resp.content_type == 'application/json':
                    data = await resp.json()
                else:
                    data = await resp.text()
                
                return {
                    'status_code': resp.status,
                    'success': resp.status < 400,
                    'data': data,
                    'headers': dict(resp.headers)
                }
        except asyncio.TimeoutError:
            return {
                'status_code': 408,
                'success': False,
                'error': 'Request timeout',
                'data': None
            }
        except Exception as e:
            logger.error(f"API request failed: {e}")
            return {
                'status_code': 500,
                'success': False,
                'error': str(e),
                'data': None
            }
    
    async def close(self):
        if self.session and not self.session.closed:
            await self.session.close()

# Global API client
api_client = APIClient()

# CORS Support
def enable_cors():
    """Enable CORS for all routes"""
    response.headers['Access-Control-Allow-Origin'] = '*'
    response.headers['Access-Control-Allow-Methods'] = 'GET, POST, PUT, DELETE, OPTIONS'
    response.headers['Access-Control-Allow-Headers'] = 'Content-Type, Authorization, X-API-Key'

# Static file serving
@app.route('/static/<filepath:path>')
def serve_static(filepath):
    """Serve static files"""
    return static_file(filepath, root='.')

@app.route('/')
def index():
    """Serve the advanced UI"""
    return static_file('advanced-index.html', root='.')

@app.route('/basic')
def basic_index():
    """Serve the basic UI"""
    return static_file('index.html', root='.')

@app.route('/styles.css')
def styles():
    """Serve basic CSS"""
    return static_file('styles.css', root='.')

@app.route('/advanced-styles.css')
def advanced_styles():
    """Serve advanced CSS"""
    return static_file('advanced-styles.css', root='.')

@app.route('/app.js')
def app_js():
    """Serve basic JavaScript"""
    return static_file('app.js', root='.')

@app.route('/advanced-app.js')
def advanced_app_js():
    """Serve advanced JavaScript"""
    return static_file('advanced-app.js', root='.')

@app.route('/api-client.js')
def api_client_js():
    """Serve basic API client JavaScript"""
    return static_file('api-client.js', root='.')

@app.route('/advanced-api-client.js')
def advanced_api_client_js():
    """Serve advanced API client JavaScript"""
    return static_file('advanced-api-client.js', root='.')

# API Proxy Endpoints
@app.route('/api/proxy/health/<service>')
def proxy_health(service):
    """Proxy health checks to backend services"""
    enable_cors()
    
    url_map = {
        'autogen': f"{CONFIG['AUTOGEN_URL']}/health",
        'graphflow': f"{CONFIG['GRAPHFLOW_URL']}/api/v1/health",
        'neurosync': f"{CONFIG['NEUROSYNC_URL']}/health",
        'neurosync-local': f"{CONFIG['NEUROSYNC_LOCAL_URL']}/scb/ping"
    }
    
    if service not in url_map:
        abort(404, "Service not found")
    
    async def fetch_health():
        result = await api_client.make_request('GET', url_map[service])
        return result
    
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        result = loop.run_until_complete(fetch_health())
        response.content_type = 'application/json'
        
        if result['success']:
            return json.dumps({
                'status': 'success',
                'service': service,
                'data': result['data'],
                'timestamp': datetime.now().isoformat()
            })
        else:
            response.status = result['status_code']
            return json.dumps({
                'status': 'error',
                'service': service,
                'error': result.get('error', 'Unknown error'),
                'timestamp': datetime.now().isoformat()
            })
    finally:
        loop.close()

@app.route('/api/proxy/autogen/statistics')
def proxy_autogen_statistics():
    """Proxy AutoGen statistics endpoint"""
    enable_cors()
    
    timeframe = request.query.get('timeframe', '1h')
    agent_filter = request.query.get('agent_filter', '')
    
    url = f"{CONFIG['AUTOGEN_URL']}/api/statistics/detailed"
    params = {'timeframe': timeframe}
    if agent_filter:
        params['agent_filter'] = agent_filter
    
    async def fetch_stats():
        return await api_client.make_request('GET', url, params=params)
    
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        result = loop.run_until_complete(fetch_stats())
        response.content_type = 'application/json'
        
        if result['success']:
            return json.dumps(result['data'])
        else:
            response.status = result['status_code']
            return json.dumps({'error': result.get('error', 'Failed to fetch statistics')})
    finally:
        loop.close()

@app.route('/api/proxy/autogen/performance')
def proxy_autogen_performance():
    """Proxy AutoGen performance analytics"""
    enable_cors()
    
    url = f"{CONFIG['AUTOGEN_URL']}/api/analytics/performance"
    
    async def fetch_performance():
        return await api_client.make_request('GET', url)
    
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        result = loop.run_until_complete(fetch_performance())
        response.content_type = 'application/json'
        
        if result['success']:
            return json.dumps(result['data'])
        else:
            response.status = result['status_code']
            return json.dumps({'error': result.get('error', 'Failed to fetch performance data')})
    finally:
        loop.close()

@app.route('/api/proxy/autogen/gpu-status')
def proxy_gpu_status():
    """Proxy GPU status endpoint"""
    enable_cors()
    
    url = f"{CONFIG['AUTOGEN_URL']}/api/gpu-status"
    
    async def fetch_gpu():
        return await api_client.make_request('GET', url)
    
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        result = loop.run_until_complete(fetch_gpu())
        response.content_type = 'application/json'
        
        if result['success']:
            return json.dumps(result['data'])
        else:
            response.status = result['status_code']
            return json.dumps({'error': result.get('error', 'Failed to fetch GPU status')})
    finally:
        loop.close()

@app.route('/api/proxy/autogen/agents')
def proxy_agent_learning():
    """Proxy agent learning status"""
    enable_cors()
    
    url = f"{CONFIG['AUTOGEN_URL']}/api/agent-learning"
    
    async def fetch_agents():
        return await api_client.make_request('GET', url)
    
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        result = loop.run_until_complete(fetch_agents())
        response.content_type = 'application/json'
        
        if result['success']:
            return json.dumps(result['data'])
        else:
            response.status = result['status_code']
            return json.dumps({'error': result.get('error', 'Failed to fetch agent data')})
    finally:
        loop.close()

@app.route('/api/proxy/autogen/persona')
def proxy_persona_status():
    """Proxy persona status"""
    enable_cors()
    
    url = f"{CONFIG['AUTOGEN_URL']}/api/persona/status"
    
    async def fetch_persona():
        return await api_client.make_request('GET', url)
    
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        result = loop.run_until_complete(fetch_persona())
        response.content_type = 'application/json'
        
        if result['success']:
            return json.dumps(result['data'])
        else:
            response.status = result['status_code']
            return json.dumps({'error': result.get('error', 'Failed to fetch persona status')})
    finally:
        loop.close()

@app.route('/api/proxy/autogen/stimuli/status')
def proxy_stimuli_status():
    """Proxy stimuli processing status"""
    enable_cors()
    
    url = f"{CONFIG['AUTOGEN_URL']}/api/stimuli/status"
    
    async def fetch_stimuli():
        return await api_client.make_request('GET', url)
    
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        result = loop.run_until_complete(fetch_stimuli())
        response.content_type = 'application/json'
        
        if result['success']:
            return json.dumps(result['data'])
        else:
            response.status = result['status_code']
            return json.dumps({'error': result.get('error', 'Failed to fetch stimuli status')})
    finally:
        loop.close()

@app.route('/api/proxy/autogen/stimuli/submit', method='POST')
def proxy_submit_stimuli():
    """Proxy stimuli submission"""
    enable_cors()
    
    try:
        data = request.json
    except:
        abort(400, "Invalid JSON")
    
    url = f"{CONFIG['AUTOGEN_URL']}/api/stimuli/receive"
    
    async def submit_stimuli():
        return await api_client.make_request('POST', url, json=data)
    
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        result = loop.run_until_complete(submit_stimuli())
        response.content_type = 'application/json'
        
        if result['success']:
            return json.dumps(result['data'])
        else:
            response.status = result['status_code']
            return json.dumps({'error': result.get('error', 'Failed to submit stimuli')})
    finally:
        loop.close()

@app.route('/api/proxy/autogen/emergency-stop', method='POST')
def proxy_emergency_stop():
    """Proxy emergency stop"""
    enable_cors()
    
    url = f"{CONFIG['AUTOGEN_URL']}/api/stimuli/control/pause"
    
    async def emergency_stop():
        return await api_client.make_request('POST', url)
    
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        result = loop.run_until_complete(emergency_stop())
        response.content_type = 'application/json'
        
        if result['success']:
            return json.dumps({'status': 'success', 'message': 'Emergency stop executed'})
        else:
            response.status = result['status_code']
            return json.dumps({'error': result.get('error', 'Failed to execute emergency stop')})
    finally:
        loop.close()

@app.route('/api/proxy/semantic/export')
def proxy_semantic_export():
    """Proxy semantic map export"""
    enable_cors()
    
    format_type = request.query.get('format', 'd3js')
    url = f"{CONFIG['AUTOGEN_URL']}/api/semantic-map/export"
    params = {'format': format_type}
    
    async def fetch_semantic():
        return await api_client.make_request('GET', url, params=params)
    
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        result = loop.run_until_complete(fetch_semantic())
        response.content_type = 'application/json'
        
        if result['success']:
            return json.dumps(result['data'])
        else:
            response.status = result['status_code']
            return json.dumps({'error': result.get('error', 'Failed to export semantic map')})
    finally:
        loop.close()

@app.route('/api/proxy/semantic/metrics')
def proxy_semantic_metrics():
    """Proxy semantic map metrics"""
    enable_cors()
    
    url = f"{CONFIG['AUTOGEN_URL']}/api/semantic-map/metrics"
    
    async def fetch_metrics():
        return await api_client.make_request('GET', url)
    
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        result = loop.run_until_complete(fetch_metrics())
        response.content_type = 'application/json'
        
        if result['success']:
            return json.dumps(result['data'])
        else:
            response.status = result['status_code']
            return json.dumps({'error': result.get('error', 'Failed to fetch semantic metrics')})
    finally:
        loop.close()

@app.route('/api/proxy/neurosync/character/current')
def proxy_current_character():
    """Proxy current character info"""
    enable_cors()
    
    url = f"{CONFIG['NEUROSYNC_URL']}/character/current"
    
    async def fetch_character():
        return await api_client.make_request('GET', url)
    
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        result = loop.run_until_complete(fetch_character())
        response.content_type = 'application/json'
        
        if result['success']:
            return json.dumps(result['data'])
        else:
            response.status = result['status_code']
            return json.dumps({'error': result.get('error', 'Failed to fetch character info')})
    finally:
        loop.close()

@app.route('/api/proxy/scb/status')
def proxy_scb_status():
    """Proxy SCB status"""
    enable_cors()
    
    url = f"{CONFIG['NEUROSYNC_LOCAL_URL']}/scb/global/slice"
    
    async def fetch_scb():
        return await api_client.make_request('GET', url)
    
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        result = loop.run_until_complete(fetch_scb())
        response.content_type = 'application/json'
        
        if result['success']:
            return json.dumps(result['data'])
        else:
            response.status = result['status_code']
            return json.dumps({'error': result.get('error', 'Failed to fetch SCB status')})
    finally:
        loop.close()

# System Info Endpoint
@app.route('/api/system/info')
def system_info():
    """Get system configuration info for the UI"""
    enable_cors()
    response.content_type = 'application/json'
    
    return json.dumps({
        'version': '1.0.0',
        'name': 'Autonomy UI',
        'services': {
            'autogen': CONFIG['AUTOGEN_URL'],
            'graphflow': CONFIG['GRAPHFLOW_URL'],
            'neurosync': CONFIG['NEUROSYNC_URL'],
            'neurosync_local': CONFIG['NEUROSYNC_LOCAL_URL']
        },
        'features': {
            'real_time_updates': True,
            'semantic_graph': True,
            'agent_monitoring': True,
            'stimuli_processing': True,
            'character_management': True
        },
        'timestamp': datetime.now().isoformat()
    })

# Health Check
@app.route('/health')
def health_check():
    """UI service health check"""
    enable_cors()
    response.content_type = 'application/json'
    
    return json.dumps({
        'status': 'healthy',
        'service': 'autonomy-ui',
        'version': '1.0.0',
        'uptime': time.time(),
        'timestamp': datetime.now().isoformat()
    })

# OPTIONS handler for CORS preflight
@app.route('/<path:path>', method='OPTIONS')
def options_handler(path):
    """Handle CORS preflight requests"""
    enable_cors()
    return HTTPResponse(status=200)

# Error handlers
@app.error(404)
def error404(error):
    """Handle 404 errors"""
    enable_cors()
    response.content_type = 'application/json'
    return json.dumps({
        'error': 'Not Found',
        'message': f'The requested resource was not found: {request.path}',
        'status_code': 404
    })

@app.error(500)
def error500(error):
    """Handle 500 errors"""
    enable_cors()
    response.content_type = 'application/json'
    logger.error(f"Internal server error: {error}")
    return json.dumps({
        'error': 'Internal Server Error',
        'message': 'An internal server error occurred',
        'status_code': 500
    })

# Cleanup on shutdown
import atexit

@atexit.register
def cleanup():
    """Cleanup resources on shutdown"""
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        loop.run_until_complete(api_client.close())
    finally:
        loop.close()

if __name__ == '__main__':
    logger.info(f"Starting Autonomy UI on {CONFIG['UI_HOST']}:{CONFIG['UI_PORT']}")
    logger.info(f"AutoGen URL: {CONFIG['AUTOGEN_URL']}")
    logger.info(f"GraphFlow URL: {CONFIG['GRAPHFLOW_URL']}")
    logger.info(f"NeuroSync URL: {CONFIG['NEUROSYNC_URL']}")
    logger.info(f"NeuroSync Local URL: {CONFIG['NEUROSYNC_LOCAL_URL']}")
    logger.info(f"Debug mode: {CONFIG['DEBUG']}")
    
    try:
        run(app, 
            host=CONFIG['UI_HOST'], 
            port=CONFIG['UI_PORT'], 
            debug=CONFIG['DEBUG'],
            reloader=CONFIG['DEBUG'],
            quiet=not CONFIG['DEBUG'])
    except KeyboardInterrupt:
        logger.info("Shutting down Autonomy UI...")
    except Exception as e:
        logger.error(f"Failed to start server: {e}")
        raise