import assert from "node:assert/strict";
import test from "node:test";

import { ApiError } from "../src/api/client.ts";
import { checkoutWorkspaceBranch } from "../src/api/workspaces.ts";

test("checkoutWorkspaceBranch posts branch checkout requests to the workspace API", async () => {
  const calls: { url: string; init: RequestInit }[] = [];
  const originalFetch = globalThis.fetch;
  globalThis.fetch = async (url, init = {}) => {
    calls.push({ url: String(url), init });
    return new Response(
      JSON.stringify({
        ok: true,
        message: "Checked out feature.",
        workspace: {
          project_id: "project_1",
          display_name: "repo",
          root_path: "/repo",
          is_git_repo: true,
          current_branch: "feature",
          branches: ["feature", "master"],
          git_status: { staged: 0, unstaged: 0, untracked: 0, conflicted: 0 },
          dirty: false,
        },
      }),
      { status: 200, headers: { "Content-Type": "application/json" } },
    );
  };
  try {
    const result = await checkoutWorkspaceBranch("project_1", { branch: "feature", confirm_dirty: true });

    assert.equal(result.workspace.current_branch, "feature");
    assert.equal(calls[0].url, "http://127.0.0.1:8010/workspaces/project_1/checkout");
    assert.equal(calls[0].init.method, "POST");
    assert.deepEqual(JSON.parse(String(calls[0].init.body)), { branch: "feature", confirm_dirty: true });
  } finally {
    globalThis.fetch = originalFetch;
  }
});

test("checkoutWorkspaceBranch surfaces dirty-worktree API errors", async () => {
  const originalFetch = globalThis.fetch;
  globalThis.fetch = async () => new Response(JSON.stringify({ detail: "Workspace has uncommitted changes" }), { status: 409, statusText: "Conflict" });
  try {
    await assert.rejects(
      () => checkoutWorkspaceBranch("project_1", { branch: "feature" }),
      (error) => error instanceof ApiError && error.status === 409 && error.body.includes("uncommitted changes"),
    );
  } finally {
    globalThis.fetch = originalFetch;
  }
});
