import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { join } from "node:path";
import test from "node:test";
import { fileURLToPath } from "node:url";

const root = fileURLToPath(new URL("../..", import.meta.url));
const srcRoot = join(root, "frontend", "src");

test("workspace controls live below the chat composer input instead of in the header", () => {
  const app = readFileSync(join(srcRoot, "App.tsx"), "utf8");
  const composer = readFileSync(join(srcRoot, "components", "chat", "ChatComposer.tsx"), "utf8");
  const header = readFileSync(join(srcRoot, "components", "layout", "StatusHeader.tsx"), "utf8");
  const styles = readFileSync(join(srcRoot, "styles.css"), "utf8");

  assert.match(composer, /WorkspaceControl/);
  assert.match(composer, /<div className="composer-surface">[\s\S]*<\/div>\s*<div className="composer-workspace-row">[\s\S]*<WorkspaceControl/);
  assert.match(app, /<ChatComposer[\s\S]*workspace=\{activeWorkspace\}/);
  assert.match(app, /<ChatComposer[\s\S]*onCheckoutBranch=\{\(branch\) => void checkoutBranch\(branch\)\}/);
  assert.doesNotMatch(header, /WorkspaceControl|workspaceError|onCheckoutBranch|onAddWorkspace/);
  assert.match(styles, /\.composer-workspace-row\s*\{[^}]*width:\s*min\(var\(--chat-column-width\),\s*calc\(100% - 24px\)\)/);
});
