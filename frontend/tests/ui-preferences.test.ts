import assert from "node:assert/strict";
import test from "node:test";

import type { RuntimeEvent } from "../src/api/schemas.ts";
import {
  DEFAULT_UI_PREFERENCES,
  filterEventsByPreferences,
  loadUIPreferences,
  saveUIPreferences,
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
