#!/usr/bin/env python3
"""
GraphFlow External Stimuli System Runner Script

This script provides a convenient way to run the GraphFlow External Stimuli System
with proper environment setup and configuration.
"""

import os
import sys
import argparse
import subprocess
from pathlib import Path


# Add the project root to Python path
PROJECT_ROOT = Path(__file__).parent.absolute()
sys.path.insert(0, str(PROJECT_ROOT))


def setup_environment(env: str):
    """Setup environment variables based on the environment."""
    env_file = PROJECT_ROOT / "config" / f"{env}.env"
    
    if env_file.exists():
        print(f"Loading environment from {env_file}")
        with open(env_file) as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#') and '=' in line:
                    key, value = line.split('=', 1)
                    os.environ[key.strip()] = value.strip().strip('"')
    
    # Set additional environment variables
    os.environ["PYTHONPATH"] = str(PROJECT_ROOT)
    os.environ["ENVIRONMENT"] = env


def check_dependencies():
    """Check if all required dependencies are installed."""
    try:
        import fastapi
        import uvicorn
        import graphflow
        import openai
        import prometheus_client
    except ImportError as e:
        print(f"Missing dependency: {e}")
        print("Please run: pip install -r requirements.txt")
        sys.exit(1)


def run_development():
    """Run the application in development mode."""
    print("Starting GraphFlow External Stimuli System in DEVELOPMENT mode...")
    setup_environment("development")
    
    # Run with auto-reload enabled
    cmd = [
        sys.executable, "-m", "uvicorn",
        "src.api_server:app",
        "--host", "0.0.0.0",
        "--port", "8080",
        "--reload",
        "--reload-dir", str(PROJECT_ROOT / "src"),
        "--log-level", "debug"
    ]
    
    subprocess.run(cmd)


def run_testing():
    """Run the application in testing mode."""
    print("Starting GraphFlow External Stimuli System in TESTING mode...")
    setup_environment("testing")
    
    # Import and run the main module
    from src.main import main
    main()


def run_production():
    """Run the application in production mode."""
    print("Starting GraphFlow External Stimuli System in PRODUCTION mode...")
    setup_environment("production")
    
    # Import and run the main module with production settings
    from src.main import main
    main()


def run_tests():
    """Run the test suite."""
    print("Running GraphFlow External Stimuli System tests...")
    
    # Run pytest with coverage
    cmd = [
        sys.executable, "-m", "pytest",
        "tests/",
        "-v",
        "--cov=src",
        "--cov-report=html",
        "--cov-report=term"
    ]
    
    subprocess.run(cmd)


def run_docker_build():
    """Build the Docker image."""
    print("Building GraphFlow External Stimuli System Docker image...")
    
    cmd = [
        "docker", "build",
        "-f", "docker/Dockerfile",
        "-t", "graphflow-stimuli-system:latest",
        "."
    ]
    
    subprocess.run(cmd)


def run_docker_compose(env: str):
    """Run with docker-compose."""
    print(f"Starting GraphFlow External Stimuli System with docker-compose ({env})...")
    
    compose_file = "docker-compose.yml"
    if env == "development":
        compose_file = "docker/docker-compose.dev.yml"
    elif env == "testing":
        compose_file = "docker/docker-compose.test.yml"
    
    cmd = ["docker-compose", "-f", compose_file, "up"]
    subprocess.run(cmd)


def main():
    """Main entry point for the runner script."""
    parser = argparse.ArgumentParser(
        description="GraphFlow External Stimuli System Runner",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Run in development mode with auto-reload
  python run.py dev
  
  # Run in production mode
  python run.py prod
  
  # Run tests
  python run.py test
  
  # Build Docker image
  python run.py docker-build
  
  # Run with docker-compose
  python run.py docker --env production
        """
    )
    
    parser.add_argument(
        "command",
        choices=["dev", "test", "prod", "docker-build", "docker"],
        help="Command to run"
    )
    
    parser.add_argument(
        "--env",
        choices=["development", "testing", "production"],
        default="production",
        help="Environment for docker-compose (default: production)"
    )
    
    parser.add_argument(
        "--host",
        default="0.0.0.0",
        help="Host to bind to (default: 0.0.0.0)"
    )
    
    parser.add_argument(
        "--port",
        type=int,
        default=8080,
        help="Port to bind to (default: 8080)"
    )
    
    args = parser.parse_args()
    
    # Check dependencies first
    if args.command not in ["docker-build", "docker"]:
        check_dependencies()
    
    # Execute the appropriate command
    if args.command == "dev":
        run_development()
    elif args.command == "test":
        run_tests()
    elif args.command == "prod":
        run_production()
    elif args.command == "docker-build":
        run_docker_build()
    elif args.command == "docker":
        run_docker_compose(args.env)


if __name__ == "__main__":
    main()