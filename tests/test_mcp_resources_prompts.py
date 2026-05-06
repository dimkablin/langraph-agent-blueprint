"""MCP resources and prompts service coverage."""

from __future__ import annotations

import sys
from pathlib import Path

from langgraph_agent_blueprint.services.mcp_service import MCPService


def _service() -> MCPService:
    server = Path(__file__).parent / "fixtures" / "mcp" / "fake_mcp_server.py"
    return MCPService(
        {
            "servers": {
                "fake": {
                    "enabled": True,
                    "transport": "stdio",
                    "command": sys.executable,
                    "args": [str(server)],
                    "timeout_seconds": 5,
                }
            }
        },
        output_limit=80,
    )


def test_read_resource_marks_external_content_and_truncates_large_results() -> None:
    service = _service()
    try:
        service.discover()
        small = service.read_resource("fake", "mcp://fake/readme")
        large = service.read_resource("fake", "mcp://fake/large", max_content_length=50)
    finally:
        service.close()

    assert small.status == "ok"
    assert small.external is True
    assert small.untrusted is True
    assert "Fake MCP resource content" in small.content
    assert large.truncated is True
    assert len(large.content) <= 80


def test_get_prompt_returns_external_prompt_content() -> None:
    service = _service()
    try:
        service.discover()
        prompt = service.get_prompt("fake", "summarize", {"topic": "MCP"})
    finally:
        service.close()

    assert prompt.status == "ok"
    assert prompt.external is True
    assert prompt.untrusted is True
    assert "Summarize this topic: MCP" in prompt.content
