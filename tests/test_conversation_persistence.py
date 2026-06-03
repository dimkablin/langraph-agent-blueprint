from __future__ import annotations

from langgraph_agent_blueprint.models.conversations import ConversationCreate, MessageCreate, StreamEventCreate
from langgraph_agent_blueprint.services.conversation_service import ConversationAccessError, ConversationService
from langgraph_agent_blueprint.storage.conversation_storage import SQLiteConversationStorage


def service_at(tmp_path):
    return ConversationService(SQLiteConversationStorage(tmp_path / "history.sqlite3"))


def test_conversations_are_durable_and_scoped_by_user(tmp_path):
    service = service_at(tmp_path)
    created = service.create_conversation(
        "user-a",
        ConversationCreate(title="First chat", project_id="project-1"),
    )
    service.append_turn(
        "user-a",
        created.conversation_id,
        user_message=MessageCreate(role="user", content="hello", idempotency_key="turn-1:user"),
        assistant_message=MessageCreate(role="assistant", content="hi", idempotency_key="turn-1:assistant"),
        events=[StreamEventCreate(event_id="event-1", type="final", payload={"ok": True})],
    )

    reloaded = service_at(tmp_path)

    assert [item.conversation_id for item in reloaded.list_conversations("user-a")] == [created.conversation_id]
    assert reloaded.list_conversations("user-b") == []
    detail = reloaded.get_conversation("user-a", created.conversation_id)
    assert detail.conversation.title == "First chat"
    assert detail.conversation.thread_id == created.conversation_id
    assert [message.role for message in detail.messages] == ["user", "assistant"]
    assert [event.event_id for event in detail.events] == ["event-1"]


def test_conversation_ownership_is_enforced_for_mutations(tmp_path):
    service = service_at(tmp_path)
    created = service.create_conversation("user-a", ConversationCreate(title="Private"))

    for operation in [
        lambda: service.get_conversation("user-b", created.conversation_id),
        lambda: service.rename_conversation("user-b", created.conversation_id, "stolen"),
        lambda: service.archive_conversation("user-b", created.conversation_id),
        lambda: service.soft_delete_conversation("user-b", created.conversation_id),
        lambda: service.append_turn(
            "user-b",
            created.conversation_id,
            user_message=MessageCreate(role="user", content="steal"),
        ),
    ]:
        try:
            operation()
        except ConversationAccessError:
            pass
        else:
            raise AssertionError("expected cross-user operation to fail")

    assert service.get_conversation("user-a", created.conversation_id).conversation.title == "Private"


def test_append_turn_is_idempotent_for_messages_and_events(tmp_path):
    service = service_at(tmp_path)
    created = service.create_conversation("user-a", ConversationCreate(title="Retry"))

    for _ in range(2):
        service.append_turn(
            "user-a",
            created.conversation_id,
            user_message=MessageCreate(role="user", content="same", idempotency_key="turn-1:user"),
            assistant_message=MessageCreate(role="assistant", content="same answer", idempotency_key="turn-1:assistant"),
            events=[StreamEventCreate(event_id="event-1", type="progress", payload={"step": 1})],
        )

    detail = service.get_conversation("user-a", created.conversation_id)
    assert [(message.role, message.content) for message in detail.messages] == [
        ("user", "same"),
        ("assistant", "same answer"),
    ]
    assert [event.event_id for event in detail.events] == ["event-1"]
    metrics = service.storage.metrics_snapshot()
    assert metrics.write_count > 0
    assert metrics.last_write_latency_ms >= 0


def test_archive_soft_delete_and_search_hide_deleted_conversations(tmp_path):
    service = service_at(tmp_path)
    keep = service.create_conversation("user-a", ConversationCreate(title="Keep Python"))
    archived = service.create_conversation("user-a", ConversationCreate(title="Archive Python"))
    deleted = service.create_conversation("user-a", ConversationCreate(title="Delete Python"))

    service.archive_conversation("user-a", archived.conversation_id)
    service.soft_delete_conversation("user-a", deleted.conversation_id)

    visible = service.list_conversations("user-a")
    assert {item.conversation_id for item in visible} == {keep.conversation_id}
    assert {item.conversation_id for item in service.list_conversations("user-a", include_archived=True)} == {
        keep.conversation_id,
        archived.conversation_id,
    }
    assert [item.conversation_id for item in service.search_conversations("user-a", "python", include_archived=True)] == [
        archived.conversation_id,
        keep.conversation_id,
    ]
    try:
        service.get_conversation("user-a", deleted.conversation_id)
    except ConversationAccessError:
        pass
    else:
        raise AssertionError("expected deleted conversation to be hidden")
