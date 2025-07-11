#!/usr/bin/env python3
"""
EMERGENCY MAIN ENTRY POINT FOR GRAPHFLOW
========================================

This bypasses the complex gateway system and runs a simple API server
that directly routes stimuli to S1 using the nuclear decision matrix.
"""

import sys
import os
import logging

# Add src to path
sys.path.insert(0, '/app/src')

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger("emergency_main")

def main():
    """Emergency main entry point."""
    logger.info("🚨 STARTING EMERGENCY GRAPHFLOW SERVER")
    logger.info("🎯 Using nuclear decision matrix routing")
    logger.info("🔓 Authentication disabled for emergency testing")
    
    try:
        # Import and run the simple API server
        from src.simple_api_server import app
        import uvicorn
        
        logger.info("🚀 Starting emergency API server on port 8080")
        uvicorn.run(app, host="0.0.0.0", port=8080, log_level="info")
        
    except Exception as e:
        logger.error(f"❌ Emergency server failed: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()