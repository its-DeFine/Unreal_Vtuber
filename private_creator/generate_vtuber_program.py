#!/usr/bin/env python3
"""Generate and submit VTuber scripts based on a natural-language prompt.

Responsibilities:
1. Ask OpenAI to decompose the prompt into timed actions (audio + TCP commands)
   constrained by `backend_logic/TCP_Controller_Documentation.md`.
2. Render audio segments with ElevenLabs (short filenames, MP3 format).
3. Package the script payload expected by the Unreal script runner and optionally
   POST it to `/scripts/execute`.

Environment (loaded from `private_creator/.env` if present):
  OPENAI_API_KEY
  ELEVENLABS_API_KEY
  ELEVENLABS_VOICE_ID (optional, default `21m00Tcm4TlvDq8ikWAM`)
  ELEVENLABS_MODEL_ID (optional, default `eleven_multilingual_v2`)
  VTUBER_RUNNER_URL (optional default for `--runner-url`)
"""
from __future__ import annotations

import argparse
import base64
import json
import os
import re
import textwrap
import uuid
from pathlib import Path
from typing import Dict, List, Tuple

import requests
from openai import OpenAI

REPO_ROOT = Path(__file__).resolve().parents[2]
PRIVATE_DIR = Path(__file__).resolve().parent
DEFAULT_OUTPUT_DIR = PRIVATE_DIR / "generated_scripts"
TCP_DOC = REPO_ROOT / "backend_logic" / "TCP_Controller_Documentation.md"
TCP_REFERENCE = TCP_DOC.read_text(encoding="utf-8") if TCP_DOC.exists() else ""

DEFAULT_VOICE_ID = "21m00Tcm4TlvDq8ikWAM"
DEFAULT_MODEL_ID = "eleven_multilingual_v2"
SCRIPT_RUNNER_TIMEOUT = 60

SYSTEM_PROMPT = textwrap.dedent(
    f"""
    You plan scripted performances for a VTuber who can speak via ElevenLabs
    audio clips and execute TCP commands (appearance changes, gestures). Produce
    concise JSON describing the steps needed to fulfil the user's prompt.

    Available TCP commands and their semantics:
    {TCP_REFERENCE}

    Guidelines:
    - Keep the total runtime under 60 seconds.
    - Group speech into natural segments of 5-15 seconds.
    - Include occasional TCP commands when helpful, but no more than one command
      between audio segments.
    - For audio steps, supply the exact text to speak. Filenames must be short
      (<=12 characters), simple ASCII snake_case with `.mp3` extension.
    - Use only commands listed in the reference above. If no command is
      necessary, leave the `command` field as an empty string.
    - For command-only steps leave the `text` and `filename` fields as empty
      strings.
    - Always include a delay_ms value (0 is acceptable).
    - delay_ms specifies the pause before the step runs.
    Respond strictly in JSON conforming to the provided schema.
    """
)

JSON_SCHEMA = {
    "name": "vtuber_program",
    "schema": {
        "type": "object",
        "additionalProperties": False,
        "properties": {
            "summary": {"type": "string"},
            "steps": {
                "type": "array",
                "minItems": 1,
                "maxItems": 8,
                "items": {
                    "type": "object",
                    "additionalProperties": False,
                    "properties": {
                        "type": {"enum": ["audio", "command"]},
                        "text": {"type": "string"},
                        "command": {"type": "string"},
                        "delay_ms": {"type": "integer", "minimum": 0},
                        "filename": {
                            "type": "string",
                            "pattern": r"^$|^[a-z0-9_\-]+\.mp3$",
                        },
                    },
                    "required": ["type", "text", "command", "delay_ms", "filename"],
                },
            },
        },
        "required": ["summary", "steps"],
    },
}


def load_private_env() -> None:
    env_path = PRIVATE_DIR / ".env"
    if not env_path.exists():
        return
    for line in env_path.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#") or "=" not in stripped:
            continue
        key, value = stripped.split("=", 1)
        os.environ.setdefault(key.strip(), value.strip())


