import type { ChatTimelineItem } from "./reducer.ts";

export type ChatPresentationItem =
  | {
      kind: "single";
      item: ChatTimelineItem;
    }
  | {
      kind: "assistantTurn";
      id: string;
      items: ChatTimelineItem[];
    };

export function buildChatPresentationItems(items: ChatTimelineItem[]): ChatPresentationItem[] {
  const presentationItems: ChatPresentationItem[] = [];
  let assistantTurnItems: ChatTimelineItem[] = [];

  function flushAssistantTurn() {
    if (!assistantTurnItems.length) {
      return;
    }
    if (assistantTurnItems.length === 1 && assistantTurnItems[0].kind === "message") {
      presentationItems.push({ kind: "single", item: assistantTurnItems[0] });
    } else {
      presentationItems.push({ kind: "assistantTurn", id: assistantTurnId(assistantTurnItems), items: assistantTurnItems });
    }
    assistantTurnItems = [];
  }

  for (const item of items) {
    if (isAssistantTurnItem(item)) {
      assistantTurnItems.push(item);
      continue;
    }
    flushAssistantTurn();
    presentationItems.push({ kind: "single", item });
  }

  flushAssistantTurn();
  return presentationItems;
}

export function isLastAssistantMessageInTurn(items: ChatTimelineItem[], index: number): boolean {
  const item = items[index];
  if (item?.kind !== "message" || item.message.role !== "assistant") {
    return false;
  }
  return !items.slice(index + 1).some((next) => next.kind === "message" && next.message.role === "assistant");
}

function isAssistantTurnItem(item: ChatTimelineItem): boolean {
  if (item.kind === "activity") {
    return true;
  }
  return item.kind === "message" && item.message.role === "assistant";
}

function assistantTurnId(items: ChatTimelineItem[]): string {
  const message = items.find((item) => item.kind === "message");
  if (message?.kind === "message") {
    return `assistant-turn:${message.message.id}`;
  }
  return `assistant-turn:${items[0]?.id || "activity"}`;
}
