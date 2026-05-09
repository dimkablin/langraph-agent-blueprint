import type { RuntimeContextState } from "../../runtime/reducer.ts";

export function ComposerContextMeter({ context, configuredMaxTokens }: { context: RuntimeContextState; configuredMaxTokens?: number | null }) {
  const budgetMaxTokens = numberValue(context.budget?.max_tokens);
  const maxTokens = budgetMaxTokens || configuredMaxTokens || 0;
  const usedTokens = numberValue(context.budget?.used_tokens);
  const percent = maxTokens ? Math.min(100, Math.round((usedTokens / maxTokens) * 100)) : 0;
  const hasErrors = context.errors.length > 0;
  const radius = 7;
  const circumference = 2 * Math.PI * radius;
  const progressOffset = circumference - (circumference * percent) / 100;

  return (
    <div className={hasErrors ? "composer-context-control composer-context-warning" : "composer-context-control"}>
      <div className="composer-context-icon" role="img" tabIndex={0} aria-label={`Контекст заполнен на ${percent}%`}>
        <svg viewBox="0 0 18 18" aria-hidden="true">
          <circle className="context-ring-track" cx="9" cy="9" r={radius} />
          <circle
            className="context-ring-progress"
            cx="9"
            cy="9"
            r={radius}
            strokeDasharray={circumference}
            strokeDashoffset={progressOffset}
          />
        </svg>
      </div>
      <div className="composer-context-popover" role="tooltip">
        <strong>Контекстное окно</strong>
        <span>{percent}% заполнено</span>
        <span>
          Использовано {formatTokenCount(usedTokens)} / {maxTokens ? formatTokenCount(maxTokens) : "budget"} tokens
        </span>
        <small>{context.fragments.length} фрагментов</small>
      </div>
    </div>
  );
}

function numberValue(value: unknown): number {
  return typeof value === "number" && Number.isFinite(value) ? value : 0;
}

function formatTokenCount(value: number): string {
  if (Math.abs(value) >= 1000) {
    return `${new Intl.NumberFormat(undefined, { maximumFractionDigits: 1 }).format(value / 1000)}к`;
  }
  return new Intl.NumberFormat(undefined, { maximumFractionDigits: 0 }).format(value);
}
