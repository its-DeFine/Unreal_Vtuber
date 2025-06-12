#!/usr/bin/env bash
# Entry point for the NeuroSync BYOC worker container
# Registers the capability (handled inside the Python app) and then launches
# the FastAPI HTTP server.

set -euo pipefail

python /app/server_adapter.py 