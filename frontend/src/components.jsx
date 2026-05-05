import { Check, CircleHelp, Command, KeyRound, Send, ShieldAlert, Sparkles, Terminal, X } from "lucide-react";
import { filterHints, keyboardHints, skillHints, slashCommands, toolHints } from "./commandHints.js";

export function StatusBar({ sessionId, threadId, busy, apiStatus }) {
  return (
    <header className="status-bar">
      <div className="brand">
        <Terminal size={18} aria-hidden="true" />
        <span>claude-code-langgraph</span>
      </div>
      <div className="status-items">
        <span>{busy ? "running" : "idle"}</span>
        <span>{apiStatus}</span>
        <span>session {sessionId ? sessionId.slice(0, 12) : "new"}</span>
        <span>thread {threadId ? threadId.slice(0, 12) : "new"}</span>
      </div>
    </header>
  );
}

export function TerminalShell({ transcript, input, setInput, onSubmit, busy }) {
  function handleKeyDown(event) {
    if (event.key === "Enter" && !event.shiftKey) {
      event.preventDefault();
      onSubmit();
    }
  }

  return (
    <section className="terminal-shell" aria-label="CLI terminal">
      <div className="terminal-output">
        {transcript.map((item) => (
          <div className={`line line-${item.role}`} key={item.id}>
            <span className="prompt">{item.prompt}</span>
            <span className="line-text">{item.text}</span>
          </div>
        ))}
      </div>
      <div className="input-row">
        <span className="input-prompt">&gt;</span>
        <textarea
          value={input}
          onChange={(event) => setInput(event.target.value)}
          onKeyDown={handleKeyDown}
          placeholder="Type /help, /skills, or ask the assistant..."
          rows={3}
          aria-label="CLI input"
        />
        <button className="icon-button primary" type="button" onClick={onSubmit} disabled={busy || !input.trim()} title="Send">
          <Send size={18} aria-hidden="true" />
        </button>
      </div>
    </section>
  );
}

export function HintPanel({ input, liveCommands, liveTools, liveSkills }) {
  const commandHints = input.trim().startsWith("/") ? filterHints(input, slashCommands) : slashCommands;
  const mergedTools = mergeLive(toolHints, liveTools);
  const mergedSkills = mergeLive(skillHints, liveSkills);
  return (
    <aside className="hint-panel" aria-label="CLI hints">
      <HintGroup icon={<Command size={16} />} title="Slash commands" items={mergeLive(commandHints, liveCommands)} />
      <HintGroup icon={<Sparkles size={16} />} title="Skills" items={mergedSkills} />
      <HintGroup icon={<ShieldAlert size={16} />} title="Tools" items={mergedTools} />
      <div className="hint-group">
        <div className="hint-title">
          <KeyRound size={16} aria-hidden="true" />
          <span>Input hints</span>
        </div>
        {keyboardHints.map((hint) => (
          <div className="hint-row" key={hint}>
            <span>{hint}</span>
          </div>
        ))}
      </div>
    </aside>
  );
}

function HintGroup({ icon, title, items }) {
  return (
    <div className="hint-group">
      <div className="hint-title">
        {icon}
        <span>{title}</span>
      </div>
      {items.slice(0, 12).map((item) => (
        <div className="hint-row" key={item.name}>
          <code>{item.name}</code>
          <span>{item.detail || item.description || ""}</span>
        </div>
      ))}
    </div>
  );
}

export function PermissionPrompt({ request, onApprove, onReject, busy }) {
  if (!request) return null;
  return (
    <div className="permission-bar" role="alert">
      <ShieldAlert size={18} aria-hidden="true" />
      <div>
        <strong>{request.tool_name}</strong>
        <p>{request.reason}</p>
      </div>
      <button className="icon-button" type="button" onClick={onApprove} disabled={busy} title="Approve">
        <Check size={18} aria-hidden="true" />
      </button>
      <button className="icon-button danger" type="button" onClick={onReject} disabled={busy} title="Reject">
        <X size={18} aria-hidden="true" />
      </button>
    </div>
  );
}

export function EmptyState() {
  return (
    <div className="empty-state">
      <CircleHelp size={18} aria-hidden="true" />
      <span>Try /help, /skills, /status, or tool:bash echo hi.</span>
    </div>
  );
}

function mergeLive(fallback, live) {
  const liveItems = Object.entries(live || {}).map(([name, meta]) => ({
    name: name.startsWith("/") ? name : name,
    detail: meta.description || meta.type || "",
  }));
  return liveItems.length ? liveItems : fallback;
}

