"""MCP client lifecycle, discovery, and invocation service."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any

from pydantic import ValidationError

from langgraph_agent_blueprint.models import (
    MCPConnectionState,
    MCPHttpConfig,
    MCPPromptContribution,
    MCPPromptGetResult,
    MCPResourceContribution,
    MCPResourceReadResult,
    MCPServerConfig,
    MCPStdioConfig,
    MCPToolCallRequest,
    MCPToolCallResult,
    MCPToolContribution,
    event,
)
from langgraph_agent_blueprint.services.mcp_transport import MCPStdioTransport, MCPTransportError


@dataclass(frozen=True)
class MCPToolDefinition:
    """Legacy mock MCP tool definition retained for tests and local adapters."""

    name: str
    description: str
    handler: Callable[[dict[str, Any]], dict[str, Any]]
    input_schema: dict[str, Any]


class MCPService:
    """Client manager for configured MCP servers.

    The service owns MCP protocol operations and process lifecycle. LangGraph nodes still own
    workflow decisions, permission gating, and state updates.
    """

    transport_support = {"stdio": True, "streamable_http": False}

    def __init__(self, config: dict[str, Any], output_limit: int = 12000) -> None:
        self.config = config or {}
        self.output_limit = output_limit
        self.server_configs, self.invalid_servers = self._parse_server_configs(self.config)
        self._transports: dict[str, MCPStdioTransport] = {}
        self._states: dict[str, MCPConnectionState] = {
            server.name: MCPConnectionState(
                name=server.name,
                status="disabled" if not server.enabled else "configured",
                transport=server.transport,
            )
            for server in self.server_configs
        }
        self._tools: dict[str, MCPToolContribution] = {}
        self._resources: dict[str, list[MCPResourceContribution]] = {}
        self._prompts: dict[str, list[MCPPromptContribution]] = {}
        self._events: list[dict[str, Any]] = []
        self._mock_tools: dict[str, MCPToolDefinition] = {}
        self._discovered = False

    def __del__(self) -> None:
        try:
            self.close()
        except Exception:
            pass

    def register_mock_tool(self, name: str, handler: Callable[[dict[str, Any]], dict[str, Any]]) -> None:
        self._mock_tools[name] = MCPToolDefinition(
            name=name,
            description=f"Mock MCP tool {name}",
            handler=handler,
            input_schema={"type": "object", "properties": {}},
        )
        registry_name = f"mcp.{name}"
        self._tools[registry_name] = MCPToolContribution(
            server_name="mock",
            tool_name=name,
            registry_name=registry_name,
            description=f"Mock MCP tool {name}",
            input_schema={"type": "object", "properties": {}},
            raw={"mock": True},
        )

    def enabled_server_configs(self) -> list[MCPServerConfig]:
        return [server for server in self.server_configs if server.enabled]

    def discover(self) -> dict[str, Any]:
        if not self._discovered:
            for server in self.server_configs:
                if not server.enabled:
                    continue
                self._connect_and_discover(server)
            self._discovered = True
        return self.snapshot()

    def snapshot(self) -> dict[str, Any]:
        return {
            "servers": [state.model_dump(mode="json") for state in self._states.values()],
            "tools": {name: tool.model_dump(mode="json", exclude_none=True) for name, tool in self._tools.items()},
            "resources": {
                server: [resource.model_dump(mode="json", exclude_none=True) for resource in resources]
                for server, resources in self._resources.items()
            },
            "prompts": {
                server: [prompt.model_dump(mode="json", exclude_none=True) for prompt in prompts]
                for server, prompts in self._prompts.items()
            },
            "events": list(self._events),
            "transport_support": dict(self.transport_support),
            "invalid_servers": list(self.invalid_servers),
            "warnings": list(self.invalid_servers),
            "errors": [],
        }

    def diagnostics(self) -> dict[str, Any]:
        snapshot = self.discover()
        return {
            "servers_total": len(snapshot["servers"]),
            "servers_enabled": len(self.enabled_server_configs()),
            "servers": snapshot["servers"],
            "tools_total": len(snapshot["tools"]),
            "resources_total": sum(len(items) for items in snapshot["resources"].values()),
            "prompts_total": sum(len(items) for items in snapshot["prompts"].values()),
            "transport_support": dict(self.transport_support),
            "invalid_servers": snapshot["invalid_servers"],
            "warnings": snapshot["warnings"],
            "errors": snapshot["errors"],
        }

    def redacted_config(self) -> dict[str, Any]:
        servers: dict[str, Any] = {}
        for server in self.server_configs:
            stdio = server.stdio.model_dump(mode="json") if server.stdio else {"env": {}}
            if "env" in stdio:
                stdio["env"] = _redact_mapping(stdio.get("env", {}))
            http = server.http.model_dump(mode="json") if server.http else {"headers": {}}
            if "headers" in http:
                http["headers"] = _redact_mapping(http.get("headers", {}))
            servers[server.name] = {
                "enabled": server.enabled,
                "transport": server.transport,
                "trust_level": server.trust_level,
                "timeout_seconds": server.timeout_seconds,
                "stdio": stdio,
                "http": http,
            }
        return {"servers": servers}

    def call_tool(self, server_name: str, tool_name: str, arguments: dict[str, Any]) -> MCPToolCallResult:
        request = MCPToolCallRequest(server_name=server_name, tool_name=tool_name, arguments=arguments)
        if server_name == "mock" and tool_name in self._mock_tools:
            try:
                data = self._mock_tools[tool_name].handler(dict(arguments))
            except Exception as exc:
                return MCPToolCallResult(server_name=server_name, tool_name=tool_name, status="error", content=str(exc), error=str(exc))
            return MCPToolCallResult(server_name=server_name, tool_name=tool_name, status="ok", content=str(data), data={"result": data})
        transport = self._transport_for(request.server_name)
        try:
            payload = transport.request("tools/call", {"name": request.tool_name, "arguments": request.arguments})
        except MCPTransportError as exc:
            return MCPToolCallResult(
                server_name=request.server_name,
                tool_name=request.tool_name,
                status="error",
                content=str(exc),
                error=str(exc),
            )
        content = _content_to_text(payload.get("content"))
        is_error = bool(payload.get("isError"))
        return MCPToolCallResult(
            server_name=request.server_name,
            tool_name=request.tool_name,
            status="error" if is_error else "ok",
            content=content,
            data=payload,
            error=content if is_error else None,
        )

    def list_resources(self) -> dict[str, list[MCPResourceContribution]]:
        self.discover()
        return {server: list(resources) for server, resources in self._resources.items()}

    def read_resource(self, server_name: str, uri: str, max_content_length: int | None = None) -> MCPResourceReadResult:
        self.discover()
        transport = self._transport_for(server_name)
        try:
            payload = transport.request("resources/read", {"uri": uri})
        except MCPTransportError as exc:
            return MCPResourceReadResult(server_name=server_name, uri=uri, status="error", error=str(exc), content=str(exc))
        contents = payload.get("contents") if isinstance(payload.get("contents"), list) else []
        text = _content_to_text(contents)
        limit = max_content_length or self.output_limit
        truncated = len(text) > limit
        if truncated:
            text = text[:limit].rstrip() + "\n[truncated]"
        mime_type = None
        if contents and isinstance(contents[0], dict):
            mime_type = contents[0].get("mimeType")
        return MCPResourceReadResult(
            server_name=server_name,
            uri=uri,
            status="ok",
            content=text,
            mime_type=mime_type,
            truncated=truncated,
            raw=payload,
        )

    def list_prompts(self) -> dict[str, list[MCPPromptContribution]]:
        self.discover()
        return {server: list(prompts) for server, prompts in self._prompts.items()}

    def get_prompt(self, server_name: str, prompt_name: str, arguments: dict[str, Any] | None = None) -> MCPPromptGetResult:
        self.discover()
        transport = self._transport_for(server_name)
        try:
            payload = transport.request("prompts/get", {"name": prompt_name, "arguments": arguments or {}})
        except MCPTransportError as exc:
            return MCPPromptGetResult(server_name=server_name, prompt_name=prompt_name, status="error", error=str(exc), content=str(exc))
        text = _messages_to_text(payload.get("messages"))
        return MCPPromptGetResult(server_name=server_name, prompt_name=prompt_name, status="ok", content=text, raw=payload)

    def close(self) -> None:
        for transport in list(self._transports.values()):
            transport.close()
        self._transports.clear()
        for name, state in list(self._states.items()):
            if state.status in {"connected", "starting"}:
                self._states[name] = state.model_copy(update={"status": "stopped", "pid": None})

    def _connect_and_discover(self, server: MCPServerConfig) -> None:
        self._record_event("mcp_server_starting", server=server.name, transport=server.transport)
        if server.transport == "streamable_http":
            message = "streamable_http transport is not implemented in Phase 2"
            self._states[server.name] = MCPConnectionState(
                name=server.name,
                status="failed",
                transport=server.transport,
                error=message,
            )
            self._record_event("mcp_server_failed", server=server.name, error=message, severity="warning")
            return
        try:
            transport = MCPStdioTransport(server)
            transport.start()
            initialized = transport.request(
                "initialize",
                {
                    "protocolVersion": "2025-11-25",
                    "capabilities": {"tools": {}, "resources": {}, "prompts": {}},
                    "clientInfo": {"name": "langgraph-agent-blueprint", "version": "0.1.0"},
                },
            )
            transport.notify("notifications/initialized")
            capabilities = initialized.get("capabilities") if isinstance(initialized.get("capabilities"), dict) else {}
            self._transports[server.name] = transport
            self._states[server.name] = transport.state.model_copy(update={"capabilities": capabilities})
            self._record_event("mcp_server_connected", server=server.name, transport=server.transport, pid=transport.state.pid)
            self._discover_tools(server, transport)
            self._discover_resources(server, transport)
            self._discover_prompts(server, transport)
        except (MCPTransportError, ValidationError, ValueError) as exc:
            self._states[server.name] = MCPConnectionState(
                name=server.name,
                status="failed",
                transport=server.transport,
                error=str(exc),
            )
            self._record_event("mcp_server_failed", server=server.name, error=str(exc), severity="warning")

    def _discover_tools(self, server: MCPServerConfig, transport: MCPStdioTransport) -> None:
        payload = transport.request("tools/list")
        raw_tools = payload.get("tools") if isinstance(payload.get("tools"), list) else []
        for raw in raw_tools:
            if not isinstance(raw, dict) or not raw.get("name"):
                continue
            tool_name = str(raw["name"])
            registry_name = f"mcp.{server.name}.{tool_name}"
            self._tools[registry_name] = MCPToolContribution(
                server_name=server.name,
                tool_name=tool_name,
                registry_name=registry_name,
                description=raw.get("description"),
                input_schema=raw.get("inputSchema") if isinstance(raw.get("inputSchema"), dict) else {"type": "object", "properties": {}},
                output_schema=raw.get("outputSchema") if isinstance(raw.get("outputSchema"), dict) else {"type": "object"},
                raw=raw,
            )
        self._record_event("mcp_tools_discovered", server=server.name, count=len(raw_tools))

    def _discover_resources(self, server: MCPServerConfig, transport: MCPStdioTransport) -> None:
        payload = transport.request("resources/list")
        raw_resources = payload.get("resources") if isinstance(payload.get("resources"), list) else []
        resources: list[MCPResourceContribution] = []
        for raw in raw_resources:
            if not isinstance(raw, dict) or not raw.get("uri"):
                continue
            resources.append(
                MCPResourceContribution(
                    server_name=server.name,
                    uri=str(raw["uri"]),
                    name=raw.get("name"),
                    description=raw.get("description"),
                    mime_type=raw.get("mimeType"),
                    raw=raw,
                )
            )
        self._resources[server.name] = resources
        self._record_event("mcp_resources_discovered", server=server.name, count=len(resources))

    def _discover_prompts(self, server: MCPServerConfig, transport: MCPStdioTransport) -> None:
        payload = transport.request("prompts/list")
        raw_prompts = payload.get("prompts") if isinstance(payload.get("prompts"), list) else []
        prompts: list[MCPPromptContribution] = []
        for raw in raw_prompts:
            if not isinstance(raw, dict) or not raw.get("name"):
                continue
            prompt_name = str(raw["name"])
            prompts.append(
                MCPPromptContribution(
                    server_name=server.name,
                    prompt_name=prompt_name,
                    registry_name=f"mcp/{server.name}/prompt/{prompt_name}",
                    description=raw.get("description"),
                    arguments_schema={"arguments": raw.get("arguments", [])},
                    raw=raw,
                )
            )
        self._prompts[server.name] = prompts
        self._record_event("mcp_prompts_discovered", server=server.name, count=len(prompts))

    def _transport_for(self, server_name: str) -> MCPStdioTransport:
        self.discover()
        transport = self._transports.get(server_name)
        if not transport:
            state = self._states.get(server_name)
            detail = f": {state.error}" if state and state.error else ""
            raise MCPTransportError(f"MCP server is not connected: {server_name}{detail}")
        return transport

    def _record_event(self, event_type: str, *, severity: str = "info", **data: Any) -> None:
        data.setdefault("timestamp_utc", datetime.now(timezone.utc).isoformat())
        self._events.append(event(event_type, severity=severity, **data))

    @staticmethod
    def _parse_server_configs(config: dict[str, Any]) -> tuple[list[MCPServerConfig], list[dict[str, str]]]:
        raw_servers = config.get("servers", {})
        if not raw_servers and config:
            raw_servers = config
        if not isinstance(raw_servers, dict):
            return [], [{"name": "servers", "error": "MCP servers config must be an object"}]
        servers: list[MCPServerConfig] = []
        invalid_servers: list[dict[str, str]] = []
        for name, raw in raw_servers.items():
            if not isinstance(raw, dict):
                invalid_servers.append({"name": str(name), "error": "MCP server config must be an object"})
                continue
            payload = _normalize_server_payload(str(name), raw)
            try:
                servers.append(MCPServerConfig.model_validate(payload))
            except ValidationError as exc:
                invalid_servers.append({"name": str(name), "error": _redact_text(str(exc), raw)})
                continue
        return servers, invalid_servers


def _normalize_server_payload(name: str, raw: dict[str, Any]) -> dict[str, Any]:
    transport = raw.get("transport", "stdio")
    payload: dict[str, Any] = {
        "name": raw.get("name", name),
        "enabled": raw.get("enabled", True),
        "transport": transport,
        "timeout_seconds": raw.get("timeout_seconds", raw.get("timeout", 30.0)),
        "trust_level": raw.get("trust_level", "untrusted"),
        "metadata": raw.get("metadata", {}),
    }
    if transport == "stdio":
        stdio = raw.get("stdio")
        if not isinstance(stdio, dict):
            stdio = {
                "command": raw.get("command"),
                "args": raw.get("args", []),
                "env": raw.get("env", {}),
                "cwd": raw.get("cwd"),
            }
        payload["stdio"] = stdio
    if transport == "streamable_http":
        http = raw.get("http")
        if not isinstance(http, dict):
            http = {
                "url": raw.get("url"),
                "headers": raw.get("headers", {}),
                "timeout_seconds": raw.get("timeout_seconds", raw.get("timeout", 30.0)),
            }
        payload["http"] = http
    else:
        headers = raw.get("headers")
        if headers:
            payload["http"] = {"url": raw.get("url", "http://localhost"), "headers": headers}
    return payload


def _redact_mapping(values: dict[str, Any]) -> dict[str, Any]:
    redacted = {}
    for key, value in values.items():
        key_text = str(key).lower()
        if any(marker in key_text for marker in ["key", "token", "secret", "password", "authorization", "auth"]):
            redacted[key] = "***" if value else value
        else:
            redacted[key] = value
    return redacted


def _redact_text(text: str, raw: dict[str, Any]) -> str:
    redacted = text

    def collect(value: Any, key: str | None = None) -> list[str]:
        if isinstance(value, dict):
            values: list[str] = []
            for item_key, item_value in value.items():
                values.extend(collect(item_value, str(item_key)))
            return values
        if isinstance(value, list):
            values = []
            for item in value:
                values.extend(collect(item, key))
            return values
        if key and any(marker in key.lower() for marker in ["key", "token", "secret", "password", "authorization", "auth"]):
            return [str(value)] if value not in (None, "") else []
        return []

    for secret in collect(raw):
        redacted = redacted.replace(secret, "***")
    return redacted


def _content_to_text(content: Any) -> str:
    if isinstance(content, str):
        return content
    if isinstance(content, dict):
        if "text" in content:
            return str(content.get("text") or "")
        if "content" in content:
            return _content_to_text(content.get("content"))
        return str(content)
    if isinstance(content, list):
        return "\n".join(_content_to_text(item) for item in content if item is not None).strip()
    if content is None:
        return ""
    return str(content)


def _messages_to_text(messages: Any) -> str:
    if not isinstance(messages, list):
        return _content_to_text(messages)
    parts = []
    for message in messages:
        if not isinstance(message, dict):
            parts.append(str(message))
            continue
        role = message.get("role", "user")
        content = _content_to_text(message.get("content"))
        parts.append(f"{role}: {content}")
    return "\n".join(parts).strip()
