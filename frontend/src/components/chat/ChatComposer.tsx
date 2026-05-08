import { Send, Square } from "lucide-react";
import { useState } from "react";

const CONTEXT_HINTS = [
  "@README.md",
  "@src/",
  "@glob:src/**/*.py",
  "@notebook:notebook.ipynb",
  "@mcp:<server>:<uri>",
  "@plugin:<plugin>:<provider>",
  "@url:https://example.com",
];

export function ChatComposer({
  disabled,
  isStreaming,
  onSubmit,
  onStop,
}: {
  disabled?: boolean;
  isStreaming: boolean;
  onSubmit: (value: string) => void;
  onStop: () => void;
}) {
  const [input, setInput] = useState("");

  function submit() {
    const value = input.trim();
    if (!value || disabled || isStreaming) return;
    setInput("");
    onSubmit(value);
  }

  return (
    <section className="composer" aria-label="Chat composer">
      <div className="context-hints" aria-label="Context reference examples">
        {CONTEXT_HINTS.map((hint) => (
          <button key={hint} type="button" onClick={() => setInput((value) => `${value}${value ? " " : ""}${hint}`)} disabled={disabled || isStreaming}>
            {hint}
          </button>
        ))}
      </div>
      <div className="composer-box">
        <textarea
          value={input}
          onChange={(event) => setInput(event.target.value)}
          onKeyDown={(event) => {
            if (event.key === "Enter" && !event.shiftKey) {
              event.preventDefault();
              submit();
            }
          }}
          placeholder="Ask the runtime, use /commands, or reference context with @README.md..."
          disabled={disabled}
          rows={4}
        />
        {isStreaming ? (
          <button className="send-button stop" type="button" onClick={onStop} aria-label="Stop stream">
            <Square size={18} />
          </button>
        ) : (
          <button className="send-button" type="button" onClick={submit} disabled={disabled || !input.trim()} aria-label="Send message">
            <Send size={18} />
          </button>
        )}
      </div>
    </section>
  );
}

