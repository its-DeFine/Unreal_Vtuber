# Capture Storage Pipeline

This guide describes how to collect Pixel Streaming captures from orchestrator hosts and push them into the storage unit (formerly the `private_creator` box).

## Components

- **Storage service** (`storage_service/app.py`): a small FastAPI app that accepts WebM uploads and stores them under `captures/<orchestrator>/<session>/<timestamp>.webm`.
- **Uploader script** (`scripts/upload_capture.py`): CLI helper that orchestrator jobs can call after generating a recording.

## Running the storage service

```sh
# on the storage unit EC2
cd autonomy
python -m venv .venv
source .venv/bin/activate
pip install -r storage_service/requirements.txt
STORAGE_SERVICE_ROOT=/data/captures \
STORAGE_SERVICE_TOKEN=supersecret \
python -m storage_service
```

By default the service listens on `0.0.0.0:9000`. Set `STORAGE_SERVICE_PORT` if you need a different port.

## Uploading from an orchestrator

1. Record the session (for example using the Playwright recorder container).
2. Run the uploader:

```sh
python scripts/upload_capture.py \
    /path/to/capture/webm \
    session-20250927 \
    http://storage-unit:9000 \
    --orchestrator-id orch-alpha \
    --token supersecret
```

The script prints the JSON response indicating where the file was stored.

## API quick reference

- `POST /api/captures` – upload a file (`multipart/form-data` with `file`, `session_id`, optional `orchestrator_id`).
- `GET /api/captures` – list stored captures (optional `orchestrator_id` query).
- `GET /api/captures/{orchestrator}/{session}/{filename}` – download an individual capture.

Include the `X-Storage-Token` header when `STORAGE_SERVICE_TOKEN` is set.
