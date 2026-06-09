import { buildActivityEntries, formatTerminalBlock } from "./activityTimeline.ts";
import type { RuntimeEvent, RuntimeStreamEvent } from "../api/schemas.ts";
import type { ActivityItem } from "./reducer.ts";
import { legacyActivityKindFromStructuredCategory, legacyChildToolStatus } from "./legacyStreamFallbacks.ts";
import { activityFromStreamEvent, runtimeStreamEvent } from "./streamEvents.ts";

export type SubagentTimelineRow = {
  id: string;
  kind: "status" | "message" | "tool" | "permission" | "event";
  title: string;
  summary: string;
  content: string;
  status: ActivityItem["status"];
};

export function buildSubagentTimelineRows(activities: ActivityItem[]): SubagentTimelineRow[] {
  const rows: SubagentTimelineRow[] = [];
  let tokenDraft: SubagentTimelineRow | null = null;
  let pendingToolActivities: ActivityItem[] = [];
  const expandedActivities = flattenSubagentActivities(activities);

  function flushTokenDraft() {
    const content = tokenDraft?.content.trim() || "";
    if (tokenDraft && content && !isDecorativeMessage(content)) {
      rows.push({ ...tokenDraft, content });
    }
    tokenDraft = null;
  }

  function discardTokenDraftIfDuplicatedBy(content: string) {
    if (!tokenDraft) return;
    const draft = normalizedContent(tokenDraft.content);
    const full = normalizedContent(content);
    if (draft && full && (full.startsWith(draft) || draft.startsWith(full))) {
      tokenDraft = null;
    }
  }

  function flushToolRows() {
    if (!pendingToolActivities.length) return;
    for (const entry of buildActivityEntries(pendingToolActivities)) {
      rows.push({
        id: entry.id,
        kind: "tool",
        title: entry.title,
        summary: entry.summary,
        content: entry.terminal ? formatTerminalBlock(entry) : "",
        status: entry.status,
      });
    }
    pendingToolActivities = [];
  }

  for (const activity of expandedActivities) {
    const child = childEvent(activity);
    if (activity.eventType === "subagent_started") {
      flushTokenDraft();
      flushToolRows();
      rows.push(statusRow(activity, "Started", stringValue(activity.summary, activity.data.name)));
      continue;
    }
    if (activity.eventType === "subagent_finished") {
      flushTokenDraft();
      flushToolRows();
      rows.push(statusRow(activity, "Finished", stringValue(activity.summary, activity.data.summary)));
      continue;
    }
    if (activity.eventType === "subagent_error") {
      flushTokenDraft();
      flushToolRows();
      rows.push(statusRow(activity, "Failed", stringValue(activity.summary, activity.data.error, activity.data.message)));
      continue;
    }
    if (activity.eventType !== "subagent_event") {
      flushTokenDraft();
      flushToolRows();
      rows.push(statusRow(activity, activity.label || activity.eventType, activity.summary));
      continue;
    }
    if (isLowSignalChildEvent(child.type)) {
      continue;
    }
    const typedChild = childStreamEvent(activity, child);
    if (typedChild) {
      if (typedChild.kind === "assistant_delta") {
        flushToolRows();
        if (!typedChild.delta) continue;
        tokenDraft = {
          id: tokenDraft?.id || typedChild.message_id || activity.id,
          kind: "message",
          title: "Message",
          summary: "",
          content: `${tokenDraft?.content || ""}${typedChild.delta}`,
          status: "running",
        };
        continue;
      }
      if (typedChild.kind === "assistant_final") {
        flushToolRows();
        discardTokenDraftIfDuplicatedBy(typedChild.content);
        flushTokenDraft();
        if (typedChild.content.trim() && !isDecorativeMessage(typedChild.content)) {
          rows.push({
            id: typedChild.message_id || activity.id,
            kind: "message",
            title: "Final response",
            summary: "",
            content: typedChild.content.trim(),
            status: activity.status,
          });
        }
        continue;
      }
      const typedActivity = childTypedActivity(activity, child, typedChild);
      if (typedActivity) {
        flushTokenDraft();
        if (typedActivity.kind === "tool") {
          pendingToolActivities.push(typedActivity);
        } else {
          flushToolRows();
          rows.push(typedActivityRow(typedActivity));
        }
        continue;
      }
    }
    if (child.type === "agent_activity") {
      const structuredActivity = childStructuredActivity(activity, child);
      if (structuredActivity && !isLowSignalStructuredActivity(structuredActivity)) {
        flushTokenDraft();
        pendingToolActivities.push(structuredActivity);
      }
      continue;
    }
    if (child.type === "model_token") {
      flushToolRows();
      const token = stringValue(child.data.token);
      if (!token) continue;
      tokenDraft = {
        id: tokenDraft?.id || activity.id,
        kind: "message",
        title: "Message",
        summary: "",
        content: `${tokenDraft?.content || ""}${token}`,
        status: "running",
      };
      continue;
    }
    if (child.type === "model_message" || child.type === "final_response") {
      flushToolRows();
      const content = stringValue(child.data.content);
      discardTokenDraftIfDuplicatedBy(content);
      flushTokenDraft();
      if (content.trim() && !isDecorativeMessage(content)) {
        rows.push({
          id: activity.id,
          kind: "message",
          title: child.type === "final_response" ? "Final response" : "Message",
          summary: "",
          content: content.trim(),
          status: activity.status,
        });
      }
      continue;
    }
    if (child.type === "tool_call_started" || child.type === "tool_call_finished" || child.type === "tool_call_error") {
      flushTokenDraft();
      pendingToolActivities.push(childToolActivity(activity, child));
      continue;
    }
    flushTokenDraft();
    flushToolRows();
    if (child.type === "permission_required" || child.type === "permission_resolved") {
      rows.push({
        id: activity.id,
        kind: "permission",
        title: child.type === "permission_required" ? "Permission required" : "Permission resolved",
        summary: stringValue(child.data.tool_name, child.data.command, activity.summary),
        content: "",
        status: activity.status,
      });
      continue;
    }
    rows.push({
      id: activity.id,
      kind: "event",
      title: readableChildEventType(child.type || activity.eventType),
      summary: stringValue(activity.summary, child.data.summary, child.data.message),
      content: "",
      status: activity.status,
    });
  }
  flushTokenDraft();
  flushToolRows();
  return rows;
}

