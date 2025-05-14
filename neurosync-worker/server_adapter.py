import os
import logging
import time
import json
import threading
from typing import Any, Dict, Union

import requests
import hashlib
import secrets
from fastapi import FastAPI, HTTPException, Request, status
from fastapi.responses import JSONResponse, StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
from jsonschema import validate, ValidationError
import httpx

# -----------------------------------------------------------------------------
# Logging Setup – structured JSON for easy ingestion by Grafana/Loki/DataDog…
# -----------------------------------------------------------------------------

_LOGGER_NAME = "neurosync.worker"
logger = logging.getLogger(_LOGGER_NAME)
logger.setLevel(logging.DEBUG)

# Ensure we only add a handler once when the module is re-imported (pytest etc.)
if not logger.handlers:
    handler = logging.StreamHandler()
    formatter = logging.Formatter(
        "%(asctime)s %(levelname)s %(name)s %(message)s",
        datefmt="%Y-%m-%dT%H:%M:%SZ",
    )
    handler.setFormatter(formatter)
    logger.addHandler(handler)

# -----------------------------------------------------------------------------
# Environment Configuration & Global Constants
# -----------------------------------------------------------------------------

ORCH_URL = os.getenv("ORCH_URL", "")
ORCH_SECRET = os.getenv("ORCH_SECRET", "")
SERVER_PORT = int(os.getenv("SERVER_PORT", "9876"))

CAPABILITY_NAME = os.getenv("CAPABILITY_NAME", "start-echo-test")
CAPABILITY_URL = os.getenv("CAPABILITY_URL", f"http://localhost:{SERVER_PORT}")
CAPABILITY_DESCRIPTION = os.getenv("CAPABILITY_DESCRIPTION", "simple text echo capability")
CAPABILITY_CAPACITY = int(os.getenv("CAPABILITY_CAPACITY", 1))
CAPABILITY_PRICE_PER_UNIT = int(os.getenv("CAPABILITY_PRICE_PER_UNIT", 1))
CAPABILITY_PRICE_SCALING = int(os.getenv("CAPABILITY_PRICE_SCALING", 1))

NEUROSYNC_CORE_JOB_URL = os.getenv("NEUROSYNC_CORE_JOB_URL", "http://localhost:5000/v1/jobs")

WINDOW_DURATION_SEC = int(os.getenv("REQUEST_WINDOW_MINUTES", "60")) * 60
WINDOW_ACTIVE_FLAG_PATH = "/app/neurosync_window_active.flag" # Shared flag file path

_window_expiry: Union[float, None] = None
_window_lock = threading.Lock()

# Define paths that are allowed to initiate a job window
WINDOW_INITIATING_PATHS = ["/start-echo-test", "/v1/vtuber/start"]

# -----------------------------------------------------------------------------
# JSON Schemas – will evolve with real contract.  Kept here for re-use in tests.
# -----------------------------------------------------------------------------

NEUROSYNC_VTUBER_REQUEST_SCHEMA: Dict[str, Any] = {
    "type": "object",
    "properties": {
        "job_id": {"type": "string"},
        "character": {"type": "string"},
        "knowledge_source_url": {"type": "string", "format": "uri"},
        "model_time_seconds": {"type": "number", "minimum": 1},
        "prompt": {"type": "string"},
    },
    "required": ["job_id", "character", "prompt"],
    "additionalProperties": False,
}

# The realtime frame format – loosely defined for now.
NEUROSYNC_REALTIME_FRAME_SCHEMA: Dict[str, Any] = {
    "type": "object",
    "properties": {
        "sequence_number": {"type": "integer"},
        "timestamp_ms": {"type": "integer"},
        "audio_base64": {"type": "string"},
        "blendshapes": {"type": "array"},
    },
    "required": ["sequence_number", "timestamp_ms"],
    "additionalProperties": True,
}

# -----------------------------------------------------------------------------
# Rolling Window Flag and State Management
# -----------------------------------------------------------------------------

