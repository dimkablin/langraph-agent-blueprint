import type { ActivityItem, ActivityKind } from "./reducer.ts";
import { isLegacyToolLifecycleActivity, legacyOperationActivityTitle } from "./legacyStreamFallbacks.ts";

export type ActivityTerminalBlock = {
  command: string;
  output: string;
  exitCode?: number;
  truncated: boolean;
};

export type ActivityTimelineEntry = {
  id: string;
  activity: ActivityItem;
  activities: ActivityItem[];
  title: string;
  titleLead: string;
  titleRest: string;
  summary: string;
  status: ActivityItem["status"];
  kind: ActivityKind;
  category: string;
  terminal: ActivityTerminalBlock | null;
  debugPayload: unknown;
  isCommand: boolean;
  isSubagent: boolean;
  subagentName: string;
  detailStatusLabel: string;
};

const TERMINAL_OUTPUT_LIMIT = 1600;

export function buildActivityEntries(activities: ActivityItem[]): ActivityTimelineEntry[] {
  const buckets: { key: string; activity: ActivityItem; activities: ActivityItem[] }[] = [];
  for (const activity of activities) {
    if (isLowSignalSubagentActivity(activity)) {
      continue;
    }
    const key = activityGroupingKey(activity);
    const bucket = buckets.find((item) => item.key === key);
    if (!bucket) {
      buckets.push({ key, activity, activities: [activity] });
      continue;
    }
    bucket.activity = mergeActivity(bucket.activity, activity);
    bucket.activities.push(activity);
  }
  return buckets.map((bucket) => activityTimelineEntry(bucket.activity, bucket.activities));
}

export function groupActivitiesForTimeline(activities: ActivityItem[]): ActivityItem[] {
  return activities.reduce<ActivityItem[]>((items, activity) => mergeActivityForTimeline(items, activity), []);
}

export function mergeActivityForTimeline(activities: ActivityItem[], activity: ActivityItem): ActivityItem[] {
  const key = activityGroupingKey(activity);
  const index = activities.findIndex((item) => activityGroupingKey(item) === key);
  if (index === -1) {
    return [...activities, activity];
  }
  const next = [...activities];
  next[index] = mergeActivity(next[index], activity);
  return next;
}

export function formatTerminalBlock(entry: ActivityTimelineEntry): string {
  if (!entry.terminal) return "";
  const lines = [`$ ${entry.terminal.command}`];
  if (entry.terminal.output) {
    lines.push(entry.terminal.output);
  }
  if (entry.terminal.truncated) {
    lines.push("...<truncated>");
  }
  return lines.join("\n");
}

export function activityStatusLabel(status: ActivityItem["status"]): string {
  if (status === "running") return "Running";
  if (status === "success" || status === "ok") return "Success";
  if (status === "error") return "Failed";
  if (status === "blocked") return "Blocked";
  if (status === "warning") return "Warning";
  if (status === "pending") return "Pending";
  return "Info";
}

export function activityTimelineGroupTitle(entries: ActivityTimelineEntry[]): string {
  const subagentEntries = entries.filter((entry) => entry.isSubagent);
  if (subagentEntries.length === 1) {
    return `Subagent ${subagentEntries[0].subagentName || "activity"}`;
  }
  if (subagentEntries.length > 1) {
    const runningCount = subagentEntries.filter((entry) => isRunning(entry.activity)).length;
    if (runningCount > 0) {
      return `${runningCount}/${subagentEntries.length} parallel subagents running`;
    }
    return `Ran ${subagentEntries.length} parallel subagents`;
  }
  const commandEntries = entries.filter((entry) => Boolean(entry.terminal));
  if (commandEntries.length > 0 && commandEntries.length === entries.length) {
    return `Ran ${commandEntries.length} ${commandEntries.length === 1 ? "command" : "commands"}`;
  }
  const toolEntries = entries.filter(isToolTimelineEntry);
  if (toolEntries.length === 1 && entries.length === 1) {
    return toolEntries[0].title;
  }
  if (toolEntries.length > 0 && toolEntries.length === entries.length) {
    return `Ran ${toolEntries.length} ${toolEntries.length === 1 ? "tool" : "tools"}`;
  }
  if (entries.length === 1) {
    return entries[0].title || "1 activity";
  }
  return `${entries.length} activities`;
}

