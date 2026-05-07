"""Plugin-owned runtime policy checks that still route through LangGraph skills."""

from __future__ import annotations

from langgraph_agent_blueprint.dependencies import AppDependencies
from langgraph_agent_blueprint.models.messages import event
from langgraph_agent_blueprint.models.plugins import PluginPolicyContribution, PluginPolicyContext
from langgraph_agent_blueprint.plugins.policy import evaluate_plugin_policy_contributions


def plugin_policy_node(state: dict, deps: AppDependencies) -> dict:
    """Apply enabled plugin policies before the first model response for a turn."""

    input_text = state.get("input_text", "")
    if state.get("final_response") or state.get("active_skill") or input_text.strip().startswith("tool:"):
        return {}
    policy_state = state.get("plugin_state", {}).get("policies", [])
    contributions = []
    for raw in policy_state:
        try:
            contributions.append(PluginPolicyContribution.model_validate(raw))
        except Exception as exc:
            return {"ui_events": [event("plugin_policy_error", error=str(exc), severity="warning")]}
    metadata = state.get("metadata", {}) if isinstance(state.get("metadata"), dict) else {}
    context = PluginPolicyContext(
        session_id=str(state.get("session_id") or "unknown"),
        input_text=input_text,
        metadata=metadata,
        invoked_skills=[str(item) for item in metadata.get("skill_invocations", [])],
    )
    results = evaluate_plugin_policy_contributions(contributions, context)
    if not results:
        return {}
    errors = [result for result in results if result.action == "error"]
    if errors:
        return {
            "ui_events": [
                event(
                    "plugin_policy_error",
                    policy_id=result.contribution_id,
                    plugin_name=result.plugin_name,
                    error=result.reason,
                    severity="warning",
                )
                for result in errors
            ]
        }
    activation = next((result for result in results if result.action == "activate_skill" and result.skill_name), None)
    if activation is None:
        return {}
    return {
        "active_skill": {"name": activation.skill_name, "args": input_text, "policy": activation.contribution_id},
        "ui_events": [
            event(
                "plugin_policy_applied",
                policy_id=activation.contribution_id,
                plugin_name=activation.plugin_name,
                skill=activation.skill_name,
                reason=activation.reason,
            )
        ],
    }
