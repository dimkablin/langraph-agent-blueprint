import assert from "node:assert/strict";
import test from "node:test";

import { buildContextWindowView, contextRecordPreview, formatContextBudgetLine, isExpandableContextRecord } from "../src/runtime/contextWindow.ts";
import type { RuntimeContextState } from "../src/runtime/reducer.ts";

function context(overrides: Partial<RuntimeContextState> = {}): RuntimeContextState {
  return {
    references: [],
    fragments: [],
    attachments: [],
    budget: null,
    errors: [],
    ...overrides,
  };
}

test("context window budget uses configured max tokens when no budget event exists yet", () => {
  const view = buildContextWindowView(context(), 8000);

  assert.equal(view.budget.usedTokens, 0);
  assert.equal(view.budget.maxTokens, 8000);
  assert.equal(view.budget.remainingTokens, 8000);
  assert.equal(view.budget.percent, 0);
});

test("context window budget reports remaining tokens from backend budget values", () => {
  const view = buildContextWindowView(
    context({
      budget: { max_tokens: 100, used_tokens: 32 },
    }),
    8000,
  );

  assert.equal(view.budget.usedTokens, 32);
  assert.equal(view.budget.maxTokens, 100);
  assert.equal(view.budget.remainingTokens, 68);
  assert.equal(view.budget.percent, 32);
  assert.equal(formatContextBudgetLine(view.budget, "gpt-4.1"), "Контекст gpt-4.1: 32 / 100 токенов");
});

test("context window fragment section exposes preview text and token counts", () => {
  const view = buildContextWindowView(
    context({
      fragments: [
        {
          id: "ctx_1",
          title: "README.md",
          content: "Important runtime context",
          token_estimate: 6,
          trust: "trusted_local",
        },
      ],
    }),
    100,
  );

  const fragment = view.sections.find((section) => section.kind === "fragments")?.items[0];

  assert.equal(fragment?.title, "README.md");
  assert.equal(fragment?.preview, "Important runtime context");
  assert.equal(fragment?.tokens, 6);
  assert.deepEqual(fragment?.chips, ["trusted_local"]);
});

test("context record preview can be expanded from the collapsed text", () => {
  const longText = `${"context ".repeat(80)}final visible token`;
  const view = buildContextWindowView(
    context({
      fragments: [{ id: "ctx_1", title: "large.txt", content: longText }],
    }),
    1000,
  );
  const fragment = view.sections.find((section) => section.kind === "fragments")?.items[0];

  assert.ok(fragment);
  assert.equal(isExpandableContextRecord(fragment), true);
  assert.match(contextRecordPreview(fragment, false), /\.\.\.$/);
  assert.equal(contextRecordPreview(fragment, true), longText);
});
