import assert from "node:assert/strict";
import test from "node:test";

import { workspaceControlView, workspaceDirtyFileCount, workspaceErrorMessage, type WorkspaceInfo } from "../src/runtime/workspaces.ts";

test("workspace control asks the user to select a project when no workspace is active", () => {
  const view = workspaceControlView(null);

  assert.equal(view.mode, "empty");
  assert.equal(view.localLabel, "Выбрать проект");
  assert.equal(view.branchLabel, null);
  assert.equal(view.branchDisabled, true);
  assert.equal(view.showDirtyIndicator, false);
});

test("workspace control disables branch selection for a non-git local project", () => {
  const view = workspaceControlView(workspace({ display_name: "plain", is_git_repo: false }));

  assert.equal(view.mode, "local");
  assert.equal(view.localLabel, "plain");
  assert.equal(view.projectLabel, "plain");
  assert.equal(view.branchLabel, "No Git");
  assert.equal(view.branchDisabled, true);
});

test("workspace control exposes selected project name, current branch, and dirty state for git projects", () => {
  const view = workspaceControlView(
    workspace({
      display_name: "langgraph-agent-blueprint",
      is_git_repo: true,
      current_branch: "master",
      branches: ["feature", "master"],
      dirty: true,
    }),
  );

  assert.equal(view.mode, "git");
  assert.equal(view.localLabel, "langgraph-agent-blueprint");
  assert.equal(view.branchLabel, "master");
  assert.equal(view.branchDisabled, false);
  assert.equal(view.showDirtyIndicator, true);
  assert.deepEqual(view.branches, ["feature", "master"]);
});

test("workspace dirty file count sums the public git status summary", () => {
  assert.equal(
    workspaceDirtyFileCount(
      workspace({
        dirty: true,
        git_status: {
          staged: 2,
          unstaged: 3,
          untracked: 5,
          conflicted: 7,
        },
      }),
    ),
    17,
  );
});

test("workspace errors explain Docker folder picker fallback instead of surfacing raw 501 text", () => {
  const message = workspaceErrorMessage(new Error('501 Not Implemented: {"detail":"Folder picker is unavailable in this environment."}'));

  assert.match(message, /Docker/);
  assert.match(message, /\/workspace\/my-project/);
  assert.doesNotMatch(message, /501 Not Implemented/);
});

function workspace(overrides: Partial<WorkspaceInfo>): WorkspaceInfo {
  return {
    project_id: "project_1",
    display_name: "repo",
    root_path: "/repo",
    is_git_repo: false,
    current_branch: null,
    branches: [],
    git_status: null,
    dirty: false,
    created_at: null,
    last_opened_at: null,
    ...overrides,
  };
}