def _delete_window_flag():
    """Safely delete the window active flag file."""
    if os.path.exists(WINDOW_ACTIVE_FLAG_PATH):
        try:
            os.remove(WINDOW_ACTIVE_FLAG_PATH)
            logger.info(f"Rolling window active flag deleted: {WINDOW_ACTIVE_FLAG_PATH}")
        except OSError as e:
            logger.error(f"Error deleting rolling window active flag {WINDOW_ACTIVE_FLAG_PATH}: {e}")
    else:
        logger.debug(f"Attempted to delete rolling window flag, but it did not exist: {WINDOW_ACTIVE_FLAG_PATH}")

def _create_window_flag():
    """Create the window active flag file, storing the current time for info."""
    try:
        with open(WINDOW_ACTIVE_FLAG_PATH, "w") as f:
            f.write(str(time.monotonic()))
        logger.info(f"Rolling window active flag created/updated: {WINDOW_ACTIVE_FLAG_PATH}")
    except OSError as e:
        logger.error(f"Error creating/updating rolling window active flag {WINDOW_ACTIVE_FLAG_PATH}: {e}")

def open_job_window():
    """Opens the job window, sets expiry, and creates the flag.
    Called by job submission endpoints upon success."""
    global _window_expiry
    with _window_lock:
        _window_expiry = time.monotonic() + WINDOW_DURATION_SEC
        _create_window_flag()
        logger.info(f"Job window opened. Expires at: {_window_expiry:.2f}. Flag created.")

def extend_job_window():
    """Extends the current job window's expiry if it's active."""
    global _window_expiry
    with _window_lock:
        if _window_expiry is not None and time.monotonic() < _window_expiry:
            _window_expiry = time.monotonic() + WINDOW_DURATION_SEC
            _create_window_flag() # Re-touch the flag with new timestamp
            logger.info(f"Job window extended. New expiry: {_window_expiry:.2f}. Flag updated.")
        elif _window_expiry is not None: # Was set, but current time is past expiry
            logger.info("Attempted to extend window, but it was already expired. Closing it.")
            _window_expiry = None
            _delete_window_flag()
        # If _window_expiry is None, extend_job_window does nothing; window must be opened first.

def close_job_window_if_expired():
    """Checks if the window is expired; if so, marks as closed and deletes the flag."""
    global _window_expiry
    with _window_lock:
        if _window_expiry is not None and time.monotonic() >= _window_expiry:
            logger.info(f"Job window expired at {_window_expiry:.2f}. Closing now and deleting flag.")
            _window_expiry = None
            _delete_window_flag()
            return True # Window was closed
    return False # Window was not closed (either not open or not expired)

def is_job_window_active() -> bool:
    """Checks if the job window is currently considered active."""
    with _window_lock:
        # Primary check is on the _window_expiry variable.
        # The flag file is a secondary signal for other processes.
        return _window_expiry is not None and time.monotonic() < _window_expiry

# -----------------------------------------------------------------------------
# Orchestrator Registration
# -----------------------------------------------------------------------------

