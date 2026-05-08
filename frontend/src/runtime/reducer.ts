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

export type ActivityKind =
  | "event"
  | "tool"
  | "permission"
  | "skill"
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
  status: "running" | "ok" | "error" | "warning" | "info";
  timestamp: string;
  eventType: string;
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
  activities: ActivityItem[];
  context: RuntimeContextState;
  pendingPermission: PermissionRequest | null;
  finalResponse: string | null;
  error: string | null;
  isStreaming: boolean;
};

export function createInitialRuntimeState(): RuntimeState {
  return {
    sessionId: null,
    threadId: null,
    messages: [],
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
  return {
    ...state,
    messages: [
      ...state.messages,
      {
        id: `user-${Date.now()}`,
        role: "user",
        content,
        timestamp: new Date().toISOString(),
      },
    ],
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
      finalResponse && finalResponse !== state.finalResponse
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
      ...next,
      finalResponse: content || next.finalResponse,
      activities: [...next.activities, runtimeEventToActivity(event)],
      isStreaming: false,
    };
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
  } else if (event.type === "error") {
    next = {
      ...next,
      error: eventSummary(event) || "Runtime error",
      isStreaming: false,
    };
  }

  return {
    ...next,
    activities: [...next.activities, runtimeEventToActivity(event)],
  };
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
  if (response.final_response && response.final_response !== next.finalResponse) {
    next = appendAssistantMessage(next, response.final_response, new Date().toISOString(), `response-${Date.now()}`);
    next = { ...next, finalResponse: response.final_response };
  }
  return { ...next, isStreaming: false };
}

export function applySessionDetail(state: RuntimeState, detail: SessionDetailDTO): RuntimeState {
  return {
    ...state,
    sessionId: detail.session_id,
    threadId: stringOrNull(detail.metadata.thread_id) || state.threadId,
    messages: detail.messages.map(messageFromDto),
    activities: detail.events.map(runtimeEventToActivity),
    context: contextFromDto(detail.context),
    finalResponse: lastAssistantMessage(detail.messages),
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
  return {
    id: event.id,
    kind: activityKind(event.type),
    label: eventTitle(event),
    summary: eventSummary(event),
    status: activityStatus(event),
    timestamp: event.timestamp,
    eventType: event.type,
    data: event.data || {},
  };
}

function appendAssistantMessage(state: RuntimeState, content: string, timestamp: string, id: string): RuntimeState {
  const last = state.messages.at(-1);
  if (last?.role === "assistant" && last.content === content) {
    return state;
  }
  return {
    ...state,
    messages: [
      ...state.messages,
      {
        id,
        role: "assistant",
        content,
        timestamp,
      },
    ],
  };
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

function activityStatus(event: RuntimeEvent): ActivityItem["status"] {
  if (event.severity === "error" || event.type.endsWith("_error")) return "error";
  if (event.severity === "warning" || event.type === "permission_required") return "warning";
  if (event.type.endsWith("_started")) return "running";
  if (event.type.endsWith("_finished") || event.type === "final_response" || event.type === "permission_resolved") return "ok";
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

function lastAssistantMessage(messages: MessageDTO[]): string | null {
  for (const message of [...messages].reverse()) {
    if ((message.role === "ai" || message.role === "assistant") && message.content) {
      return message.content;
    }
  }
  return null;
}

function stringOrNull(value: unknown): string | null {
  return typeof value === "string" && value ? value : null;
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return Boolean(value) && typeof value === "object" && !Array.isArray(value);
}
