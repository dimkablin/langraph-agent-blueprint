import { useEffect, useState } from "react";

import { IconChevronRight } from "../../icons.ts";
import { buildActivityEntries, formatTerminalBlock, type ActivityTimelineEntry } from "../../runtime/activityTimeline.ts";
import { safeJson } from "../../runtime/events.ts";
import type { ActivityItem } from "../../runtime/reducer.ts";

export function EventTimeline({
  activities,
  variant = "panel",
  compactCommands = false,
}: {
  activities: ActivityItem[];
  variant?: "panel" | "inline";
  compactCommands?: boolean;
}) {
  const [open, setOpen] = useState(() => !compactCommands);
  const entries = buildActivityEntries(activities);
  const visible = variant === "inline" ? entries.slice(-24) : entries.slice(-80).reverse();

  useEffect(() => {
    if (compactCommands) setOpen(false);
  }, [compactCommands]);

  if (visible.length === 0) {
    return null;
  }

  const title = variant === "inline" ? activityGroupTitle(entries) : "Activity";
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
  const [expandedOverride, setExpandedOverride] = useState<boolean | null>(null);
  const expanded = expandedOverride ?? (!entry.isCommand && entry.expandedByDefault);
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
          onClick={() => setExpandedOverride((value) => !(value ?? (!entry.isCommand && entry.expandedByDefault)))}
        >
          {!isCompactCommand ? <span className="activity-kind">{entry.category}</span> : null}
          <span className="activity-title-cell">
            <span className="activity-title-text">
              <strong className="activity-title-lead">{entry.titleLead}</strong>
              {entry.titleRest ? <span className="activity-title-rest">{entry.titleRest}</span> : null}
            </span>
            <span className="activity-detail-toggle" aria-hidden="true">
              <IconChevronRight size={14} className={expanded ? "rotated" : ""} />
            </span>
          </span>
        </button>
        {entry.summary && !entry.isCommand ? <p className="activity-summary">{truncateActivityText(entry.summary)}</p> : null}
        {expanded ? <div className="activity-debug-details">
          {entry.summary && entry.isCommand ? <p className="activity-summary">{truncateActivityText(entry.summary)}</p> : null}
          {entry.terminal ? <pre className="activity-terminal"><code>{formatTerminalBlock(entry)}</code></pre> : null}
          <pre>{truncateActivityText(safeJson(entry.debugPayload), 3600)}</pre>
          <div className="activity-detail-footer">
            <span className="activity-status-detail">{entry.detailStatusLabel}</span>
          </div>
        </div> : null}
      </div>
    </article>
  );
}

function truncateActivityText(value: string, limit = 280): string {
  if (value.length <= limit) return value;
  return `${value.slice(0, Math.max(0, limit - 14))}...<truncated>`;
}

function activityGroupTitle(entries: ActivityTimelineEntry[]): string {
  const commandCount = entries.filter((entry) => Boolean(entry.terminal)).length;
  if (commandCount > 0) {
    return `Ran ${commandCount} ${commandCount === 1 ? "command" : "commands"}`;
  }
  return `${entries.length} ${entries.length === 1 ? "activity" : "activities"}`;
}