def register_to_orchestrator(max_retries: int = 10, delay: int = 2) -> bool:
    """Register this worker capability with the orchestrator.

    Retries a few times because orchestrator might still be starting up.
    Returns True on success, False otherwise.
    """
    if not ORCH_URL:
        logger.error("ORCH_URL environment variable not set – skipping registration")
        return False

    register_req: Dict[str, Any] = {
        "url": CAPABILITY_URL,
        "name": CAPABILITY_NAME,
        "description": CAPABILITY_DESCRIPTION,
        "capacity": CAPABILITY_CAPACITY,
        "price_per_unit": CAPABILITY_PRICE_PER_UNIT,
        "price_scaling": CAPABILITY_PRICE_SCALING,
    }
    headers = {
        "Authorization": ORCH_SECRET,
        "Content-Type": "application/json",
    }

    logger.info("Attempting capability registration with orchestrator", extra={"payload": register_req})

    for attempt in range(1, max_retries + 1):
        try:
            response = requests.post(
                f"{ORCH_URL}/capability/register",
                json=register_req,
                headers=headers,
                timeout=5,
                verify=False,  # self-signed TLS in dev
            )
            if response.status_code == 200:
                logger.info("Capability successfully registered with orchestrator")
                return True
            elif response.status_code == 400:
                logger.error("Orchestrator rejected registration – check ORCH_SECRET token", extra={"status": 400})
                return False
            else:
                logger.warning("Registration attempt %s returned status %s", attempt, response.status_code)
        except requests.RequestException as exc:
            logger.warning("Registration attempt %s failed: %s", attempt, exc)

        time.sleep(delay)

    logger.error("All registration retries exhausted – giving up")
    return False

# -----------------------------------------------------------------------------
# FastAPI Application
# -----------------------------------------------------------------------------

app = FastAPI(title="NeuroSync BYOC Worker")

# Allow CORS for webapp hitting this worker directly during local dev
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
async def _startup_event():
    """Register with orchestrator on container start and ensure window flag is cleared."""
    logger.info("Application startup: Ensuring rolling window flag is initially deleted.")
    _delete_window_flag() # Clear any stale flag from a previous run
    success = register_to_orchestrator()
    if not success:
        logger.error("Registration failed – continuing to run but orchestrator will not dispatch work")

@app.on_event("shutdown")
async def _shutdown_event():
    logger.info("Application shutdown: Ensuring rolling window flag is deleted.")
    _delete_window_flag()


@app.get("/healthz", status_code=status.HTTP_200_OK)
async def healthz():
    """Simple health probe for orchestrator readiness checks."""
    return {"status": "ok"}


@app.post("/text-echo")
async def text_echo_handler(request: Request):
    """Handles requests for the text-echo capability."""
    logger.info("Received request for /text-echo capability")
    try:
        body = await request.json()
    except json.JSONDecodeError as e:
        logger.warning(f"Invalid JSON payload received at /text-echo: {e}")
        raise HTTPException(status_code=400, detail=f"Invalid JSON payload: {e}")

    text_input = body.get("text") # Expect "text" key
    if text_input is None:
        logger.warning("Missing 'text' field in JSON payload at /text-echo")
        raise HTTPException(status_code=400, detail="Missing 'text' field in JSON payload")
    
    if not isinstance(text_input, str):
        logger.warning(f"'text' field is not a string: {type(text_input)}")
        raise HTTPException(status_code=400, detail="'text' field must be a string")

    response_payload = {"echo": f"{text_input}a", "received_at": time.time()}
    logger.info(f"Responding from /text-echo: {response_payload}")
    return JSONResponse(content=response_payload)


@app.post("/v1/vtuber/start")
async def vtuber_start(request: Request):
    """Start a NeuroSync VTuber job – placeholder implementation.

    In production this should call into NeuroSync internal pipeline and stream
    Server-Sent Events or chunked JSON frames.  For now, we validate the request
    and return a dummy streaming sequence to exercise the Livepeer pipeline.
    """
    try:
        body = await request.json()
    except json.JSONDecodeError:
        logger.warning("Invalid JSON payload received at /v1/vtuber/start")
        raise HTTPException(status_code=400, detail="Invalid JSON payload")

    # Schema validation
    try:
        validate(instance=body, schema=NEUROSYNC_VTUBER_REQUEST_SCHEMA)
    except ValidationError as ve:
        logger.warning("Validation error: %s", ve)
        raise HTTPException(status_code=400, detail=f"Schema validation error: {ve.message}")

    job_id = body["job_id"]
    character = body["character"]

    # ---------------------------------------------------------------------
    # Forward the validated job to NeuroSync-Core (placeholder implementation)
    # ---------------------------------------------------------------------
    job_hash = submit_job_to_neurosync(body)

    response_payload = {
        "job_id": job_id,
        "hash": job_hash,
        "status": "accepted",
        "received_at": time.time(),
    }

    logger.info(
        "VTuber job accepted and forwarded to NeuroSync-Core",
        extra={"job_id": job_id, "character": character, "hash": job_hash},
    )

    # Return a simple JSON confirmation instead of a streaming response for now.
    # Open the rolling window now that a job is successfully accepted
    open_job_window()
    return JSONResponse(content=response_payload)


