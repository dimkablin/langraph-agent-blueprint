import { memo } from "react";
import ReactMarkdown, { defaultUrlTransform, type Components } from "react-markdown";
import remarkGfm from "remark-gfm";

const MARKDOWN_BLOCK_CLASS = "markdown-block";
const MARKDOWN_INVERTED_CLASS = "markdown-inverted";
const MARKDOWN_SCROLL_CLASS = "markdown-scroll-block";

type MarkdownBlockProps = {
  content: string;
  inverted?: boolean;
  className?: string;
};

function buildMarkdownClassName({ inverted = false, className }: Pick<MarkdownBlockProps, "inverted" | "className">) {
  const classNames = [MARKDOWN_BLOCK_CLASS];
  if (inverted) {
    classNames.push(MARKDOWN_INVERTED_CLASS);
  }
  if (className) {
    classNames.push(className);
  }
  return classNames.join(" ");
}

const markdownComponents: Components = {
  pre({ node: _node, ...props }) {
    return (
      <div className={MARKDOWN_SCROLL_CLASS}>
        <pre {...props} />
      </div>
    );
  },
  a({ node: _node, ...props }) {
    return <a {...props} target="_blank" rel="noreferrer" />;
  },
  table({ node: _node, ...props }) {
    return (
      <div className={MARKDOWN_SCROLL_CLASS}>
        <table {...props} />
      </div>
    );
  },
};

const markdownRemarkPlugins = [remarkGfm];

export const MarkdownBlock = memo(function MarkdownBlock({ content, inverted = false, className }: MarkdownBlockProps) {
  return (
    <div className={buildMarkdownClassName({ inverted, className })}>
      <ReactMarkdown
        components={markdownComponents}
        remarkPlugins={markdownRemarkPlugins}
        skipHtml
        urlTransform={defaultUrlTransform}
      >
        {content || "\u00a0"}
      </ReactMarkdown>
    </div>
  );
});
