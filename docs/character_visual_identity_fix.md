# Character Visual Identity Fix Documentation
*Created: 2025-07-14 22:35*

## Issue Summary

The visual identity system was not being triggered when characters were activated due to an API endpoint mismatch between S2 (orchestrator) and S1 (avatar) systems.

### Root Cause
- **S2 System** was calling `POST /character/activate` when switching characters
- **S1 System** only had `POST /character/switch` endpoint
- This resulted in 404 errors, preventing character switches and visual identity updates

## The Fix

### Solution: Add Compatibility Endpoint
Added `/character/activate` endpoint to S1 as an alias for the existing `/character/switch` functionality:

```python
@app.route("/character/activate", methods=['POST'])
def handle_character_activate():
    """Activate a character (alias for switch) - for S2 compatibility"""
    app.logger.info("🔄 /character/activate called - redirecting to switch")
    return handle_character_switch()
```

### Files Modified
- `/docker-vtuber/app/AVATAR/NeuroBridge/NeuroSync_Player/llm_to_face.py`
  - Added `/character/activate` endpoint
  - Updated startup message to list all character endpoints

## How Visual Identity Works

### 1. Character Configuration
Each character profile includes visual identity settings:
```python
visual_identity: {
    "preset_name": "emerald_elegance",
    "tcp_commands": [
        "PRS.Fem",           # Preset selection
        "OF.MaidDress",      # Outfit
        "HS.Long",           # Hair style
        "HCR.0.2",          # Hair color RGB
        "HCG.0.8",
        "HCB.0.3",
        "EC.0.5",           # Eye color
        "ES.35000.0"        # Eye saturation
    ]
}
```

### 2. Character Activation Flow
```
S2 Orchestrator                S1 Avatar System              Unreal Engine
      |                              |                            |
      |--POST /character/activate--->|                            |
      |  {character_id: "emma"}      |                            |
      |                              |                            |
      |                              |--switch_character()        |
      |                              |                            |
      |                              |--apply_visual_identity()   |
      |                              |                            |
      |                              |--TCP Commands------------->|
      |                              |  PRS.Fem, OF.MaidDress... |
      |                              |                            |
      |<---200 OK {success}----------|<---TCP ACK----------------|
```

### 3. Key Components

#### Visual Identity Manager (`visual_identity_manager.py`)
- Manages TCP connection to Unreal Engine
- Sends visual appearance commands
- Tracks current visual identity state
- Optimizes command delays for smooth transitions

#### Character Manager (`character_config.py`)
- Stores character profiles with visual identities
- Handles character switching logic
- Applies visual identity during switch
- Prevents redundant updates if already on same preset

#### TCP Controller (`unreal_tcp_controller.py`)
- Maintains connection to Unreal Engine on port 7777
- Sends individual commands with appropriate delays
- Handles connection failures gracefully
- Provides batch command support

## Testing the Fix

### Manual Testing
1. Start the containers:
   ```bash
   docker-compose -f docker-compose.all.yml up
   ```

2. Test character activation:
   ```bash
   # Test new endpoint
   curl -X POST http://localhost:5001/character/activate \
     -H "Content-Type: application/json" \
     -d '{"character_id": "emma_educator"}'
   
   # Test original endpoint (should still work)
   curl -X POST http://localhost:5001/character/switch \
     -H "Content-Type: application/json" \
     -d '{"character_id": "dr_house_trader"}'
   ```

3. Observe Unreal Engine for visual changes

### Automated Testing
Run the test script:
```bash
cd /home/geo/directories/autonomy
python tests/test_character_activation_fix.py
```

## Visual Identity Command Reference

### Preset Commands
- `PRS.Fem` - Feminine preset
- `PRS.Masc` - Masculine preset

### Outfit Commands
- `OF.Default` - Default outfit
- `OF.BusinessSuit` - Business attire
- `OF.MaidDress` - Maid outfit
- `OF.CasualWear` - Casual clothing

### Hair Commands
- `HS.Long` - Long hair style
- `HS.Short` - Short hair style
- `HCR.{0-1}` - Hair color red component
- `HCG.{0-1}` - Hair color green component
- `HCB.{0-1}` - Hair color blue component

### Eye Commands
- `EC.{0-1}` - Eye color
- `ES.{value}.0` - Eye saturation

## Troubleshooting

### Visual Identity Not Applying
1. Check TCP connection to Unreal Engine:
   - Verify port 7777 is accessible
   - Check `host.docker.internal` resolves correctly

2. Verify character has visual_identity defined:
   ```bash
   curl http://localhost:5001/character/current
   ```

3. Check logs for errors:
   ```bash
   docker logs neurosync_s1 | grep -E "visual|TCP|character"
   ```

### Character Not Switching
1. Verify character exists:
   ```bash
   curl http://localhost:5001/character/list
   ```

2. Check S2 logs for forwarding errors:
   ```bash
   docker logs autogen_s2 | grep "character/activate"
   ```

## Future Improvements

1. **Unified API**: Consider standardizing on one endpoint name across systems
2. **Visual Preview**: Add endpoint to preview visual changes without applying
3. **Transition Effects**: Add support for smooth visual transitions
4. **State Persistence**: Save last visual identity to restore on restart
5. **Error Recovery**: Implement retry logic for failed TCP commands