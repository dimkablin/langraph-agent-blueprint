import { requestJson } from "./client.ts";
import type { WorkspaceCheckoutRequest, WorkspaceCheckoutResult, WorkspaceInfo } from "./schemas.ts";

export function fetchWorkspaces(): Promise<WorkspaceInfo[]> {
  return requestJson<WorkspaceInfo[]>("/workspaces");
}

export function fetchActiveWorkspace(): Promise<WorkspaceInfo | null> {
  return requestJson<WorkspaceInfo | null>("/workspaces/active");
}

export function addWorkspace(rootPath: string): Promise<WorkspaceInfo> {
  return requestJson<WorkspaceInfo>("/workspaces", {
    method: "POST",
    body: JSON.stringify({ root_path: rootPath }),
  });
}

export function pickWorkspaceFolder(): Promise<WorkspaceInfo | null> {
  return requestJson<WorkspaceInfo | null>("/workspaces/pick", {
    method: "POST",
  });
}

export function selectWorkspace(projectId: string): Promise<WorkspaceInfo> {
  return requestJson<WorkspaceInfo>("/workspaces/select", {
    method: "POST",
    body: JSON.stringify({ project_id: projectId }),
  });
}

export function checkoutWorkspaceBranch(projectId: string, request: WorkspaceCheckoutRequest): Promise<WorkspaceCheckoutResult> {
  return requestJson<WorkspaceCheckoutResult>(`/workspaces/${encodeURIComponent(projectId)}/checkout`, {
    method: "POST",
    body: JSON.stringify({
      branch: request.branch,
      confirm_dirty: request.confirm_dirty ?? false,
    }),
  });
}
