import { useMemo, useState } from "react";

import type { SessionListItemDTO } from "../../api/schemas.ts";
import { IconBlocks, IconPlus, IconSearch, IconSettings } from "../../icons.ts";
import { formatSessionTime } from "../../runtime/sessionTime.ts";

type RuntimeSidebarProps = {
  open: boolean;
  sessions: SessionListItemDTO[];
  activeSessionId: string | null;
  error: string | null;
  onNewChat: () => void;
  onOpenPlugins: () => void;
  onOpenSettings: () => void;
  onSelectSession: (sessionId: string) => void;
};

export function RuntimeSidebar({
  open,
  sessions,
  activeSessionId,
  error,
  onNewChat,
  onOpenPlugins,
  onOpenSettings,
  onSelectSession,
}: RuntimeSidebarProps) {
  const [searchOpen, setSearchOpen] = useState(false);
  const [query, setQuery] = useState("");

  const filteredSessions = useMemo(() => {
    const normalizedQuery = query.trim().toLowerCase();
    if (!normalizedQuery) return sessions;
    return sessions.filter((session) => sessionMatchesQuery(session, normalizedQuery));
  }, [query, sessions]);

  if (!open) return null;

  return (
    <aside className="runtime-sidebar" aria-label="Боковая панель">
      <div className="runtime-sidebar-panel">
      <nav className="runtime-sidebar-actions" aria-label="Быстрые действия">
        <button type="button" className="runtime-sidebar-action" onClick={onNewChat}>
          <IconPlus size={17} />
          <span>Новый чат</span>
        </button>
        <button type="button" className="runtime-sidebar-action" onClick={() => setSearchOpen((value) => !value)}>
          <IconSearch size={17} />
          <span>Поиск</span>
        </button>
        <button type="button" className="runtime-sidebar-action" onClick={onOpenPlugins}>
          <IconBlocks size={17} />
          <span>Плагины</span>
        </button>
      </nav>
      {searchOpen ? (
        <label className="runtime-sidebar-search">
          <IconSearch size={16} />
          <input value={query} onChange={(event) => setQuery(event.target.value)} placeholder="Поиск чатов" autoFocus />
        </label>
      ) : null}
      <section className="runtime-sidebar-section" aria-label="Чаты">
        <div className="runtime-sidebar-section-title">
          <span>Чаты</span>
        </div>
        {error ? <p className="runtime-sidebar-error">{error}</p> : null}
        <div className="runtime-sidebar-chat-list">
          {filteredSessions.length ? (
            filteredSessions.map((session) => (
              <button
                type="button"
                className={session.session_id === activeSessionId ? "runtime-sidebar-chat selected" : "runtime-sidebar-chat"}
                key={session.session_id}
                onClick={() => onSelectSession(session.session_id)}
              >
                <span>
                  <strong>{sessionTitle(session)}</strong>
                </span>
                <time>{formatSessionTime(session.updated_at || session.created_at)}</time>
              </button>
            ))
          ) : (
            <p className="runtime-sidebar-empty">Чаты появятся после первого сообщения.</p>
          )}
        </div>
      </section>
      <div className="runtime-sidebar-bottom">
        <button type="button" className="runtime-sidebar-action" onClick={onOpenSettings}>
          <IconSettings size={17} />
          <span>Настройки</span>
        </button>
      </div>
      </div>
    </aside>
  );
}

function sessionMatchesQuery(session: SessionListItemDTO, query: string): boolean {
  return [session.title, session.model, session.provider].some((value) => (value || "").toLowerCase().includes(query));
}

function sessionTitle(session: SessionListItemDTO): string {
  return session.title || "Новый чат";
}
