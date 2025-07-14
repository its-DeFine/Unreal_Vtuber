# Orchestrator Tests

This directory contains tests for the VTuber system orchestrator.

## Test Files

### Core Orchestrator Tests
- **`test_orchestrator_integration.py`** - Tests basic orchestrator functionality:
  - Health checks
  - API registry loading
  - Routing decisions (S1 vs S2)
  - Latency requirements (<10ms)
  - Persona assignment

- **`test_full_execution.py`** - Tests complete execution flow:
  - End-to-end stimulus processing
  - Route + execute combined endpoint
  - Response verification
  - S1/S2 communication

### Visual Identity Tests
- **`test_visual_identity_switching.py`** - Tests character visual switching:
  - Direct S1 character switching
  - Orchestrator-routed character changes
  - Visual preset verification

- **`test_visual_clean_switch.py`** - Tests clean visual transitions:
  - Speech stopping before character switch
  - No audio overlap between characters
  - Proper visual identity application
  - Complete switching cycle

## Running Tests

### Run all tests:
```bash
./run_tests.sh
```

### Run specific test:
```bash
python3 test_visual_clean_switch.py
```

### Run with pytest:
```bash
pytest test_orchestrator_integration.py -v
```

## Test Requirements
- Docker containers must be running:
  - `vtuber_orchestrator` (port 8082)
  - `neurosync_s1` (port 5001)
  - `vtuber-ollama` (port 11434)

## Visual Identity Testing
The visual tests verify that:
1. Characters switch based on orchestrator persona routing
2. Visual appearances change in Unreal Engine via TCP
3. Speech stops cleanly between character switches
4. Each character has distinct visual identity:
   - Sophia Trader: Golden Goddess (blonde)
   - Diana Educator: Emerald Elegance (green)
   - Luna Streamer: Ruby Sensation (red/pink)