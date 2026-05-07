"""Regression tests for guarded web fetch behavior."""

from __future__ import annotations

from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from threading import Thread

import pytest

from langgraph_agent_blueprint.config import AppConfig
from langgraph_agent_blueprint.services.web_service import WebService


@pytest.mark.parametrize("url", ["file:///etc/passwd", "ftp://example.test/file", "javascript:alert(1)", "data:text/plain,hello", "example.com"])
def test_web_fetch_rejects_unsupported_schemes_before_network(url: str) -> None:
    service = WebService(enabled=True)

    with pytest.raises(ValueError):
        service.fetch(url)


@pytest.mark.parametrize(
    "url",
    [
        "http://localhost:8000/",
        "http://127.0.0.1:8000/",
        "http://[::1]:8000/",
        "http://10.0.0.1/",
        "http://172.16.0.1/",
        "http://192.168.1.10/",
        "http://169.254.169.254/latest/meta-data/",
    ],
)
def test_web_fetch_rejects_private_hosts_by_default(url: str) -> None:
    service = WebService(enabled=True)

    with pytest.raises(ValueError, match="private|internal|localhost"):
        service.fetch(url)


def test_web_fetch_can_allow_localhost_when_explicitly_configured() -> None:
    class Handler(BaseHTTPRequestHandler):
        def do_GET(self):  # noqa: N802
            self.send_response(200)
            self.send_header("content-type", "text/plain")
            self.end_headers()
            self.wfile.write(b"local ok")

        def log_message(self, format, *args):  # noqa: A002
            return

    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    thread = Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        result = WebService(enabled=True, allow_private_hosts=True).fetch(f"http://127.0.0.1:{server.server_port}/")
    finally:
        server.shutdown()
        server.server_close()

    assert result["text"] == "local ok"
    assert result["url"].startswith("http://127.0.0.1:")


def test_web_fetch_caps_large_response_before_decoding() -> None:
    class Handler(BaseHTTPRequestHandler):
        def do_GET(self):  # noqa: N802
            self.send_response(200)
            self.send_header("content-type", "text/plain")
            self.end_headers()
            self.wfile.write(b"abcdef")

        def log_message(self, format, *args):  # noqa: A002
            return

    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    thread = Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        result = WebService(enabled=True, allow_private_hosts=True, max_bytes=3).fetch(f"http://127.0.0.1:{server.server_port}/")
    finally:
        server.shutdown()
        server.server_close()

    assert result["text"] == "abc"
    assert result["truncated"] is True


def test_web_fetch_handles_binary_content_safely() -> None:
    class Handler(BaseHTTPRequestHandler):
        def do_GET(self):  # noqa: N802
            self.send_response(200)
            self.send_header("content-type", "application/octet-stream")
            self.end_headers()
            self.wfile.write(b"\x00\x01\x02\x03")

        def log_message(self, format, *args):  # noqa: A002
            return

    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    thread = Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        result = WebService(enabled=True, allow_private_hosts=True).fetch(f"http://127.0.0.1:{server.server_port}/")
    finally:
        server.shutdown()
        server.server_close()

    assert result["binary"] is True
    assert "binary content omitted" in result["text"]


def test_web_fetch_validates_redirect_final_url(monkeypatch) -> None:
    class FakeResponse:
        url = "http://127.0.0.1/private"
        status_code = 302
        headers = {"content-type": "text/plain"}
        encoding = "utf-8"

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

        def raise_for_status(self) -> None:
            return None

        def iter_bytes(self):
            yield b"private"

    class FakeClient:
        def __init__(self, *args, **kwargs):
            pass

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

        def stream(self, method, url):
            assert method == "GET"
            assert url == "https://example.test/redirect"
            return FakeResponse()

    monkeypatch.setattr("langgraph_agent_blueprint.services.web_service.httpx.Client", FakeClient)

    with pytest.raises(ValueError, match="private|internal|localhost"):
        WebService(enabled=True).fetch("https://example.test/redirect")


def test_web_fetch_config_reads_guardrail_env(monkeypatch, tmp_path) -> None:
    monkeypatch.setenv("WEB_FETCH_ALLOW_PRIVATE_HOSTS", "true")
    monkeypatch.setenv("WEB_FETCH_MAX_BYTES", "42")

    config = AppConfig.from_env(project_root=tmp_path)

    assert config.web_fetch_allow_private_hosts is True
    assert config.web_fetch_max_bytes == 42
