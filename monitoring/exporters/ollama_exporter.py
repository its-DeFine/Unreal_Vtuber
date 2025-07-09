#!/usr/bin/env python3
"""
Prometheus exporter for Ollama metrics.
"""

import os
import time
import requests
from prometheus_client import start_http_server, Gauge, Counter, Info
from prometheus_client.core import GaugeMetricFamily, REGISTRY
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

OLLAMA_HOST = os.getenv('OLLAMA_HOST', 'http://localhost:11434')
EXPORTER_PORT = int(os.getenv('EXPORTER_PORT', '9122'))

class OllamaCollector:
    def __init__(self):
        self.ollama_host = OLLAMA_HOST
        
    def collect(self):
        try:
            # Get running models
            response = requests.get(f"{self.ollama_host}/api/ps", timeout=5)
            if response.status_code == 200:
                data = response.json()
                models = data.get('models', [])
                
                # Number of running models
                yield GaugeMetricFamily(
                    'ollama_running_models_count',
                    'Number of currently running models',
                    value=len(models)
                )
                
                # Memory usage per model
                for model in models:
                    labels = [model.get('name', 'unknown')]
                    yield GaugeMetricFamily(
                        'ollama_model_memory_bytes',
                        'Memory usage of running model in bytes',
                        value=model.get('size', 0),
                        labels=['model']
                    )
        except Exception as e:
            logger.error(f"Failed to collect Ollama metrics: {e}")
            
        # Check if Ollama is up
        try:
            response = requests.get(f"{self.ollama_host}/", timeout=5)
            up = 1 if response.status_code == 200 else 0
        except:
            up = 0
            
        yield GaugeMetricFamily(
            'ollama_up',
            'Whether Ollama is up and responding',
            value=up
        )

if __name__ == '__main__':
    # Register the collector
    REGISTRY.register(OllamaCollector())
    
    # Start the HTTP server
    start_http_server(EXPORTER_PORT)
    logger.info(f"Ollama exporter started on port {EXPORTER_PORT}")
    logger.info(f"Monitoring Ollama at {OLLAMA_HOST}")
    
    # Keep the server running
    while True:
        time.sleep(60)