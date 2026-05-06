"""Plugin-owned runtime policy checks that still route through LangGraph skills."""

from __future__ import annotations

from langgraph_agent_blueprint.dependencies import AppDependencies
from langgraph_agent_blueprint.models.messages import event
from langgraph_agent_blueprint.plugins.superpowers import choose_superpowers_activation


def plugin_policy_node(state: dict, deps: AppDependencies) -> dict:
    """Apply enabled plugin policies before the first model response for a turn."""

    input_text = state.get("input_text", "")
    if state.get("final_response") or state.get("active_skill") or input_text.strip().startswith("tool:"):
        return {}
    activation = choose_superpowers_activation(input_text, state)
    if not activation:
        return {}
    return {
        "active_skill": {"name": activation["name"], "args": activation.get("args", ""), "policy": activation.get("policy")},
        "ui_events": [
            event(
                "superpowers_skill_policy_applied",
                skill=activation["name"],
                reason=activation.get("reason"),
            )
        ],
    }
