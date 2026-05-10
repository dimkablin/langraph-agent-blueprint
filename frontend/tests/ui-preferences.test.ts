import assert from "node:assert/strict";
import test from "node:test";

import type { RuntimeEvent } from "../src/api/schemas.ts";
import {
  applyThemePreset,
  DEFAULT_THEME_PREFERENCES,
  DEFAULT_UI_PREFERENCES,
  filterEventsByPreferences,
  loadUIPreferences,
  saveUIPreferences,
  themeCSSVariables,
  themePresetOptionsForVariant,
  updateThemeConfig,
} from "../src/runtime/uiPreferences.ts";

class MemoryStorage {
  private values = new Map<string, string>();

  getItem(key: string): string | null {
    return this.values.get(key) ?? null;
  }

  setItem(key: string, value: string): void {
    this.values.set(key, value);
  }

  removeItem(key: string): void {
    this.values.delete(key);
  }
}

function event(type: string, severity: RuntimeEvent["severity"] = "info"): RuntimeEvent {
  return {
    id: type,
    type,
    timestamp: "2026-05-09T00:00:00Z",
    session_id: "session_1",
    severity,
    data: {},
  };
}

test("UI preferences load defaults and persist valid local-only values", () => {
  const storage = new MemoryStorage();

  assert.deepEqual(loadUIPreferences(storage), DEFAULT_UI_PREFERENCES);

  const saved = saveUIPreferences(
    {
      theme: "dark",
      themes: DEFAULT_THEME_PREFERENCES,
      density: "compact",
      eventVerbosity: "essential",
      autoScroll: false,
      showDebugEvents: false,
    },
    storage,
  );

  assert.equal(saved.theme, "dark");
  assert.deepEqual(loadUIPreferences(storage), saved);
});

test("UI preferences ignore malformed stored values", () => {
  const storage = new MemoryStorage();
  storage.setItem("lg-agent-ui-preferences", JSON.stringify({ theme: "neon", autoScroll: "yes" }));

  assert.deepEqual(loadUIPreferences(storage), DEFAULT_UI_PREFERENCES);
});

test("theme preferences expose CSS variables and normalize editable values", () => {
  const updated = updateThemeConfig(DEFAULT_UI_PREFERENCES, "dark", {
    accent: "#ABCDEF",
    surface: "#111111",
    ink: "#fcfcfc",
    contrast: 250,
    uiFontSize: 22,
    codeFontSize: 3,
    usePointerCursor: false,
  });
  const variables = themeCSSVariables({ ...updated, theme: "dark" });

  assert.equal(updated.themes.dark.accent, "#abcdef");
  assert.equal(updated.themes.dark.contrast, 100);
  assert.equal(updated.themes.dark.uiFontSize, 18);
  assert.equal(updated.themes.dark.codeFontSize, 10);
  assert.equal(variables["--codex-accent"], "#abcdef");
  assert.equal(variables["--codex-theme-id"], "codex");
  assert.equal(variables["--codex-theme-variant"], "dark");
  assert.equal(variables["--codex-surface"], "#111111");
  assert.equal(variables["--codex-ink"], "#fcfcfc");
  assert.equal(variables["--codex-diff-added"], "#00a240");
  assert.equal(variables["--app-interactive-cursor"], "default");
  assert.equal(variables["--font-size-caption"], "16px");
  assert.equal(variables["--font-size-small"], "17px");
  assert.equal(variables["--font-size-body"], "18px");
  assert.equal(variables["--font-size-body-lg"], "19px");
  assert.equal(variables["--font-size-title"], "25px");
  assert.equal(variables["--font-size-heading"], "27px");
  assert.equal(variables["--font-size-code"], "10px");
  assert.match(variables["--font-sans"], /ui-sans-serif/);
  assert.match(variables["--font-mono"], /Cascadia Code/);
});

test("theme presets expose the requested light and dark theme catalog", () => {
  const lightPresets = themePresetOptionsForVariant("light").map((option) => option.value);
  const darkPresets = themePresetOptionsForVariant("dark").map((option) => option.value);

  assert.deepEqual(lightPresets, ["codex", "everforest", "notion", "github"]);
  assert.deepEqual(darkPresets, ["codex", "matrix", "github"]);

  const matrix = applyThemePreset(DEFAULT_UI_PREFERENCES, "dark", "matrix");
  const githubLight = applyThemePreset(DEFAULT_UI_PREFERENCES, "light", "github");
  const matrixVariables = themeCSSVariables({ ...matrix, theme: "dark" });
  const githubVariables = themeCSSVariables({ ...githubLight, theme: "light" });

  assert.equal(matrix.themes.dark.codeThemeId, "matrix");
  assert.equal(matrixVariables["--codex-accent"], "#1eff5a");
  assert.equal(matrixVariables["--codex-skill"], "#1eff5a");
  assert.equal(githubLight.themes.light.codeThemeId, "github");
  assert.equal(githubVariables["--codex-accent"], "#0969da");
  assert.equal(githubVariables["--codex-diff-removed"], "#cf222e");
});

test("event verbosity filters debug events without removing errors", () => {
  const events = [event("final_response"), event("hook_event"), event("mcp_tools_discovered"), event("error", "error")];

  const essential = filterEventsByPreferences(events, {
    ...DEFAULT_UI_PREFERENCES,
    eventVerbosity: "essential",
    showDebugEvents: false,
  });
  const debug = filterEventsByPreferences(events, {
    ...DEFAULT_UI_PREFERENCES,
    eventVerbosity: "debug",
    showDebugEvents: true,
  });

  assert.deepEqual(
    essential.map((item) => item.type),
    ["final_response", "error"],
  );
  assert.deepEqual(
    debug.map((item) => item.type),
    ["final_response", "hook_event", "mcp_tools_discovered", "error"],
  );
});
