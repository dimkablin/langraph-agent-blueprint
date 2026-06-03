import { apiUrl, ApiError, userScopedHeaders } from "./client.ts";
import type { ChatRequest, StreamFrame } from "./schemas.ts";

export type StreamHandlers = {
  onFrame: (frame: StreamFrame) => void;
  signal?: AbortSignal;
};

type BufferedSseParser = {
  push: (chunk: string) => StreamFrame[];
  flush: () => StreamFrame[];
};

export function parseSseFramesFromText(text: string): StreamFrame[] {
  return parseCompleteBlocks(text);
}

parseSseFramesFromText.createBufferedParser = function createBufferedParser(): BufferedSseParser {
  let buffer = "";
  return {
    push(chunk: string): StreamFrame[] {
      buffer += chunk;
      const boundary = lastFrameBoundary(buffer);
      if (boundary < 0) {
        return [];
      }
      const complete = buffer.slice(0, boundary);
      buffer = buffer.slice(boundary);
      return parseCompleteBlocks(complete);
    },
    flush(): StreamFrame[] {
      const frames = parseCompleteBlocks(buffer);
      buffer = "";
      return frames;
    },
  };
};

export async function streamChat(request: ChatRequest, handlers: StreamHandlers): Promise<void> {
  const response = await fetch(apiUrl("/chat/stream"), {
    method: "POST",
    headers: userScopedHeaders(),
    body: JSON.stringify(request),
    signal: handlers.signal,
  });
  if (!response.ok) {
    const body = await response.text();
    throw new ApiError(response.status, response.statusText, body);
  }
  if (!response.body) {
    throw new Error("Streaming response body is unavailable.");
  }
  const decoder = new TextDecoder("utf-8");
  const parser = parseSseFramesFromText.createBufferedParser();
  const reader = response.body.getReader();
  while (true) {
    const { value, done } = await reader.read();
    if (done) {
      break;
    }
    const text = decoder.decode(value, { stream: true });
    for (const frame of parser.push(text)) {
      handlers.onFrame(frame);
    }
  }
  const tail = decoder.decode();
  for (const frame of parser.push(tail)) {
    handlers.onFrame(frame);
  }
  for (const frame of parser.flush()) {
    handlers.onFrame(frame);
  }
}

function parseCompleteBlocks(text: string): StreamFrame[] {
  return text
    .split(/\r?\n\r?\n/)
    .map((block) => block.trim())
    .filter(Boolean)
    .map(parseBlock)
    .filter((frame): frame is StreamFrame => frame !== null);
}

function parseBlock(block: string): StreamFrame | null {
  const data = block
    .split(/\r?\n/)
    .filter((line) => line.startsWith("data:"))
    .map((line) => line.slice("data:".length).trimStart())
    .join("\n");
  if (!data) {
    return null;
  }
  return JSON.parse(data) as StreamFrame;
}

function lastFrameBoundary(text: string): number {
  const lf = text.lastIndexOf("\n\n");
  const crlf = text.lastIndexOf("\r\n\r\n");
  if (lf < 0 && crlf < 0) {
    return -1;
  }
  if (crlf > lf) {
    return crlf + 4;
  }
  return lf + 2;
}
