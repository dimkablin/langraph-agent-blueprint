import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { join } from "node:path";
import test from "node:test";

const runtimeDir = join(process.cwd(), "src", "runtime");

test("stream runtime keeps legacy string heuristics out of primary reducer and timeline modules", () => {
  const primaryFiles = [
    "reducer.ts",
    "activityTimeline.ts",
    "subagentTimeline.ts",
  ];
  const forbiddenPatterns = [
    /startsWith\("tool_call/,
    /startsWith\("permission/,
    /startsWith\("skill/,
    /startsWith\("mcp/,
    /startsWith\("hook/,
    /startsWith\("context/,
    /endsWith\("_started"\)/,
    /endsWith\("_finished"\)/,
    /endsWith\("_error"\)/,
    /operation\.startsWith\("shell\./,
    /operation\.startsWith\("file\./,
    /operation\.startsWith\("search\./,
  ];

  for (const file of primaryFiles) {
    const source = readFileSync(join(runtimeDir, file), "utf8");
    for (const pattern of forbiddenPatterns) {
      assert.doesNotMatch(source, pattern, `${file} should delegate ${pattern} to legacy compatibility helpers`);
    }
  }
});
