"""LangGraph node that resolves typed context references before context_builder."""

from __future__ import annotations

from langgraph_agent_blueprint.dependencies import AppDependencies
from langgraph_agent_blueprint.models.base import dump_model, validate_list
from langgraph_agent_blueprint.models.context import AttachmentRef, ContextReference
from langgraph_agent_blueprint.models.messages import event


def resolve_context_node(state: dict, deps: AppDependencies) -> dict:
    """Resolve context refs/attachments through provider services and apply a context budget."""

    metadata = dict(state.get("metadata", {}))
    if metadata.get("context_resolved"):
        return {}
    references = validate_list(ContextReference, state.get("context_references", []))
    attachments = validate_list(AttachmentRef, state.get("attachments", []))
    if not references and not attachments:
        return {}
    events = [event("context_resolution_started", count=len(references), attachments_count=len(attachments))]
    items = deps.context_provider_service.resolve_many(references, attachments)
    fragments = []
    errors = []
    attachment_contents = []
    for item in items:
        fragments.extend(item.fragments)
        attachment_contents.extend(item.attachments)
        errors.extend(item.errors)
    budgeted_fragments, budget_report = deps.context_budget_service.apply(fragments)
    rendered_context = deps.context_provider_service.render_fragments(budgeted_fragments)
    for fragment in budgeted_fragments:
        events.append(
            event(
                "context_fragment_added",
                id=fragment.id,
                kind=fragment.kind,
                title=fragment.title,
                trust=fragment.trust,
                token_estimate=fragment.token_estimate,
                truncated=fragment.truncated,
            )
        )
    for error in errors:
        events.append(event("context_resolution_error", severity="warning", **error))
    events.append(
        event(
            "context_budget_applied",
            max_tokens=budget_report.max_tokens,
            used_tokens=budget_report.used_tokens,
            included=len(budget_report.included),
            dropped=len(budget_report.dropped),
            truncated=len(budget_report.truncated),
        )
    )
    context_status = dict(state.get("context_status", {}))
    context_status.update(
        {
            "context_fragments": [dump_model(fragment) for fragment in budgeted_fragments],
            "context_provider_context": rendered_context,
            "context_budget": dump_model(budget_report),
            "context_errors": errors,
        }
    )
    metadata.update(
        {
            "context_resolved": True,
            "context_references": [dump_model(reference) for reference in references],
            "attachments": [dump_model(attachment) for attachment in attachments],
            "context_budget": dump_model(budget_report),
        }
    )
    return {
        "metadata": metadata,
        "context_status": context_status,
        "resolved_context": [dump_model(fragment) for fragment in budgeted_fragments],
        "attachment_contents": [dump_model(content) for content in attachment_contents],
        "ui_events": events,
    }
