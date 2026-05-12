import { useEffect, useMemo, useRef, useState } from "react";

import type { WorkspaceInfo } from "../../api/schemas.ts";
import { IconCheck, IconChevronDown, IconFolder, IconGitCompare, IconPlus, IconSearch } from "../../icons.ts";
import { workspaceControlView } from "../../runtime/workspaces.ts";

type WorkspaceMenu = "project" | "branch" | null;

export function WorkspaceControl({
  workspace,
  workspaces,
  workspaceError,
  onAddWorkspace,
  onSelectWorkspace,
  onCheckoutBranch,
}: {
  workspace: WorkspaceInfo | null;
  workspaces: WorkspaceInfo[];
  workspaceError: string | null;
  onAddWorkspace: () => void;
  onSelectWorkspace: (projectId: string) => void;
  onCheckoutBranch: (branch: string) => void;
}) {
  const [openMenu, setOpenMenu] = useState<WorkspaceMenu>(null);
  const [projectQuery, setProjectQuery] = useState("");
  const [branchQuery, setBranchQuery] = useState("");
  const controlRef = useRef<HTMLDivElement | null>(null);
  const view = workspaceControlView(workspace);
  const filteredWorkspaces = useMemo(() => {
    const query = projectQuery.trim().toLowerCase();
    if (!query) return workspaces;
    return workspaces.filter((project) => {
      const searchable = `${project.display_name} ${project.root_path}`.toLowerCase();
      return searchable.includes(query);
    });
  }, [projectQuery, workspaces]);
  const filteredBranches = useMemo(() => {
    const query = branchQuery.trim().toLowerCase();
    if (!query) return view.branches;
    return view.branches.filter((branch) => branch.toLowerCase().includes(query));
  }, [branchQuery, view.branches]);

  useEffect(() => {
    if (!openMenu) return;

    function handlePointerDown(event: PointerEvent) {
      if (!controlRef.current?.contains(event.target as Node)) {
        setOpenMenu(null);
      }
    }

    function handleKeyDown(event: KeyboardEvent) {
      if (event.key === "Escape") {
        setOpenMenu(null);
      }
    }

    document.addEventListener("pointerdown", handlePointerDown);
    document.addEventListener("keydown", handleKeyDown);
    return () => {
      document.removeEventListener("pointerdown", handlePointerDown);
      document.removeEventListener("keydown", handleKeyDown);
    };
  }, [openMenu]);

  function openProjectMenu() {
    setOpenMenu((current) => (current === "project" ? null : "project"));
    setProjectQuery("");
  }

  function openBranchMenu() {
    if (view.branchDisabled) return;
    setOpenMenu((current) => (current === "branch" ? null : "branch"));
    setBranchQuery("");
  }

  return (
    <div className="workspace-control" aria-label="Workspace controls" ref={controlRef}>
      <div className="workspace-menu-wrapper">
        <button
          type="button"
          className="workspace-local-button"
          aria-haspopup="menu"
          aria-expanded={openMenu === "project"}
          onClick={openProjectMenu}
        >
          <IconFolder size={14} />
          <span>{view.localLabel}</span>
          <IconChevronDown size={13} className={openMenu === "project" ? "workspace-chevron-open" : undefined} />
        </button>
        {openMenu === "project" ? (
          <div className="workspace-popover workspace-project-popover" role="menu" aria-label="Проекты">
            <label className="workspace-search">
              <IconSearch size={14} />
              <input
                value={projectQuery}
                onChange={(event) => setProjectQuery(event.target.value)}
                placeholder="Поиск проектов"
                autoFocus
              />
            </label>
            <div className="workspace-menu-list">
              {filteredWorkspaces.length > 0 ? (
                filteredWorkspaces.map((project) => {
                  const isSelected = project.project_id === workspace?.project_id;
                  return (
                    <button
                      key={project.project_id}
                      type="button"
                      className={isSelected ? "workspace-menu-row workspace-menu-row-selected" : "workspace-menu-row"}
                      role="menuitemradio"
                      aria-checked={isSelected}
                      onClick={() => {
                        onSelectWorkspace(project.project_id);
                        setOpenMenu(null);
                      }}
                    >
                      <IconFolder size={15} />
                      <span>{project.display_name || project.root_path}</span>
                      {isSelected ? <IconCheck size={15} /> : null}
                    </button>
                  );
                })
              ) : (
                <p className="workspace-menu-empty">Проекты не найдены</p>
              )}
            </div>
            <button
              type="button"
              className="workspace-menu-row workspace-menu-add"
              role="menuitem"
              onClick={() => {
                onAddWorkspace();
                setOpenMenu(null);
              }}
            >
              <IconPlus size={15} />
              <span>Добавить новый проект</span>
            </button>
          </div>
        ) : null}
      </div>

      {view.branchLabel ? (
        <div className="workspace-menu-wrapper">
          <button
            type="button"
            className="workspace-branch-button"
            aria-haspopup="menu"
            aria-expanded={openMenu === "branch"}
            disabled={view.branchDisabled}
            onClick={openBranchMenu}
          >
            <IconGitCompare size={14} />
            <span>{view.branchLabel}</span>
            {view.showDirtyIndicator ? <span className="workspace-dirty-dot" aria-label="Workspace has changes" /> : null}
            <IconChevronDown size={13} className={openMenu === "branch" ? "workspace-chevron-open" : undefined} />
          </button>
          {openMenu === "branch" ? (
            <div className="workspace-popover workspace-branch-popover" role="menu" aria-label="Ветки">
              <label className="workspace-search">
                <IconSearch size={14} />
                <input
                  value={branchQuery}
                  onChange={(event) => setBranchQuery(event.target.value)}
                  placeholder="Поиск ветвей"
                  autoFocus
                />
              </label>
              <div className="workspace-menu-title">Ветки</div>
              <div className="workspace-menu-list">
                {filteredBranches.length > 0 ? (
                  filteredBranches.map((branch) => {
                    const isSelected = branch === workspace?.current_branch;
                    return (
                      <button
                        key={branch}
                        type="button"
                        className={isSelected ? "workspace-branch-row workspace-menu-row-selected" : "workspace-branch-row"}
                        role="menuitemradio"
                        aria-checked={isSelected}
                        onClick={() => {
                          onCheckoutBranch(branch);
                          setOpenMenu(null);
                        }}
                      >
                        <IconGitCompare size={15} />
                        <span>
                          <strong>{branch}</strong>
                        </span>
                        {isSelected ? <IconCheck size={15} /> : null}
                      </button>
                    );
                  })
                ) : (
                  <p className="workspace-menu-empty">Ветки не найдены</p>
                )}
              </div>
              <button type="button" className="workspace-menu-row workspace-menu-add" role="menuitem" disabled>
                <IconPlus size={15} />
                <span>Создать и переключиться на новую ветку...</span>
              </button>
            </div>
          ) : null}
        </div>
      ) : null}

      {workspaceError ? <span className="workspace-warning">{workspaceError}</span> : null}
    </div>
  );
}
