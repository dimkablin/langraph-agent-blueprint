import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { join } from "node:path";
import test from "node:test";

const root = new URL("../..", import.meta.url).pathname.replace(/^\/([A-Za-z]:)/, "$1");
const srcRoot = join(root, "frontend", "src");

test("settings center is read-only for backend config and uses passive MCP status", () => {
  const app = readFileSync(join(srcRoot, "App.tsx"), "utf8");
  const statusApi = readFileSync(join(srcRoot, "api", "status.ts"), "utf8");
  const settingsPage = readFileSync(join(srcRoot, "components", "settings", "SettingsPage.tsx"), "utf8");
  const settingsTabs = readFileSync(join(srcRoot, "components", "settings", "SettingsTabs.tsx"), "utf8");
  const settingsCenter = readFileSync(join(srcRoot, "components", "settings", "SettingsCenter.tsx"), "utf8");
  const uiPreferences = readFileSync(join(srcRoot, "runtime", "uiPreferences.ts"), "utf8");
  const routesMcp = readFileSync(join(root, "src", "langgraph_agent_blueprint", "api", "routes_mcp.py"), "utf8");

  assert.match(app, /type AppView = "chat" \| "settings"/);
  assert.match(app, /SettingsPage/);
  assert.match(app, /setAppView\("settings"\)/);
  assert.doesNotMatch(app, /RuntimeStatusPanel/);
  assert.match(routesMcp, /\/mcp\/snapshot/);
  assert.match(statusApi, /\/mcp\/snapshot/);
  assert.doesNotMatch(statusApi, /requestJson<MCPStatusDTO>\("\/mcp"\)/);
  assert.match(settingsPage, /GeneralSettingsTab/);
  assert.match(settingsPage, /AppearanceSettingsTab/);
  assert.match(settingsPage, /ConfigurationSettingsTab/);
  assert.match(settingsPage, /MCPServersSettingsTab/);
  assert.match(settingsPage, /PluginsSettingsTab/);
  assert.match(settingsPage, /SkillsSettingsTab/);
  assert.match(settingsTabs, /aria-selected/);
  assert.match(settingsCenter, /SettingsPage/);
  assert.match(`${settingsCenter}\n${settingsPage}`, /read-only/i);
  assert.match(`${settingsCenter}\n${settingsPage}`, /config file only/i);
  assert.match(uiPreferences, /localStorage/);
  assert.match(uiPreferences, /eventVerbosity/);
  assert.doesNotMatch(`${settingsCenter}\n${settingsPage}\n${statusApi}`, /PATCH \/settings|requestJson<.*>\("\/settings"/);
  assert.doesNotMatch(`${settingsCenter}\n${settingsPage}`, /api[_-]?key\s*[:=]/i);
  assert.doesNotMatch(`${settingsCenter}\n${settingsPage}\n${statusApi}`, /plugins\/install|plugins\/update|plugins\/remove|\/mcp"\)/);
});
