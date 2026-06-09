import type {
  ContextStateDTO,
  MessageDTO,
  PermissionRequest,
  RuntimeEvent,
  RuntimeStreamEvent,
  SessionDetailDTO,
  StreamFrame,
} from "../api/schemas.ts";
import { groupActivitiesForTimeline, mergeActivityForTimeline } from "./activityTimeline.ts";
import { eventSummary, eventTitle, firstString } from "./events.ts";
import { legacyActivityKind, legacyActivityKindFromStructuredCategory, legacyActivityStatus } from "./legacyStreamFallbacks.ts";
import { activityFromStreamEvent, permissionRequestFromStreamEvent, runtimeStreamEvent } from "./streamEvents.ts";

export type ChatMessage = {
  id: string;
  role: "user" | "assistant" | "system";
  content: string;
  timestamp: string;
};

export type ChatTimelineItem =
  | {
      kind: "message";
      message: ChatMessage;
    }
  | {
      kind: "activity";
      id: string;
      timestamp: string;
      activities: ActivityItem[];
      messageId?: string;
    }
  | {
      kind: "separator";
      id: string;
      label: string;
      timestamp: string;
      eventType: "compact_started" | "compact_finished";
      status: "running" | "done";
    };

export type ActivityKind =
  | "event"
  | "runtime"
  | "workspace"
  | "git"
  | "tool"
  | "permission"
  | "skill"
  | "verification"
  | "subagent"
  | "mcp"
  | "hook"
  | "context"
  | "error";

export type ActivityItem = {
  id: string;
  kind: ActivityKind;
  label: string;
  summary: string;
  status: "pending" | "running" | "success" | "ok" | "error" | "blocked" | "warning" | "info";
  timestamp: string;
  eventType: string;
  category?: string;
  data: Record<string, unknown>;
  relatedActivities?: ActivityItem[];
};

export type RuntimeContextState = {
  references: Record<string, unknown>[];
  fragments: Record<string, unknown>[];
  attachments: Record<string, unknown>[];
  budget: Record<string, unknown> | null;
  modelContext: Record<string, unknown> | null;
  errors: Record<string, unknown>[];
};

export type RuntimeState = {
  sessionId: string | null;
  threadId: string | null;
  messages: ChatMessage[];
  timeline: ChatTimelineItem[];
  activities: ActivityItem[];
  context: RuntimeContextState;
  usage: Record<string, unknown>;
  pendingPermission: PermissionRequest | null;
  finalResponse: string | null;
  error: string | null;
  isStreaming: boolean;
};

const STREAMING_DRAFT_ID_PREFIX = "draft:";
const INTERNAL_COMPACTION_PREFIX = "Compacted prior context:";
const TOOL_MESSAGE_ROLE = "tool";
const TOOL_MESSAGE_TYPE = "ToolMessage";
const ASSISTANT_DTO_ROLES = new Set<string>(["ai", "assistant"]);

export function createInitialRuntimeState(): RuntimeState {
  return {
    sessionId: null,
    threadId: null,
    messages: [],
    timeline: [],
    activities: [],
    context: {
      references: [],
      fragments: [],
      attachments: [],
      budget: null,
      modelContext: null,
      errors: [],
    },
    usage: {},
    pendingPermission: null,
    finalResponse: null,
    error: null,
    isStreaming: false,
  };
}

export function appendUserMessage(state: RuntimeState, content: string): RuntimeState {
  const message: ChatMessage = {
    id: `user-${Date.now()}`,
    role: "user",
    content,
    timestamp: new Date().toISOString(),
  };
  return {
    ...state,
    messages: [...state.messages, message],
    timeline: [...state.timeline, messageTimelineItem(message)],
    error: null,
    isStreaming: true,
  };
}

export function applyStreamFrame(state: RuntimeState, frame: StreamFrame): RuntimeState {
  if (frame.type === "event") {
    return applyRuntimeEvent(state, frame.event);
  }
  if (frame.type === "done") {
    const finalResponse = frame.final_response ?? state.finalResponse;
    const next =
      finalResponse && finalResponse !== state.finalResponse && !isCompactionStatusResponse(finalResponse, state)
        ? appendAssistantMessage(state, finalResponse, new Date().toISOString(), `done-${Date.now()}`)
        : state;
    return {
      ...next,
      sessionId: frame.session_id || next.sessionId,
      threadId: frame.thread_id || next.threadId,
      finalResponse,
      isStreaming: false,
    };
  }
  return {
    ...appendActivityItem({ ...state, error: frame.error, isStreaming: false }, errorActivity(frame.error)),
  };
}

