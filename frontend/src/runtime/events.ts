import type { RuntimeEvent } from "../api/schemas";

export const LOW_SIGNAL_EVENTS = new Set([
  "session_started",
  "session_persisted",
  "node_started",
  "node_finished",
  "context_resolution_started",
]);

export function eventTitle(event: RuntimeEvent): string {
  const data = event.data || {};
  const named = firstString(data.name, data.tool_name, data.server, data.hook_id, data.child_run_id);
  return named ? `${event.type}: ${named}` : event.type;
}

export function eventSummary(event: RuntimeEvent): string {
  const data = event.data || {};
  const content = firstString(
    data.content,
    data.reason,
    data.args_summary,
    data.summary,
    data.status,
    data.error,
    data.message,
  );
  if (content) {
    return content;
  }
  const keys = Object.keys(data);
  return keys.length ? keys.slice(0, 4).join(", ") : "";
}

export function firstString(...values: unknown[]): string {
  for (const value of values) {
    if (typeof value === "string" && value.trim()) {
      return value;
    }
  }
  return "";
}

export function safeJson(value: unknown): string {
  try {
    return JSON.stringify(value, null, 2);
  } catch {
    return String(value);
  }
}

