"""Tiny JSON-RPC stdio MCP fixture used by runtime tests.

It intentionally implements only the MCP operations exercised by the test suite.
The fixture never touches the network or filesystem.
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from typing import Any


TOOLS = [
    {
        "name": "echo",
        "description": "Echo text back to the caller.",
        "inputSchema": {
            "type": "object",
            "properties": {"text": {"type": "string"}},
            "required": ["text"],
        },
        "annotations": {"readOnlyHint": True},
    },
    {
        "name": "make_note",
        "description": "Create a note in the fake server process.",
        "inputSchema": {
            "type": "object",
            "properties": {"note": {"type": "string"}},
            "required": ["note"],
        },
    },
    {
        "name": "fail",
        "description": "Return a structured tool error.",
        "inputSchema": {"type": "object", "properties": {}},
    },
]

RESOURCES = [
    {
        "uri": "mcp://fake/readme",
        "name": "Fake README",
        "description": "Small fake MCP resource.",
        "mimeType": "text/plain",
    },
    {
        "uri": "mcp://fake/large",
        "name": "Large fake resource",
        "description": "Large resource used to verify truncation.",
        "mimeType": "text/plain",
    },
]

PROMPTS = [
    {
        "name": "summarize",
        "description": "Summarize a topic.",
        "arguments": [{"name": "topic", "description": "Topic to summarize", "required": True}],
    },
    {
        "name": "debug_prompt",
        "description": "Debugging prompt template.",
        "arguments": [{"name": "failure", "description": "Failure text", "required": False}],
    },
]


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--hang-initialize", action="store_true")
    args = parser.parse_args()

    notes: list[str] = []
    for line in sys.stdin:
        line = line.strip()
        if not line:
            continue
        try:
            request = json.loads(line)
        except json.JSONDecodeError:
            continue
        if "id" not in request:
            continue
        if args.hang_initialize and request.get("method") == "initialize":
            time.sleep(30)
            continue
        response = handle_request(request, notes)
        sys.stdout.write(json.dumps(response, separators=(",", ":")) + "\n")
        sys.stdout.flush()
    return 0


def handle_request(request: dict[str, Any], notes: list[str]) -> dict[str, Any]:
    method = request.get("method")
    params = request.get("params") or {}
    request_id = request.get("id")
    try:
        if method == "initialize":
            result = {
                "protocolVersion": "2025-11-25",
                "capabilities": {"tools": {}, "resources": {}, "prompts": {}},
                "serverInfo": {"name": "fake-mcp", "version": "0.1.0"},
            }
        elif method == "tools/list":
            result = {"tools": TOOLS}
        elif method == "tools/call":
            result = call_tool(params, notes)
        elif method == "resources/list":
            result = {"resources": RESOURCES}
        elif method == "resources/read":
            result = read_resource(params)
        elif method == "prompts/list":
            result = {"prompts": PROMPTS}
        elif method == "prompts/get":
            result = get_prompt(params)
        else:
            return {"jsonrpc": "2.0", "id": request_id, "error": {"code": -32601, "message": f"Unknown method: {method}"}}
    except Exception as exc:  # pragma: no cover - fixture defensive path
        return {"jsonrpc": "2.0", "id": request_id, "error": {"code": -32000, "message": str(exc)}}
    return {"jsonrpc": "2.0", "id": request_id, "result": result}


def call_tool(params: dict[str, Any], notes: list[str]) -> dict[str, Any]:
    name = params.get("name")
    arguments = params.get("arguments") or {}
    if name == "echo":
        return {"content": [{"type": "text", "text": f"echo: {arguments.get('text', '')}"}]}
    if name == "make_note":
        note = str(arguments.get("note", ""))
        notes.append(note)
        return {"content": [{"type": "text", "text": f"note: {note}"}], "structuredContent": {"notes": list(notes)}}
    if name == "fail":
        return {"isError": True, "content": [{"type": "text", "text": "fake MCP failure"}]}
    raise ValueError(f"Unknown tool: {name}")


def read_resource(params: dict[str, Any]) -> dict[str, Any]:
    uri = params.get("uri")
    if uri == "mcp://fake/readme":
        text = "Fake MCP resource content."
    elif uri == "mcp://fake/large":
        text = "large-content " * 100
    else:
        raise ValueError(f"Unknown resource: {uri}")
    return {"contents": [{"uri": uri, "mimeType": "text/plain", "text": text}]}


def get_prompt(params: dict[str, Any]) -> dict[str, Any]:
    name = params.get("name")
    arguments = params.get("arguments") or {}
    if name == "summarize":
        text = f"Summarize this topic: {arguments.get('topic', '')}"
    elif name == "debug_prompt":
        text = f"Debug this failure: {arguments.get('failure', '')}"
    else:
        raise ValueError(f"Unknown prompt: {name}")
    return {"description": f"Prompt {name}", "messages": [{"role": "user", "content": {"type": "text", "text": text}}]}


if __name__ == "__main__":
    raise SystemExit(main())
