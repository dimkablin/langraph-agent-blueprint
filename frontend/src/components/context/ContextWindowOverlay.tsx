import { useEffect, useState, type ReactNode } from "react";

import { IconFileText, IconX } from "../../icons.ts";
import {
  buildContextWindowView,
  contextRecordPreview,
  formatContextBudgetLine,
  formatContextTokenCount,
  isExpandableContextRecord,
  type ContextWindowRecordView,
  type ContextWindowSectionView,
} from "../../runtime/contextWindow.ts";
import type { RuntimeContextState } from "../../runtime/reducer.ts";

type ContextWindowOverlayProps = {
  open: boolean;
  context: RuntimeContextState;
  usage?: Record<string, unknown>;
  modelName: string;
  configuredMaxTokens?: number | null;
  onClose: () => void;
};

const SECTION_COPY = {
  title: "Context manager state",
  description: "Raw context manager snapshot currently known to the runtime.",
  emptyLabel: "Context manager state is empty.",
};

export function ContextWindowOverlay({ open, context, usage, modelName, configuredMaxTokens, onClose }: ContextWindowOverlayProps) {
  const [expandedRecords, setExpandedRecords] = useState<Set<string>>(new Set());

  useEffect(() => {
    if (!open) return;
    function onKeyDown(event: KeyboardEvent) {
      if (event.key === "Escape") onClose();
    }
    window.addEventListener("keydown", onKeyDown);
    return () => window.removeEventListener("keydown", onKeyDown);
  }, [open, onClose]);

  useEffect(() => {
    if (!open) setExpandedRecords(new Set());
  }, [open]);

  if (!open) return null;

  const view = buildContextWindowView(context, configuredMaxTokens, usage);
  const budget = view.budget;
  const toggleRecord = (recordKey: string) => {
    setExpandedRecords((current) => {
      const next = new Set(current);
      if (next.has(recordKey)) {
        next.delete(recordKey);
      } else {
        next.add(recordKey);
      }
      return next;
    });
  };

  return (
    <div className="context-window-overlay" role="dialog" aria-modal="true" aria-label="Context window">
      <button className="context-window-backdrop" type="button" aria-label="Close context window" onClick={onClose} />
      <section className="context-window-page">
        <header className="context-window-header">
          <div>
            <p className="context-window-eyebrow">Runtime context</p>
            <h2>Context window</h2>
          </div>
          <button className="context-window-close" type="button" onClick={onClose} aria-label="Close context window">
            <IconX size={18} />
          </button>
        </header>

        <div className="context-window-budget-line" aria-label="Context summary">
          {formatContextBudgetLine(budget, modelName)}
        </div>

        <div className="context-window-progress" aria-hidden="true">
          <span style={{ width: `${budget.percent ?? 0}%` }} />
        </div>

        {view.hasContext ? (
          <div className="context-window-content">
            {view.sections.map((section) => (
              <ContextRecordSection key={section.kind} section={section} expandedRecords={expandedRecords} onToggleRecord={toggleRecord} />
            ))}
          </div>
        ) : (
          <div className="context-window-empty">
            <IconFileText size={22} />
            <strong>Context is empty</strong>
            <span>Add a context reference through @README.md, @glob:src/**/*.py, or another supported context reference.</span>
          </div>
        )}
      </section>
    </div>
  );
}

function ContextRecordSection({
  section,
  expandedRecords,
  onToggleRecord,
}: {
  section: ContextWindowSectionView;
  expandedRecords: Set<string>;
  onToggleRecord: (recordKey: string) => void;
}) {
  return (
    <section className="context-window-section">
      <header>
        <div>
          <h3>{SECTION_COPY.title}</h3>
          <p>{SECTION_COPY.description}</p>
        </div>
        <span className="context-window-count">{section.items.length}</span>
      </header>
      {section.items.length > 0 ? (
        <div className="context-window-records">
          {section.items.map((item) => (
            <ContextRecordCard
              key={item.key}
              item={item}
              className="context-window-fragment"
              expanded={expandedRecords.has(item.key)}
              onToggle={() => onToggleRecord(item.key)}
            />
          ))}
        </div>
      ) : (
        <p className="context-window-section-empty">{SECTION_COPY.emptyLabel}</p>
      )}
    </section>
  );
}

function ContextRecordCard({
  item,
  icon,
  className,
  expanded,
  onToggle,
}: {
  item: ContextWindowRecordView;
  icon?: ReactNode;
  className?: string;
  expanded: boolean;
  onToggle: () => void;
}) {
  const expandable = isExpandableContextRecord(item);
  return (
    <article className={["context-window-record", className].filter(Boolean).join(" ")}>
      <header>
        <div className="context-window-record-title">
          {icon ? <span className="context-window-record-icon">{icon}</span> : null}
          <strong title={item.title}>{item.title}</strong>
        </div>
        {item.tokens == null ? null : <span className="context-window-token-pill">{formatContextTokenCount(item.tokens)}</span>}
      </header>
      {item.chips.length > 0 ? (
        <div className="context-window-chips">
          {item.chips.map((chip) => (
            <span key={chip}>{chip}</span>
          ))}
        </div>
      ) : null}
      <p>{contextRecordPreview(item, expanded)}</p>
      {expandable ? (
        <button className="context-window-expand-button" type="button" onClick={onToggle} aria-expanded={expanded}>
          {expanded ? "Свернуть" : "Развернуть"}
        </button>
      ) : null}
    </article>
  );
}
