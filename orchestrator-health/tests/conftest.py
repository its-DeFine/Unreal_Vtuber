from __future__ import annotations

import sys
from pathlib import Path

# Ensure `orchestrator_health` is importable when running pytest with importlib-mode.
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