# -----------------------------------------------------------------------------
# Temporary echo endpoint for VTuber schema – lets us verify end-to-end flow  
# without implementing the full NeuroSync VTuber pipeline yet.
# -----------------------------------------------------------------------------

@app.post("/start-echo-test")
async def start_echo_test(request: Request):
    """Accepts a NeurosyncVTuberRequest payload and echoes it back.

    The orchestrator will route `/process/request/start-echo-test` here once the
    capability is registered under the same name.  This keeps the existing
    `/v1/vtuber/start` stub untouched while front-end and payment flows migrate
    to the new JSON schema.
    """
    logger.info("Received request for /start-echo-test capability")

    try:
        body = await request.json()
    except json.JSONDecodeError:
        logger.warning("Invalid JSON payload received at /start-echo-test")
        raise HTTPException(status_code=400, detail="Invalid JSON payload")

    # Schema validation – ensures front-end already sends the full VTuber
    # request structure (job_id, character, etc.)
    try:
        validate(instance=body, schema=NEUROSYNC_VTUBER_REQUEST_SCHEMA)
    except ValidationError as ve:
        logger.warning("Schema validation error at /start-echo-test: %s", ve)
        raise HTTPException(status_code=400, detail=f"Schema validation error: {ve.message}")

    # Forward to NeuroSync-Core (stub)
    job_hash = submit_job_to_neurosync(body)

    response_payload = {
        "job_id": body["job_id"],
        "hash": job_hash,
        "status": "accepted",
        "received_at": time.time(),
    }
    logger.info("VTuber job forwarded to NeuroSync-Core", extra={"job_id": body["job_id"], "hash": job_hash})

    # Job successfully accepted – open rolling window
    open_job_window()
    return JSONResponse(content=response_payload)


# -----------------------------------------------------------------------------
# Simpler ping/test endpoint for early integration testing
# -----------------------------------------------------------------------------

@app.get("/v1/byoc-test", response_model=dict)
async def byoc_test():
    """Very simple health endpoint to make sure BYOC adapter responds."""
    logger.debug("/v1/byoc-test called")
    return {"message": "BYOC worker is alive!"}


@app.post("/")
async def echo_root(req: Request):
    """
    Livepeer orchestrator will forward exactly the payload the client sent to
    /process/request/<capability_name_if_base_url_registered>.
    This root handler is now distinct from the /text-echo specific handler.
    """
    logger.info("Request to root path / received")
    try:
        body = await req.json()
    except json.JSONDecodeError:
        raise HTTPException(status_code=400, detail="Invalid JSON payload")

    text = body.get("text", "")
    # Differentiate response to avoid confusion if this is hit unexpectedly
    return {"echo_from_root": text, "received_at": time.time(), "message": "This is the root handler, not /text-echo"}


# -----------------------------------------------------------------------------
# Placeholder integration with NeuroSync-Core
# -----------------------------------------------------------------------------

