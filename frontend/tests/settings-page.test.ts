import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { join } from "node:path";
import test from "node:test";

import {
  DEFAULT_SETTINGS_TAB,
  SETTINGS_TABS,
  isSettingsTab,
  settingsTabLabel,
  type SettingsTab,
} from "../src/runtime/settingsPage.ts";

const root = new URL("../..", import.meta.url).pathname.replace(/^\/([A-Za-z]:)/, "$1");
const srcRoot = join(root, "frontend", "src");

test("settings tabs expose the required stable Russian labels", () => {
  const labels = SETTINGS_TABS.map((tab) => tab.label);

  assert.deepEqual(labels, ["Общее", "Внешний вид", "Конфигурация", "Серверы MCP", "Плагины", "Скилы"]);
  assert.equal(DEFAULT_SETTINGS_TAB, "general");
});

test("settings tab helpers accept only known tabs", () => {
  const ids = SETTINGS_TABS.map((tab) => tab.id);

  assert.deepEqual(ids, ["general", "appearance", "configuration", "mcp", "plugins", "skills"] satisfies SettingsTab[]);
  assert.equal(isSettingsTab("mcp"), true);
  assert.equal(isSettingsTab("unknown"), false);
  assert.equal(settingsTabLabel("plugins"), "Плагины");
});

test("settings sidebar tabs stay a six-by-one list at narrow widths", () => {
  const styles = readFileSync(join(srcRoot, "components", "settings", "settings.css"), "utf8");

  assert.match(styles, /\.settings-tabs\s*\{[^}]*display:\s*flex/);
  assert.match(styles, /\.settings-tabs\s*\{[^}]*flex-direction:\s*column/);
  assert.doesNotMatch(
    styles,
    /@media \(max-width:\s*820px\)\s*\{[\s\S]*?\.settings-tabs\s*\{[^}]*grid-template-columns:\s*repeat\(2,\s*minmax\(0,\s*1fr\)\)/,
  );
});
