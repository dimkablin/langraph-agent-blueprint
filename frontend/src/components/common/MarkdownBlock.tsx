import { Fragment, type ReactNode } from "react";

import { parseMarkdown, type MarkdownBlockNode, type MarkdownInlineNode } from "./markdown.ts";

export function MarkdownBlock({ content, inverted = false }: { content: string; inverted?: boolean }) {
  const blocks = parseMarkdown(content);
  return (
    <div className={inverted ? "markdown-block markdown-inverted" : "markdown-block"}>
      {blocks.length > 0 ? blocks.map((block, index) => renderBlock(block, index)) : <p>{"\u00a0"}</p>}
    </div>
  );
}

function renderBlock(block: MarkdownBlockNode, index: number): ReactNode {
  const key = `${block.type}-${index}`;
  if (block.type === "paragraph") {
    return <p key={key}>{renderInline(block.children, key)}</p>;
  }
  if (block.type === "heading") {
    return renderHeading(block, key);
  }
  if (block.type === "unordered_list") {
    return (
      <ul key={key}>
        {block.items.map((item, itemIndex) => (
          <li key={`${key}-item-${itemIndex}`}>{renderInline(item, `${key}-item-${itemIndex}`)}</li>
        ))}
      </ul>
    );
  }
  if (block.type === "ordered_list") {
    return (
      <ol key={key} start={block.start}>
        {block.items.map((item, itemIndex) => (
          <li key={`${key}-item-${itemIndex}`}>{renderInline(item, `${key}-item-${itemIndex}`)}</li>
        ))}
      </ol>
    );
  }
  if (block.type === "blockquote") {
    return <blockquote key={key}>{renderInline(block.children, key)}</blockquote>;
  }
  return (
    <pre key={key}>
      <code className={block.language ? `language-${block.language}` : undefined}>{block.code || "\u00a0"}</code>
    </pre>
  );
}

function renderHeading(block: Extract<MarkdownBlockNode, { type: "heading" }>, key: string): ReactNode {
  const children = renderInline(block.children, key);
  if (block.level === 1) return <h1 key={key}>{children}</h1>;
  if (block.level === 2) return <h2 key={key}>{children}</h2>;
  if (block.level === 3) return <h3 key={key}>{children}</h3>;
  if (block.level === 4) return <h4 key={key}>{children}</h4>;
  if (block.level === 5) return <h5 key={key}>{children}</h5>;
  return <h6 key={key}>{children}</h6>;
}

function renderInline(nodes: MarkdownInlineNode[], keyPrefix: string): ReactNode[] {
  return nodes.map((node, index) => {
    const key = `${keyPrefix}-inline-${index}`;
    if (node.type === "text") {
      return <Fragment key={key}>{node.text}</Fragment>;
    }
    if (node.type === "strong") {
      return <strong key={key}>{renderInline(node.children, key)}</strong>;
    }
    if (node.type === "emphasis") {
      return <em key={key}>{renderInline(node.children, key)}</em>;
    }
    if (node.type === "inline_code") {
      return <code key={key}>{node.code}</code>;
    }
    return (
      <a key={key} href={node.href} target="_blank" rel="noreferrer">
        {renderInline(node.children, key)}
      </a>
    );
  });
}
