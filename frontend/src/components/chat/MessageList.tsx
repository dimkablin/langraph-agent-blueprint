import { useEffect, useRef } from "react";

import { Spinner } from "../common/Spinner.tsx";
import { IconFileText } from "../../icons.ts";
import { MessageBubble } from "./MessageBubble.tsx";
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
      {timelineItems.map((item) =>
        item.kind === "separator" ? (
          <MessageSeparator key={item.id} item={item} />
        ) : (
          <MessageBubble key={item.message.id} message={item.message} />
        ),
      )}
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
