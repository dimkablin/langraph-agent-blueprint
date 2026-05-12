import { useCallback, useEffect, useState } from "react";

import {
  addWorkspace,
  checkoutWorkspaceBranch,
  fetchActiveWorkspace,
  fetchWorkspaces,
  pickWorkspaceFolder,
  selectWorkspace,
} from "../api/workspaces.ts";
import type { WorkspaceInfo } from "../api/schemas.ts";
import { workspaceErrorMessage } from "../runtime/workspaces.ts";

export function useWorkspaces() {
  const [workspaces, setWorkspaces] = useState<WorkspaceInfo[]>([]);
  const [activeWorkspace, setActiveWorkspace] = useState<WorkspaceInfo | null>(null);
  const [workspaceError, setWorkspaceError] = useState<string | null>(null);

  const refreshWorkspaces = useCallback(async () => {
    const [items, active] = await Promise.all([fetchWorkspaces(), fetchActiveWorkspace()]);
    setWorkspaces(items);
    setActiveWorkspace(active);
  }, []);

  useEffect(() => {
    void refreshWorkspaces().catch((error) => setWorkspaceError(workspaceErrorMessage(error)));
  }, [refreshWorkspaces]);

  const addLocalWorkspace = useCallback(
    async (rootPath: string) => {
      try {
        const workspace = await addWorkspace(rootPath);
        setActiveWorkspace(workspace);
        await refreshWorkspaces();
        setWorkspaceError(null);
      } catch (error) {
        setWorkspaceError(workspaceErrorMessage(error));
      }
    },
    [refreshWorkspaces],
  );

  const pickLocalWorkspace = useCallback(async () => {
    try {
      const workspace = await pickWorkspaceFolder();
      if (workspace) {
        setActiveWorkspace(workspace);
        await refreshWorkspaces();
      }
      setWorkspaceError(null);
    } catch (error) {
      setWorkspaceError(workspaceErrorMessage(error));
    }
  }, [refreshWorkspaces]);

  const setActiveProject = useCallback(
    async (projectId: string) => {
      try {
        setActiveWorkspace(await selectWorkspace(projectId));
        await refreshWorkspaces();
        setWorkspaceError(null);
      } catch (error) {
        setWorkspaceError(workspaceErrorMessage(error));
      }
    },
    [refreshWorkspaces],
  );

  const checkoutBranch = useCallback(
    async (branch: string) => {
      if (!activeWorkspace || !branch || branch === activeWorkspace.current_branch) {
        return;
      }
      try {
        const result = await checkoutWorkspaceBranch(activeWorkspace.project_id, { branch });
        setActiveWorkspace(result.workspace);
        await refreshWorkspaces();
        setWorkspaceError(null);
      } catch (error) {
        setWorkspaceError(workspaceErrorMessage(error));
      }
    },
    [activeWorkspace, refreshWorkspaces],
  );

  return {
    workspaces,
    activeWorkspace,
    workspaceError,
    refreshWorkspaces,
    addLocalWorkspace,
    pickLocalWorkspace,
    setActiveProject,
    checkoutBranch,
  };
}