def submit_job_to_neurosync(payload: Dict[str, Any]) -> str:
    """Forward a VTuber job request to the local NeuroSync-Core server.

    This function attempts to POST the payload to the configured
    NEUROSYNC_CORE_JOB_URL. It returns a mock hash for the UI.
    The actual NeuroSync-Core endpoint is expected to handle the job and
    can, for now, simply print that the job was received.
    """
    job_id = payload.get("job_id")
    logger.info(
        f"Attempting to forward job to NeuroSync-Core at {NEUROSYNC_CORE_JOB_URL}",
        extra={"job_id": job_id, "target_url": NEUROSYNC_CORE_JOB_URL}
    )
    # 1️⃣ Try direct in-process import first to avoid HTTP overhead
    try:
        from neurosync.cli.client import accept_vtuber_job  # type: ignore

        job_hash = accept_vtuber_job(payload)
        logger.info(
            "Job handled via internal accept_vtuber_job",
            extra={"job_id": job_id, "hash": job_hash}
        )
        return job_hash
    except ImportError as imp_err:
        logger.warning(
            "Could not import accept_vtuber_job – falling back to HTTP",
            extra={"job_id": job_id, "error": str(imp_err)}
        )

    # 2️⃣ Fallback to HTTP POST to NeuroSync-Core if import failed or not available
    try:
        response = requests.post(NEUROSYNC_CORE_JOB_URL, json=payload, timeout=10)
        response.raise_for_status()
        logger.info(
            "Successfully forwarded job to NeuroSync-Core via HTTP",
            extra={"job_id": job_id, "status_code": response.status_code}
        )
        # Optionally read real hash from response:
        # core_response_data = response.json(); return core_response_data.get("job_hash", fallback_hash)
    except requests.RequestException as e:
        logger.error(
            "Failed to forward job to NeuroSync-Core via HTTP",
            extra={"job_id": job_id, "error": str(e)}
        )

    # Produce a pseudo-random but valid hex hash for the UI (as per current accepted behavior)
    mock_hash = hashlib.sha256(secrets.token_bytes(32)).hexdigest()
    logger.debug(
        "Generated mock hash for job",
        extra={"job_id": job_id, "hash": mock_hash}
    )
    return mock_hash


# -----------------------------------------------------------------------------
# FastAPI middleware – gate all endpoints (except /healthz) behind the window
# -----------------------------------------------------------------------------

from starlette.responses import JSONResponse as _StarletteJSON


@app.middleware("http")
async def _window_guard(request: Request, call_next):
    # Allow healthz regardless
    if request.url.path == "/healthz":
        return await call_next(request)

    close_job_window_if_expired() # Check for and handle expirations first

    request_path = request.url.path

    if request_path in WINDOW_INITIATING_PATHS:
        # These paths are allowed to proceed to attempt to open a window.
        # The handler for these paths MUST call open_job_window() on success.
        logger.debug(f"Request to window-initiating path {request_path} allowed to proceed.")
        # No explicit window extension here; handler is responsible for opening.
    elif not is_job_window_active():
        # For non-initiating paths, window must be active.
        with _window_lock:
            current_expiry_for_log = _window_expiry
        flag_exists_for_log = os.path.exists(WINDOW_ACTIVE_FLAG_PATH)
        logger.warning(
            f"Access denied to {request_path}: Job window not active. "
            f"Current expiry state: {current_expiry_for_log}, Flag exists: {flag_exists_for_log}"
        )
        return _StarletteJSON({"error": "Worker is idle – no active job window"}, status_code=403)
    else:
        # Window is active, and it's not an initiating path (or we don't care if it is, window is already open)
        # Extend its life on any activity.
        extend_job_window()
        logger.debug(f"Window active, request to {request_path} allowed. Window extended.")

    return await call_next(request)


# -----------------------------------------------------------------------------
# CLI entrypoint when executed via `

if __name__ == "__main__":
    import uvicorn

    # Default host/port fallbacks
    host = os.getenv("SERVER_HOST", "0.0.0.0")
    port = SERVER_PORT  # already int via env cast at top

    logger.info(
        "Starting BYOC adapter via uvicorn", extra={"host": host, "port": port}
    )

    # The `factory` style string import ensures reloads work the same whether this file
    # is executed as a script or as a module.  It also avoids potential path issues if
    # the CWD is not /app.
    uvicorn.run("server_adapter:app", host=host, port=port, log_level="info")