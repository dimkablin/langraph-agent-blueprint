import { AlertTriangle, FileText } from "lucide-react";

import type { RuntimeContextState } from "../../runtime/reducer.ts";

export function ContextPanel({ context }: { context: RuntimeContextState }) {
  const maxTokens = numberValue(context.budget?.max_tokens);
  const usedTokens = numberValue(context.budget?.used_tokens);
  const percent = maxTokens ? Math.min(100, Math.round((usedTokens / maxTokens) * 100)) : 0;

  return (
    <section className="panel-section" aria-label="Context">
      <div className="section-heading">
        <h2>Context</h2>
        <span>{context.fragments.length}</span>
      </div>
      <div className="budget-meter">
        <div>
          <strong>{usedTokens || 0}</strong>
          <span>/ {maxTokens || "budget"} tokens</span>
        </div>
        <div className="meter-track">
          <span style={{ width: `${percent}%` }} />
        </div>
      </div>
      {context.fragments.length ? (
        <div className="context-list">
          {context.fragments.map((fragment, index) => (
            <article className="context-row" key={String(fragment.id || index)}>
              <FileText size={14} />
              <div>
                <strong>{String(fragment.title || fragment.kind || "Context fragment")}</strong>
                <span>{String(fragment.trust || "unknown trust")}</span>
              </div>
            </article>
          ))}
        </div>
      ) : (
        <p className="muted">No context fragments yet. Try @README.md or @glob:src/**/*.py.</p>
      )}
      {context.errors.map((error, index) => (
        <div className="context-error" key={`${index}-${String(error.message || error.error || "")}`}>
          <AlertTriangle size={14} />
          <span>{String(error.message || error.error || "Context error")}</span>
        </div>
      ))}
    </section>
  );
}

function numberValue(value: unknown): number {
  return typeof value === "number" && Number.isFinite(value) ? value : 0;
}

