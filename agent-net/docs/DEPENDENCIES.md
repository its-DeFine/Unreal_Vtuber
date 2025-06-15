# NeuroSync Mock Worker Dependencies

This document explains the minimal dependencies required for the NeuroSync BYOC mock worker.

## Minimal Requirements (`requirements-minimal.txt`)

### Core Web Framework
- **`fastapi>=0.104.1`** - High-performance web framework for building APIs
- **`uvicorn[standard]>=0.24.0`** - ASGI server for running FastAPI applications

### HTTP Client & Schema Validation  
- **`requests>=2.31.0`** - HTTP library for orchestrator registration
- **`httpx>=0.25.0`** - Async HTTP client (alternative to requests)
- **`jsonschema>=4.19.0`** - JSON schema validation for VTuber requests
- **`python-multipart>=0.0.6`** - Support for form data parsing

## What We Removed

### Heavy ML Dependencies (Not Needed for Mock)
- ❌ `torch>=2.6.0` - PyTorch ML framework (2GB+ download)
- ❌ `transformers>=4.51.0` - Hugging Face transformers library
- ❌ `diffusers>=0.33.1` - Diffusion models library  
- ❌ `torchao` - PyTorch AO optimization
- ❌ `bitsandbytes` - 8-bit optimizers
- ❌ `accelerate` - Distributed training utilities
- ❌ `torchaudio` - Audio processing for PyTorch
- ❌ `torchvision` - Computer vision for PyTorch

### Hardware-Specific Dependencies
- ❌ `nvidia-ml-py` - NVIDIA GPU monitoring (not needed without GPU)
- ❌ `huggingface_hub[cli,hf_transfer]` - Model downloading utilities

### Build Tools (Already in Base Image)
- ❌ `setuptools` - Python package building
- ❌ `wheel` - Python wheel format support

## Build Time Impact

| Requirements File | Dependencies | Estimated Build Time | Size |
|------------------|--------------|---------------------|------|
| `requirements.txt` (original) | 18 packages + ML libs | 5-15 minutes | 2-4 GB |
| `requirements-minimal.txt` | 6 packages only | 30-60 seconds | 100-200 MB |

## What Each Dependency Enables

### FastAPI (`fastapi`)
- REST API endpoints (`/healthz`, `/text-echo`, etc.) 
- Automatic OpenAPI/Swagger documentation
- Request/response validation
- Async request handling

### Uvicorn (`uvicorn[standard]`)
- ASGI server to run FastAPI apps
- Hot reloading during development
- Production-ready performance
- WebSocket support (if needed later)

### Requests (`requests`)
- HTTP POST to orchestrator for capability registration
- Synchronous HTTP calls for simple operations
- Robust error handling and retries

### HTTPX (`httpx`)
- Async alternative to requests
- Consistent API with requests library
- Better performance for concurrent operations

### JSONSchema (`jsonschema`)
- Validates VTuber request payloads
- Ensures proper schema compliance
- Clear error messages for invalid data

### Python-Multipart (`python-multipart`)
- Handles form data in HTTP requests
- Required by FastAPI for certain content types
- Lightweight parsing utilities

## Usage in Code

```python
# FastAPI - Web framework
from fastapi import FastAPI, HTTPException, Request

# Requests - Orchestrator registration  
import requests
response = requests.post(f"{ORCH_URL}/capability/register", ...)

# JSONSchema - Request validation
from jsonschema import validate, ValidationError
validate(instance=body, schema=NEUROSYNC_VTUBER_REQUEST_SCHEMA)

# HTTPX - Async HTTP (if needed)
import httpx
async with httpx.AsyncClient() as client:
    response = await client.post(url, json=data)
```

## Development vs Production

For **mock testing** and **development**, these 6 dependencies provide everything needed:
- ✅ Web server with API endpoints
- ✅ HTTP client for orchestrator communication
- ✅ Request validation and error handling  
- ✅ JSON processing and schema validation
- ✅ Fast build times and small container size

For **production AI workloads**, you would add back the ML dependencies as needed for your specific use case. 