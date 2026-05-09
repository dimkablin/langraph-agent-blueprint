import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { join } from "node:path";
import test from "node:test";

const root = new URL("../..", import.meta.url).pathname.replace(/^\/([A-Za-z]:)/, "$1");
const srcRoot = join(root, "frontend", "src");

test("settings center is read-only for backend config and uses passive MCP status", () => {
  const app = readFileSync(join(srcRoot, "App.tsx"), "utf8");
  const statusApi = readFileSync(join(srcRoot, "api", "status.ts"), "utf8");
  const settingsCenter = readFileSync(join(srcRoot, "components", "settings", "SettingsCenter.tsx"), "utf8");
  const uiPreferences = readFileSync(join(srcRoot, "runtime", "uiPreferences.ts"), "utf8");
  const routesMcp = readFileSync(join(root, "src", "langgraph_agent_blueprint", "api", "routes_mcp.py"), "utf8");

  assert.match(app, /SettingsCenter/);
  assert.doesNotMatch(app, /RuntimeStatusPanel/);
  assert.match(routesMcp, /\/mcp\/snapshot/);
  assert.match(statusApi, /\/mcp\/snapshot/);
  assert.doesNotMatch(statusApi, /requestJson<MCPStatusDTO>\("\/mcp"\)/);
  assert.match(settingsCenter, /ModelSettingsSection/);
  assert.match(settingsCenter, /PluginSettingsSection/);
  assert.match(settingsCenter, /UIPreferencesSection/);
  assert.match(settingsCenter, /read-only/i);
  assert.match(settingsCenter, /config file only/i);
  assert.match(uiPreferences, /localStorage/);
  assert.match(uiPreferences, /eventVerbosity/);
  assert.doesNotMatch(`${settingsCenter}\n${statusApi}`, /PATCH \/settings|requestJson<.*>\("\/settings"/);
  assert.doesNotMatch(settingsCenter, /api[_-]?key\s*[:=]/i);
});
