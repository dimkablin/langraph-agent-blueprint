import ReactMarkdown, { defaultUrlTransform, type Components } from "react-markdown";
import remarkGfm from "remark-gfm";

const markdownComponents: Components = {
  a({ node: _node, ...props }) {
    return <a {...props} target="_blank" rel="noreferrer" />;
  },
  table({ node: _node, ...props }) {
    return (
      <div className="markdown-table-scroll">
        <table {...props} />
      </div>
    );
  },
};

const markdownRemarkPlugins = [remarkGfm];

export function MarkdownBlock({ content, inverted = false }: { content: string; inverted?: boolean }) {
  return (
    <div className={inverted ? "markdown-block markdown-inverted" : "markdown-block"}>
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
}
