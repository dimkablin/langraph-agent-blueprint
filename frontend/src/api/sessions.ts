import { requestJson } from "./client.ts";
import type { ContextStateDTO, SessionDetailDTO, SessionListItemDTO } from "./schemas.ts";

export function fetchSessions(): Promise<SessionListItemDTO[]> {
  return requestJson<SessionListItemDTO[]>("/sessions");
}

export function fetchSessionDetail(sessionId: string): Promise<SessionDetailDTO> {
  return requestJson<SessionDetailDTO>(`/sessions/${encodeURIComponent(sessionId)}`);
}

export function fetchSessionContext(sessionId: string): Promise<ContextStateDTO> {
  return requestJson<ContextStateDTO>(`/sessions/${encodeURIComponent(sessionId)}/context`);
}

export function exportSession(sessionId: string): Promise<{ path: string; bytes: number; format: string }> {
  return requestJson(`/sessions/${encodeURIComponent(sessionId)}/export`, {
    method: "POST",
    body: JSON.stringify({ format: "markdown" }),
  });
}
