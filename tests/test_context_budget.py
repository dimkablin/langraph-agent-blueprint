"""Context budget truncation coverage."""

from __future__ import annotations

from langgraph_agent_blueprint.context.budget import ContextBudgetService
from langgraph_agent_blueprint.models.context import ContextFragment


def test_context_budget_truncates_and_reports_fragments() -> None:
    fragment = ContextFragment(
        id="ctx_large",
        kind="text",
        title="large paste",
        content="x" * 200,
        trust="user_provided",
        token_estimate=50,
    )
    service = ContextBudgetService(max_tokens=10)

    fragments, report = service.apply([fragment])

    assert fragments[0].truncated is True
    assert report.used_tokens <= 10
    assert report.truncated[0]["id"] == "ctx_large"
