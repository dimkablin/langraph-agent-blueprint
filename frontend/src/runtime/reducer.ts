import type {
  ContextStateDTO,
  MessageDTO,
  PermissionRequest,
  RuntimeEvent,
  SessionDetailDTO,
  StreamFrame,
} from "../api/schemas.ts";
import { eventSummary, eventTitle, firstString } from "./events.ts";

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
};

export type RuntimeContextState = {
  references: Record<string, unknown>[];
  fragments: Record<string, unknown>[];
  attachments: Record<string, unknown>[];
  budget: Record<string, unknown> | null;
  errors: Record<string, unknown>[];
};

export type RuntimeState = {
  sessionId: string | null;
  threadId: string | null;
  messages: ChatMessage[];
  timeline: ChatTimelineItem[];
  activities: ActivityItem[];
  context: RuntimeContextState;
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
      errors: [],
    },
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
    ...state,
    error: frame.error,
    isStreaming: false,
    activities: [...state.activities, errorActivity(frame.error)],
  };
}

export function markStreamingStopped(state: RuntimeState): RuntimeState {
  return {
    ...state,
    isStreaming: false,
  };
}

export function applyRuntimeEvent(state: RuntimeState, event: RuntimeEvent): RuntimeState {
  let next: RuntimeState = {
    ...state,
    sessionId: event.session_id && event.session_id !== "unknown" ? event.session_id : state.sessionId,
  };

  if (event.type === "final_response") {
    const content = firstString(event.data.content);
    next = content ? appendAssistantMessage(next, content, event.timestamp, event.id) : next;
    return {
      ...appendActivity(next, event),
      finalResponse: content || next.finalResponse,
      isStreaming: false,
    };
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

export function applyChatResponse(state: RuntimeState, response: {
  session_id: string;
  thread_id: string;
  final_response?: string | null;
  events?: RuntimeEvent[];
  permission_required?: PermissionRequest | null;
}): RuntimeState {
  let next: RuntimeState = {
    ...state,
    sessionId: response.session_id,
    threadId: response.thread_id,
    pendingPermission: response.permission_required || state.pendingPermission,
  };
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
  return {
    ...state,
    sessionId: detail.session_id,
    threadId: stringOrNull(detail.metadata.thread_id) || state.threadId,
    messages,
    timeline: messages.map(messageTimelineItem),
    activities: uniqueActivities(detail.events.map(runtimeEventToActivity)),
    context: contextFromDto(detail.context),
    finalResponse: lastAssistantMessage(visibleMessages),
    pendingPermission: null,
    error: null,
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
  if (state.activities.some((item) => item.id === activity.id)) {
    return state;
  }
  return {
    ...state,
    activities: [...state.activities, activity],
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
  if (last?.role === "assistant" && last.content === content) {
    return state;
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

function tokenString(value: unknown): string | null {
  return typeof value === "string" && value.length > 0 ? value : null;
}

function isStreamingDraft(message: ChatMessage): boolean {
  return message.id.startsWith(STREAMING_DRAFT_ID_PREFIX);
}

function replaceLastMessage(state: RuntimeState, message: ChatMessage): RuntimeState {
  const timeline = [...state.timeline];
  for (let index = timeline.length - 1; index >= 0; index -= 1) {
    if (timeline[index].kind === "message") {
      timeline[index] = messageTimelineItem(message);
      break;
    }
  }
  return {
    ...state,
    messages: [...state.messages.slice(0, -1), message],
    timeline,
  };
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

function permissionFromEvent(event: RuntimeEvent): PermissionRequest {
  return {
    tool_call_id: String(event.data.tool_call_id || ""),
    tool_name: String(event.data.tool_name || "unknown_tool"),
    action: stringOrNull(event.data.action),
    risk: stringOrNull(event.data.risk),
    args_summary: stringOrNull(event.data.args_summary),
    reason: stringOrNull(event.data.reason),
    args: isRecord(event.data.args) ? event.data.args : {},
  };
}

function activityKind(type: string): ActivityKind {
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
  if (category === "runtime") return "runtime";
  if (category === "workspace") return "workspace";
  if (category === "git") return "git";
  if (category === "tool") return "tool";
  if (category === "permission") return "permission";
  if (category === "skill") return "skill";
  if (category === "verification") return "verification";
  if (category === "mcp") return "mcp";
  if (category === "hook") return "hook";
  if (category === "context") return "context";
  if (category === "error") return "error";
  return activityKind(type);
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
  if (event.severity === "error" || event.type.endsWith("_error")) return "error";
  if (event.severity === "warning" || event.type === "permission_required") return "warning";
  if (event.type.endsWith("_started")) return "running";
  if (event.type.endsWith("_finished") || event.type === "final_response" || event.type === "permission_resolved") return "success";
  return "info";
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
