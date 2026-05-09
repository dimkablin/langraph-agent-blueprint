import { useState } from "react";

import { MarkdownBlock } from "../common/MarkdownBlock.tsx";
import { IconCheck, IconCopy } from "../../icons.ts";
import type { ChatMessage } from "../../runtime/reducer.ts";

export function MessageBubble({ message }: { message: ChatMessage }) {
  const isUser = message.role === "user";
  return (
    <article className={isUser ? "message-row message-row-user" : "message-row"}>
      <div className={isUser ? "message-card message-card-user" : "message-card"}>
        <MarkdownBlock content={message.content} inverted={isUser} />
      </div>
      <MessageMeta align={isUser ? "user" : "assistant"} content={message.content} timestamp={message.timestamp} />
    </article>
  );
}

function MessageMeta({ align, content, timestamp }: { align: "assistant" | "user"; content: string; timestamp: string }) {
  const [copied, setCopied] = useState(false);
  const time = formatTime(timestamp);
  const canCopy = Boolean(content.trim());

  async function copyMessage() {
    if (!canCopy || !navigator.clipboard) return;
    try {
      await navigator.clipboard.writeText(content);
      setCopied(true);
      window.setTimeout(() => setCopied(false), 1400);
    } catch {
      setCopied(false);
    }
  }

  return (
    <div className={align === "user" ? "message-meta message-meta-user" : "message-meta message-meta-assistant"}>
      <time dateTime={timestamp}>{time}</time>
      <button
        type="button"
        className="message-copy-button"
        onClick={() => void copyMessage()}
        disabled={!canCopy}
        aria-label="Copy message"
        data-tooltip={copied ? "Скопировано" : "Копировать"}
        data-tooltip-placement="top"
        data-tooltip-align={align === "user" ? "end" : "start"}
      >
        {copied ? <IconCheck size={16} /> : <IconCopy size={16} />}
      </button>
    </div>
  );
}

function formatTime(timestamp: string): string {
  const date = new Date(timestamp);
  if (Number.isNaN(date.getTime())) return "";
  return new Intl.DateTimeFormat(undefined, { hour: "2-digit", minute: "2-digit" }).format(date);
}
