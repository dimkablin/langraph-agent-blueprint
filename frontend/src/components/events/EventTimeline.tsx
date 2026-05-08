import { ChevronRight } from "lucide-react";
import { useState } from "react";

import { safeJson } from "../../runtime/events.ts";
import type { ActivityItem } from "../../runtime/reducer.ts";

export function EventTimeline({ activities }: { activities: ActivityItem[] }) {
  const [expanded, setExpanded] = useState<Record<string, boolean>>({});
  const visible = activities.slice(-80).reverse();

  return (
    <section className="panel-section" aria-label="Runtime activity">
      <div className="section-heading">
        <h2>Activity</h2>
        <span>{activities.length}</span>
      </div>
      {visible.length ? (
        <div className="activity-list">
          {visible.map((activity) => {
            const open = Boolean(expanded[activity.id]);
            return (
              <article className={`activity-row activity-${activity.status}`} key={activity.id}>
                <button type="button" onClick={() => setExpanded((items) => ({ ...items, [activity.id]: !open }))}>
                  <ChevronRight size={14} className={open ? "rotated" : ""} />
                  <span className="activity-kind">{activity.kind}</span>
                  <strong>{activity.label}</strong>
                </button>
                {activity.summary ? <p>{activity.summary}</p> : null}
                {open ? <pre>{safeJson(activity.data)}</pre> : null}
              </article>
            );
          })}
        </div>
      ) : (
        <p className="muted">No runtime events yet.</p>
      )}
    </section>
  );
}

