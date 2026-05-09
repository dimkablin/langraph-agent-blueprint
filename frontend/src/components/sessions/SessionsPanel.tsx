import type { SessionDetailDTO, SessionListItemDTO } from "../../api/schemas.ts";
import { IconDownload } from "../../icons.ts";

export function SessionsPanel({
  sessions,
  selected,
  activeSessionId,
  error,
  onSelect,
  onExport,
}: {
  sessions: SessionListItemDTO[];
  selected: SessionDetailDTO | null;
  activeSessionId: string | null;
  error: string | null;
  onSelect: (sessionId: string) => void;
  onExport: (sessionId: string) => void;
}) {
  return (
    <section className="panel-section" aria-label="Sessions">
      <div className="section-heading">
        <h2>Sessions</h2>
        <span>{sessions.length}</span>
      </div>
      {error ? <p className="error-text">{error}</p> : null}
      <div className="session-list">
        {sessions.slice(0, 14).map((session) => (
          <button
            type="button"
            className={session.session_id === activeSessionId ? "session-row selected" : "session-row"}
            key={session.session_id}
            onClick={() => onSelect(session.session_id)}
          >
            <span>{sessionTitle(session)}</span>
          </button>
        ))}
      </div>
      {selected ? (
        <div className="session-detail">
          <strong>{selected.title || "Новый чат"}</strong>
          <span>{selected.messages.length} messages</span>
          <span>{selected.events.length} events</span>
          <span>{selected.child_runs.length} child runs</span>
          <button type="button" onClick={() => onExport(selected.session_id)}>
            <IconDownload size={16} />
            Export markdown
          </button>
        </div>
      ) : null}
    </section>
  );
}

function sessionTitle(session: SessionListItemDTO): string {
  return session.title || "Новый чат";
}
