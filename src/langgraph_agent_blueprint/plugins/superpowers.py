"""Superpowers plugin adapter and graph-level activation policy."""

from __future__ import annotations

from pathlib import Path

from langgraph_agent_blueprint.models.plugins import PluginContribution, PluginPolicyContribution


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


def superpowers_policy_contribution() -> PluginPolicyContribution:
    """Return the default declarative Superpowers methodology policy."""

    return PluginPolicyContribution(
        id="superpowers.default_methodology_policy",
        plugin_name=SUPERPOWERS_PLUGIN_NAME,
        priority=50,
        policy_type="skill_activation",
        metadata={
            "rules": [
                {
                    "skill_name": "superpowers/systematic-debugging",
                    "match_any": list(DEBUG_TERMS),
                    "reason": "debugging request matched Superpowers policy",
                    "once_per_session": True,
                },
                {
                    "skill_name": "superpowers/brainstorming",
                    "match_any": list(DEVELOPMENT_TERMS),
                    "reason": "development request matched Superpowers brainstorming policy",
                    "once_per_session": True,
                },
            ]
        },
    )
