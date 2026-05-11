export type MarkdownInlineNode =
  | { type: "text"; text: string }
  | { type: "strong"; children: MarkdownInlineNode[] }
  | { type: "emphasis"; children: MarkdownInlineNode[] }
  | { type: "inline_code"; code: string }
  | { type: "link"; href: string; children: MarkdownInlineNode[] };

export type MarkdownBlockNode =
  | { type: "paragraph"; children: MarkdownInlineNode[] }
  | { type: "heading"; level: 1 | 2 | 3 | 4 | 5 | 6; children: MarkdownInlineNode[] }
  | { type: "unordered_list"; items: MarkdownInlineNode[][] }
  | { type: "ordered_list"; start: number; items: MarkdownInlineNode[][] }
  | { type: "blockquote"; children: MarkdownInlineNode[] }
  | { type: "code_block"; language: string | null; code: string };

const FENCE_PATTERN = /^```([A-Za-z0-9_-]+)?\s*$/;
const HEADING_PATTERN = /^(#{1,6})\s+(.+)$/;
const UNORDERED_ITEM_PATTERN = /^\s*[-*]\s+(.+)$/;
const ORDERED_ITEM_PATTERN = /^\s*(\d+)[.)]\s+(.+)$/;
const BLOCKQUOTE_PATTERN = /^\s*>\s?(.*)$/;

export function parseMarkdown(markdown: string): MarkdownBlockNode[] {
  const lines = markdown.replace(/\r\n?/g, "\n").split("\n");
  const blocks: MarkdownBlockNode[] = [];
  let index = 0;

  while (index < lines.length) {
    const line = lines[index];
    if (isBlank(line)) {
      index += 1;
      continue;
    }

    const fence = line.match(FENCE_PATTERN);
    if (fence) {
      const [block, nextIndex] = parseCodeBlock(lines, index, fence[1] || null);
      blocks.push(block);
      index = nextIndex;
      continue;
    }

    const heading = line.match(HEADING_PATTERN);
    if (heading) {
      const level = heading[1].length as 1 | 2 | 3 | 4 | 5 | 6;
      blocks.push({
        type: "heading",
        level,
        children: parseMarkdownInline(heading[2].trim()),
      });
      index += 1;
      continue;
    }

    if (UNORDERED_ITEM_PATTERN.test(line)) {
      const [block, nextIndex] = parseList(lines, index, "unordered");
      blocks.push(block);
      index = nextIndex;
      continue;
    }

    if (ORDERED_ITEM_PATTERN.test(line)) {
      const [block, nextIndex] = parseList(lines, index, "ordered");
      blocks.push(block);
      index = nextIndex;
      continue;
    }

    if (BLOCKQUOTE_PATTERN.test(line)) {
      const [block, nextIndex] = parseBlockquote(lines, index);
      blocks.push(block);
      index = nextIndex;
      continue;
    }

    const [block, nextIndex] = parseParagraph(lines, index);
    blocks.push(block);
    index = nextIndex;
  }

  return blocks;
}

export function parseMarkdownInline(text: string): MarkdownInlineNode[] {
  const nodes: MarkdownInlineNode[] = [];
  let index = 0;

  while (index < text.length) {
    if (text.startsWith("`", index)) {
      const closeIndex = text.indexOf("`", index + 1);
      if (closeIndex > index + 1) {
        nodes.push({ type: "inline_code", code: text.slice(index + 1, closeIndex) });
        index = closeIndex + 1;
        continue;
      }
      pushText(nodes, text.slice(index));
      break;
    }

    if (text.startsWith("**", index) || text.startsWith("__", index)) {
      const marker = text.slice(index, index + 2);
      const closeIndex = text.indexOf(marker, index + 2);
      if (closeIndex > index + 2) {
        nodes.push({ type: "strong", children: parseMarkdownInline(text.slice(index + 2, closeIndex)) });
        index = closeIndex + 2;
        continue;
      }
      pushText(nodes, text.slice(index));
      break;
    }

    if (text.startsWith("[", index)) {
      const link = parseLink(text, index);
      if (link) {
        nodes.push(link.node);
        index = link.nextIndex;
        continue;
      }
    }

    if (text[index] === "*" || text[index] === "_") {
      const marker = text[index];
      const closeIndex = text.indexOf(marker, index + 1);
      if (closeIndex > index + 1) {
        nodes.push({ type: "emphasis", children: parseMarkdownInline(text.slice(index + 1, closeIndex)) });
        index = closeIndex + 1;
        continue;
      }
      pushText(nodes, text.slice(index));
      break;
    }

    pushText(nodes, text[index]);
    index += 1;
  }

  return nodes;
}

