from __future__ import annotations

from .agent_tools import AgentInput, AgentOutput, AgentTool


class TaskTool(AgentTool):
    name = "task"
    description = "Create and run a task through the agent service."
    input_schema = AgentInput
    output_schema = AgentOutput

