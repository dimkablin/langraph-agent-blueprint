import assert from "node:assert/strict";
import test from "node:test";

import { clearActiveSessionId, loadActiveSessionId, saveActiveSessionId } from "../src/runtime/activeSession.ts";

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

test("active session storage persists the selected chat id", () => {
  const storage = new MemoryStorage();

  assert.equal(loadActiveSessionId(storage), null);

  assert.equal(saveActiveSessionId(" session_123 ", storage), "session_123");
  assert.equal(loadActiveSessionId(storage), "session_123");
});

test("active session storage ignores malformed values and supports explicit clearing", () => {
  const storage = new MemoryStorage();

  storage.setItem("lg-agent-active-session", JSON.stringify({ sessionId: "" }));
  assert.equal(loadActiveSessionId(storage), null);

  saveActiveSessionId("session_456", storage);
  clearActiveSessionId(storage);

  assert.equal(loadActiveSessionId(storage), null);
});
