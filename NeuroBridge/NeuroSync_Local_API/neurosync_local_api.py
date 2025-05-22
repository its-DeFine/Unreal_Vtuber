# This software is licensed under a **dual-license model**
# For individuals and businesses earning **under $1M per year**, this software is licensed under the **MIT License**
# Businesses or organizations with **annual revenue of $1,000,000 or more** must obtain permission to use this software commercially.

import torch
import os
import numpy as np
from flask import Flask, request, jsonify
from flask_cors import CORS

# Assuming your model and utilities are structured as shown
from utils.model.model import load_model
from utils.generate_face_shapes import generate_facial_data_from_bytes
from utils.config import config as config_data

app = Flask(__name__)
CORS(app)

# ---------------------------------------------------------------------------
# Shared Cognitive Blackboard (SCB) Endpoints
# ---------------------------------------------------------------------------

# NOTE: These routes expose the SCB in a minimal form so that external
#       services (e.g. Eliza/the-org Conductor) can consume a live slice or
#       publish directives.  The implementation is intentionally thin and
#       delegates all state handling to utils.scb.scb_store which already
#       supports Redis-backed storage as well as an in-memory fallback.  To
#       enable cross-process sharing inside the container, make sure the
#       environment variable USE_REDIS_SCB=true and a Redis instance is
#       available (docker-compose.bridge.yml already provides this).

from utils.scb import scb_store  # noqa: E402 – imported after Flask creation

# Optional very lightweight API-key guard.  If NEUROSYNC_API_KEY is set, every
# incoming request must include the same value in the X-NeuroSync-Key header.
_API_KEY = os.getenv("NEUROSYNC_API_KEY")


def _check_api_key() -> bool:
    """Return True if request contains a valid API key (or none configured)."""
    if not _API_KEY:  # No key configured – public endpoint (dev default)
        return True
    return request.headers.get("X-NeuroSync-Key") == _API_KEY


def _unauthorized_response():
    return jsonify({"error": "Unauthorized"}), 401


# ------------------------------  GET /scb/ping  -----------------------------


@app.route("/scb/ping", methods=["GET"])
def scb_ping():
    """Lightweight health probe used by docker-compose healthcheck."""
    if not _check_api_key():
        return _unauthorized_response()
    return jsonify({"status": "ok"})


# ---------------------------  GET /scb/slice  ------------------------------


@app.route("/scb/slice", methods=["GET"])
def scb_slice():
    """Return a summary + window slice of the SCB.

    Query params:
      tokens (int): Approx token budget.  Currently we approximate 1 token ≈ 1
                    word for a quick heuristic.  The slice always includes the
                    full summary and then back-fills the log window until the
                    budget is reached.
    """
    if not _check_api_key():
        return _unauthorized_response()

    try:
        token_budget = int(request.args.get("tokens", "600"))
    except ValueError:
        token_budget = 600

    full = scb_store.get_full()
    summary = full.get("summary", "")
    window = full.get("window", [])  # list of dict entries (oldest→newest)

    # Very naive token accounting – count words until budget reached.
    # We iterate from newest to oldest so we keep the most recent context.
    remaining = max(token_budget, 0)
    selected = []
    for entry in reversed(window):
        text = str(entry.get("text", ""))
        token_estimate = len(text.split())
        if remaining - token_estimate < 0:
            break
        selected.append(entry)
        remaining -= token_estimate

    # Reverse again so caller gets chronological order (oldest→newest)
    selected_window = list(reversed(selected))

    return jsonify({"summary": summary, "window": selected_window})


# ---------------------------  POST /scb/event  -----------------------------


@app.route("/scb/event", methods=["POST"])
def scb_event():
    """Append a generic event entry to the SCB log."""
    if not _check_api_key():
        return _unauthorized_response()

    payload = request.get_json(silent=True) or {}
    if not isinstance(payload, dict):
        return jsonify({"error": "Invalid JSON payload"}), 400

    scb_store.append(payload)
    return jsonify({"status": "ok"})


# -------------------------  POST /scb/directive  ---------------------------


@app.route("/scb/directive", methods=["POST"])
def scb_directive():
    """Convenience wrapper to append a directive entry."""
    if not _check_api_key():
        return _unauthorized_response()

    payload = request.get_json(silent=True) or {}
    if not isinstance(payload, dict):
        return jsonify({"error": "Invalid JSON payload"}), 400

    text = payload.get("text", "").strip()
    actor = payload.get("actor", "planner")
    ttl = int(payload.get("ttl", 15)) if str(payload.get("ttl", "")).isdigit() else 15

    if not text:
        return jsonify({"error": "'text' is required"}), 400

    scb_store.append_directive(text=text, actor=actor, ttl=ttl)
    return jsonify({"status": "ok"})

# Load configuration and model
config = config_data
# Force CPU usage
# device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
device = torch.device('cpu')
blendshape_model = load_model(config["model_path"], config, device)

print(f" * Using device: {device}")  # Log the device being used

@app.route('/audio_to_blendshapes', methods=['POST'])
def audio_to_blendshapes_route():
    # if 'audio' not in request.files:
    #     return jsonify({"error": "No audio file part"}), 400
    # audio_bytes = request.files['audio'].read()
    audio_bytes = request.data # Use request.data again
    generated_facial_data = generate_facial_data_from_bytes(audio_bytes, blendshape_model, device, config)
    generated_facial_data_list = generated_facial_data.tolist() if isinstance(generated_facial_data, np.ndarray) else generated_facial_data
    return jsonify({'blendshapes': generated_facial_data_list})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
