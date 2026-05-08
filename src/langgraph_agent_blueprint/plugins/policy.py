"""Generic plugin policy contribution evaluation."""

from __future__ import annotations

from typing import Any

from langgraph_agent_blueprint.models import PluginPolicyContribution, PluginPolicyContext, PluginPolicyResult


def evaluate_plugin_policy_contributions(
    contributions: list[PluginPolicyContribution],
    context: PluginPolicyContext,
) -> list[PluginPolicyResult]:
    """Evaluate enabled policy contributions in priority order."""

    results: list[PluginPolicyResult] = []
    for contribution in sorted((item for item in contributions if item.enabled), key=lambda item: (item.priority, item.id)):
        try:
            result = _evaluate_contribution(contribution, context)
        except Exception as exc:
            result = PluginPolicyResult(
                contribution_id=contribution.id,
                plugin_name=contribution.plugin_name,
                action="error",
                reason=str(exc),
            )
        if result.action != "continue":
            results.append(result)
    return results


def _evaluate_contribution(contribution: PluginPolicyContribution, context: PluginPolicyContext) -> PluginPolicyResult:
    if contribution.policy_type in {"none", "context"}:
        return _continue(contribution)
    if contribution.policy_type == "skill_activation":
        return _evaluate_skill_activation(contribution, context)
    return PluginPolicyResult(
        contribution_id=contribution.id,
        plugin_name=contribution.plugin_name,
        action="error",
        reason=f"Unsupported plugin policy type: {contribution.policy_type}",
    )


def _evaluate_skill_activation(contribution: PluginPolicyContribution, context: PluginPolicyContext) -> PluginPolicyResult:
    rules = contribution.metadata.get("rules")
    if rules is None:
        rules = [contribution.metadata]
    if not isinstance(rules, list):
        raise ValueError("skill_activation policy metadata.rules must be a list")
    input_text = context.input_text.lower()
    invoked = set(context.invoked_skills)
    for index, rule in enumerate(rules):
        if not isinstance(rule, dict):
            raise ValueError(f"policy rule {index} must be an object")
        skill_name = rule.get("skill_name") or rule.get("skill")
        if not isinstance(skill_name, str) or not skill_name:
            raise ValueError("skill_activation policy rule requires skill_name")
        if bool(rule.get("once_per_session", True)) and skill_name in invoked:
            continue
        match_any = _string_list(rule.get("match_any") or rule.get("terms") or [])
        if match_any and not any(term.lower() in input_text for term in match_any):
            continue
        match_all = _string_list(rule.get("match_all") or [])
        if match_all and not all(term.lower() in input_text for term in match_all):
            continue
        if not match_any and not match_all:
            continue
        return PluginPolicyResult(
            contribution_id=contribution.id,
            plugin_name=contribution.plugin_name,
            action="activate_skill",
            skill_name=skill_name,
            reason=str(rule.get("reason") or contribution.metadata.get("reason") or f"Plugin policy {contribution.id} matched"),
            metadata={"rule_index": index, **{key: value for key, value in rule.items() if key not in {"match_any", "match_all", "terms"}}},
        )
    return _continue(contribution)


def _continue(contribution: PluginPolicyContribution) -> PluginPolicyResult:
    return PluginPolicyResult(contribution_id=contribution.id, plugin_name=contribution.plugin_name)


def _string_list(value: Any) -> list[str]:
    if isinstance(value, str):
        return [value]
    if isinstance(value, list):
        return [str(item) for item in value if str(item)]
    return []
