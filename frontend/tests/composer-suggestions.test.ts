import assert from "node:assert/strict";
import test from "node:test";

import {
  applyComposerSuggestion,
  buildCommandSuggestions,
  CONTEXT_SUGGESTIONS,
  detectComposerSuggestionTrigger,
  filterComposerSuggestions,
} from "../src/runtime/composerSuggestions.ts";

test("detects context and slash command triggers from the active token", () => {
  assert.deepEqual(detectComposerSuggestionTrigger("@"), { kind: "context", query: "", tokenStart: 0, tokenEnd: 1 });
  assert.deepEqual(detectComposerSuggestionTrigger("read @glob"), { kind: "context", query: "glob", tokenStart: 5, tokenEnd: 10 });
  assert.deepEqual(detectComposerSuggestionTrigger("/co"), { kind: "command", query: "co", tokenStart: 0, tokenEnd: 3 });
  assert.equal(detectComposerSuggestionTrigger("plain text"), null);
});

test("filters context suggestions and applies the selected value to the active token", () => {
  const trigger = detectComposerSuggestionTrigger("Use @g");
  assert.ok(trigger);

  const filtered = filterComposerSuggestions(CONTEXT_SUGGESTIONS, trigger);
  assert.equal(filtered[0].value, "@glob:src/**/*.py");
  assert.equal(applyComposerSuggestion("Use @g", trigger, filtered[0]), "Use @glob:src/**/*.py ");
});

test("builds slash command suggestions from backend registry items", () => {
  const suggestions = buildCommandSuggestions({
    compact: { name: "compact", description: "Compact context" },
    memory: { name: "memory", description: "Show memory" },
  });

  assert.deepEqual(
    suggestions.map((item) => item.value),
    ["/compact", "/memory"],
  );
  assert.equal(filterComposerSuggestions(suggestions, { kind: "command", query: "mem", tokenStart: 0, tokenEnd: 4 })[0].value, "/memory");
});
