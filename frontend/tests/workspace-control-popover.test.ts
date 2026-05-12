import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { test } from "node:test";

const component = readFileSync(new URL("../src/components/workspaces/WorkspaceControl.tsx", import.meta.url), "utf8");
const styles = readFileSync(new URL("../src/styles.css", import.meta.url), "utf8");

test("workspace controls use app-styled popovers for project and branch selection", () => {
  assert.doesNotMatch(component, /<select\b/);
  assert.match(component, /workspace-project-popover/);
  assert.match(component, /workspace-branch-popover/);
  assert.match(component, /placeholder="Поиск проектов"/);
  assert.match(component, /placeholder="Поиск ветвей"/);
  assert.match(component, /Создать и переключиться на новую ветку/);
  assert.match(component, /onSelectWorkspace\(project\.project_id\)/);
  assert.match(component, /onCheckoutBranch\(branch\)/);
});

test("workspace buttons are borderless until hover or open state", () => {
  assert.match(styles, /\.workspace-local-button,\s*\.workspace-branch-button\s*\{[^}]*border:\s*0/);
  assert.match(styles, /\.workspace-local-button,\s*\.workspace-branch-button\s*\{[^}]*background:\s*transparent/);
  assert.match(styles, /\.workspace-local-button:hover,\s*\.workspace-local-button:focus-visible,\s*\.workspace-local-button\[aria-expanded="true"\],\s*\.workspace-branch-button:hover,\s*\.workspace-branch-button:focus-visible,\s*\.workspace-branch-button\[aria-expanded="true"\]\s*\{[^}]*background:\s*var\(--hover-surface\)/);
});