function isToolTimelineEntry(entry: ActivityTimelineEntry): boolean {
  return ["tool", "verification", "mcp"].includes(entry.kind) || ["tool", "verification", "mcp"].includes(entry.category);
}

function activityTimelineEntry(activity: ActivityItem, activities: ActivityItem[]): ActivityTimelineEntry {
  const relatedActivities = expandRelatedActivities(activities);
  const terminal = terminalBlock(activity);
  const title = compactTitle(activity);
  const titleParts = activityTitleParts(title, terminal);
  return {
    id: activity.id,
    activity,
    activities: relatedActivities,
    title,
    titleLead: titleParts.lead,
    titleRest: titleParts.rest,
    summary: compactSummary(activity),
    status: activity.status,
    kind: activity.kind,
    category: activity.category || activity.kind,
    terminal,
    debugPayload: relatedActivities.length > 1 ? relatedActivities.map(debugPayloadForActivity) : debugPayloadForActivity(activity),
    isCommand: Boolean(terminal),
    isSubagent: isSubagentActivity(activity),
    subagentName: subagentName(activity),
    detailStatusLabel: activityStatusLabel(activity.status),
  };
}

function activityTitleParts(title: string, terminal: ActivityTerminalBlock | null): { lead: string; rest: string } {
  return splitTitleLead(terminal?.command || title);
}

function splitTitleLead(value: string): { lead: string; rest: string } {
  const match = value.trim().match(/^(\S+)(?:\s+([\s\S]+))?$/);
  if (!match) {
    return { lead: value, rest: "" };
  }
  return { lead: match[1], rest: match[2] || "" };
}

function mergeActivity(previous: ActivityItem, activity: ActivityItem): ActivityItem {
  const relatedActivities = [...activitySnapshots(previous), ...activitySnapshots(activity)];
  const kind = preferredActivityKind(previous, activity);
  const category = preferredActivityCategory(previous, activity);
  return {
    ...previous,
    ...activity,
    id: previous.id,
    kind,
    status: preferredActivityStatus(previous, activity),
    label: activity.label || previous.label,
    summary: activity.summary || previous.summary,
    category,
    data: { ...previous.data, ...activity.data },
    relatedActivities,
  };
}

function preferredActivityStatus(previous: ActivityItem, activity: ActivityItem): ActivityItem["status"] {
  if (isSubagentActivity(previous) && activity.eventType === "subagent_event" && activity.status === "info") {
    return previous.status;
  }
  return activity.status;
}

function activityGroupingKey(activity: ActivityItem): string {
  const childRunId = stringValue(activity.data.child_run_id);
  if (childRunId && activity.kind === "subagent") {
    return `subagent:${childRunId}`;
  }
  const toolCallId = stringValue(activity.data.tool_call_id);
  if (toolCallId && isToolLifecycleActivity(activity)) {
    return `tool-call:${toolCallId}`;
  }
  return `activity:${activity.id}`;
}

function isToolLifecycleActivity(activity: ActivityItem): boolean {
  return isLegacyToolLifecycleActivity(activity);
}

function expandRelatedActivities(activities: ActivityItem[]): ActivityItem[] {
  return activities.flatMap((activity) => activity.relatedActivities?.length ? activity.relatedActivities : [activity]);
}

function activitySnapshots(activity: ActivityItem): ActivityItem[] {
  const activities = activity.relatedActivities?.length ? activity.relatedActivities : [activity];
  return activities.map(activitySnapshot);
}

function activitySnapshot(activity: ActivityItem): ActivityItem {
  const { relatedActivities: _relatedActivities, ...snapshot } = activity;
  return snapshot;
}

