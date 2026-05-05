"""Executable example showing how to run with ollama with the assistant runtime."""

from claude_code_langgraph.config import AppConfig
from claude_code_langgraph.dependencies import build_dependencies
from claude_code_langgraph.graph.builder import AssistantGraphRuntime


config = AppConfig(llm_provider="ollama", ollama_model="llama3.1")
runtime = AssistantGraphRuntime(build_dependencies(config))
print(runtime.invoke("Say hello from Ollama.", input_kind="headless")["final_response"])

