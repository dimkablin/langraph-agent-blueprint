import { Bot } from "lucide-react";

import { Spinner } from "../common/Spinner.tsx";
import { MessageBubble } from "./MessageBubble.tsx";
import type { ChatMessage } from "../../runtime/reducer.ts";

export function MessageList({ messages, isStreaming }: { messages: ChatMessage[]; isStreaming: boolean }) {
  if (!messages.length && !isStreaming) {
    return (
      <div className="empty-chat">
        <div className="empty-icon">
          <Bot size={24} />
        </div>
        <strong>Runtime ready</strong>
        <span>Ask a question, use a slash command, or attach context with @README.md.</span>
      </div>
    );
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
    </div>
  );
}

