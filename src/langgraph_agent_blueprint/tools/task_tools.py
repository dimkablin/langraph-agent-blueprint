"""Model-callable tool module exposing typed operations through the central ToolRegistry."""

from __future__ import annotations

from .agent_tools import AgentInput, AgentOutput, AgentTool


class TaskTool(AgentTool):
    """Placeholder task tool surface reserved for task-management capabilities."""
    name = "task"
    description = "Create and run a task through the agent service."
    input_schema = AgentInput
    output_schema = AgentOutput

