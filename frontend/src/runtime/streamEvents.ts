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
        scope: streamEvent.scope ?? "tool",
        parent_session_id: streamEvent.parent_session_id ?? null,
        parent_thread_id: streamEvent.parent_thread_id ?? null,
        child_session_id: streamEvent.child_session_id ?? null,
        child_thread_id: streamEvent.child_thread_id ?? null,
        child_run_id: streamEvent.child_run_id ?? null,
        subagent_name: streamEvent.subagent_name ?? null,
      },
    };
  }
  if (streamEvent.kind === "subagent") {
    const childEvent = recordValue(streamEvent.child_event);
    const childStreamEvent = recordValue(streamEvent.child_stream_event);
    const childData = recordValue(childEvent.data);
    const childEventType = streamEvent.child_event_type || stringValue(childEvent.type) || (childStreamEvent.kind ? "typed_child_event" : "");
    const normalizedChildEvent =
      Object.keys(childEvent).length > 0
        ? childEvent
        : childEventType || Object.keys(childStreamEvent).length > 0
          ? { type: childEventType || "typed_child_event", data: { stream_event: childStreamEvent } }
          : {};
    return {
      id: `subagent:${streamEvent.run_id}:${streamEvent.sequence}`,
      kind: "subagent",
      label: subagentLabel(streamEvent),
      summary: streamEvent.summary || stringValue(childData.content, childData.summary, childData.message) || "",
      status: subagentStatus(streamEvent),
      timestamp: event.timestamp,
      eventType: subagentEventType(streamEvent.phase),
      category: "subagent",
      data: {
        stream_event_kind: streamEvent.kind,
        phase: streamEvent.phase,
        subagent_id: streamEvent.subagent_id,
        run_id: streamEvent.run_id,
        child_run_id: streamEvent.run_id,
        sequence: streamEvent.sequence,
        parent_session_id: streamEvent.parent_session_id ?? null,
        parent_thread_id: streamEvent.parent_thread_id ?? null,
        child_session_id: streamEvent.child_session_id ?? null,
        child_thread_id: streamEvent.child_thread_id ?? null,
        agent_call_id: streamEvent.agent_call_id ?? null,
        name: streamEvent.name ?? null,
        purpose: streamEvent.purpose ?? null,
        status: streamEvent.status ?? null,
        summary: streamEvent.summary ?? null,
        child_event_id: (streamEvent.child_event_id ?? stringValue(childEvent.id)) || null,
        child_event_type: childEventType || null,
        child_event: normalizedChildEvent,
        child_stream_event: childStreamEvent,
        error: streamEvent.error ?? null,
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
    scope: streamEvent.scope ?? "tool",
    parent_session_id: streamEvent.parent_session_id ?? null,
    parent_thread_id: streamEvent.parent_thread_id ?? null,
    child_session_id: streamEvent.child_session_id ?? null,
    child_thread_id: streamEvent.child_thread_id ?? null,
    child_run_id: streamEvent.child_run_id ?? null,
    subagent_name: streamEvent.subagent_name ?? null,
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

function subagentEventType(phase: Extract<RuntimeStreamEvent, { kind: "subagent" }>["phase"]): string {
  if (phase === "started") return "subagent_started";
  if (phase === "finished") return "subagent_finished";
  if (phase === "error") return "subagent_error";
  if (phase === "cancelled") return "subagent_cancelled";
  if (phase === "timeout") return "subagent_timeout";
  return "subagent_event";
}

function subagentStatus(streamEvent: Extract<RuntimeStreamEvent, { kind: "subagent" }>): ActivityItem["status"] {
  if (streamEvent.phase === "started") return "running";
  if (streamEvent.phase === "finished") return "success";
  if (streamEvent.phase === "error" || streamEvent.phase === "timeout") return "error";
  if (streamEvent.phase === "cancelled") return "blocked";
  if (streamEvent.error) return "error";
  return "info";
}

function subagentLabel(streamEvent: Extract<RuntimeStreamEvent, { kind: "subagent" }>): string {
  const name = streamEvent.name || streamEvent.run_id;
  if (streamEvent.phase === "started") return `Subagent started: ${name}`;
  if (streamEvent.phase === "finished") return `Subagent finished: ${name}`;
  if (streamEvent.phase === "error") return `Subagent failed: ${name}`;
  return `Subagent event: ${name}`;
}

function recordValue(value: unknown): Record<string, unknown> {
  return value && typeof value === "object" && !Array.isArray(value) ? value as Record<string, unknown> : {};
}

function stringValue(value: unknown): string {
  return typeof value === "string" && value ? value : "";
}
