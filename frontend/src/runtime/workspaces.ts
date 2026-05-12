import type { WorkspaceInfo } from "../api/schemas.ts";

export type WorkspaceControlMode = "empty" | "local" | "git";

export type WorkspaceControlView = {
  mode: WorkspaceControlMode;
  localLabel: string;
  projectLabel: string | null;
  branchLabel: string | null;
  branchDisabled: boolean;
  branches: string[];
  showDirtyIndicator: boolean;
};

export function workspaceDirtyFileCount(workspace: WorkspaceInfo | null): number {
  if (!workspace?.dirty) {
    return 0;
  }
  if (!workspace.git_status) {
    return 1;
  }
  return (
    workspace.git_status.staged +
    workspace.git_status.unstaged +
    workspace.git_status.untracked +
    workspace.git_status.conflicted
  );
}

export function workspaceControlView(workspace: WorkspaceInfo | null): WorkspaceControlView {
  if (!workspace) {
    return {
      mode: "empty",
      localLabel: "Выбрать проект",
      projectLabel: null,
      branchLabel: null,
      branchDisabled: true,
      branches: [],
      showDirtyIndicator: false,
    };
  }
  const workspaceLabel = workspace.display_name || workspace.root_path;
  if (!workspace.is_git_repo) {
    return {
      mode: "local",
      localLabel: workspaceLabel,
      projectLabel: workspaceLabel,
      branchLabel: "No Git",
      branchDisabled: true,
      branches: [],
      showDirtyIndicator: false,
    };
  }
  return {
    mode: "git",
    localLabel: workspaceLabel,
    projectLabel: workspaceLabel,
    branchLabel: workspace.current_branch || "detached",
    branchDisabled: workspace.branches.length === 0,
    branches: workspace.branches,
    showDirtyIndicator: workspace.dirty,
  };
}

export function workspaceErrorMessage(error: unknown): string {
  const message = error instanceof Error ? error.message : String(error);
  if (message.includes("409") || message.includes("uncommitted changes")) {
    return "Есть несохранённые изменения. Переключение ветки остановлено.";
  }
  return message;
}