function parseCodeBlock(lines: string[], startIndex: number, language: string | null): [MarkdownBlockNode, number] {
  const codeLines: string[] = [];
  let index = startIndex + 1;
  while (index < lines.length) {
    if (FENCE_PATTERN.test(lines[index])) {
      return [{ type: "code_block", language, code: codeLines.join("\n") }, index + 1];
    }
    codeLines.push(lines[index]);
    index += 1;
  }
  return [{ type: "code_block", language, code: codeLines.join("\n") }, index];
}

function parseList(lines: string[], startIndex: number, kind: "unordered" | "ordered"): [MarkdownBlockNode, number] {
  const items: MarkdownInlineNode[][] = [];
  const firstOrdered = lines[startIndex].match(ORDERED_ITEM_PATTERN);
  let index = startIndex;

  while (index < lines.length) {
    const match = kind === "unordered" ? lines[index].match(UNORDERED_ITEM_PATTERN) : lines[index].match(ORDERED_ITEM_PATTERN);
    if (!match) break;
    const text = kind === "unordered" ? match[1] : match[2];
    items.push(parseMarkdownInline(text.trim()));
    index += 1;
  }

  if (kind === "ordered") {
    return [{ type: "ordered_list", start: Number(firstOrdered?.[1] || 1), items }, index];
  }
  return [{ type: "unordered_list", items }, index];
}

function parseBlockquote(lines: string[], startIndex: number): [MarkdownBlockNode, number] {
  const quoteLines: string[] = [];
  let index = startIndex;
  while (index < lines.length) {
    const match = lines[index].match(BLOCKQUOTE_PATTERN);
    if (!match) break;
    quoteLines.push(match[1]);
    index += 1;
  }
  return [{ type: "blockquote", children: parseMarkdownInline(quoteLines.join("\n")) }, index];
}

function parseParagraph(lines: string[], startIndex: number): [MarkdownBlockNode, number] {
  const paragraphLines: string[] = [];
  let index = startIndex;
  while (index < lines.length && !isBlank(lines[index]) && !startsBlock(lines[index])) {
    paragraphLines.push(lines[index]);
    index += 1;
  }
  return [{ type: "paragraph", children: parseMarkdownInline(paragraphLines.join("\n")) }, index];
}

function parseLink(text: string, startIndex: number): { node: MarkdownInlineNode; nextIndex: number } | null {
  const labelEnd = text.indexOf("]", startIndex + 1);
  if (labelEnd <= startIndex + 1 || text[labelEnd + 1] !== "(") return null;
  const hrefEnd = text.indexOf(")", labelEnd + 2);
  if (hrefEnd <= labelEnd + 2) return null;

  const href = text.slice(labelEnd + 2, hrefEnd).trim();
  const raw = text.slice(startIndex, hrefEnd + 1);
  if (!isSafeLinkHref(href)) {
    return { node: { type: "text", text: raw }, nextIndex: hrefEnd + 1 };
  }

  return {
    node: {
      type: "link",
      href,
      children: parseMarkdownInline(text.slice(startIndex + 1, labelEnd)),
    },
    nextIndex: hrefEnd + 1,
  };
}

function isSafeLinkHref(href: string): boolean {
  if (href.startsWith("#") || href.startsWith("/") || href.startsWith("./") || href.startsWith("../")) return true;
  try {
    const parsed = new URL(href);
    return parsed.protocol === "http:" || parsed.protocol === "https:" || parsed.protocol === "mailto:";
  } catch {
    return false;
  }
}

function startsBlock(line: string): boolean {
  return (
    FENCE_PATTERN.test(line) ||
    HEADING_PATTERN.test(line) ||
    UNORDERED_ITEM_PATTERN.test(line) ||
    ORDERED_ITEM_PATTERN.test(line) ||
    BLOCKQUOTE_PATTERN.test(line)
  );
}

function isBlank(line: string): boolean {
  return line.trim() === "";
}

function pushText(nodes: MarkdownInlineNode[], text: string): void {
  if (!text) return;
  const previous = nodes.at(-1);
  if (previous?.type === "text") {
    previous.text += text;
    return;
  }
  nodes.push({ type: "text", text });
}