function preferredActivityKind(previous: ActivityItem, activity: ActivityItem): ActivityKind {
  if (previous.kind !== "permission" && activity.kind === "permission") {
    return previous.kind;
  }
  return activity.kind;
}

function preferredActivityCategory(previous: ActivityItem, activity: ActivityItem): string | undefined {
  const previousCategory = previous.category || previous.kind;
  const activityCategory = activity.category || activity.kind;
  if (previousCategory !== "permission" && activityCategory === "permission") {
    return previous.category;
  }
  return activity.category || previous.category;
}

function compactTitle(activity: ActivityItem): string {
  const typedTitle = stringValue(activity.data.stream_event_kind) ? stringValue(activity.data.title) : "";
  if (typedTitle) return typedTitle;
  const permissionTitle = permissionActivityTitle(activity);
  if (permissionTitle) return permissionTitle;
  const subagentTitle = subagentActivityTitle(activity);
  if (subagentTitle) return subagentTitle;
  const skillTitle = skillActivityTitle(activity);
  if (skillTitle) return skillTitle;
  const operationTitle = operationActivityTitle(activity);
  if (operationTitle) return operationTitle;
  return activity.label || activity.eventType;
}

function isLowSignalSubagentActivity(activity: ActivityItem): boolean {
  if (activity.kind !== "subagent" && activity.category !== "subagent") {
    return false;
  }
  if (activity.eventType !== "subagent_event") {
    return false;
  }
  const childEventType = stringValue(activity.data.child_event_type);
  return [
    "node_started",
    "node_finished",
    "usage_updated",
    "session_persisted",
    "runtime_metrics",
    "context_resolution_started",
    "context_budget_applied",
    "user_message",
  ].includes(childEventType);
}

function compactSummary(activity: ActivityItem): string {
  const summary = oneLine(activity.summary);
  if (isRedundantStatusSummary(summary)) {
    return "";
  }
  if (summary && normalizeComparable(summary) !== normalizeComparable(compactTitle(activity))) {
    return summary;
  }
  const resultCount = numberValue(activity.data.result_count);
  if (typeof resultCount === "number") {
    return `Found ${resultCount} ${resultCount === 1 ? "result" : "results"}.`;
  }
  const exitCode = numberValue(activity.data.exit_code);
  if (typeof exitCode === "number") {
    return `Exit code ${exitCode}.`;
  }
  return "";
}

function isRedundantStatusSummary(summary: string): boolean {
  return /\bfinished with status (ok|success|error|blocked|warning|info)\.?$/i.test(summary);
}

function operationActivityTitle(activity: ActivityItem): string | null {
  const command = stringValue(activity.data.command);
  if (command) {
    return `${isRunning(activity) ? "Running" : "Ran"} ${command}`;
  }

  const legacyOperationTitle = legacyOperationActivityTitle(activity, isRunning(activity));
  if (legacyOperationTitle) return legacyOperationTitle;

  const workspaceName = stringValue(activity.data.project_name, activity.data.workspace_name, activity.data.name);
  if (activity.kind === "workspace" && workspaceName) {
    return `Working in ${workspaceName}`;
  }
  const branch = stringValue(activity.data.branch, activity.data.current_branch);
  if (activity.kind === "git" && branch) {
    return `On branch ${branch}`;
  }
  return null;
}

function permissionActivityTitle(activity: ActivityItem): string | null {
  if (activity.kind !== "permission" && activity.category !== "permission") {
    return null;
  }
  const summary = oneLine(activity.summary);
  if (summary) return summary;
  const reason = stringValue(activity.data.reason);
  if (activity.status === "blocked") {
    return reason ? `Permission denied: ${reason}` : "Permission denied";
  }
  const target = stringValue(activity.data.command, activity.data.path, activity.data.tool_name);
  if (activity.status === "pending" || activity.status === "running" || activity.status === "warning") {
    return target ? `Waiting for approval: ${target}` : "Waiting for approval";
  }
  if (activity.status === "success" || activity.status === "ok") {
    return target ? `Approved: ${target}` : "Approved";
  }
  return activity.label || "Permission event";
}

