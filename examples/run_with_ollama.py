"""Executable example showing how to run with ollama with the assistant runtime."""

from langgraph_agent_blueprint.config import AppConfig
from langgraph_agent_blueprint.dependencies import build_dependencies
from langgraph_agent_blueprint.graph.builder import AssistantGraphRuntime


config = AppConfig(llm_provider="ollama", ollama_model="llama3.1")
runtime = AssistantGraphRuntime(build_dependencies(config))
print(runtime.invoke("Say hello from Ollama.", input_kind="headless")["final_response"])

