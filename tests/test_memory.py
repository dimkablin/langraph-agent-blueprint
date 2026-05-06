"""Pytest coverage for memory behavior in the Python/LangGraph assistant."""

from langgraph_agent_blueprint.services.memory_service import MemoryService


def test_memory_loads_into_context_and_remember_writes(tmp_path):
    service = MemoryService(tmp_path)

    service.remember("project", "Prefer pytest.")
    memory = service.load_memory(project_root=tmp_path)

    assert "Prefer pytest." in memory["project"]
    assert "project" in service.build_context(memory)

