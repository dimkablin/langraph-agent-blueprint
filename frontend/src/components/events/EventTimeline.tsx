import { useState } from "react";

import { IconChevronRight } from "../../icons.ts";
import { safeJson } from "../../runtime/events.ts";
import type { ActivityItem } from "../../runtime/reducer.ts";

export function EventTimeline({ activities }: { activities: ActivityItem[] }) {
  const [expanded, setExpanded] = useState<Record<string, boolean>>({});
  const visible = activities.slice(-80).reverse();
  if (visible.length === 0) {
    return null;
  }

  return (
    <section className="activity-timeline" aria-label="Agent activity">
      <div className="section-heading activity-heading">
        <h2>Activity</h2>
        <span>{activities.length}</span>
      </div>
      <div className="activity-list">
        {visible.map((activity) => {
          const open = Boolean(expanded[activity.id]);
          return (
            <article className={`activity-row activity-${activity.status}`} key={activity.id}>
              <button
                type="button"
                aria-expanded={open}
                onClick={() => setExpanded((items) => ({ ...items, [activity.id]: !open }))}
              >
                <IconChevronRight size={16} className={open ? "rotated" : ""} />
                <span className="activity-kind">{activity.category || activity.kind}</span>
                <strong>{activity.label}</strong>
                <span className="activity-status">{activity.status}</span>
              </button>
              {activity.summary ? <p>{truncateActivityText(activity.summary)}</p> : null}
              {open ? <pre>{truncateActivityText(safeJson(activity.data), 2400)}</pre> : null}
            </article>
          );
        })}
      </div>
    </section>
  );
}

function truncateActivityText(value: string, limit = 280): string {
  if (value.length <= limit) return value;
  return `${value.slice(0, Math.max(0, limit - 14))}...<truncated>`;
}
