import assert from "node:assert/strict";
import test from "node:test";

import { formatSessionTime } from "../src/runtime/sessionTime.ts";

const NOW = new Date("2026-05-09T12:00:00.000Z");

test("sidebar chat timestamps use one relative unit", () => {
  assert.equal(formatSessionTime("2026-05-09T11:55:00.000Z", NOW), "5м");
  assert.equal(formatSessionTime("2026-05-09T10:00:00.000Z", NOW), "2ч");
  assert.equal(formatSessionTime("2026-05-07T12:00:00.000Z", NOW), "2д");
  assert.equal(formatSessionTime("2026-04-25T12:00:00.000Z", NOW), "2н");
});

test("sidebar chat timestamps tolerate missing or invalid values", () => {
  assert.equal(formatSessionTime(null, NOW), "");
  assert.equal(formatSessionTime(undefined, NOW), "");
  assert.equal(formatSessionTime("not-a-date", NOW), "");
  assert.equal(formatSessionTime("2026-05-09T12:00:30.000Z", NOW), "1м");
});