function flattenSubagentActivities(activities: ActivityItem[]): ActivityItem[] {
  const flattened = activities.flatMap((activity) => {
    if (activity.relatedActivities?.length) {
      return activity.relatedActivities;
    }
    return [activity];
  });
  return flattened.map((activity, index) => ({ activity, index })).sort((left, right) => {
    const leftRun = stringValue(left.activity.data.run_id, left.activity.data.child_run_id);
    const rightRun = stringValue(right.activity.data.run_id, right.activity.data.child_run_id);
    if (leftRun && rightRun && leftRun !== rightRun) {
      return left.index - right.index;
    }
    const leftSequence = numberValue(left.activity.data.sequence);
    const rightSequence = numberValue(right.activity.data.sequence);
    if (leftSequence !== undefined && rightSequence !== undefined && leftSequence !== rightSequence) {
      return leftSequence - rightSequence;
    }
    return left.index - right.index;
  }).map((item) => item.activity);
}

function statusRow(activity: ActivityItem, title: string, summary: string): SubagentTimelineRow {
  return {
    id: activity.id,
    kind: "status",
    title,
    summary,
    content: "",
    status: activity.status,
  };
}

function childToolActivity(activity: ActivityItem, child: { type: string; data: Record<string, unknown> }): ActivityItem {
  const nested = recordValue(child.data.activity);
  const nestedData = recordValue(nested.data);
  const toolName = stringValue(child.data.name, child.data.tool_name, nestedData.tool_name);
  return {
    id: stringValue(nested.id) || activity.id,
    kind: "tool",
    category: stringValue(nested.category) || "tool",
    label: stringValue(nested.title) || readableChildEventType(child.type),
    summary: stringValue(nested.summary, activity.summary),
    status: statusFromChildToolEvent(child.type, nested.status, activity.status),
    timestamp: activity.timestamp,
    eventType: stringValue(nested.type) || child.type,
    data: {
      ...child.data,
      ...nestedData,
      tool_call_id: stringValue(nestedData.tool_call_id, child.data.tool_call_id, child.data.id) || activity.id,
      tool_name: toolName,
    },
  };
}

