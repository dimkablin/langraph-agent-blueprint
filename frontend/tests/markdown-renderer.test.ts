import assert from "node:assert/strict";
import test from "node:test";
import { fileURLToPath } from "node:url";

import React from "react";
import { renderToStaticMarkup } from "react-dom/server";
import { createServer, type ViteDevServer } from "vite";

type MarkdownBlockComponent = React.ComponentType<{ content: string; inverted?: boolean }>;

const frontendRoot = fileURLToPath(new URL("..", import.meta.url));
let viteServer: ViteDevServer | null = null;
let MarkdownBlock: MarkdownBlockComponent | null = null;

test.after(async () => {
  await viteServer?.close();
});

async function renderMarkdown(content: string): Promise<string> {
  if (!viteServer) {
    viteServer = await createServer({
      appType: "custom",
      logLevel: "error",
      root: frontendRoot,
      server: { middlewareMode: true },
    });
  }
  if (!MarkdownBlock) {
    const module = (await viteServer.ssrLoadModule("/src/components/common/MarkdownBlock.tsx")) as {
      MarkdownBlock: MarkdownBlockComponent;
    };
    MarkdownBlock = module.MarkdownBlock;
  }
  return renderToStaticMarkup(React.createElement(MarkdownBlock, { content }));
}

test("renders GitHub-flavored markdown emitted by assistant responses", async () => {
  const html = await renderMarkdown("https://example.com\n\n~~removed~~\n\n- [x] done\n- [ ] todo");

  assert.match(html, /<a href="https:\/\/example\.com"[^>]*>https:\/\/example\.com<\/a>/);
  assert.match(html, /<del>removed<\/del>/);
  assert.match(html, /<input[^>]+type="checkbox"[^>]+checked/);
  assert.match(html, /<input[^>]+type="checkbox"[^>]+disabled/);
});

test("renders assistant tables, horizontal rules, and fenced code blocks", async () => {
  const html = await renderMarkdown(
    "| date | actual | planned |\n|---|---:|---:|\n| 2023-01-01 | 29,662 | `27,199` |\n\n---\n\n```json\n{\"limit\": 10}\n```",
  );

  assert.match(html, /<div class="markdown-table-scroll"><table>/);
  assert.match(html, /<th[^>]*>date<\/th>/);
  assert.match(html, /<td[^>]*>2023-01-01<\/td>/);
  assert.match(html, /<td[^>]*><code>27,199<\/code><\/td>/);
  assert.match(html, /<hr\/>/);
  assert.match(html, /<pre><code class="language-json">/);
  assert.match(html, /&quot;limit&quot;: 10/);
});

test("does not render raw HTML or unsafe markdown links into the chat DOM", async () => {
  const html = await renderMarkdown("<script>alert('xss')</script>\n\n[bad](javascript:alert(1))");

  assert.doesNotMatch(html, /<script/i);
  assert.doesNotMatch(html, /javascript:alert/i);
});
