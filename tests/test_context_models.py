"""Pydantic boundary tests for context provider and attachment runtime models."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from langgraph_agent_blueprint.models.context import (
    AttachmentContent,
    AttachmentRef,
    ContextBudgetReport,
    ContextFragment,
    ContextReference,
    ResolvedContextItem,
)


def test_context_reference_and_fragment_are_json_safe() -> None:
    reference = ContextReference(kind="file", value="README.md", label="Readme")
    fragment = ContextFragment(
        id="ctx_123",
        kind="file",
        title="README.md",
        content="hello",
        trust="trusted_local",
        token_estimate=2,
        source_ref=reference.model_dump(mode="json"),
    )
    item = ResolvedContextItem(reference=reference, fragments=[fragment])

    dumped = item.model_dump(mode="json")

    assert dumped["reference"]["kind"] == "file"
    assert dumped["fragments"][0]["trust"] == "trusted_local"


def test_attachment_and_budget_models_validate() -> None:
    attachment = AttachmentRef(id="att_1", kind="text", name="paste.txt", trust="user_provided")
    content = AttachmentContent(ref_id=attachment.id, kind="text", text="pasted", trust="user_provided")
    report = ContextBudgetReport(max_tokens=10, used_tokens=2, included=["ctx_1"])

    assert content.model_dump(mode="json")["text"] == "pasted"
    assert report.used_tokens == 2


def test_invalid_context_kind_is_rejected() -> None:
    with pytest.raises(ValidationError):
        ContextReference.model_validate({"kind": "unsupported", "value": "x"})
