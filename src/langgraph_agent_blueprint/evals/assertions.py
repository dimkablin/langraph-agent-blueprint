"""Tolerant expectation assertions for eval/replay results."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from langgraph_agent_blueprint.models import EvalExpectations


class EvalAssertionEngine:
    """Assert scenario expectations against one graph result/state snapshot."""

    def assert_expectations(
        self,
        result: dict[str, Any],
        expectations: EvalExpectations,
        *,
        workspace: str | Path | None = None,
    ) -> list[str]:
        failures: list[str] = []
        events = _events(result)
        failures.extend(self._assert_events(events, expectations))
        failures.extend(self._assert_tool_calls(result, expectations))
        failures.extend(self._assert_skills(events, expectations))
        failures.extend(self._assert_permissions(events, expectations))
        failures.extend(self._assert_mcp(events, expectations))
        failures.extend(self._assert_subagents(events, expectations))
        failures.extend(self._assert_context(result, expectations))
        failures.extend(self._assert_final_response(result, expectations))
        if workspace is not None:
            failures.extend(self._assert_files(Path(workspace), expectations))
        return failures

    def _assert_events(self, events: list[dict[str, Any]], expectations: EvalExpectations) -> list[str]:
        failures = []
        for expected in expectations.events:
            matches = [event for event in events if event.get("type") == expected.type and _contains_subset(_event_payload(event), expected.contains)]
            count = len(matches)
            if count < expected.min_count:
                failures.append(f"Expected event {expected.type} at least {expected.min_count} time(s), found {count}")
            if expected.max_count is not None and count > expected.max_count:
                failures.append(f"Expected event {expected.type} at most {expected.max_count} time(s), found {count}")
        return failures

    def _assert_tool_calls(self, result: dict[str, Any], expectations: EvalExpectations) -> list[str]:
        failures = []
        tool_results = [item for item in result.get("tool_results", []) if isinstance(item, dict)]
        for expected in expectations.tool_calls:
            matches = [
                item
                for item in tool_results
                if item.get("name") == expected.name and (expected.status == "any" or item.get("status") == expected.status)
            ]
            if len(matches) < expected.min_count:
                failures.append(f"Expected tool call {expected.name} status {expected.status}, found {len(matches)}")
        return failures

    def _assert_skills(self, events: list[dict[str, Any]], expectations: EvalExpectations) -> list[str]:
        failures = []
        for expected in expectations.skills:
            matches = [
                event for event in events if event.get("type") in {"skill_started", "skill_finished"} and event.get("data", {}).get("name") == expected.name
            ]
            if len(matches) < expected.min_count:
                failures.append(f"Expected skill invocation {expected.name}, found {len(matches)} skill events")
        return failures

    def _assert_permissions(self, events: list[dict[str, Any]], expectations: EvalExpectations) -> list[str]:
        failures = []
        for expected in expectations.permissions:
            if expected.decision == "required":
                event_type = "permission_required"
            elif expected.decision in {"approved", "rejected"}:
                event_type = "permission_resolved"
            else:
                event_type = None
            matches = []
            for event in events:
                data = event.get("data", {})
                if event_type and event.get("type") != event_type:
                    continue
                if not event_type and event.get("type") not in {"permission_required", "permission_resolved"}:
                    continue
                if expected.tool_name and data.get("tool_name") != expected.tool_name:
                    continue
                if expected.decision == "approved" and data.get("approved") is not True:
                    continue
                if expected.decision == "rejected" and data.get("approved") is not False:
                    continue
                matches.append(event)
            if not matches:
                failures.append(f"Expected permission {expected.decision} for {expected.tool_name or 'any tool'}")
        return failures

    def _assert_mcp(self, events: list[dict[str, Any]], expectations: EvalExpectations) -> list[str]:
        failures = []
        for expected in expectations.mcp_calls:
            matches = []
            for event in events:
                if event.get("type") not in {"mcp_tool_call_finished", "mcp_tool_call_error"}:
                    continue
                data = event.get("data", {})
                if data.get("server_name") != expected.server_name or data.get("tool_name") != expected.tool_name:
                    continue
                if expected.status != "any" and data.get("status") != expected.status:
                    continue
                matches.append(event)
            if not matches:
                failures.append(f"Expected MCP call {expected.server_name}/{expected.tool_name} status {expected.status}")
        return failures

    def _assert_subagents(self, events: list[dict[str, Any]], expectations: EvalExpectations) -> list[str]:
        failures = []
        for expected in expectations.subagents:
            matches = []
            for event in events:
                if expected.status == "ok" and event.get("type") != "subagent_finished":
                    continue
                if expected.status == "error" and event.get("type") != "subagent_error":
                    continue
                if expected.status == "timeout" and event.get("type") != "subagent_timeout":
                    continue
                if expected.status == "any" and event.get("type") not in {"subagent_finished", "subagent_error", "subagent_timeout"}:
                    continue
                matches.append(event)
            if len(matches) < expected.min_count:
                failures.append(f"Expected subagent run status {expected.status}, found {len(matches)}")
        return failures

    def _assert_context(self, result: dict[str, Any], expectations: EvalExpectations) -> list[str]:
        failures = []
        fragments = [item for item in result.get("resolved_context", []) if isinstance(item, dict)]
        for expected in expectations.context_fragments:
            matches = []
            for fragment in fragments:
                if expected.kind and fragment.get("kind") != expected.kind:
                    continue
                if expected.trust and fragment.get("trust") != expected.trust:
                    continue
                if expected.title_contains and expected.title_contains not in str(fragment.get("title", "")):
                    continue
                if expected.content_contains and expected.content_contains not in str(fragment.get("content", "")):
                    continue
                matches.append(fragment)
            if not matches:
                failures.append(f"Expected context fragment kind={expected.kind} title_contains={expected.title_contains}")
        return failures

    def _assert_final_response(self, result: dict[str, Any], expectations: EvalExpectations) -> list[str]:
        expected = expectations.final_response
        if expected is None:
            return []
        text = str(result.get("final_response") or "")
        failures = []
        for item in expected.contains:
            if item not in text:
                failures.append(f"Expected final response to contain {item!r}")
        for item in expected.not_contains:
            if item in text:
                failures.append(f"Expected final response not to contain {item!r}")
        return failures

    def _assert_files(self, workspace: Path, expectations: EvalExpectations) -> list[str]:
        failures = []
        for expected in expectations.files:
            path = (workspace / expected.path).resolve()
            try:
                path.relative_to(workspace.resolve())
            except ValueError:
                failures.append(f"Expected file path escapes workspace: {expected.path}")
                continue
            exists = path.exists()
            if exists != expected.exists:
                failures.append(f"Expected file {expected.path} exists={expected.exists}, got {exists}")
                continue
            if not exists:
                continue
            text = path.read_text(encoding="utf-8", errors="replace")
            for item in expected.contains:
                if item not in text:
                    failures.append(f"Expected file {expected.path} to contain {item!r}")
            for item in expected.not_contains:
                if item in text:
                    failures.append(f"Expected file {expected.path} not to contain {item!r}")
        return failures


def _events(result: dict[str, Any]) -> list[dict[str, Any]]:
    return [item for item in result.get("ui_events", []) if isinstance(item, dict)]


def _event_payload(event: dict[str, Any]) -> dict[str, Any]:
    data = event.get("data", {})
    if isinstance(data, dict):
        return {**event, **data}
    return dict(event)


def _contains_subset(payload: dict[str, Any], expected: dict[str, Any]) -> bool:
    for key, value in expected.items():
        if key not in payload:
            return False
        actual = payload[key]
        if isinstance(value, dict) and isinstance(actual, dict):
            if not _contains_subset(actual, value):
                return False
        elif actual != value:
            return False
    return True
