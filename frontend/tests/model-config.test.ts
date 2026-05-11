import assert from "node:assert/strict";
import test from "node:test";

import { effectiveModelName } from "../src/runtime/modelConfig.ts";

test("effective model name prefers provider specific model values", () => {
  assert.equal(
    effectiveModelName({
      values: {
        llm_provider: "openai",
        model_name: "fallback-model",
        openai_model: "gpt-4.1",
      },
    }),
    "gpt-4.1",
  );
  assert.equal(
    effectiveModelName({
      values: {
        llm_provider: "anthropic",
        model_name: "fallback-model",
        anthropic_model: "claude-3-5-sonnet",
      },
    }),
    "claude-3-5-sonnet",
  );
});

test("effective model name falls back to configured model_name", () => {
  assert.equal(
    effectiveModelName({
      values: {
        llm_provider: "openai_compatible",
        model_name: "local-default",
      },
    }),
    "local-default",
  );
  assert.equal(effectiveModelName(null), "unknown");
});
