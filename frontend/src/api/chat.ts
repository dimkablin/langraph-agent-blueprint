import { requestJson } from "./client.ts";
import type { ChatRequest, ChatResponse } from "./schemas.ts";

export function sendChat(request: ChatRequest): Promise<ChatResponse> {
  return requestJson<ChatResponse>("/chat", {
    method: "POST",
    body: JSON.stringify(request),
  });
}
