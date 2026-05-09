import assert from "node:assert/strict";
import test from "node:test";

import {
  DEFAULT_SETTINGS_TAB,
  SETTINGS_TABS,
  isSettingsTab,
  settingsTabLabel,
  type SettingsTab,
} from "../src/runtime/settingsPage.ts";

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
