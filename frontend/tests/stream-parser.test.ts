import assert from "node:assert/strict";
import test from "node:test";

import { parseSseFramesFromText } from "../src/api/stream.ts";

test("parses event, done, and error StreamFrame payloads from SSE text", () => {
  const text = [
    'event: runtime_event\ndata: {"type":"event","event":{"id":"event_1","type":"final_response","timestamp":"2026-05-08T00:00:00Z","session_id":"session_1","severity":"info","data":{"content":"ok"}}}',
    'event: done\ndata: {"type":"done","session_id":"session_1","final_response":"ok"}',
    'event: error\ndata: {"type":"error","error":"boom"}',
    "",
  ].join("\n\n");

  const frames = parseSseFramesFromText(text);

  assert.equal(frames.length, 3);
  assert.equal(frames[0].type, "event");
  assert.equal(frames[0].event.type, "final_response");
  assert.equal(frames[1].type, "done");
  assert.equal(frames[1].session_id, "session_1");
  assert.equal(frames[2].type, "error");
  assert.equal(frames[2].error, "boom");
});

test("buffers partial SSE frames across chunks", () => {
  const parser = parseSseFramesFromText.createBufferedParser();

  assert.deepEqual(parser.push('event: runtime_event\ndata: {"type":"event","event":'), []);
  const frames = parser.push('{"id":"event_2","type":"tool_call_started","timestamp":"2026-05-08T00:00:00Z","session_id":"session_1","severity":"info","data":{"name":"read_file"}}}\n\n');

  assert.equal(frames.length, 1);
  assert.equal(frames[0].type, "event");
  assert.equal(frames[0].event.type, "tool_call_started");
  assert.equal(frames[0].event.data.name, "read_file");
});

