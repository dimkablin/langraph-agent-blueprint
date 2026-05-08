"""Report writing for eval/replay runs."""

from __future__ import annotations

import json
from collections import Counter
from pathlib import Path
from typing import Any

from langgraph_agent_blueprint.models.evals import EvalReport, EvalRunResult


class EvalReporter:
    """Write compact redacted JSON and Markdown reports for eval runs."""

    def write_scenario_result(self, run_dir: str | Path, result: EvalRunResult) -> tuple[Path, Path]:
        """Write one scenario result under ``scenario-results``."""

        scenario_dir = Path(run_dir) / "scenario-results"
        scenario_dir.mkdir(parents=True, exist_ok=True)
        json_path = scenario_dir / f"{result.scenario_id}.json"
        md_path = scenario_dir / f"{result.scenario_id}.md"
        payload = _scenario_payload(result)
        json_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
        md_path.write_text(_scenario_markdown(payload), encoding="utf-8")
        return json_path, md_path

    def write_run_report(self, run_dir: str | Path, report: EvalReport) -> tuple[Path, Path]:
        """Write aggregate report files for a run."""

        target = Path(run_dir)
        target.mkdir(parents=True, exist_ok=True)
        json_path = target / "report.json"
        md_path = target / "report.md"
        payload = report.model_dump(mode="json")
        json_path.write_text(json.dumps(_redact(payload), ensure_ascii=False, indent=2), encoding="utf-8")
        md_path.write_text(_run_markdown(report), encoding="utf-8")
        return json_path, md_path


def _scenario_payload(result: EvalRunResult) -> dict[str, Any]:
    events = [item for item in result.events if isinstance(item, dict)]
    event_counts = Counter(str(event.get("type")) for event in events)
    tool_calls = _compact_tool_results(result.final_state.get("tool_results", []))
    context_fragments = _compact_context_fragments(result.final_state.get("resolved_context", []))
    final_response = str(result.final_state.get("final_response") or "")
    payload = {
        "scenario_id": result.scenario_id,
        "passed": result.passed,
        "failures": result.failures,
        "metadata": result.metadata,
        "event_counts": dict(sorted(event_counts.items())),
        "tool_calls": tool_calls,
        "skills": _event_names(events, {"skill_started", "skill_finished"}),
        "permissions": _event_names(events, {"permission_required", "permission_resolved"}),
        "mcp_calls": _event_names(events, {"mcp_tool_call_started", "mcp_tool_call_finished", "mcp_tool_call_error"}),
        "subagents": _event_names(events, {"subagent_started", "subagent_finished", "subagent_error", "subagent_timeout"}),
        "context_fragments": context_fragments,
        "final_response_excerpt": _truncate(final_response, 1000),
    }
    return _redact(payload)


def _compact_tool_results(raw_items: Any) -> list[dict[str, Any]]:
    items: list[dict[str, Any]] = []
    if not isinstance(raw_items, list):
        return items
    for raw in raw_items:
        if not isinstance(raw, dict):
            continue
        items.append(
            {
                "name": raw.get("name"),
                "status": raw.get("status"),
                "content_excerpt": _truncate(str(raw.get("content") or ""), 500),
            }
        )
    return items


def _compact_context_fragments(raw_items: Any) -> list[dict[str, Any]]:
    items: list[dict[str, Any]] = []
    if not isinstance(raw_items, list):
        return items
    for raw in raw_items:
        if not isinstance(raw, dict):
            continue
        items.append(
            {
                "kind": raw.get("kind"),
                "title": raw.get("title"),
                "trust": raw.get("trust"),
                "truncated": raw.get("truncated"),
                "token_estimate": raw.get("token_estimate"),
            }
        )
    return items


def _event_names(events: list[dict[str, Any]], event_types: set[str]) -> list[dict[str, Any]]:
    items = []
    for event in events:
        if event.get("type") not in event_types:
            continue
        data = event.get("data") if isinstance(event.get("data"), dict) else {}
        items.append({"type": event.get("type"), "data": _redact(data)})
    return items


def _scenario_markdown(payload: dict[str, Any]) -> str:
    status = "passed" if payload["passed"] else "failed"
    lines = [
        f"# Eval Scenario: {payload['scenario_id']}",
        "",
        f"Status: **{status}**",
        "",
        "## Failures",
    ]
    failures = payload.get("failures") or []
    if failures:
        lines.extend(f"- {failure}" for failure in failures)
    else:
        lines.append("- none")
    lines.extend(
        [
            "",
            "## Event Counts",
            "",
            "```json",
            json.dumps(payload.get("event_counts", {}), ensure_ascii=False, indent=2),
            "```",
            "",
            "## Final Response Excerpt",
            "",
            payload.get("final_response_excerpt", ""),
            "",
        ]
    )
    return "\n".join(lines)


def _run_markdown(report: EvalReport) -> str:
    status = "passed" if report.passed else "failed"
    lines = [f"# Eval Run {report.run_id}", "", f"Status: **{status}**", "", "## Scenarios"]
    for result in report.results:
        scenario_status = "passed" if result.passed else "failed"
        lines.append(f"- {result.scenario_id}: {scenario_status}")
        for failure in result.failures:
            lines.append(f"  - {failure}")
    lines.append("")
    return "\n".join(lines)


def _redact(value: Any, key: str | None = None) -> Any:
    sensitive = ("api_key", "apikey", "authorization", "auth", "cookie", "credential", "key", "password", "secret", "token")
    if key and any(part in key.lower() for part in sensitive):
        return "***" if value not in (None, "") else None
    if isinstance(value, dict):
        return {str(item_key): _redact(item_value, str(item_key)) for item_key, item_value in value.items()}
    if isinstance(value, list):
        return [_redact(item) for item in value]
    if isinstance(value, str):
        return _truncate(value, 4000)
    return value


def _truncate(text: str, limit: int) -> str:
    if len(text) <= limit:
        return text
    return text[:limit].rstrip() + "\n[truncated]"
