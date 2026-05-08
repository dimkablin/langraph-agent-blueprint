import { requestJson } from "./client.ts";
import type { ApprovalRequest, ChatResponse } from "./schemas.ts";

export function sendApproval(request: ApprovalRequest): Promise<ChatResponse> {
  return requestJson<ChatResponse>("/approval", {
    method: "POST",
    body: JSON.stringify(request),
  });
}
