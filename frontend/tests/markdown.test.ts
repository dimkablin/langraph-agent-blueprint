import assert from "node:assert/strict";
import test from "node:test";

import { parseMarkdown, type MarkdownBlockNode, type MarkdownInlineNode } from "../src/components/common/markdown.ts";

function onlyBlock(markdown: string): MarkdownBlockNode {
  const blocks = parseMarkdown(markdown);
  assert.equal(blocks.length, 1);
  return blocks[0];
}

function onlyInline(markdown: string): MarkdownInlineNode {
  const block = onlyBlock(markdown);
  assert.equal(block.type, "paragraph");
  assert.equal(block.children.length, 1);
  return block.children[0];
}

test("parses common assistant markdown blocks into a renderable AST", () => {
  const blocks = parseMarkdown("## Plan\n\n- **Read** files\n- `Patch` code\n\n```ts\nconst ok = true;\n```");

  assert.deepEqual(
    blocks.map((block) => block.type),
    ["heading", "unordered_list", "code_block"],
  );
  assert.equal(blocks[0].type, "heading");
  assert.equal(blocks[0].level, 2);
  assert.equal(blocks[1].type, "unordered_list");
  assert.equal(blocks[1].items.length, 2);
  assert.equal(blocks[1].items[0][0].type, "strong");
  assert.equal(blocks[2].type, "code_block");
  assert.equal(blocks[2].language, "ts");
  assert.equal(blocks[2].code, "const ok = true;");
});

test("keeps incomplete fenced code blocks renderable while tokens are streaming", () => {
  const block = onlyBlock("```python\nprint('streaming')");

  assert.equal(block.type, "code_block");
  assert.equal(block.language, "python");
  assert.equal(block.code, "print('streaming')");
});

test("parses safe links and leaves unsafe links as text", () => {
  const safe = onlyInline("[docs](https://example.com)");
  const unsafe = onlyInline("[bad](javascript:alert(1))");

  assert.equal(safe.type, "link");
  assert.equal(safe.href, "https://example.com");
  assert.equal(unsafe.type, "text");
  assert.equal(unsafe.text, "[bad](javascript:alert(1))");
});

test("does not drop partial inline markdown while tokens are streaming", () => {
  const block = onlyBlock("Status: **generat");

  assert.equal(block.type, "paragraph");
  assert.equal(block.children.map((child) => (child.type === "text" ? child.text : child.type)).join(""), "Status: **generat");
});