def call_openai(prompt: str) -> Dict:
    client = OpenAI()
    configured_model = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
    model = configured_model if not configured_model.startswith("o3") else "gpt-4o-mini"
    base_kwargs = {
        "model": model,
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": prompt},
        ],
    }
    response_formats = [
        {
            "type": "json_schema",
            "json_schema": {**JSON_SCHEMA, "strict": True},
        },
        {"type": "json_object"},
        None,
    ]

    last_error: Exception | None = None

    for fmt in response_formats:
        kwargs = dict(base_kwargs)
        if fmt is not None:
            kwargs["response_format"] = fmt
        try:
            response = client.chat.completions.create(**kwargs)
        except TypeError as exc:
            if fmt is not None and "response_format" in str(exc):
                last_error = exc
                continue
            raise RuntimeError(f"OpenAI chat completion failed: {exc}") from exc
        except Exception as exc:  # pragma: no cover - surface useful diagnostics
            raise RuntimeError(f"OpenAI chat completion failed: {exc}") from exc

        message = response.choices[0].message  # type: ignore[index]
        parsed = getattr(message, "parsed", None)
        if isinstance(parsed, dict):
            return parsed

        content = getattr(message, "content", None)
        if not content:
            last_error = RuntimeError("Model returned an empty response")
            continue
        try:
            return json.loads(content)
        except json.JSONDecodeError as exc:
            last_error = exc
            if fmt is not None:
                continue
            raise RuntimeError(f"Model returned invalid JSON:\n{content}") from exc

    if last_error is not None:
        raise RuntimeError(f"Unable to parse model output: {last_error}") from last_error
    raise RuntimeError("Model did not return parsable content")


def elevenlabs_tts(text: str, voice_id: str, outfile: Path, model_id: str) -> None:
    url = f"https://api.elevenlabs.io/v1/text-to-speech/{voice_id}"
    headers = {
        "accept": "audio/mpeg",
        "xi-api-key": os.environ["ELEVENLABS_API_KEY"],
        "content-type": "application/json",
    }
    payload = {"text": text, "model_id": model_id}
    resp = requests.post(url, headers=headers, json=payload, timeout=60)
    if resp.status_code != 200:
        raise RuntimeError(
            f"ElevenLabs synthesis failed ({resp.status_code}): {resp.text[:200]}"
        )
    outfile.parent.mkdir(parents=True, exist_ok=True)
    outfile.write_bytes(resp.content)


def normalize_filename(candidate: str | None, idx: int) -> str:
    base = Path(candidate).stem if candidate else f"segment_{idx:02d}"
    base = base.lower()
    base = re.sub(r"[^a-z0-9_-]", "", base)
    if len(base) > 8:
        base = base[:8]
    if not base:
        base = f"seg{idx:02d}"
    return f"{base}.mp3"


def build_script_payload(
    steps: List[Dict],
    audio_dir: Path,
    voice_default: str,
    model_default: str,
) -> Tuple[Dict, Dict[str, Tuple[str, str, str, Path]]]:
    commands: List[Dict] = []
    audio_assets: List[Dict] = []
    file_map: Dict[str, Tuple[str, str, str, Path]] = {}

    for idx, step in enumerate(steps, start=1):
        delay_ms = int(step.get("delay_ms", 0))
        step_command = step.get("command", "")
        if step["type"] == "command":
            if not step_command:
                continue  # harmless no-op command step
            commands.append({"type": "tcp", "value": step_command, "delay_ms": delay_ms})
            continue

        filename = normalize_filename(step.get("filename"), idx)
        asset_id = Path(filename).stem
        voice_label = step.get("voice", "default")
        voice_id = voice_default if voice_label == "default" else voice_label
        model_id = model_default
        text = step.get("text", "").strip()
        if not text:
            raise RuntimeError(f"Audio step {idx} missing narration text")
        output_path = audio_dir / filename

        commands.append({"type": "audio", "id": asset_id, "delay_ms": delay_ms})
        asset_entry = {
            "id": asset_id,
            "filename": filename,
            "payload_b64": None,
        }
        if "duration_ms" in step:
            asset_entry["duration_ms"] = int(step["duration_ms"])
        audio_assets.append(asset_entry)
        file_map[asset_id] = (text, voice_id, model_id, output_path)

    payload = {"commands": commands, "audio": audio_assets}
    return payload, file_map