export function markStreamingStopped(state: RuntimeState): RuntimeState {
  return {
    ...state,
    isStreaming: false,
  };
}

export function clearPendingPermission(state: RuntimeState): RuntimeState {
  if (!state.pendingPermission) return state;
  return {
    ...state,
    pendingPermission: null,
  };
}

export function applyRuntimeEvent(state: RuntimeState, event: RuntimeEvent): RuntimeState {
  let next: RuntimeState = {
    ...state,
    sessionId: event.session_id && event.session_id !== "unknown" ? event.session_id : state.sessionId,
  };

  next = applyUsageFromRuntimeEvent(next, event);

  const streamEvent = runtimeStreamEvent(event);
  if (streamEvent) {
    return applyTypedRuntimeEvent(next, event, streamEvent);
  }

  if (event.type === "final_response") {
    const content = firstString(event.data.content);
    next = content ? appendAssistantMessage(next, content, event.timestamp, event.id) : next;
    return {
      ...appendActivity(next, event),
      finalResponse: content || next.finalResponse,
      isStreaming: false,
    };
  }

  if (event.type === "user_message") {
    const content = firstString(event.data.content);
    return content ? appendUserMessageFromEvent(next, content, event.timestamp, event.id) : next;
  }

  if (event.type === "model_token") {
    const token = tokenString(event.data.token);
    return token !== null ? appendAssistantToken(next, token, event.timestamp, event.id) : next;
  }

  if (event.type === "model_message") {
    const content = firstString(event.data.content);
    next = content ? appendAssistantMessage(next, content, event.timestamp, event.id) : next;
  }

  if (event.type === "permission_required") {
    next = {
      ...next,
      pendingPermission: permissionFromEvent(event),
    };
  } else if (event.type === "permission_resolved") {
    next = {
      ...next,
      pendingPermission: null,
    };
  } else if (event.type === "context_fragment_added") {
    next = {
      ...next,
      context: {
        ...next.context,
        fragments: [...next.context.fragments, event.data],
      },
    };
  } else if (event.type === "context_budget_applied") {
    next = {
      ...next,
      context: {
        ...next.context,
        budget: event.data,
      },
    };
  } else if (event.type === "model_context_prepared") {
    next = {
      ...next,
      context: {
        ...next.context,
        modelContext: isRecord(event.data.model_context) ? event.data.model_context : null,
      },
    };
  } else if (event.type === "context_resolution_error") {
    next = {
      ...next,
      context: {
        ...next.context,
        errors: [...next.context.errors, event.data],
      },
    };
  } else if (event.type === "compact_started") {
    next = appendTimelineSeparator(next, event, "Контекст автоматически сжимается", "running");
  } else if (event.type === "compact_finished") {
    next = completeTimelineSeparator(next, event, "Контекст автоматически сжат");
  } else if (event.type === "error") {
    next = {
      ...next,
      error: eventSummary(event) || "Runtime error",
      isStreaming: false,
    };
  }

  return appendActivity(next, event);
}

function applyTypedRuntimeEvent(state: RuntimeState, event: RuntimeEvent, streamEvent: RuntimeStreamEvent): RuntimeState {
  if (streamEvent.kind === "assistant_delta") {
    return appendAssistantDelta(state, streamEvent.message_id, streamEvent.delta, event.timestamp);
  }
  if (streamEvent.kind === "assistant_final") {
    const next = appendAssistantFinal(state, streamEvent.message_id, streamEvent.content, event.timestamp);
    return { ...next, finalResponse: streamEvent.content, isStreaming: false };
  }

  let next = state;
  if (streamEvent.kind === "permission_state") {
    next = { ...next, pendingPermission: permissionRequestFromStreamEvent(streamEvent) };
  } else if (streamEvent.kind === "error") {
    next = { ...next, error: streamEvent.message, isStreaming: false };
  }

  const activity = activityFromStreamEvent(event, streamEvent);
  return activity ? appendActivityItem(next, activity, shouldShowActivityItemInTimeline(activity)) : next;
}