function subagentActivityTitle(activity: ActivityItem): string | null {
  if (!isSubagentActivity(activity)) {
    return null;
  }
  const name = subagentName(activity);
  return name ? `Subagent ${name}` : "Subagent activity";
}

function subagentName(activity: ActivityItem): string {
  const latest = latestMeaningfulSubagentActivity(activity);
  return stringValue(latest.data.name, activity.data.name, latest.data.child_run_id, activity.data.child_run_id);
}

function isSubagentActivity(activity: ActivityItem): boolean {
  return activity.kind === "subagent" || activity.category === "subagent";
}

export function latestMeaningfulSubagentActivity(activity: ActivityItem): ActivityItem {
  const related = activity.relatedActivities?.length ? activity.relatedActivities : [activity];
  for (let index = related.length - 1; index >= 0; index -= 1) {
    const item = related[index];
    if (!isLowSignalSubagentActivity(item)) {
      return item;
    }
  }
  return activity;
}

function skillActivityTitle(activity: ActivityItem): string | null {
  if (activity.kind !== "skill" && activity.category !== "skill") {
    return null;
  }
  const name = skillName(activity);
  const stage = activity.eventType.split(".").at(-1);
  if (stage === "loaded") return `Loaded skill: ${name}`;
  if (stage === "activated") return `Using skill: ${name}`;
  if (stage === "loading") return `Loading skill: ${name}`;
  if (stage === "failed") return `Skill failed: ${name}`;
  if (stage === "discovered") return `Discovered skill: ${name}`;
  return activity.label || `Skill: ${name}`;
}

function skillName(activity: ActivityItem): string {
  const explicit = stringValue(activity.data.display_name, activity.data.name, activity.data.skill_name);
  if (explicit) return explicit;
  const parts = activity.eventType.split(".");
  if (parts.length >= 3 && parts[0] === "skill") {
    return parts[1].replaceAll("_", "-");
  }
  return "unknown";
}

function terminalBlock(activity: ActivityItem): ActivityTerminalBlock | null {
  const command = stringValue(activity.data.command);
  if (!command) {
    return null;
  }
  const stdout = stringValue(activity.data.stdout_summary, activity.data.stdout);
  const stderr = stringValue(activity.data.stderr_summary, activity.data.stderr);
  const output = truncateTerminalOutput([stdout, stderr ? `stderr:\n${stderr}` : ""].filter(Boolean).join("\n"));
  return {
    command,
    output,
    exitCode: numberValue(activity.data.exit_code),
    truncated: Boolean(activity.data.truncated) || output.length >= TERMINAL_OUTPUT_LIMIT,
  };
}

function truncateTerminalOutput(value: string): string {
  if (value.length <= TERMINAL_OUTPUT_LIMIT) {
    return value;
  }
  return value.slice(0, TERMINAL_OUTPUT_LIMIT).trimEnd();
}

function debugPayloadForActivity(activity: ActivityItem): Record<string, unknown> {
  return {
    id: activity.id,
    type: activity.eventType,
    category: activity.category || activity.kind,
    status: activity.status,
    title: activity.label,
    summary: activity.summary,
    data: activity.data,
  };
}

function oneLine(value: string): string {
  return value.replace(/\s+/g, " ").trim();
}

function normalizeComparable(value: string): string {
  return value.toLowerCase().replace(/[.`]/g, "").trim();
}

function isRunning(activity: ActivityItem): boolean {
  return activity.status === "running" || activity.status === "pending";
}

function stringValue(...values: unknown[]): string {
  for (const value of values) {
    if (typeof value === "string" && value.trim()) {
      return value.trim();
    }
  }
  return "";
}

function numberValue(value: unknown): number | undefined {
  return typeof value === "number" && Number.isFinite(value) ? value : undefined;
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return Boolean(value) && typeof value === "object" && !Array.isArray(value);
}