def encode_audio_assets(
    payload: Dict,
    file_map: Dict[str, Tuple[str, str, str, Path]],
) -> None:
    for asset in payload["audio"]:
        asset_id = asset["id"]
        text, voice_id, model_id, outfile = file_map[asset_id]
        elevenlabs_tts(text, voice_id, outfile, model_id)
        asset["payload_b64"] = base64.b64encode(outfile.read_bytes()).decode("utf-8")


def post_script(runner_url: str, session_id: str, payload: Dict, callback_url: str | None) -> Dict:
    body = {"session_id": session_id, **payload}
    if callback_url:
        body["callback_url"] = callback_url
    resp = requests.post(
        runner_url.rstrip("/") + "/scripts/execute",
        json=body,
        timeout=SCRIPT_RUNNER_TIMEOUT,
    )
    resp.raise_for_status()
    return resp.json()


def main() -> None:
    load_private_env()
    parser = argparse.ArgumentParser(description="Generate a VTuber program from a prompt")
    parser.add_argument("--prompt", required=True, help="High-level directive")
    parser.add_argument(
        "--runner-url",
        default=os.getenv("VTUBER_RUNNER_URL"),
        help="Script runner base URL (default env VTUBER_RUNNER_URL)",
    )
    parser.add_argument("--session-id", help="Override session ID")
    parser.add_argument(
        "--output-dir",
        default=str(DEFAULT_OUTPUT_DIR),
        help="Directory to store plan/script/audio",
    )
    parser.add_argument("--callback-url", help="Status callback URL")
    parser.add_argument("--no-send", action="store_true", help="Generate assets without POSTing")
    args = parser.parse_args()
    runner_url = args.runner_url
    if not runner_url and not args.no_send:
        raise SystemExit("Provide --runner-url or set VTUBER_RUNNER_URL in .env")

    if "OPENAI_API_KEY" not in os.environ:
        raise SystemExit("OPENAI_API_KEY is required")
    if "ELEVENLABS_API_KEY" not in os.environ:
        raise SystemExit("ELEVENLABS_API_KEY is required")

    voice_default = os.getenv("ELEVENLABS_VOICE_ID", DEFAULT_VOICE_ID)
    model_default = os.getenv("ELEVENLABS_MODEL_ID", DEFAULT_MODEL_ID)

    session_id = args.session_id or f"program-{uuid.uuid4().hex[:8]}"
    output_dir = Path(args.output_dir)
    audio_dir = output_dir / session_id / "audio"

    plan = call_openai(args.prompt)
    print(json.dumps(plan, indent=2))

    payload, file_map = build_script_payload(plan["steps"], audio_dir, voice_default, model_default)
    encode_audio_assets(payload, file_map)

    session_path = output_dir / session_id
    session_path.mkdir(parents=True, exist_ok=True)
    (session_path / "plan.json").write_text(json.dumps(plan, indent=2), encoding="utf-8")
    (session_path / "script.json").write_text(
        json.dumps({"session_id": session_id, **payload}, indent=2), encoding="utf-8"
    )

    if args.no_send:
        print(f"Script written to {session_path} (not sent)")
        return

    response = post_script(runner_url, session_id, payload, args.callback_url)
    print("Runner response:", json.dumps(response, indent=2))


if __name__ == "__main__":
    main()