export function applyChatResponse(state: RuntimeState, response: {
  session_id: string;
  thread_id: string;
  final_response?: string | null;
  events?: RuntimeEvent[];
  usage?: Record<string, unknown>;
  permission_required?: PermissionRequest | null;
}): RuntimeState {
  const hasPermissionField = Object.prototype.hasOwnProperty.call(response, "permission_required");
  let next: RuntimeState = {
    ...state,
    sessionId: response.session_id,
    threadId: response.thread_id,
    pendingPermission: hasPermissionField ? response.permission_required ?? null : state.pendingPermission,
  };
  if (isRecord(response.usage)) {
    next = { ...next, usage: mergeUsage(next.usage, response.usage) };
  }
  for (const event of response.events || []) {
    next = applyRuntimeEvent(next, event);
  }
  if (response.final_response && response.final_response !== next.finalResponse && !isCompactionStatusResponse(response.final_response, next)) {
    next = appendAssistantMessage(next, response.final_response, new Date().toISOString(), `response-${Date.now()}`);
    next = { ...next, finalResponse: response.final_response };
  }
  return { ...next, isStreaming: false };
}

export function applySessionDetail(state: RuntimeState, detail: SessionDetailDTO): RuntimeState {
  const visibleMessages = detail.messages.filter(isVisibleMessageDto);
  const messages = visibleMessages.map(messageFromDto);
  const eventRestored = restoreSessionTimelineFromEvents(state, detail);
  if (eventRestored) {
    return eventRestored;
  }
  const activities = uniqueActivities(detail.events.map(runtimeEventToActivity));
  return {
    ...state,
    sessionId: detail.session_id,
    threadId: stringOrNull(detail.metadata.thread_id) || state.threadId,
    messages,
    timeline: timelineFromMessagesAndActivities(messages, activities),
    activities,
    context: contextFromDto(detail.context),
    usage: isRecord(detail.usage) ? { ...detail.usage } : {},
    finalResponse: lastAssistantMessage(visibleMessages),
    pendingPermission: null,
    error: null,
    isStreaming: false,
  };
}

function restoreSessionTimelineFromEvents(state: RuntimeState, detail: SessionDetailDTO): RuntimeState | null {
  const hasReplayableMessageEvents = detail.events.some((event) => event.type === "model_message" || event.type === "final_response");
  if (!hasReplayableMessageEvents) {
    return null;
  }
  const hasUserMessageEvents = detail.events.some((event) => event.type === "user_message");
  const fallbackUserMessages = hasUserMessageEvents
    ? []
    : detail.messages.filter(isVisibleMessageDto).filter((message) => message.role === "human" || message.role === "user").map(messageFromDto);
  let next: RuntimeState = {
    ...state,
    sessionId: detail.session_id,
    threadId: stringOrNull(detail.metadata.thread_id) || state.threadId,
    messages: fallbackUserMessages,
    timeline: fallbackUserMessages.map(messageTimelineItem),
    activities: [],
    context: contextFromDto(detail.context),
    usage: isRecord(detail.usage) ? { ...detail.usage } : {},
    pendingPermission: null,
    finalResponse: null,
    error: null,
    isStreaming: false,
  };
  for (const event of detail.events) {
    if (event.type === "model_token") {
      continue;
    }
    next = applyRuntimeEvent(next, event);
  }
  return {
    ...next,
    sessionId: detail.session_id,
    threadId: stringOrNull(detail.metadata.thread_id) || next.threadId,
    isStreaming: false,
  };
}

export function applyContextState(state: RuntimeState, context: ContextStateDTO): RuntimeState {
  return {
    ...state,
    context: contextFromDto(context),
  };
}

export function setThreadId(state: RuntimeState, threadId: string): RuntimeState {
  return { ...state, threadId };
}

export function runtimeEventToActivity(event: RuntimeEvent): ActivityItem {
  const structured = activityFromRuntimeEvent(event);
  if (structured) {
    return structured;
  }
  return {
    id: event.id,
    kind: activityKind(event.type),
    label: eventTitle(event),
    summary: eventSummary(event),
    status: activityStatus(event),
    timestamp: event.timestamp,
    eventType: event.type,
    category: activityKind(event.type),
    data: event.data || {},
  };
}

function appendActivity(state: RuntimeState, event: RuntimeEvent): RuntimeState {
  const activity = runtimeEventToActivity(event);
  return appendActivityItem(state, activity, isChatVisibleActivity(event, activity));
}

