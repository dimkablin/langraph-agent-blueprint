"""Superpowers plugin adapter and graph-level activation policy."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from langgraph_agent_blueprint.models.plugins import PluginContribution


SUPERPOWERS_PLUGIN_NAME = "superpowers"
SUPERPOWERS_BOOTSTRAP_SKILL = "using-superpowers"

TOOL_MAPPING = {
    "Skill": "skill",
    "TodoWrite": "todo_write",
    "Task": "agent",
    "Read": "read_file",
    "Bash": "bash",
    "Grep": "grep",
    "Glob": "glob",
}

DEVELOPMENT_TERMS = (
    "build",
    "make",
    "create",
    "add",
    "implement",
    "feature",
    "todo list",
    "react",
    "component",
    "app",
)

DEBUG_TERMS = ("fix", "bug", "failing", "failure", "error", "traceback", "broken", "regression")


def superpowers_bootstrap_context(contribution: PluginContribution, skill_names: list[str]) -> str:
    """Build compact bootstrap context without rewriting upstream skill content."""

    skills = ", ".join(sorted(skill_names))
    mapping = ", ".join(f"{source} -> `{target}`" for source, target in TOOL_MAPPING.items())
    bootstrap_id = f"{contribution.plugin_name}/{contribution.bootstrap_skill or SUPERPOWERS_BOOTSTRAP_SKILL}"
    return "\n".join(
        [
            "Superpowers plugin is enabled.",
            f"Bootstrap skill: {bootstrap_id}.",
            "Before responding to development work, check whether a Superpowers skill applies.",
            "If a Superpowers skill might apply, invoke the `skill` tool with the namespaced skill id before answering or taking action.",
            "For new feature/build/component requests, activate `superpowers/brainstorming` before writing code.",
            "User explicit instructions override Superpowers methodology.",
            f"Relevant Superpowers skills: {skills or 'none discovered'}.",
            f"Tool mapping for upstream skill text: {mapping}.",
        ]
    )


def is_superpowers_repo(root: str | Path, plugin_name: str) -> bool:
    """Return whether a discovered plugin should use the Superpowers adapter."""

    return plugin_name == SUPERPOWERS_PLUGIN_NAME and (Path(root) / "skills").exists()


def choose_superpowers_activation(input_text: str, state: dict[str, Any]) -> dict[str, Any] | None:
    """Choose a mandatory Superpowers pre-skill for obvious tasks.

    This deterministic policy covers the harness acceptance path and a small
    extensible set of high-value workflow triggers. The skill runtime still owns
    actual skill invocation.
    """

    plugin_state = state.get("plugin_state", {})
    if not _superpowers_enabled(plugin_state):
        return None
    metadata = state.get("metadata", {})
    invoked = set(metadata.get("skill_invocations", []))
    text = input_text.lower()
    if _contains_any(text, DEBUG_TERMS) and "superpowers/systematic-debugging" not in invoked:
        return {
            "name": "superpowers/systematic-debugging",
            "args": input_text,
            "policy": "superpowers",
            "reason": "debugging request matched Superpowers policy",
        }
    if _contains_any(text, DEVELOPMENT_TERMS) and "superpowers/brainstorming" not in invoked:
        return {
            "name": "superpowers/brainstorming",
            "args": input_text,
            "policy": "superpowers",
            "reason": "development request matched Superpowers brainstorming policy",
        }
    return None


def _superpowers_enabled(plugin_state: dict[str, Any]) -> bool:
    for plugin in plugin_state.get("plugins", []):
        if plugin.get("name") == SUPERPOWERS_PLUGIN_NAME and plugin.get("enabled", True):
            return True
    return False


def _contains_any(text: str, terms: tuple[str, ...]) -> bool:
    return any(term in text for term in terms)
