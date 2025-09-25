# Private Creator Workspace

This directory stores local-only assets required for generating VTuber scripts:

- `.env` – place your `OPENAI_API_KEY`, `ELEVENLABS_API_KEY`, optional `ELEVENLABS_VOICE_ID`, `ELEVENLABS_MODEL_ID`, and `VTUBER_RUNNER_URL` here. The generator loads it automatically.
- `generated_scripts/` – audio clips, plan JSON, and script payloads produced by `generate_vtuber_program.py`.

## Usage

```bash
cd autonomy/private_creator
python3 generate_vtuber_program.py \
  --prompt "Announce the new product launch" \
  --session-id launch-demo
```

By default the script writes artefacts under `generated_scripts/<session-id>/` and POSTs the plan to the Unreal script runner at `VTUBER_RUNNER_URL`. Add `--no-send` to skip the POST.

Both paths are git-ignored so secrets and large binaries never leave your workstation.
