import os
import sys
import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

import autogen_orchestrator


def test_create_manager_missing_config():
    with pytest.raises(RuntimeError):
        autogen_orchestrator.create_manager()
