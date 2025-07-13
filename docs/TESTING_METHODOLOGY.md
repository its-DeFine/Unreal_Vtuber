# 📐 Incremental Testing & Improvement Methodology

*Created: 2025-07-13*

---

## Overview

This document defines the **phased approach** we will follow to systematically improve and benchmark the Autonomous VTuber System.  The workflow is strictly *test → measure → fix → retest* for each major subsystem, starting with **System 1 (S1)** and ending with the **Stimuli Processor**.

> **Why this order?**  S1 is the primary user-facing bottleneck and RTMP gateway; a rock-solid, sub-second S1 is prerequisite for reliable SCB usage, which in turn is prerequisite for advanced S2 coordination and smart stimuli routing.

---

## Phase 1 – S1 Performance & RTMP Testing  ✅ *Current Focus*

| Goal | Target | Success Metric |
|------|--------|---------------|
| Minimise end-to-end latency | `POST /process_text` → WAV written → RTMP pushed | **< 1 s** P95 |
| Guarantee stability | 1-hour soak test, 100 req/min | **0 errors** |
| Produce actionable logs | Timestamp **on receive** & **on WAV write** | Logs parseable by tests |

### Implementation Steps
1. **Add precise timestamps** in NeuroSync Player logs:
   * `LOG «S1_RECEIVED» {stimuli_id}` on request reception.
   * `LOG «S1_WAV_READY» {stimuli_id}` after WAV is saved.
2. **Create pytest benchmark** `tests/s1/perf/test_s1_latency.py` that:
   * Fires N requests (configurable).
   * Parses container logs via Docker API.
   * Calculates latency per request and asserts P95 < threshold.
3. **RTMP verification** script `tests/s1/rtmp/test_rtmp_stream.py` that:
   * Subscribes to the configured RTMP endpoint.
   * Confirms audio frames appear < 300 ms after `S1_WAV_READY`.
4. **Logging location**: All raw and summary logs archived under `/logs/s1/` (root-level `logs/` folder).

### Failure Handling
* If **latency ≥ threshold** → profile TTS/LLM pipeline, identify slow segments, patch, and rerun tests.
* If **RTMP gap > 300 ms** → inspect FFmpeg pipeline and network IO.

---

## Phase 2 – S2 Performance & Tool Utilisation

| Goal | Target | Success Metric |
|------|--------|---------------|
| Fast multi-agent reasoning | Trader/Educator/Streamer teams | **< 2 s** P95 total processing |
| Correct tool usage | AutoGen `tool_call` events vs. planned tools | **100 %** alignment |
| Comprehensive logging | Tool decisions & durations | Logs in `/logs/s2/` |

### Test Suite
* `tests/s2/perf/test_team_latency.py` – measures end-to-end team processing time.
* `tests/s2/tools/test_tool_usage.py` – validates that mandatory tools (`market_data`, `curriculum_builder`, etc.) are invoked.

### Iteration Loop
1. Run tests → 2. Patch slow/incorrect code → 3. Re-run until green.

---

## Phase 3 – SCB (Shared Cognitive Blackboard) Redesign & Validation

### Design Requirements
1. **Dual-layer SCB**
   * **Team-local SCB** – private to each S2 team.
   * **Global SCB** – readable/writable by all teams **and** S1.
2. **Access Patterns**
   * **S1** reads global SCB **every prompt** after the first.
   * **S2** agents read/write both their local SCB and the global SCB.
3. **Isolation Guarantees** – teams cannot read/write other teams’ local SCB.
4. **API** – minimal Redis-backed interface: `scb.set_slice`, `scb.get_slice`, `scb.append_event`.

### Implementation Milestones
| Step | Output |
|------|--------|
| 1 | Architectural RFC (`docs/scb/SCB_REDESIGN_RFC.md`) |
| 2 | Prototype Redis schema + client library (`autogen_agent/clients/scb_v2_client.py`) |
| 3 | Unit tests (`tests/scb/`) ensuring isolation & global-access behaviours |
| 4 | Integration tests with S1 & S2 (`tests/integration/test_scb_flow.py`) |

### Success Metrics
* **< 5 ms** read/write latency (Redis P95).
* **100 %** test pass rate across isolation and access patterns.

---

## Phase 4 – Stimuli Processor Optimisation

### Objectives
1. **Ultra-fast routing** – decision time **< 10 ms**.
2. **Accurate system choice** – ≥ 95 % correct mode (`s1_only`, `s2_only`, `s1_and_s2`).
3. **Clean abstraction** – decouple NLP analysis from HTTP orchestration.

### Planned Actions
1. Profiling current `StimuliProcessor` → identify NLP bottlenecks.
2. Evaluate lightweight ML models (e.g., sentence-transformers) or rule-based hybrid for intent detection.
3. Refactor into separate module `stimuli_router_v2.py` with clear interfaces.
4. Build benchmark `tests/stimuli/test_router_latency_and_accuracy.py` using labelled dataset.

### Completion Criteria
* Benchmarks green (latency & accuracy).
* All existing integration tests pass.

---

## Directory Layout Additions
```
logs/
├── s1/
│   ├── raw/               # raw container or application logs
│   └── summaries/         # CSV/JSON metrics per test run
├── s2/
│   ├── raw/
│   └── summaries/
└── scb/
    └── design_notes/
```

Tests live under `tests/` with the same sub-directory structure (`tests/s1/`, `tests/s2/`, `tests/scb/`, `tests/stimuli/`).

---

## Continuous Integration Note
Each phase will add its new tests to the CI pipeline (`.github/workflows/ci.yml`).  The pipeline will fail if any performance budget or functional assertion is violated, ensuring regressions are caught immediately.

---

### Change Log
* **v1.0** – Initial methodology drafted based on user requirements (2025-07-13) 