import { requestJson } from "./client.ts";
import type { ChatCancelRequest, ChatCancelResponse, ChatRequest, ChatResponse } from "./schemas.ts";

export function sendChat(request: ChatRequest): Promise<ChatResponse> {
  return requestJson<ChatResponse>("/chat", {
    method: "POST",
    body: JSON.stringify(request),
  });
}

export function cancelChat(request: ChatCancelRequest): Promise<ChatCancelResponse> {
  return requestJson<ChatCancelResponse>("/chat/cancel", {
    method: "POST",
    body: JSON.stringify(request),
  });
}
