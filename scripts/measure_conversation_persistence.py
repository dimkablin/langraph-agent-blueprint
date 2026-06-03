"""Smoke benchmark for durable multi-user conversation persistence.

Run from the repository root:

    python scripts/measure_conversation_persistence.py

The benchmark uses the local SQLite implementation through the public
ConversationService boundary. It simulates 100 users with multiple conversations,
records storage call deltas, and reports local wall-clock latencies. Treat the
numbers as smoke evidence for regressions rather than universal performance
claims.
"""

from __future__ import annotations

import json
import statistics
import tempfile
import time
from pathlib import Path
from typing import Any, Callable

from langgraph_agent_blueprint.models.conversations import ConversationCreate, MessageCreate, StreamEventCreate, ToolCallCreate
from langgraph_agent_blueprint.services.conversation_service import ConversationService
from langgraph_agent_blueprint.storage.conversation_storage import SQLiteConversationStorage

USER_COUNT = 100
CONVERSATIONS_PER_USER = 2
TURNS_PER_CONVERSATION = 2


def main() -> None:
    with tempfile.TemporaryDirectory(prefix="lg-agent-conversation-bench-") as tmp:
        db_path = Path(tmp) / "conversations.sqlite3"
        service = ConversationService(SQLiteConversationStorage(db_path))

        create_latencies_ms: list[float] = []
        append_latencies_ms: list[float] = []
        list_latencies_ms: list[float] = []
        get_latencies_ms: list[float] = []
        write_deltas: list[int] = []
        read_deltas: list[int] = []
        conversation_ids: list[tuple[str, str]] = []

        for user_index in range(USER_COUNT):
            user_id = f"user-{user_index:03d}"
            for conversation_index in range(CONVERSATIONS_PER_USER):
                create_latency, conversation = _measure_ms(
                    lambda user_id=user_id, conversation_index=conversation_index: service.create_conversation(
                        user_id,
                        ConversationCreate(title=f"Benchmark chat {conversation_index}", project_id="benchmark"),
                    )
                )
                create_latencies_ms.append(create_latency)
                conversation_ids.append((user_id, conversation.conversation_id))

                for turn_index in range(TURNS_PER_CONVERSATION):
                    before = service.storage.metrics_snapshot()
                    append_latency, _ = _measure_ms(
                        lambda user_id=user_id, conversation_id=conversation.conversation_id, turn_index=turn_index: service.append_turn(
                            user_id,
                            conversation_id,
                            user_message=MessageCreate(
                                role="user",
                                content=f"hello from {user_id} turn {turn_index}",
                                idempotency_key=f"{conversation.conversation_id}:turn-{turn_index}:user",
                            ),
                            assistant_message=MessageCreate(
                                role="assistant",
                                content=f"answer for {user_id} turn {turn_index}",
                                idempotency_key=f"{conversation.conversation_id}:turn-{turn_index}:assistant",
                            ),
                            events=[
                                StreamEventCreate(
                                    event_id=f"{conversation.conversation_id}-event-{turn_index}",
                                    type="final_response",
                                    payload={"content": f"answer for {user_id} turn {turn_index}"},
                                )
                            ],
                            tool_calls=[
                                ToolCallCreate(
                                    tool_call_id=f"{conversation.conversation_id}-tool-{turn_index}",
                                    name="benchmark_tool",
                                    status="completed",
                                    input={"api_key": "should-be-redacted", "turn": turn_index},
                                    output={"ok": True},
                                    idempotency_key=f"{conversation.conversation_id}:turn-{turn_index}:tool",
                                )
                            ],
                        )
                    )
                    after = service.storage.metrics_snapshot()
                    append_latencies_ms.append(append_latency)
                    write_deltas.append(after.write_count - before.write_count)
                    read_deltas.append(after.read_count - before.read_count)

        for user_id, conversation_id in conversation_ids[:: max(1, len(conversation_ids) // USER_COUNT)]:
            list_latency, rows = _measure_ms(lambda user_id=user_id: service.list_conversations(user_id))
            get_latency, detail = _measure_ms(lambda user_id=user_id, conversation_id=conversation_id: service.get_conversation(user_id, conversation_id))
            list_latencies_ms.append(list_latency)
            get_latencies_ms.append(get_latency)
            assert rows, "user conversation list should not be empty"
            assert detail.messages, "conversation detail should include persisted messages"

        metrics = service.storage.metrics_snapshot()

    result = {
        "users": USER_COUNT,
        "conversations_per_user": CONVERSATIONS_PER_USER,
        "turns_per_conversation": TURNS_PER_CONVERSATION,
        "total_conversations": USER_COUNT * CONVERSATIONS_PER_USER,
        "total_turns": USER_COUNT * CONVERSATIONS_PER_USER * TURNS_PER_CONVERSATION,
        "storage_reads_total": metrics.read_count,
        "storage_writes_total": metrics.write_count,
        "writes_per_append_turn_p50": _percentile(write_deltas, 50),
        "writes_per_append_turn_p95": _percentile(write_deltas, 95),
        "reads_per_append_turn_p50": _percentile(read_deltas, 50),
        "reads_per_append_turn_p95": _percentile(read_deltas, 95),
        "create_latency_ms": _summary(create_latencies_ms),
        "append_turn_latency_ms": _summary(append_latencies_ms),
        "list_latency_ms": _summary(list_latencies_ms),
        "get_latency_ms": _summary(get_latencies_ms),
    }
    print(json.dumps(result, indent=2, sort_keys=True))


def _measure_ms(callback: Callable[[], Any]) -> tuple[float, Any]:
    start = time.perf_counter()
    value = callback()
    return (time.perf_counter() - start) * 1000, value


def _summary(values: list[float]) -> dict[str, float]:
    return {
        "min": round(min(values), 3),
        "p50": round(_percentile(values, 50), 3),
        "p95": round(_percentile(values, 95), 3),
        "max": round(max(values), 3),
        "mean": round(statistics.fmean(values), 3),
    }


def _percentile(values: list[float] | list[int], percentile: int) -> float:
    ordered = sorted(float(value) for value in values)
    if not ordered:
        return 0.0
    index = round((len(ordered) - 1) * (percentile / 100))
    return ordered[index]


if __name__ == "__main__":
    main()
