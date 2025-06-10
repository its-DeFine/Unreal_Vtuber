"""Example tool used by the AutoGen agent."""
from typing import Dict


def run(context: Dict) -> Dict:
    # simple tool that echoes last message
    message = context.get("message", "Hello from example tool")
    return {"message": message, "tool": "example"}
