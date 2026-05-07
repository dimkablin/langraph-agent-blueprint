"""Tests for conservative @mention context reference parsing."""

from __future__ import annotations

from langgraph_agent_blueprint.context.references import parse_context_references


def test_parse_file_directory_glob_notebook_url_and_mcp_refs() -> None:
    text = 'Use @README.md @src/ @glob:src/**/*.py @notebook:notebook.ipynb @url:https://example.com @mcp:fake:mcp://fake/readme'

    refs = parse_context_references(text)

    assert [(ref.kind, ref.value) for ref in refs] == [
        ("file", "README.md"),
        ("directory", "src/"),
        ("glob", "src/**/*.py"),
        ("notebook", "notebook.ipynb"),
        ("url", "https://example.com"),
        ("mcp_resource", "fake:mcp://fake/readme"),
    ]


def test_parse_markdown_url_reference() -> None:
    refs = parse_context_references("Use @url:[https://example.com](https://example.com) as context")

    assert [(ref.kind, ref.value) for ref in refs] == [("url", "https://example.com")]


def test_parse_quoted_path_with_spaces_and_ignores_email_or_username() -> None:
    refs = parse_context_references('Email a@b.com and ping @dimka, but read @"docs/My File.md"')

    assert [(ref.kind, ref.value) for ref in refs] == [("file", "docs/My File.md")]
