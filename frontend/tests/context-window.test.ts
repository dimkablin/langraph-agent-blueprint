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
    modelContext: null,
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
  assert.equal(formatContextBudgetLine(view.budget, "gpt-4.1"), "Контекст gpt-4.1: 32 / 100 tokens");
});

test("context window budget prefers live Hermes-style usage over context-reference budget", () => {
  const view = buildContextWindowView(
    context({
      budget: { max_tokens: 100, used_tokens: 12 },
    }),
    8000,
    { context_used: 4096, context_max: 16384, context_percent: 25 },
  );

  assert.equal(view.budget.usedTokens, 4096);
  assert.equal(view.budget.maxTokens, 16384);
  assert.equal(view.budget.remainingTokens, 12288);
  assert.equal(view.budget.percent, 25);
});

test("context window shows model-facing context report when available", () => {
  const view = buildContextWindowView(
    context({
      budget: { max_tokens: 100, used_tokens: 12 },
      modelContext: {
        max_tokens: 1000,
        used_tokens: 320,
        remaining_tokens: 680,
        percent: 32,
        truncated: true,
        parts: [
          {
            kind: "system",
            title: "System context",
            content: "Base system prompt and tool contract",
            token_estimate: 20,
            included: true,
            truncated: false,
          },
          {
            kind: "messages",
            title: "Message 1",
            content: "current question",
            token_estimate: 4,
            included: true,
            truncated: false,
          },
        ],
      },
    }),
    8000,
  );

  assert.equal(view.budget.usedTokens, 320);
  assert.equal(view.budget.maxTokens, 1000);
  assert.equal(view.budget.remainingTokens, 680);
  assert.equal(view.budget.percent, 32);

  const stateSection = view.sections.find((section) => section.kind === "state");
  const modelReport = stateSection?.items.find((item) => item.title === "Model request report");
  assert.match(modelReport?.preview || "", /Base system prompt and tool contract/);
  assert.deepEqual(modelReport?.chips, ["model_context", "truncated"]);
});

test("context window budget ignores cumulative token totals when live context fields are absent", () => {
  const view = buildContextWindowView(context({ budget: { max_tokens: 500, used_tokens: 40 } }), 1000, { input_tokens: 120, output_tokens: 30, total_tokens: 150 });

  assert.equal(view.budget.usedTokens, 40);
  assert.equal(view.budget.maxTokens, 500);
  assert.equal(view.budget.remainingTokens, 460);
  assert.equal(view.budget.percent, 8);
  assert.equal(view.hasContext, true);
});

test("context window exposes raw context manager state instead of fragment cards", () => {
  const view = buildContextWindowView(
    context({
      references: [{ kind: "file", value: "README.md" }],
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

  assert.deepEqual(view.sections.map((section) => section.kind), ["state"]);
  const managerState = view.sections[0];
  const references = managerState.items.find((item) => item.title === "References");
  const fragments = managerState.items.find((item) => item.title === "Resolved fragments");

  assert.match(references?.preview || "", /README\.md/);
  assert.match(fragments?.preview || "", /Important runtime context/);
  assert.deepEqual(fragments?.chips, ["fragments", "1"]);
});

test("context record preview can be expanded from the collapsed text", () => {
  const longText = `${"context ".repeat(80)}final visible token`;
  const view = buildContextWindowView(
    context({
      fragments: [{ id: "ctx_1", title: "large.txt", content: longText }],
    }),
    1000,
  );
  const fragment = view.sections[0].items.find((item) => item.title === "Resolved fragments");

  assert.ok(fragment);
  assert.equal(isExpandableContextRecord(fragment), true);
  assert.match(contextRecordPreview(fragment, false), /\.\.\.$/);
  assert.match(contextRecordPreview(fragment, true), /"title": "large\.txt"/);
  assert.match(contextRecordPreview(fragment, true), /final visible token/);
});
