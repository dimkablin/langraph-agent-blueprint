import { useEffect, useState } from "react";

import { IconCheck, IconChevronRight, IconCopy } from "../../icons.ts";
import { activityTimelineGroupTitle, buildActivityEntries, formatTerminalBlock, type ActivityTimelineEntry } from "../../runtime/activityTimeline.ts";
import { safeJson } from "../../runtime/events.ts";
import type { ActivityItem } from "../../runtime/reducer.ts";
import { buildSubagentTimelineRows } from "../../runtime/subagentTimeline.ts";

const SHELL_ACTIVITY_LABEL = "Shell";

export function EventTimeline({
  activities,
  variant = "panel",
  compactCommands = false,
}: {
  activities: ActivityItem[];
  variant?: "panel" | "inline";
  compactCommands?: boolean;
}) {
  const entries = buildActivityEntries(activities);
  const shouldOpenActivityGroup = !compactCommands || entries.some((entry) => entry.isSubagent);
  const [open, setOpen] = useState(() => shouldOpenActivityGroup);
  const visible = variant === "inline" ? entries.slice(-24) : entries.slice(-80).reverse();

  useEffect(() => {
    setOpen(shouldOpenActivityGroup);
  }, [shouldOpenActivityGroup]);

  if (visible.length === 0) {
    return null;
  }

  const title = variant === "inline" ? activityTimelineGroupTitle(entries) : "Activity";
  const className = variant === "inline" ? "activity-timeline activity-timeline-inline" : "activity-timeline";
  return (
    <section className={className} aria-label="Agent activity">
      <div className="section-heading activity-heading">
        <button type="button" className="activity-group-toggle" aria-expanded={open} onClick={() => setOpen((value) => !value)}>
          <h2>{title}</h2>
          <IconChevronRight size={16} className={open ? "rotated" : ""} />
        </button>
        {variant !== "inline" ? <span>{entries.length}</span> : null}
      </div>
      {open ? <div className="activity-list">
        {visible.map((entry) => <ActivityEntryRow compactCommands={compactCommands} entry={entry} key={entry.id} />)}
      </div> : null}
    </section>
  );
}

function ActivityEntryRow({ compactCommands, entry }: { compactCommands: boolean; entry: ActivityTimelineEntry }) {
  const [expanded, setExpanded] = useState(false);
  const isCompactCommand = compactCommands && entry.isCommand;
  const className = `activity-row activity-${entry.status}${entry.isCommand ? " activity-command-row" : ""}${isCompactCommand ? " activity-command-row-compact" : ""}`;
  return (
    <article className={className}>
      <div className="activity-row-body">
        <button
          type="button"
          className={isCompactCommand ? "activity-line activity-line-compact activity-line-toggle" : "activity-line activity-line-toggle"}
          aria-label="Toggle activity details"
          aria-expanded={expanded}
          onClick={() => setExpanded((value) => !value)}
        >
          <span className="activity-title-cell">
            <span className="activity-title-text">
              <strong className="activity-title-lead">{entry.titleLead}</strong>
              {entry.titleRest ? <span className="activity-title-rest">{entry.titleRest}</span> : null}
            </span>
            {entry.isSubagent ? <span className={`activity-inline-status activity-inline-status-${entry.status}`}>{entry.detailStatusLabel}</span> : null}
            <span className="activity-detail-toggle" aria-hidden="true">
              <IconChevronRight size={14} className={expanded ? "rotated" : ""} />
            </span>
          </span>
        </button>
        {expanded && entry.terminal ? <CommandActivityDetails entry={entry} /> : null}
        {expanded && entry.isSubagent ? <SubagentActivityDetails entry={entry} /> : null}
        {expanded && !entry.terminal && !entry.isSubagent ? <div className="activity-debug-details">
          <pre>{truncateActivityText(safeJson(entry.debugPayload), 3600)}</pre>
          <div className="activity-detail-footer">
            <span className="activity-status-detail">{entry.detailStatusLabel}</span>
          </div>
        </div> : null}
      </div>
    </article>
  );
}

