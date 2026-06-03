import assert from "node:assert/strict";
import test from "node:test";

import { buildChatPresentationItems, isLastAssistantMessageInTurn } from "../src/runtime/turnPresentation.ts";
import type { ChatMessage, ChatTimelineItem } from "../src/runtime/reducer.ts";

function message(id: string, role: ChatMessage["role"], content: string): ChatTimelineItem {
  return {
    kind: "message",
    message: {
      id,
      role,
      content,
      timestamp: "2026-05-09T00:00:00Z",
    },
  };
}

function activity(id: string): ChatTimelineItem {
  return {
    kind: "activity",
    id,
    timestamp: "2026-05-09T00:00:01Z",
    activities: [
      {
        id: `${id}_item`,
        kind: "tool",
        label: "tool.write_file.completed",
        summary: "Contract written.",
        status: "success",
        timestamp: "2026-05-09T00:00:01Z",
        eventType: "tool.write_file.completed",
        category: "tool",
        data: { tool_call_id: id, operation: "file.write", path: "common/CONTRACT.md" },
      },
    ],
  };
}

test("presentation groups assistant ReAct chunks and activities into one assistant turn", () => {
  const items = [
    message("user_1", "user", "Create frontend and backend agents."),
    message("assistant_contract", "assistant", "First I will update the contract."),
    activity("activity_contract"),
    message("assistant_launch", "assistant", "Contract updated. Now launch two subagents."),
    activity("activity_subagents"),
    message("assistant_final", "assistant", "Done."),
  ];

  const presentation = buildChatPresentationItems(items);

  assert.equal(presentation.length, 2);
  assert.equal(presentation[0].kind, "single");
  assert.equal(presentation[1].kind, "assistantTurn");
  if (presentation[1].kind === "assistantTurn") {
    assert.deepEqual(
      presentation[1].items.map((item) => item.kind === "message" ? item.message.id : item.id),
      ["assistant_contract", "activity_contract", "assistant_launch", "activity_subagents", "assistant_final"],
    );
    assert.equal(isLastAssistantMessageInTurn(presentation[1].items, 0), false);
    assert.equal(isLastAssistantMessageInTurn(presentation[1].items, 2), false);
    assert.equal(isLastAssistantMessageInTurn(presentation[1].items, 4), true);
  }
});

test("single assistant message without activity remains a normal message item", () => {
  const presentation = buildChatPresentationItems([
    message("user_1", "user", "Hello"),
    message("assistant_1", "assistant", "Hi"),
  ]);

  assert.deepEqual(presentation.map((item) => item.kind), ["single", "single"]);
});