function childStructuredActivity(activity: ActivityItem, child: { type: string; data: Record<string, unknown> }): ActivityItem | null {
  const nested = recordValue(child.data.activity);
  const type = stringValue(nested.type);
  if (!type) return null;
  const category = stringValue(nested.category) || "event";
  return {
    id: stringValue(nested.id) || activity.id,
    kind: activityKindFromStructuredCategory(category, type),
    category,
    label: stringValue(nested.title) || readableChildEventType(type),
    summary: stringValue(nested.summary),
    status: statusFromChildToolEvent(type, nested.status, activity.status),
    timestamp: activity.timestamp,
    eventType: type,
    data: recordValue(nested.data),
  };
}

function childEvent(activity: ActivityItem): { type: string; data: Record<string, unknown> } {
  const child = recordValue(activity.data.child_event);
  return {
    type: stringValue(activity.data.child_event_type, child.type),
    data: recordValue(child.data),
  };
}

function childStreamEvent(activity: ActivityItem, child: { type: string; data: Record<string, unknown> }): RuntimeStreamEvent | null {
  const direct = recordValue(activity.data.child_stream_event);
  if (direct.kind) {
    return direct as RuntimeStreamEvent;
  }
  return runtimeStreamEvent(childRuntimeEvent(activity, child));
}

function childTypedActivity(
  activity: ActivityItem,
  child: { type: string; data: Record<string, unknown> },
  streamEvent: RuntimeStreamEvent,
): ActivityItem | null {
  return activityFromStreamEvent(childRuntimeEvent(activity, child), streamEvent);
}

function childRuntimeEvent(activity: ActivityItem, child: { type: string; data: Record<string, unknown> }): RuntimeEvent {
  return {
    id: activity.id,
    type: child.type || "subagent_event",
    timestamp: activity.timestamp,
    session_id: "child",
    severity: child.type === "error" ? "error" : "info",
    data: child.data,
  };
}

function typedActivityRow(activity: ActivityItem): SubagentTimelineRow {
  return {
    id: activity.id,
    kind: activity.kind === "permission" ? "permission" : activity.kind === "tool" ? "tool" : activity.kind === "runtime" ? "status" : "event",
    title: activity.label,
    summary: activity.summary,
    content: "",
    status: activity.status,
  };
}

function statusFromChildToolEvent(type: string, nestedStatus: unknown, fallback: ActivityItem["status"]): ActivityItem["status"] {
  return legacyChildToolStatus(type, nestedStatus, fallback);
}

function readableChildEventType(type: string): string {
  return type.replaceAll("_", " ");
}

function isLowSignalChildEvent(type: string): boolean {
  return [
    "session_started",
    "node_started",
    "node_finished",
    "usage_updated",
    "session_persisted",
    "runtime_metrics",
    "context_resolution_started",
    "context_budget_applied",
    "user_message",
  ].includes(type);
}

function isLowSignalStructuredActivity(activity: ActivityItem): boolean {
  return ["runtime", "workspace", "git", "context"].includes(activity.category || activity.kind);
}

function activityKindFromStructuredCategory(category: string, type: string): ActivityItem["kind"] {
  return legacyActivityKindFromStructuredCategory(category, type);
}

function normalizedContent(value: string): string {
  return value.replace(/\s+/g, " ").trim();
}

function isDecorativeMessage(value: string): boolean {
  const compact = value.replace(/\s+/g, "");
  return compact.length >= 3 && /^[*_=-]+$/.test(compact);
}

function stringValue(...values: unknown[]): string {
  for (const value of values) {
    if (typeof value === "string" && value) {
      return value;
    }
  }
  return "";
}

function recordValue(value: unknown): Record<string, unknown> {
  return value && typeof value === "object" && !Array.isArray(value) ? value as Record<string, unknown> : {};
}

function numberValue(value: unknown): number | undefined {
  return typeof value === "number" && Number.isFinite(value) ? value : undefined;
}
