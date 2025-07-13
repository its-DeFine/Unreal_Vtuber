"""SCB Operations Tool
====================

Allows S2 agents to write reasoning, tool-call logs, or arbitrary events to
*their* team SCB slice (SCB v2).

Typical usage pattern in an AutoGen agent chat:

```json
{"name": "scb_operations", "arguments": {"event_type": "tool_call", "text": "Executed market_data:TSLA moving-average=250"}}
```
"""

from __future__ import annotations

import logging
from typing import List, Dict, Any

from ..clients.scb_v2_client import SCBv2Client
from .base_tool import (
    BaseTool,
    ToolParameter,
    ToolExecutionContext,
    ToolResult,
    ToolStatus,
)

logger = logging.getLogger(__name__)


class SCBOperationsTool(BaseTool):
    """Publish an event into the team SCB slice."""

    VALID_EVENT_TYPES = [
        "tool_call",  # agent executed a tool call
        "reasoning",  # chain-of-thought or summary
        "note",       # any other note
    ]

    def __init__(self, timeout: float = 10.0):
        params = [
            ToolParameter(
                name="event_type",
                type="string",
                description="Category of event to append (tool_call, reasoning, note)",
                required=True,
                enum=self.VALID_EVENT_TYPES,
            ),
            ToolParameter(
                name="text",
                type="string",
                description="Text content to store (max couple of sentences)",
                required=True,
            ),
        ]
        super().__init__(
            name="scb_operations",
            description="Append an event to the team SCB slice for cross-system sharing.",
            parameters=params,
            timeout=timeout,
        )
        self._scb_client = SCBv2Client()

    async def execute(
        self,
        context: ToolExecutionContext,
        **kwargs,
    ) -> ToolResult:
        team = context.team_type or "educator"  # default fallback
        event_type = kwargs.get("event_type")
        text = kwargs.get("text", "").strip()

        if not text:
            return ToolResult(
                success=False,
                status=ToolStatus.FAILED,
                error_message="'text' cannot be empty",
            )

        key = f"scb:team:{team}"
        event: Dict[str, Any] = {
            "type": event_type,
            "actor": "s2_agent",
            "text": text,
        }

        try:
            self._scb_client.append_event(key, event)
            return ToolResult(
                success=True,
                status=ToolStatus.SUCCESS,
                result={"stored_in": key},
            )
        except Exception as e:
            logger.error("SCBOperationsTool failed: %s", e)
            return ToolResult(
                success=False,
                status=ToolStatus.FAILED,
                error_message=str(e),
            )


# Helper for tool registry
scb_operations_tool = SCBOperationsTool()

# Register with catalog on import
from .tool_catalog import register_tool
register_tool(SCBOperationsTool, category="system", team_types=["trader", "educator", "streamer"], priority=7)

__all__ = ["scb_operations_tool", "SCBOperationsTool"] 