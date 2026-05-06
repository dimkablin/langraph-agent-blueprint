"""Minimal MCP JSON-RPC transports."""

from __future__ import annotations

import json
import os
import queue
import subprocess
import threading
from itertools import count
from pathlib import Path
from typing import Any

from langgraph_agent_blueprint.models.mcp import MCPConnectionState, MCPServerConfig


class MCPTransportError(RuntimeError):
    """Raised for MCP transport startup, timeout, and protocol failures."""


class MCPStdioTransport:
    """Synchronous JSON-RPC-over-stdio transport for local MCP servers.

    The implementation intentionally supports one request at a time. That keeps
    Phase 2 deterministic and sufficient for graph-owned tool execution.
    """

    def __init__(self, config: MCPServerConfig) -> None:
        if config.transport != "stdio" or config.stdio is None:
            raise MCPTransportError("MCPStdioTransport requires stdio server config")
        self.config = config
        self._process: subprocess.Popen[str] | None = None
        self._responses: "queue.Queue[dict[str, Any]]" = queue.Queue()
        self._stderr_lines: list[str] = []
        self._ids = count(1)
        self._lock = threading.Lock()
        self._state = MCPConnectionState(name=config.name, status="configured", transport="stdio")

    @property
    def state(self) -> MCPConnectionState:
        return self._state

    @property
    def stderr_tail(self) -> list[str]:
        return list(self._stderr_lines[-20:])

    def start(self) -> None:
        if self._process and self._process.poll() is None:
            return
        stdio = self.config.stdio
        cwd = self._validate_cwd(stdio.cwd)
        env = os.environ.copy()
        env.update({str(key): str(value) for key, value in stdio.env.items()})
        command = [stdio.command, *stdio.args]
        if not stdio.command.strip():
            raise MCPTransportError("MCP stdio command is empty")
        self._state = self._state.model_copy(update={"status": "starting", "error": None})
        try:
            self._process = subprocess.Popen(
                command,
                cwd=str(cwd) if cwd else None,
                env=env,
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                encoding="utf-8",
                errors="replace",
                shell=False,
            )
        except OSError as exc:
            self._state = self._state.model_copy(update={"status": "failed", "error": str(exc)})
            raise MCPTransportError(str(exc)) from exc
        self._state = self._state.model_copy(update={"status": "connected", "pid": self._process.pid})
        threading.Thread(target=self._read_stdout, name=f"mcp-{self.config.name}-stdout", daemon=True).start()
        threading.Thread(target=self._read_stderr, name=f"mcp-{self.config.name}-stderr", daemon=True).start()

    def request(self, method: str, params: dict[str, Any] | None = None, timeout: float | None = None) -> dict[str, Any]:
        self._ensure_started()
        assert self._process is not None
        request_id = next(self._ids)
        payload = {"jsonrpc": "2.0", "id": request_id, "method": method}
        if params is not None:
            payload["params"] = params
        with self._lock:
            self._write(payload)
            response = self._wait_for_response(request_id, timeout or self.config.timeout_seconds)
        if "error" in response:
            error = response["error"]
            message = error.get("message") if isinstance(error, dict) else str(error)
            raise MCPTransportError(str(message))
        result = response.get("result")
        return result if isinstance(result, dict) else {"value": result}

    def notify(self, method: str, params: dict[str, Any] | None = None) -> None:
        self._ensure_started()
        payload = {"jsonrpc": "2.0", "method": method}
        if params is not None:
            payload["params"] = params
        self._write(payload)

    def close(self) -> None:
        process = self._process
        if process is None:
            self._state = self._state.model_copy(update={"status": "stopped", "pid": None})
            return
        try:
            if process.stdin:
                process.stdin.close()
        except OSError:
            pass
        if process.poll() is None:
            process.terminate()
            try:
                process.wait(timeout=2)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait(timeout=2)
        self._process = None
        self._state = self._state.model_copy(update={"status": "stopped", "pid": None})

    def _ensure_started(self) -> None:
        if not self._process or self._process.poll() is not None:
            if self._process and self._process.poll() is not None:
                self._state = self._state.model_copy(update={"status": "failed", "error": "MCP server process exited"})
                raise MCPTransportError("MCP server process exited")
            self.start()

    def _write(self, payload: dict[str, Any]) -> None:
        assert self._process is not None and self._process.stdin is not None
        try:
            self._process.stdin.write(json.dumps(payload, separators=(",", ":")) + "\n")
            self._process.stdin.flush()
        except OSError as exc:
            self._state = self._state.model_copy(update={"status": "failed", "error": str(exc)})
            raise MCPTransportError(str(exc)) from exc

    def _wait_for_response(self, request_id: int, timeout: float) -> dict[str, Any]:
        while True:
            if self._process and self._process.poll() is not None:
                self._state = self._state.model_copy(update={"status": "failed", "error": "MCP server process exited"})
                raise MCPTransportError("MCP server process exited")
            try:
                response = self._responses.get(timeout=timeout)
            except queue.Empty as exc:
                self._state = self._state.model_copy(update={"status": "failed", "error": f"MCP request {request_id} timed out"})
                raise MCPTransportError(f"MCP request {request_id} timed out") from exc
            if response.get("id") == request_id:
                return response

    def _read_stdout(self) -> None:
        process = self._process
        if not process or process.stdout is None:
            return
        for line in process.stdout:
            try:
                payload = json.loads(line)
            except json.JSONDecodeError:
                continue
            if isinstance(payload, dict):
                self._responses.put(payload)

    def _read_stderr(self) -> None:
        process = self._process
        if not process or process.stderr is None:
            return
        for line in process.stderr:
            text = line.strip()
            if text:
                self._stderr_lines.append(text[:500])
                del self._stderr_lines[:-20]

    @staticmethod
    def _validate_cwd(cwd: str | None) -> Path | None:
        if not cwd:
            return None
        path = Path(cwd).resolve()
        if not path.exists() or not path.is_dir():
            raise MCPTransportError(f"MCP stdio cwd does not exist: {path}")
        return path
