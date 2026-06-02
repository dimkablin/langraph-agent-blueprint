import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { test } from "node:test";

const app = readFileSync(new URL("../src/App.tsx", import.meta.url), "utf8");
const hook = readFileSync(new URL("../src/hooks/useWorkspaces.ts", import.meta.url), "utf8");
const api = readFileSync(new URL("../src/api/workspaces.ts", import.meta.url), "utf8");
const control = readFileSync(new URL("../src/components/workspaces/WorkspaceControl.tsx", import.meta.url), "utf8");

test("project menu supports Docker path entry while preserving the native folder picker fallback", () => {
  assert.doesNotMatch(app, /window\.prompt/);
  assert.match(app, /addLocalWorkspace/);
  assert.match(app, /pickLocalWorkspace/);
  assert.match(hook, /addWorkspace/);
  assert.match(hook, /pickWorkspaceFolder/);
  assert.match(api, /function addWorkspace/);
  assert.match(api, /function pickWorkspaceFolder/);
  assert.match(api, /"\/workspaces\/pick"/);
  assert.match(control, /rootPathInput/);
  assert.match(control, /\/workspace\/my-project/);
  assert.match(control, /onPickWorkspace/);
});
