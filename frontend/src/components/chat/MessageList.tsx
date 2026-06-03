import { useEffect, useRef } from "react";

import { Spinner } from "../common/Spinner.tsx";
import { EventTimeline } from "../events/EventTimeline.tsx";
import { IconFileText } from "../../icons.ts";
import { MessageBubble } from "./MessageBubble.tsx";
import { buildChatPresentationItems, isLastAssistantMessageInTurn } from "../../runtime/turnPresentation.ts";
import type { ChatMessage, ChatTimelineItem } from "../../runtime/reducer.ts";

export function MessageList({
  messages,
  items,
  isStreaming,
  autoScroll = true,
}: {
  messages: ChatMessage[];
  items?: ChatTimelineItem[];
  isStreaming: boolean;
  autoScroll?: boolean;
}) {
  const endRef = useRef<HTMLDivElement | null>(null);
  const timelineItems: ChatTimelineItem[] = items ?? messages.map((message) => ({ kind: "message", message }));
  const presentationItems = buildChatPresentationItems(timelineItems);
  const activeMessageId = isStreaming ? latestAssistantMessageId(timelineItems) : undefined;

  useEffect(() => {
    if (autoScroll) {
      endRef.current?.scrollIntoView({ block: "end" });
    }
  }, [autoScroll, isStreaming, timelineItems.length]);

  if (!timelineItems.length && !isStreaming) {
    return null;
  }

  return (
    <div className="message-list">
      {presentationItems.map((item) => item.kind === "assistantTurn" ? (
        <section className="assistant-turn" key={item.id}>
          {item.items.map((turnItem, index) => renderTimelineItem(turnItem, {
            activeMessageId,
            forceHideAssistantMeta: !isLastAssistantMessageInTurn(item.items, index),
            isStreaming,
          }))}
        </section>
      ) : renderTimelineItem(item.item, { activeMessageId, forceHideAssistantMeta: false, isStreaming }))}
      {isStreaming ? (
        <div className="streaming-row">
          <Spinner />
          <span>Graph is running...</span>
        </div>
      ) : null}
      <div ref={endRef} aria-hidden="true" />
    </div>
  );
}

function renderTimelineItem(
  item: ChatTimelineItem,
  options: { activeMessageId?: string; forceHideAssistantMeta: boolean; isStreaming: boolean },
) {
  if (item.kind === "separator") {
    return <MessageSeparator key={item.id} item={item} />;
  }
  if (item.kind === "activity") {
    const activeActivity = options.isStreaming && (!item.messageId || item.messageId === options.activeMessageId || hasRunningActivity(item));
    return (
      <EventTimeline
        key={item.id}
        activities={item.activities}
        variant="inline"
        compactCommands={!activeActivity}
      />
    );
  }
  const hideMeta = options.isStreaming || (item.message.role === "assistant" && options.forceHideAssistantMeta);
  return <MessageBubble key={item.message.id} hideMeta={hideMeta} message={item.message} />;
}

function hasRunningActivity(item: Extract<ChatTimelineItem, { kind: "activity" }>): boolean {
  return item.activities.some((activity) => activity.status === "running" || activity.status === "pending");
}

function latestAssistantMessageId(items: ChatTimelineItem[]): string | undefined {
  for (let index = items.length - 1; index >= 0; index -= 1) {
    const item = items[index];
    if (item.kind === "message" && item.message.role === "assistant") {
      return item.message.id;
    }
  }
  return undefined;
}

function MessageSeparator({ item }: { item: Extract<ChatTimelineItem, { kind: "separator" }> }) {
  const className = item.status === "running" ? "message-separator message-separator-running" : "message-separator";
  return (
    <div className={className} role="status" aria-label={item.label}>
      <span className="message-separator-label">
        <IconFileText size={14} />
        {item.label}
      </span>
    </div>
  );
}
