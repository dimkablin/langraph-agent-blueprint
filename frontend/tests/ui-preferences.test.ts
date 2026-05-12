import assert from "node:assert/strict";
import test from "node:test";

import type { RuntimeEvent } from "../src/api/schemas.ts";
import {
  applyThemePreset,
  DEFAULT_THEME_PREFERENCES,
  DEFAULT_UI_PREFERENCES,
  filterEventsByPreferences,
  filterTimelineByPreferences,
  loadUIPreferences,
  saveUIPreferences,
  themeCSSVariables,
  themePresetOptionsForVariant,
  updateThemeConfig,
} from "../src/runtime/uiPreferences.ts";
import type { ActivityItem, ChatTimelineItem } from "../src/runtime/reducer.ts";

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

function activity(eventType: string, label: string, kind: ActivityItem["kind"]): ActivityItem {
  return {
    id: `activity-${eventType}`,
    kind,
    label,
    summary: "",
    status: "success",
    timestamp: "2026-05-09T00:00:00Z",
    eventType,
    category: kind,
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
      blockRadius: 18,
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

test("UI block radius preference normalizes and drives shared radius variables", () => {
  const storage = new MemoryStorage();

  const saved = saveUIPreferences({ ...DEFAULT_UI_PREFERENCES, blockRadius: 24 }, storage);
  const variables = themeCSSVariables(saved);

  assert.equal(saved.blockRadius, 24);
  assert.equal(loadUIPreferences(storage).blockRadius, 24);
  assert.equal(variables["--ui-element-radius"], "24px");

  assert.equal(saveUIPreferences({ ...DEFAULT_UI_PREFERENCES, blockRadius: 99 }, storage).blockRadius, 32);
  assert.equal(saveUIPreferences({ ...DEFAULT_UI_PREFERENCES, blockRadius: -8 }, storage).blockRadius, 0);
  assert.equal(saveUIPreferences({ ...DEFAULT_UI_PREFERENCES, blockRadius: Number.NaN }, storage).blockRadius, DEFAULT_UI_PREFERENCES.blockRadius);
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
  assert.deepEqual(darkPresets, ["codex", "matrix", "temple", "github"]);

  const matrix = applyThemePreset(DEFAULT_UI_PREFERENCES, "dark", "matrix");
  const temple = applyThemePreset(DEFAULT_UI_PREFERENCES, "dark", "temple");
  const githubLight = applyThemePreset(DEFAULT_UI_PREFERENCES, "light", "github");
  const matrixVariables = themeCSSVariables({ ...matrix, theme: "dark" });
  const templeVariables = themeCSSVariables({ ...temple, theme: "dark" });
  const githubVariables = themeCSSVariables({ ...githubLight, theme: "light" });

  assert.equal(matrix.themes.dark.codeThemeId, "matrix");
  assert.equal(matrixVariables["--codex-accent"], "#1eff5a");
  assert.equal(matrixVariables["--codex-skill"], "#1eff5a");
  assert.equal(temple.themes.dark.codeThemeId, "temple");
  assert.equal(templeVariables["--codex-accent"], "#e4f222");
  assert.equal(templeVariables["--codex-surface"], "#02120c");
  assert.equal(templeVariables["--codex-ink"], "#c7e6da");
  assert.equal(templeVariables["--codex-skill"], "#e4f222");
  assert.equal(githubLight.themes.light.codeThemeId, "github");
  assert.equal(githubVariables["--codex-accent"], "#0969da");
  assert.equal(githubVariables["--codex-diff-removed"], "#cf222e");
});

test("dark presets keep the sidebar darker than the page surface", () => {
  const codexVariables = themeCSSVariables({ ...DEFAULT_UI_PREFERENCES, theme: "dark" });
  const github = applyThemePreset(DEFAULT_UI_PREFERENCES, "dark", "github");
  const githubVariables = themeCSSVariables({ ...github, theme: "dark" });
  const matrix = applyThemePreset(DEFAULT_UI_PREFERENCES, "dark", "matrix");
  const matrixVariables = themeCSSVariables({ ...matrix, theme: "dark" });

  assert.equal(codexVariables["--codex-sidebar-surface"], "color-mix(in oklab, #111111 72%, #000000)");
  assert.equal(codexVariables["--codex-background-surface"], "color-mix(in oklab, #111111 95.57%, #fcfcfc)");
  assert.equal(githubVariables["--codex-sidebar-surface"], "color-mix(in oklab, #0d1117 72%, #000000)");
  assert.equal(githubVariables["--codex-background-surface"], "color-mix(in oklab, #0d1117 95.57%, #e6edf3)");
  assert.equal(matrixVariables["--codex-background-surface"], "#040805");
  assert.equal(matrixVariables["--codex-sidebar-surface"], "color-mix(in oklab, #040805 72%, #000000)");
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

test("activity timeline hides low signal activity unless debug events are enabled", () => {
  const timeline: ChatTimelineItem[] = [
    {
      kind: "activity",
      id: "activity-group",
      timestamp: "2026-05-09T00:00:00Z",
      activities: [
        activity("runtime.run.started", "Run started", "runtime"),
        activity("workspace.selected", "Workspace selected", "workspace"),
        activity("skill.python_backend.discovered", "Skill discovered", "skill"),
        activity("tool.bash.started", "Run Bash command", "verification"),
      ],
    },
    {
      kind: "activity",
      id: "low-signal-only",
      timestamp: "2026-05-09T00:00:01Z",
      activities: [activity("runtime.run.started", "Run started", "runtime")],
    },
  ];

  const normal = filterTimelineByPreferences(timeline, {
    ...DEFAULT_UI_PREFERENCES,
    showDebugEvents: false,
  });
  const debug = filterTimelineByPreferences(timeline, {
    ...DEFAULT_UI_PREFERENCES,
    showDebugEvents: true,
  });

  assert.equal(normal.length, 1);
  assert.equal(normal[0].kind, "activity");
  if (normal[0].kind === "activity") {
    assert.deepEqual(
      normal[0].activities.map((item) => item.eventType),
      ["tool.bash.started"],
    );
  }
  assert.equal(debug.length, 2);
  assert.equal(debug[0].kind, "activity");
  if (debug[0].kind === "activity") {
    assert.deepEqual(
      debug[0].activities.map((item) => item.eventType),
      ["runtime.run.started", "workspace.selected", "skill.python_backend.discovered", "tool.bash.started"],
    );
  }
});
