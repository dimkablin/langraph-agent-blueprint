"""Executable example showing how to run streaming with the assistant runtime."""

from langgraph_agent_blueprint.config import AppConfig
from langgraph_agent_blueprint.dependencies import build_dependencies
from langgraph_agent_blueprint.graph.builder import AssistantGraphRuntime


runtime = AssistantGraphRuntime(build_dependencies(AppConfig(llm_provider="fake")))
for item in runtime.stream("hello"):
    print(item)

