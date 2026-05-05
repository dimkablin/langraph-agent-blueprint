from claude_code_langgraph.config import AppConfig
from claude_code_langgraph.dependencies import build_dependencies
from claude_code_langgraph.graph.builder import AssistantGraphRuntime


runtime = AssistantGraphRuntime(build_dependencies(AppConfig(llm_provider="fake")))
print(runtime.invoke("hello", input_kind="headless")["final_response"])

