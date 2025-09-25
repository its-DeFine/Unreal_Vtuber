import os
import sys
from pathlib import Path

os.environ.setdefault("ORCHESTRATOR_ID", "test-orchestrator")
os.environ.setdefault("ORCHESTRATOR_ADDRESS", "0x" + "0" * 40)
os.environ.setdefault("ETH_RPC_URL", "http://localhost:8545")
os.environ.setdefault("PAYMENTS_SINGLE_ORCHESTRATOR_MODE", "false")

BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))
