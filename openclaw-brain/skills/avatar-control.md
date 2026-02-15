# Skill: Avatar Control

## Purpose
Control the Unreal Engine avatar via the script-runner TCP API.

## Connection
- **Endpoint:** http://unreal-game:9877 (script-runner REST API)
- **TCP direct:** 127.0.0.1:7777 (game TCP for raw commands)

## Available Commands

### Emotes
- `POST /api/emote` — `{"emote": "wave|nod|laugh|surprised|thinking|sad|dance"}`

### Camera
- `POST /api/camera` — `{"preset": "close-up|medium|wide|dramatic"}`
- `POST /api/camera/move` — `{"x": float, "y": float, "z": float, "duration": float}`

### Speech
- Text-to-speech is handled by the chat pipeline. The avatar lip-syncs
  automatically when the TTS audio plays.

### Scene
- `POST /api/scene` — `{"action": "change_background|toggle_prop", "params": {...}}`

## Usage Tips
- Pair emotes with chat responses for more engaging streams
- Use camera changes to emphasise important moments
- Don't spam emotes — one per response is usually enough