function applyUsageFromRuntimeEvent(state: RuntimeState, event: RuntimeEvent): RuntimeState {
  const usage = isRecord(event.data?.usage) ? event.data.usage : event.type === "usage_updated" ? event.data : null;
  return usage ? { ...state, usage: mergeUsage(state.usage, usage) } : state;
}

function mergeUsage(existing: Record<string, unknown>, update: Record<string, unknown>): Record<string, unknown> {
  return { ...(existing || {}), ...update };
}

function appendActivityItem(state: RuntimeState, activity: ActivityItem, showInTimeline = true): RuntimeState {
  if (state.activities.some((item) => item.id === activity.id)) {
    return state;
  }
  const activities = [...state.activities, activity];
  return {
    ...state,
    activities,
    timeline: showInTimeline ? upsertActivityTimelineItem(state.timeline, activity) : state.timeline,
  };
}

function uniqueActivities(items: ActivityItem[]): ActivityItem[] {
  const seen = new Set<string>();
  const activities: ActivityItem[] = [];
  for (const item of items) {
    if (seen.has(item.id)) continue;
    seen.add(item.id);
    activities.push(item);
  }
  return activities;
}

function appendAssistantMessage(state: RuntimeState, content: string, timestamp: string, id: string): RuntimeState {
  const last = state.messages.at(-1);
  if (state.isStreaming && last?.role === "assistant" && isStreamingDraft(last) && content.startsWith(last.content)) {
    return replaceLastMessage(state, { ...last, id, content, timestamp });
  }
  if (last?.role === "assistant" && isSameRenderedAssistantContent(last.content, content)) {
    return promoteDuplicateAssistantMessageAfterTrailingActivity(state, { ...last, id, content: last.content, timestamp });
  }
  const message: ChatMessage = {
    id,
    role: "assistant",
    content,
    timestamp,
  };
  return {
    ...state,
    messages: [...state.messages, message],
    timeline: [...state.timeline, messageTimelineItem(message)],
  };
}

function promoteDuplicateAssistantMessageAfterTrailingActivity(state: RuntimeState, message: ChatMessage): RuntimeState {
  const previousMessageId = state.messages.at(-1)?.id || message.id;
  const messageIndex = state.messages.length - 1;
  const messages = messageIndex >= 0
    ? state.messages.map((item, index) => index === messageIndex ? message : item)
    : state.messages;
  const timelineIndex = findLastTimelineMessageItemIndex(state.timeline, previousMessageId);
  if (timelineIndex === -1) {
    return { ...state, messages };
  }
  const hasTrailingActivity = state.timeline.slice(timelineIndex + 1).some((item) => item.kind === "activity");
  if (!hasTrailingActivity) {
    return { ...state, messages };
  }
  const withoutMessage = state.timeline.filter((item, index) => index !== timelineIndex);
  const rebound = rebindActivityGroups(withoutMessage, previousMessageId, message.id);
  return {
    ...state,
    messages,
    timeline: [...rebound, messageTimelineItem(message)],
  };
}

function findLastTimelineMessageItemIndex(timeline: ChatTimelineItem[], messageId: string): number {
  for (let index = timeline.length - 1; index >= 0; index -= 1) {
    const item = timeline[index];
    if (item.kind === "message" && item.message.id === messageId) {
      return index;
    }
  }
  return -1;
}

function isSameRenderedAssistantContent(left: string, right: string): boolean {
  return normalizeAssistantContentForDedupe(left) === normalizeAssistantContentForDedupe(right);
}

function normalizeAssistantContentForDedupe(content: string): string {
  return content.replace(/\r\n/g, "\n").replace(/\u200B/g, "").trim();
}

function appendUserMessageFromEvent(state: RuntimeState, content: string, timestamp: string, id: string): RuntimeState {
  const last = state.messages.at(-1);
  if (last?.role === "user" && last.content === content) {
    return state;
  }
  if (state.messages.some((message) => message.id === id)) {
    return state;
  }
  const message: ChatMessage = {
    id,
    role: "user",
    content,
    timestamp,
  };
  return {
    ...state,
    messages: [...state.messages, message],
    timeline: [...state.timeline, messageTimelineItem(message)],
  };
}

