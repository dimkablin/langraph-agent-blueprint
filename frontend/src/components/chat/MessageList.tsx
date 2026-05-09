import { useEffect, useRef } from "react";

import { Spinner } from "../common/Spinner.tsx";
import { MessageBubble } from "./MessageBubble.tsx";
import type { ChatMessage } from "../../runtime/reducer.ts";

export function MessageList({ messages, isStreaming, autoScroll = true }: { messages: ChatMessage[]; isStreaming: boolean; autoScroll?: boolean }) {
  const endRef = useRef<HTMLDivElement | null>(null);

  useEffect(() => {
    if (autoScroll) {
      endRef.current?.scrollIntoView({ block: "end" });
    }
  }, [autoScroll, isStreaming, messages.length]);

  if (!messages.length && !isStreaming) {
    return null;
  }

  return (
    <div className="message-list">
      {messages.map((message) => (
        <MessageBubble key={message.id} message={message} />
      ))}
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
