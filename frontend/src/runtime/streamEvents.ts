import type { PermissionRequest, RuntimeEvent, RuntimeStreamEvent } from "../api/schemas.ts";
import type { ActivityItem } from "./reducer.ts";

export function runtimeStreamEvent(event: RuntimeEvent): RuntimeStreamEvent | null {
  const payload = recordValue(event.data.stream_event);
  const kind = stringValue(payload.kind);
  if (!kind) return null;
  return payload as RuntimeStreamEvent;
}

export function activityFromStreamEvent(event: RuntimeEvent, streamEvent: RuntimeStreamEvent): ActivityItem | null {
  if (streamEvent.kind === "assistant_delta" || streamEvent.kind === "assistant_final") {
    return null;
  }
  if (streamEvent.kind === "progress") {
    return {
      id: event.id,
      kind: "runtime",
      label: streamEvent.message,
      summary: "",
      status: "info",
      timestamp: event.timestamp,
      eventType: "stream.progress",
      category: "runtime",
      data: {
        stream_event_kind: streamEvent.kind,
        message: streamEvent.message,
        stage: streamEvent.stage ?? null,
        message_id: streamEvent.message_id ?? null,
      },
    };
  }
  if (streamEvent.kind === "tool_lifecycle") {
    const status = toolLifecycleStatus(streamEvent.phase);
    const details = recordValue(streamEvent.details);
    return {
      id: `tool:${streamEvent.tool_call_id}:${streamEvent.phase}`,
      kind: "tool",
      label: streamEvent.title || streamEvent.tool_name,
      summary: streamEvent.result_summary || streamEvent.args_summary || streamEvent.error?.message || "",
      status,
      timestamp: event.timestamp,
      eventType: "stream.tool_lifecycle",
      category: "tool",
      data: {
        ...details,
        stream_event_kind: streamEvent.kind,
        phase: streamEvent.phase,
        title: streamEvent.title ?? null,
        tool_call_id: streamEvent.tool_call_id,
        tool_name: streamEvent.tool_name,
        args_summary: streamEvent.args_summary ?? null,
        result_summary: streamEvent.result_summary ?? null,
        command: streamEvent.command ?? details.command,
        path: streamEvent.path ?? details.path,
        exit_code: streamEvent.exit_code ?? details.exit_code,
        duration_ms: streamEvent.duration_ms ?? details.duration_ms,
        error: streamEvent.error ?? null,
      },
    };
  }
  if (streamEvent.kind === "permission_state") {
    return {
      id: `permission:${streamEvent.tool_call_id}:${streamEvent.status}`,
      kind: "permission",
      label: permissionLabel(streamEvent),
      summary: streamEvent.reason || streamEvent.args_summary || "",
      status: permissionStatus(streamEvent.status),
      timestamp: event.timestamp,
      eventType: "stream.permission_state",
      category: "permission",
      data: {
        stream_event_kind: streamEvent.kind,
        status: streamEvent.status,
        tool_call_id: streamEvent.tool_call_id,
        tool_name: streamEvent.tool_name,
        action: streamEvent.action ?? null,
        risk: streamEvent.risk ?? null,
        args_summary: streamEvent.args_summary ?? null,
        reason: streamEvent.reason ?? null,
        args: streamEvent.args ?? {},
      },
    };
  }
  if (streamEvent.kind === "error") {
    return {
      id: event.id,
      kind: "error",
      label: streamEvent.error_type || "Runtime error",
      summary: streamEvent.message,
      status: "error",
      timestamp: event.timestamp,
      eventType: "stream.error",
      category: "error",
      data: { stream_event_kind: streamEvent.kind, ...streamEvent },
    };
  }
  if (streamEvent.kind === "artifact") {
    return {
      id: event.id,
      kind: "event",
      label: streamEvent.title || streamEvent.artifact_kind,
      summary: streamEvent.uri || "",
      status: "success",
      timestamp: event.timestamp,
      eventType: "stream.artifact",
      category: "artifact",
      data: { stream_event_kind: streamEvent.kind, ...streamEvent },
    };
  }
  return null;
}

export function permissionRequestFromStreamEvent(streamEvent: RuntimeStreamEvent): PermissionRequest | null {
  if (streamEvent.kind !== "permission_state" || streamEvent.status !== "required") {
    return null;
  }
  return {
    tool_call_id: streamEvent.tool_call_id,
    tool_name: streamEvent.tool_name,
    action: streamEvent.action ?? null,
    risk: streamEvent.risk ?? null,
    args_summary: streamEvent.args_summary ?? null,
    reason: streamEvent.reason ?? null,
    args: streamEvent.args ?? {},
  };
}

function toolLifecycleStatus(phase: Extract<RuntimeStreamEvent, { kind: "tool_lifecycle" }>["phase"]): ActivityItem["status"] {
  if (phase === "started" || phase === "scheduled" || phase === "permission_required") return "running";
  if (phase === "completed") return "success";
  if (phase === "failed") return "error";
  if (phase === "blocked") return "blocked";
  return "info";
}

function permissionStatus(status: Extract<RuntimeStreamEvent, { kind: "permission_state" }>["status"]): ActivityItem["status"] {
  if (status === "required") return "pending";
  if (status === "approved") return "success";
  if (status === "rejected" || status === "blocked") return "blocked";
  return "info";
}

function permissionLabel(streamEvent: Extract<RuntimeStreamEvent, { kind: "permission_state" }>): string {
  if (streamEvent.status === "required") return "Permission required";
  if (streamEvent.status === "approved") return "Permission approved";
  if (streamEvent.status === "rejected") return "Permission rejected";
  return "Permission blocked";
}

function recordValue(value: unknown): Record<string, unknown> {
  return value && typeof value === "object" && !Array.isArray(value) ? value as Record<string, unknown> : {};
}

function stringValue(value: unknown): string {
  return typeof value === "string" && value ? value : "";
}