function appendAssistantToken(state: RuntimeState, token: string, timestamp: string, id: string): RuntimeState {
  const last = state.messages.at(-1);
  if (last?.role === "assistant" && isStreamingDraft(last)) {
    return replaceLastMessage(state, { ...last, content: `${last.content}${token}`, timestamp });
  }
  const message: ChatMessage = {
    id: `${STREAMING_DRAFT_ID_PREFIX}${id}`,
    role: "assistant",
    content: token,
    timestamp,
  };
  return {
    ...state,
    messages: [...state.messages, message],
    timeline: [...state.timeline, messageTimelineItem(message)],
  };
}

function appendAssistantDelta(state: RuntimeState, messageId: string, delta: string, timestamp: string): RuntimeState {
  if (!delta) return state;
  const index = state.messages.findIndex((message) => message.id === messageId);
  if (index >= 0) {
    const message = state.messages[index];
    if (message.role !== "assistant") return state;
    return replaceMessageAtIndex(state, index, { ...message, content: `${message.content}${delta}`, timestamp });
  }
  const message: ChatMessage = {
    id: messageId,
    role: "assistant",
    content: delta,
    timestamp,
  };
  return {
    ...state,
    messages: [...state.messages, message],
    timeline: [...state.timeline, messageTimelineItem(message)],
  };
}

function appendAssistantFinal(state: RuntimeState, messageId: string, content: string, timestamp: string): RuntimeState {
  const index = state.messages.findIndex((message) => message.id === messageId);
  if (index >= 0) {
    const message = state.messages[index];
    if (message.role !== "assistant") return state;
    return replaceMessageAtIndex(state, index, { ...message, content, timestamp });
  }
  return appendAssistantMessage(state, content, timestamp, messageId);
}

function tokenString(value: unknown): string | null {
  return typeof value === "string" && value.length > 0 ? value : null;
}

function isStreamingDraft(message: ChatMessage): boolean {
  return message.id.startsWith(STREAMING_DRAFT_ID_PREFIX);
}

function replaceLastMessage(state: RuntimeState, message: ChatMessage): RuntimeState {
  const timeline = [...state.timeline];
  let previousMessageId: string | null = null;
  for (let index = timeline.length - 1; index >= 0; index -= 1) {
    if (timeline[index].kind === "message") {
      previousMessageId = timeline[index].message.id;
      timeline[index] = messageTimelineItem(message);
      break;
    }
  }
  const rebound = previousMessageId ? rebindActivityGroups(timeline, previousMessageId, message.id) : timeline;
  return {
    ...state,
    messages: [...state.messages.slice(0, -1), message],
    timeline: rebound,
  };
}

function replaceMessageAtIndex(state: RuntimeState, index: number, message: ChatMessage): RuntimeState {
  const previousMessage = state.messages[index];
  const messages = state.messages.map((item, itemIndex) => itemIndex === index ? message : item);
  const timeline = state.timeline.map((item) =>
    item.kind === "message" && item.message.id === previousMessage.id ? messageTimelineItem(message) : item
  );
  const rebound = previousMessage.id === message.id ? timeline : rebindActivityGroups(timeline, previousMessage.id, message.id);
  return { ...state, messages, timeline: rebound };
}

function messageTimelineItem(message: ChatMessage): ChatTimelineItem {
  return { kind: "message", message };
}

function appendTimelineSeparator(state: RuntimeState, event: RuntimeEvent, label: string, status: "running" | "done"): RuntimeState {
  if (state.timeline.some((item) => item.kind === "separator" && item.id === event.id)) {
    return state;
  }
  return {
    ...state,
    timeline: [
      ...state.timeline,
      {
        kind: "separator",
        id: event.id,
        label,
        timestamp: event.timestamp,
        eventType: event.type === "compact_started" ? "compact_started" : "compact_finished",
        status,
      },
    ],
  };
}

function completeTimelineSeparator(state: RuntimeState, event: RuntimeEvent, label: string): RuntimeState {
  if (state.timeline.some((item) => item.kind === "separator" && item.id === event.id && item.eventType === "compact_finished")) {
    return state;
  }
  let runningIndex = -1;
  for (let index = state.timeline.length - 1; index >= 0; index -= 1) {
    const item = state.timeline[index];
    if (item.kind === "separator" && item.eventType === "compact_started" && item.status === "running") {
      runningIndex = index;
      break;
    }
  }
  if (runningIndex === -1) {
    return appendTimelineSeparator(state, event, label, "done");
  }
  const timeline = [...state.timeline];
  timeline[runningIndex] = {
    kind: "separator",
    id: event.id,
    label,
    timestamp: event.timestamp,
    eventType: "compact_finished",
    status: "done",
  };
  return { ...state, timeline };
}

