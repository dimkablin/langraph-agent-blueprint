import assert from "node:assert/strict";
import test from "node:test";

import {
  DEFAULT_MODEL_INTELLIGENCE_LEVEL,
  MODEL_INTELLIGENCE_OPTIONS,
  modelIntelligenceOptionById,
} from "../src/runtime/modelIntelligence.ts";

test("model intelligence options keep the expected order and default", () => {
  assert.equal(DEFAULT_MODEL_INTELLIGENCE_LEVEL, "medium");
  assert.deepEqual(
    MODEL_INTELLIGENCE_OPTIONS.map((option) => option.id),
    ["low", "medium", "high", "very_high"],
  );
  assert.equal(modelIntelligenceOptionById(DEFAULT_MODEL_INTELLIGENCE_LEVEL).label, "Средний");
  assert.equal(modelIntelligenceOptionById("very_high").label, "Очень высокий");
});
