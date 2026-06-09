import type { RuntimeEvent } from "../api/schemas.ts";
import type { ActivityItem, ActivityKind } from "./reducer.ts";

const STRUCTURED_ACTIVITY_KINDS = new Set<ActivityKind>([
  "runtime",
  "workspace",
  "git",
  "tool",
  "permission",
  "skill",
  "verification",
  "mcp",
  "hook",
  "context",
  "error",
]);

export function legacyActivityKind(type: string): ActivityKind {
  if (type.startsWith("tool_call")) return "tool";
  if (type.startsWith("permission")) return "permission";
  if (type.startsWith("skill")) return "skill";
  if (type.startsWith("subagent")) return "subagent";
  if (type.startsWith("mcp")) return "mcp";
  if (type.startsWith("hook")) return "hook";
  if (type.startsWith("context")) return "context";
  if (type === "error") return "error";
  return "event";
}

export function legacyActivityKindFromStructuredCategory(category: string, type: string): ActivityKind {
  if (STRUCTURED_ACTIVITY_KINDS.has(category as ActivityKind)) {
    return category as ActivityKind;
  }
  return legacyActivityKind(type);
}

export function legacyActivityStatus(event: RuntimeEvent): ActivityItem["status"] {
  if (event.severity === "error" || event.type.endsWith("_error")) return "error";
  if (event.severity === "warning" || event.type === "permission_required") return "warning";
  if (event.type.endsWith("_started")) return "running";
  if (event.type.endsWith("_finished") || event.type === "final_response" || event.type === "permission_resolved") return "success";
  return "info";
}

export function legacyChildToolStatus(type: string, nestedStatus: unknown, fallback: ActivityItem["status"]): ActivityItem["status"] {
  if (
    nestedStatus === "running" ||
    nestedStatus === "pending" ||
    nestedStatus === "success" ||
    nestedStatus === "error" ||
    nestedStatus === "blocked" ||
    nestedStatus === "warning" ||
    nestedStatus === "info"
  ) {
    return nestedStatus;
  }
  if (type === "tool_call_started") return "running";
  if (type === "tool_call_error") return "error";
  if (type === "tool_call_finished") return "success";
  return fallback;
}

export function isLegacyToolLifecycleActivity(activity: ActivityItem): boolean {
  const category = (activity.category || activity.kind).toLowerCase();
  if (category === "permission") {
    return Boolean(stringValue(activity.data.tool_call_id));
  }
  if (category === "tool" || category === "verification") {
    return true;
  }
  return legacyOperationFamily(activity.data.operation) !== null;
}

export function legacyOperationActivityTitle(activity: ActivityItem, running: boolean): string | null {
  const operation = stringValue(activity.data.operation);
  const family = legacyOperationFamily(operation);
  if (family === "search") {
    const pattern = stringValue(activity.data.pattern);
    if (!pattern) return null;
    const noun = operation.endsWith(".grep") ? "text for" : "files matching";
    return `${running ? "Searching" : "Searched"} ${noun} ${pattern}`;
  }
  if (family === "file") {
    const path = displayPath(activity.data.path);
    if (!path) return null;
    const action = operation.split(".").at(-1) || "";
    if (action === "read") return `${running ? "Reading" : "Read"} ${path}`;
    if (action === "write") return `${running ? "Writing" : "Wrote"} ${path}`;
    if (action === "edit") return `${running ? "Editing" : "Edited"} ${path}`;
  }
  return null;
}

function legacyOperationFamily(value: unknown): "shell" | "file" | "search" | null {
  const operation = stringValue(value);
  if (operation.startsWith("shell.")) return "shell";
  if (operation.startsWith("file.")) return "file";
  if (operation.startsWith("search.")) return "search";
  return null;
}

function displayPath(value: unknown): string {
  const path = pathString(value);
  if (!path) return "";
  const normalized = path.replaceAll("\\", "/");
  return normalized.split("/").filter(Boolean).at(-1) || normalized;
}

function pathString(value: unknown): string {
  if (typeof value === "string") return value;
  if (isRecord(value)) {
    return stringValue(value.basename, value.name, value.path);
  }
  return "";
}

function stringValue(...values: unknown[]): string {
  for (const value of values) {
    if (typeof value === "string" && value.trim()) {
      return value.trim();
    }
  }
  return "";
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return Boolean(value) && typeof value === "object" && !Array.isArray(value);
}