function isCompactionStatusResponse(finalResponse: string, state: RuntimeState): boolean {
  return (
    finalResponse.trim() === "Context compacted." &&
    state.timeline.some((item) => item.kind === "separator" && item.eventType === "compact_finished")
  );
}

function upsertActivityTimelineItem(timeline: ChatTimelineItem[], activity: ActivityItem): ChatTimelineItem[] {
  const groupId = currentActivityGroupId(timeline);
  const groupIndex = timeline.findIndex((item) => item.kind === "activity" && item.id === groupId);
  const existing =
    groupIndex >= 0 && timeline[groupIndex].kind === "activity"
      ? timeline[groupIndex]
      : { kind: "activity" as const, id: groupId, timestamp: activity.timestamp, activities: [] };
  if (existing.activities.some((item) => item.id === activity.id)) {
    return timeline;
  }
  const withoutExisting = groupIndex >= 0 ? [...timeline.slice(0, groupIndex), ...timeline.slice(groupIndex + 1)] : [...timeline];
  const insertion = activityGroupInsertion(withoutExisting);
  const updated = {
    ...existing,
    timestamp: activity.timestamp,
    activities: mergeActivityForTimeline(existing.activities, activity),
    messageId: insertion.messageId || existing.messageId,
  };
  return [...withoutExisting.slice(0, insertion.index), updated, ...withoutExisting.slice(insertion.index)];
}

function rebindActivityGroups(timeline: ChatTimelineItem[], oldMessageId: string, newMessageId: string): ChatTimelineItem[] {
  return timeline.map((item) => (item.kind === "activity" && item.messageId === oldMessageId ? { ...item, messageId: newMessageId } : item));
}

function timelineFromMessagesAndActivities(messages: ChatMessage[], activities: ActivityItem[]): ChatTimelineItem[] {
  const timeline = messages.map(messageTimelineItem);
  const visibleActivities = groupActivitiesForTimeline(activities.filter((activity) => shouldShowActivityItemInTimeline(activity)));
  if (!visibleActivities.length) {
    return timeline;
  }
  const assistantIndex = findLastTimelineMessageIndex(timeline, "assistant");
  const messageId = assistantIndex >= 0 && timeline[assistantIndex].kind === "message" ? timeline[assistantIndex].message.id : undefined;
  const item: ChatTimelineItem = {
    kind: "activity",
    id: messageId ? `activity-group:${messageId}` : "activity-group:session",
    timestamp: visibleActivities.at(-1)?.timestamp || new Date().toISOString(),
    activities: visibleActivities,
    messageId,
  };
  const index = assistantIndex >= 0 ? assistantIndex : timeline.length;
  return [...timeline.slice(0, index), item, ...timeline.slice(index)];
}

function currentActivityGroupId(timeline: ChatTimelineItem[]): string {
  for (let index = timeline.length - 1; index >= 0; index -= 1) {
    const item = timeline[index];
    if (item.kind === "message" && item.message.role === "assistant") {
      return `activity-group:${item.message.id}:after`;
    }
    if (item.kind === "message" && item.message.role === "user") {
      return `activity-group:${item.message.id}`;
    }
  }
  return "activity-group:session";
}

function activityGroupInsertion(timeline: ChatTimelineItem[]): { index: number; messageId?: string } {
  const last = timeline.at(-1);
  if (last?.kind === "message" && last.message.role === "assistant") {
    return { index: timeline.length };
  }
  return { index: timeline.length };
}

function findLastTimelineMessageIndex(timeline: ChatTimelineItem[], role: ChatMessage["role"]): number {
  for (let index = timeline.length - 1; index >= 0; index -= 1) {
    const item = timeline[index];
    if (item.kind === "message" && item.message.role === role) {
      return index;
    }
  }
  return -1;
}

function isChatVisibleActivity(event: RuntimeEvent, activity: ActivityItem): boolean {
  if (event.type === "final_response") return false;
  if (isRecord(event.data?.activity)) return true;
  return shouldShowActivityItemInTimeline(activity);
}

function shouldShowActivityItemInTimeline(activity: ActivityItem): boolean {
  return ["tool", "permission", "skill", "verification", "runtime", "workspace", "git", "subagent", "error"].includes(activity.kind);
}

