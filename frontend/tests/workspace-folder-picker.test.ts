import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { test } from "node:test";

const app = readFileSync(new URL("../src/App.tsx", import.meta.url), "utf8");
const hook = readFileSync(new URL("../src/hooks/useWorkspaces.ts", import.meta.url), "utf8");
const api = readFileSync(new URL("../src/api/workspaces.ts", import.meta.url), "utf8");

test("add project action opens the backend folder picker instead of a manual path prompt", () => {
  assert.doesNotMatch(app, /window\.prompt/);
  assert.match(app, /pickLocalWorkspace/);
  assert.match(hook, /pickWorkspaceFolder/);
  assert.match(hook, /pickLocalWorkspace/);
  assert.match(api, /function pickWorkspaceFolder/);
  assert.match(api, /"\/workspaces\/pick"/);
});
