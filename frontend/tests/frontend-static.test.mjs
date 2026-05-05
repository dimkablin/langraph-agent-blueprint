import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { join } from "node:path";
import { fileURLToPath } from "node:url";

const root = fileURLToPath(new URL("../..", import.meta.url));

function test(name, fn) {
  try {
    fn();
    console.log(`ok - ${name}`);
  } catch (error) {
    console.error(`not ok - ${name}`);
    throw error;
  }
}

test("React CLI frontend exposes terminal shell and all hint surfaces", () => {
  const app = readFileSync(join(root, "frontend", "src", "App.jsx"), "utf8");
  const hints = readFileSync(join(root, "frontend", "src", "commandHints.js"), "utf8");

  assert.match(app, /function App/);
  assert.match(app, /TerminalShell/);
  assert.match(app, /HintPanel/);
  assert.match(app, /PermissionPrompt/);
  assert.match(hints, /\/help/);
  assert.match(hints, /\/skills/);
  assert.match(hints, /read_file/);
  assert.match(hints, /debug/);
});

test("API client calls graph-facing backend endpoints only", () => {
  const api = readFileSync(join(root, "frontend", "src", "api.js"), "utf8");

  assert.match(api, /\/chat/);
  assert.match(api, /\/approval/);
  assert.doesNotMatch(api, /\/tools\/execute/);
});
