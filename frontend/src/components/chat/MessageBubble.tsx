import { Bot, User } from "lucide-react";

import { MarkdownBlock } from "../common/MarkdownBlock.tsx";
import type { ChatMessage } from "../../runtime/reducer.ts";

export function MessageBubble({ message }: { message: ChatMessage }) {
  const isUser = message.role === "user";
  return (
    <article className={isUser ? "message-row message-row-user" : "message-row"}>
      <div className={isUser ? "avatar avatar-user" : "avatar avatar-assistant"}>
        {isUser ? <User size={15} /> : <Bot size={15} />}
      </div>
      <div className={isUser ? "message-card message-card-user" : "message-card"}>
        <MarkdownBlock content={message.content} inverted={isUser} />
        <time>{formatTime(message.timestamp)}</time>
      </div>
    </article>
  );
}

function formatTime(timestamp: string): string {
  const date = new Date(timestamp);
  if (Number.isNaN(date.getTime())) return "";
  return new Intl.DateTimeFormat(undefined, { hour: "2-digit", minute: "2-digit" }).format(date);
}

