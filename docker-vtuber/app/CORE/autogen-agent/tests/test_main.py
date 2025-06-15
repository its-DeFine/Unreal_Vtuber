import autogen_agent.main as main
from autogen_agent.tool_registry import ToolRegistry


def test_registry_loads_example_tool():
    reg = ToolRegistry()
    reg.load_tools()
    assert "example_tool" in reg.tools
