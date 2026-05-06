"""Prompt construction helpers for the assistant system context."""

from __future__ import annotations


BASE_SYSTEM_PROMPT = """You are a coding assistant running inside a local project.
Use tools when they are useful, respect permissions, keep responses concise, and preserve user intent.
Do not claim data analyst capabilities as a direct source port unless they are explicitly implemented as extensions."""


def build_system_context(
    project_root: str,
    memory_context: str,
    tools_summary: str,
    skills_summary: str,
    todos_summary: str,
    plugin_context: str = "",
) -> str:
    """Build the runtime system context from audited prompt categories without copying source prompts."""

    parts = [
        BASE_SYSTEM_PROMPT,
        f"Project root: {project_root}",
        memory_context,
        plugin_context,
        tools_summary,
        skills_summary,
        todos_summary,
    ]
    return "\n\n".join(part for part in parts if part)

