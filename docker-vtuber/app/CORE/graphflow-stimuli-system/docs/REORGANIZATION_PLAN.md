# GraphFlow Stimuli System Reorganization Plan

## Current Structure Analysis

The graphflow-stimuli-system is already fairly well-organized with:
- `src/` containing all source code
- `docs/` with comprehensive documentation
- `config/` with configuration files
- `docker/` with Docker configurations
- `monitoring/` with Grafana/Prometheus setup
- Tests already in `/docker-vtuber/tests/core/graphflow/`

## Proposed Improvements

### 1. Move Demo/Example Files
- Move `stimuli_emulation_demo.py` → `examples/`
- Move `run_tests.py` → `scripts/` or integrate into pytest

### 2. Create Scripts Directory
- Create `scripts/` for utility scripts
- Move `run.py` → `scripts/run.py` (or keep as main entry point)

### 3. Clean Up Root Directory
- Keep only essential files in root:
  - `README.md`
  - `setup.py`
  - `requirements.txt`
  - `pytest.ini`
  - `docker-compose.yml`
- Move analysis/report files to `docs/reports/`:
  - `PIPELINE_FLOW_ANALYSIS.md`
  - `SECURITY_AUDIT_REPORT.md`
  - `VERIFICATION_REPORT.md`

### 4. Improve Source Organization
The `src/` directory is already well-structured:
- `api_server.py` - Main API server
- `main.py` - Entry point
- `gateway/` - Core gateway logic with nodes and flows
- `integrations/` - External system integrations
- `models/` - Data models
- `services/` - Business logic services
- `utils/` - Utility functions
- `config/` - Configuration management

No major changes needed here.

### 5. Configuration Organization
- Keep `config/` as is (well-organized)
- Ensure `.example` files are maintained

### 6. Documentation Structure
- Create subdirectories in `docs/`:
  - `docs/api/` - API documentation
  - `docs/architecture/` - Architecture docs
  - `docs/guides/` - Developer guides
  - `docs/reports/` - Analysis and audit reports

## Benefits
1. Cleaner root directory
2. Better separation of concerns
3. Easier to find specific types of files
4. Maintains existing good structure in src/