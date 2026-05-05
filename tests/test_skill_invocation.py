from claude_code_langgraph.config import AppConfig
from claude_code_langgraph.dependencies import build_dependencies
from claude_code_langgraph.graph.subgraphs.skill_graph import build_skill_graph
from claude_code_langgraph.graph.state import create_initial_state


def test_skill_tool_invokes_skill_graph(tmp_path):
    deps = build_dependencies(AppConfig(storage_dir=tmp_path, llm_provider="fake"))
    app = build_skill_graph(deps).compile()
    state = create_initial_state("use skill", project_root=tmp_path)
    state["active_skill"] = {"name": "debug", "args": "failing test"}

    result = app.invoke(state)

    assert result["active_skill"]["name"] == "debug"
    assert any(event["type"] == "skill_finished" for event in result["ui_events"])


def test_allowed_tools_narrowing_is_applied(tmp_path):
    deps = build_dependencies(AppConfig(storage_dir=tmp_path, llm_provider="fake"))
    state = create_initial_state("use skill", project_root=tmp_path)
    state["active_skill"] = {"name": "verify", "args": "pytest"}

    result = build_skill_graph(deps).compile().invoke(state)

    assert result["metadata"]["allowed_tools_override"] == ["bash", "powershell", "grep", "glob", "read_file"]