function permissionFromEvent(event: RuntimeEvent): PermissionRequest {
  return {
    tool_call_id: String(event.data.tool_call_id || ""),
    tool_name: String(event.data.tool_name || "unknown_tool"),
    action: stringOrNull(event.data.action),
    risk: stringOrNull(event.data.risk),
    args_summary: stringOrNull(event.data.args_summary),
    reason: stringOrNull(event.data.reason),
    args: isRecord(event.data.args) ? event.data.args : {},
    scope: event.data.scope === "subagent" ? "subagent" : "tool",
    parent_session_id: stringOrNull(event.data.parent_session_id),
    parent_thread_id: stringOrNull(event.data.parent_thread_id),
    child_session_id: stringOrNull(event.data.child_session_id),
    child_thread_id: stringOrNull(event.data.child_thread_id),
    child_run_id: stringOrNull(event.data.child_run_id),
    subagent_name: stringOrNull(event.data.subagent_name),
  };
}

function activityKind(type: string): ActivityKind {
  return legacyActivityKind(type);
}

function activityFromRuntimeEvent(event: RuntimeEvent): ActivityItem | null {
  const payload = isRecord(event.data?.activity) ? event.data.activity : null;
  if (!payload) return null;
  const type = firstString(payload.type);
  if (!type) return null;
  const category = firstString(payload.category) || "event";
  const title = firstString(payload.title) || type;
  return {
    id: firstString(payload.id) || event.id,
    kind: activityKindFromCategory(category, type),
    label: title,
    summary: firstString(payload.summary),
    status: activityStatusFromPayload(payload.status, event),
    timestamp: event.timestamp,
    eventType: type,
    category,
    data: isRecord(payload.data) ? payload.data : {},
  };
}

function activityKindFromCategory(category: string, type: string): ActivityKind {
  return legacyActivityKindFromStructuredCategory(category, type);
}

function activityStatusFromPayload(value: unknown, event: RuntimeEvent): ActivityItem["status"] {
  if (
    value === "pending" ||
    value === "running" ||
    value === "success" ||
    value === "error" ||
    value === "blocked" ||
    value === "warning" ||
    value === "info"
  ) {
    return value;
  }
  return activityStatus(event);
}

function activityStatus(event: RuntimeEvent): ActivityItem["status"] {
  return legacyActivityStatus(event);
}

function errorActivity(error: string): ActivityItem {
  return {
    id: `stream-error-${Date.now()}`,
    kind: "error",
    label: "stream_error",
    summary: error,
    status: "error",
    timestamp: new Date().toISOString(),
    eventType: "stream_error",
    category: "error",
    data: { error },
  };
}

function contextFromDto(context: ContextStateDTO): RuntimeContextState {
  return {
    references: context.references || [],
    fragments: context.fragments || [],
    attachments: context.attachments || [],
    budget: context.budget || null,
    modelContext: isRecord(context.model_context) ? context.model_context : null,
    errors: context.errors || [],
  };
}

function messageFromDto(message: MessageDTO): ChatMessage {
  const role = message.role === "ai" || message.role === "assistant" ? "assistant" : message.role === "human" || message.role === "user" ? "user" : "system";
  return {
    id: message.id,
    role,
    content: message.content,
    timestamp: new Date().toISOString(),
  };
}

function isVisibleMessageDto(message: MessageDTO): boolean {
  if (message.role === "system" && message.content.startsWith(INTERNAL_COMPACTION_PREFIX)) return false;
  if (message.role === TOOL_MESSAGE_ROLE || message.type === TOOL_MESSAGE_TYPE || message.tool_call_id) return false;
  if (isEmptyToolCallMessage(message)) return false;
  return true;
}

function lastAssistantMessage(messages: MessageDTO[]): string | null {
  for (const message of [...messages].reverse()) {
    if ((message.role === "ai" || message.role === "assistant") && message.content) {
      return message.content;
    }
  }
  return null;
}

function isEmptyToolCallMessage(message: MessageDTO): boolean {
  return ASSISTANT_DTO_ROLES.has(message.role) && !message.content.trim() && Boolean(message.tool_calls?.length);
}

function stringOrNull(value: unknown): string | null {
  return typeof value === "string" && value ? value : null;
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return Boolean(value) && typeof value === "object" && !Array.isArray(value);
}