function SubagentActivityDetails({ entry }: { entry: ActivityTimelineEntry }) {
  const rows = buildSubagentTimelineRows(entry.activities);
  return (
    <div className="activity-debug-details activity-subagent-details">
      <div className="activity-subagent-panel">
        <div className="activity-subagent-header">
          <span>{entry.subagentName || "subagent"}</span>
          <span className={`activity-subagent-status activity-subagent-status-${entry.status}`}>{entry.detailStatusLabel}</span>
        </div>
        <div className="activity-subagent-events">
          {rows.map((row) => <SubagentTimelineRowItem row={row} key={row.id} />)}
        </div>
      </div>
    </div>
  );
}

function SubagentTimelineRowItem({ row }: { row: ReturnType<typeof buildSubagentTimelineRows>[number] }) {
  const [expanded, setExpanded] = useState(false);
  const hasDetails = Boolean(row.content || row.summary);
  const isCollapsibleTool = row.kind === "tool" && hasDetails;
  const className = `activity-subagent-event activity-subagent-event-${row.status} activity-subagent-event-${row.kind}`;

  if (!isCollapsibleTool) {
    if (row.kind === "message") {
      return (
        <div className={className}>
          <pre className="activity-subagent-message-text">{truncateActivityText(row.content || row.summary, 2400)}</pre>
        </div>
      );
    }
    return (
      <div className={className}>
        <span className="activity-subagent-event-title">{row.title}</span>
        {row.content ? <pre className="activity-subagent-event-content">{truncateActivityText(row.content, 2400)}</pre> : null}
        {!row.content && row.summary ? <span className="activity-subagent-event-summary">{row.summary}</span> : null}
      </div>
    );
  }

  return (
    <div className={className}>
      <button
        type="button"
        className="activity-subagent-event-toggle"
        aria-label="Toggle subagent tool details"
        aria-expanded={expanded}
        onClick={() => setExpanded((value) => !value)}
      >
        <span className="activity-subagent-event-toggle-title">{row.title}</span>
        <span className="activity-detail-toggle" aria-hidden="true">
          <IconChevronRight size={14} className={expanded ? "rotated" : ""} />
        </span>
      </button>
      {expanded ? (
        <div className="activity-subagent-event-details">
          {row.content ? <pre className="activity-subagent-event-content">{truncateActivityText(row.content, 2400)}</pre> : null}
          {row.summary ? <span className="activity-subagent-event-summary">{row.summary}</span> : null}
        </div>
      ) : null}
    </div>
  );
}

function CommandActivityDetails({ entry }: { entry: ActivityTimelineEntry }) {
  const [copied, setCopied] = useState(false);
  const terminalText = formatTerminalBlock(entry);

  async function copyTerminalOutput() {
    if (!terminalText.trim() || !navigator.clipboard) return;
    try {
      await navigator.clipboard.writeText(terminalText);
      setCopied(true);
      window.setTimeout(() => setCopied(false), 1400);
    } catch {
      setCopied(false);
    }
  }

  return (
    <div className="activity-debug-details activity-command-details">
      <div className="activity-command-panel">
        <div className="activity-command-header">
          <span className="activity-command-label">{SHELL_ACTIVITY_LABEL}</span>
          <button
            type="button"
            className="activity-command-copy"
            aria-label="Copy command output"
            onClick={() => void copyTerminalOutput()}
            disabled={!terminalText.trim()}
          >
            {copied ? <IconCheck size={14} /> : <IconCopy size={14} />}
          </button>
        </div>
        <pre className="activity-terminal activity-command-output"><code>{terminalText}</code></pre>
        <div className="activity-command-footer">
          <span className={`activity-command-status activity-command-status-${entry.status}`}>
            {entry.status === "success" || entry.status === "ok" ? <IconCheck size={14} /> : null}
            {activityCommandStatusLabel(entry.status)}
          </span>
        </div>
      </div>
    </div>
  );
}

function activityCommandStatusLabel(status: ActivityTimelineEntry["status"]): string {
  if (status === "success" || status === "ok") return "Успех";
  if (status === "error") return "Ошибка";
  if (status === "blocked") return "Заблокировано";
  if (status === "warning") return "Предупреждение";
  if (status === "pending" || status === "running") return "Выполняется";
  return "Инфо";
}

function truncateActivityText(value: string, limit = 280): string {
  if (value.length <= limit) return value;
  return `${value.slice(0, Math.max(0, limit - 14))}...<truncated>`;
}
