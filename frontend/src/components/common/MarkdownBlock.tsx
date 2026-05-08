export function MarkdownBlock({ content, inverted = false }: { content: string; inverted?: boolean }) {
  return (
    <div className={inverted ? "markdown-block markdown-inverted" : "markdown-block"}>
      {content.split("\n").map((line, index) => (
        <p key={`${index}-${line.slice(0, 16)}`}>{line || "\u00a0"}</p>
      ))}
    </div>
  );
}

