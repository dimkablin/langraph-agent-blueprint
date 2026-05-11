import { buildContextWindowView, formatContextTokenCount } from "../../runtime/contextWindow.ts";
import type { RuntimeContextState } from "../../runtime/reducer.ts";

export function ComposerContextMeter({
  context,
  configuredMaxTokens,
  onOpenContextWindow,
}: {
  context: RuntimeContextState;
  configuredMaxTokens?: number | null;
  onOpenContextWindow?: () => void;
}) {
  const { budget } = buildContextWindowView(context, configuredMaxTokens);
  const percent = budget.percent ?? 0;
  const hasErrors = context.errors.length > 0;
  const radius = 6;
  const circumference = 2 * Math.PI * radius;
  const progressOffset = circumference - (circumference * percent) / 100;

  return (
    <div className={hasErrors ? "composer-context-control composer-context-warning" : "composer-context-control"}>
      <button className="composer-context-icon" type="button" onClick={onOpenContextWindow} aria-label={`Контекст заполнен на ${percent}%`}>
        <svg viewBox="0 0 16 16" aria-hidden="true">
          <circle className="context-ring-track" cx="8" cy="8" r={radius} />
          <circle
            className="context-ring-progress"
            cx="8"
            cy="8"
            r={radius}
            strokeDasharray={circumference}
            strokeDashoffset={progressOffset}
          />
        </svg>
      </button>
      <div className="composer-context-popover" role="tooltip">
        <strong>Контекстное окно</strong>
        <span>{percent}% заполнено</span>
        <span>
          Использовано {formatContextTokenCount(budget.usedTokens)} / {formatContextTokenCount(budget.maxTokens)} tokens
        </span>
        <span>Осталось {formatContextTokenCount(budget.remainingTokens)} tokens</span>
        <small>{context.fragments.length} фрагментов</small>
      </div>
    </div>
  );
}
