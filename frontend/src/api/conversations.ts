import { apiUrl, ApiError, requestJson, userScopedHeaders } from "./client.ts";
import type { ConversationDetailDTO, ConversationListItemDTO, ConversationRecordDTO, RuntimeEvent, SessionDetailDTO, SessionListItemDTO } from "./schemas.ts";

export function fetchConversations(query?: string): Promise<SessionListItemDTO[]> {
  const params = query?.trim() ? `?q=${encodeURIComponent(query.trim())}` : "";
  return requestJson<ConversationListItemDTO[]>(`/conversations${params}`).then((items) => items.map(conversationListItemToSession));
}

export function fetchConversationDetail(conversationId: string): Promise<SessionDetailDTO> {
  return requestJson<ConversationDetailDTO>(`/conversations/${encodeURIComponent(conversationId)}`).then(conversationDetailToSession);
}

export function renameConversation(conversationId: string, title: string): Promise<ConversationRecordDTO> {
  return requestJson<ConversationRecordDTO>(`/conversations/${encodeURIComponent(conversationId)}`, {
    method: "PATCH",
    body: JSON.stringify({ title }),
  });
}

export function archiveConversation(conversationId: string): Promise<ConversationRecordDTO> {
  return requestJson<ConversationRecordDTO>(`/conversations/${encodeURIComponent(conversationId)}/archive`, {
    method: "POST",
  });
}

export async function deleteConversation(conversationId: string): Promise<void> {
  const response = await fetch(apiUrl(`/conversations/${encodeURIComponent(conversationId)}`), {
    method: "DELETE",
    headers: userScopedHeaders(),
  });
  if (!response.ok) {
    const body = await response.text();
    throw new ApiError(response.status, response.statusText, body);
  }
}

export function conversationListItemToSession(item: ConversationListItemDTO): SessionListItemDTO {
  return {
    session_id: item.session_id,
    title: item.title,
    created_at: item.created_at,
    updated_at: item.updated_at,
    provider: null,
    model: null,
    message_count: item.message_count,
    event_count: item.event_count,
    tool_call_count: item.tool_call_count,
    child_run_count: 0,
    usage: {},
  };
}

export function conversationDetailToSession(detail: ConversationDetailDTO): SessionDetailDTO {
  return {
    session_id: detail.conversation.session_id,
    title: detail.conversation.title,
    created_at: detail.conversation.created_at,
    updated_at: detail.conversation.updated_at,
    provider: null,
    model: null,
    messages: detail.messages.map((message) => ({
      id: message.message_id,
      role: message.role,
      content: message.content,
      type: null,
      tool_calls: [],
      tool_call_id: null,
    })),
    events: detail.events.map(conversationEventToRuntimeEvent),
    tool_calls: detail.tool_calls.map((toolCall) => ({
      id: String(toolCall.tool_call_id || ""),
      name: String(toolCall.name || "tool"),
      status: String(toolCall.status || "completed"),
      metadata: asRecord(toolCall.metadata),
    })),
    todos: [],
    memory: {},
    usage: {},
    context: { references: [], fragments: [], attachments: [], budget: {}, model_context: {}, errors: [] },
    child_runs: [],
    metadata: { thread_id: detail.conversation.thread_id, conversation_id: detail.conversation.conversation_id },
  };
}

function conversationEventToRuntimeEvent(event: ConversationDetailDTO["events"][number]): RuntimeEvent {
  return {
    id: event.event_id,
    type: event.type,
    timestamp: event.created_at,
    session_id: event.conversation_id,
    node: typeof event.metadata.node === "string" ? event.metadata.node : null,
    severity: event.metadata.severity === "warning" || event.metadata.severity === "error" ? event.metadata.severity : "info",
    data: event.payload,
  };
}

function asRecord(value: unknown): Record<string, unknown> {
  return value && typeof value === "object" && !Array.isArray(value) ? (value as Record<string, unknown>) : {};
}
