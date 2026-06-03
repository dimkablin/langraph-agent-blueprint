import { useMemo, useState } from "react";

import type { SessionListItemDTO } from "../../api/schemas.ts";
import { IconBlocks, IconMessages, IconPlus, IconSearch, IconSettings } from "../../icons.ts";
import { formatSessionTime } from "../../runtime/sessionTime.ts";
import type { SettingsTab } from "../../runtime/settingsPage.ts";
import { SettingsTabs } from "../settings/SettingsTabs.tsx";

type RuntimeSidebarProps = {
  open: boolean;
  mode: "chat" | "settings";
  sessions: SessionListItemDTO[];
  activeSessionId: string | null;
  error: string | null;
  settingsActiveTab: SettingsTab;
  onNewChat: () => void;
  onOpenChat: () => void;
  onOpenPlugins: () => void;
  onOpenSettings: () => void;
  onSettingsTabChange: (tab: SettingsTab) => void;
  onArchiveSession: (sessionId: string) => void;
  onDeleteSession: (sessionId: string) => void;
  onRenameSession: (sessionId: string) => void;
  onSelectSession: (sessionId: string) => void;
};

export function RuntimeSidebar({
  open,
  mode,
  sessions,
  activeSessionId,
  error,
  settingsActiveTab,
  onNewChat,
  onOpenChat,
  onOpenPlugins,
  onOpenSettings,
  onSettingsTabChange,
  onArchiveSession,
  onDeleteSession,
  onRenameSession,
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
        {mode === "settings" ? (
          <SettingsSidebar
            activeTab={settingsActiveTab}
            onChange={onSettingsTabChange}
            onOpenChat={onOpenChat}
          />
        ) : (
          <ChatSidebar
            activeSessionId={activeSessionId}
            error={error}
            filteredSessions={filteredSessions}
            searchOpen={searchOpen}
            query={query}
            onNewChat={onNewChat}
            onOpenPlugins={onOpenPlugins}
            onOpenSettings={onOpenSettings}
            onArchiveSession={onArchiveSession}
            onDeleteSession={onDeleteSession}
            onRenameSession={onRenameSession}
            onQueryChange={setQuery}
            onSearchToggle={() => setSearchOpen((value) => !value)}
            onSelectSession={onSelectSession}
          />
        )}
      </div>
      <div className="runtime-sidebar-gap" aria-hidden="true" />
    </aside>
  );
}

function ChatSidebar({
  activeSessionId,
  error,
  filteredSessions,
  searchOpen,
  query,
  onNewChat,
  onOpenPlugins,
  onOpenSettings,
  onArchiveSession,
  onDeleteSession,
  onRenameSession,
  onQueryChange,
  onSearchToggle,
  onSelectSession,
}: {
  activeSessionId: string | null;
  error: string | null;
  filteredSessions: SessionListItemDTO[];
  searchOpen: boolean;
  query: string;
  onNewChat: () => void;
  onOpenPlugins: () => void;
  onOpenSettings: () => void;
  onArchiveSession: (sessionId: string) => void;
  onDeleteSession: (sessionId: string) => void;
  onRenameSession: (sessionId: string) => void;
  onQueryChange: (query: string) => void;
  onSearchToggle: () => void;
  onSelectSession: (sessionId: string) => void;
}) {
  return (
    <>
      <nav className="runtime-sidebar-actions" aria-label="Быстрые действия">
        <button type="button" className="runtime-sidebar-action" onClick={onNewChat}>
          <IconPlus size={17} />
          <span>Новый чат</span>
        </button>
        <button type="button" className="runtime-sidebar-action" onClick={onSearchToggle}>
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
          <input value={query} onChange={(event) => onQueryChange(event.target.value)} placeholder="Поиск чатов" autoFocus />
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
              <div
                className={session.session_id === activeSessionId ? "runtime-sidebar-chat selected" : "runtime-sidebar-chat"}
                key={session.session_id}
              >
                <button type="button" className="runtime-sidebar-chat-main" onClick={() => onSelectSession(session.session_id)}>
                  <strong>{sessionTitle(session)}</strong>
                  <time>{formatSessionTime(session.updated_at || session.created_at)}</time>
                </button>
                <span className="runtime-sidebar-chat-actions" aria-label="Действия чата">
                  <button type="button" onClick={() => onRenameSession(session.session_id)}>Переименовать</button>
                  <button type="button" onClick={() => onArchiveSession(session.session_id)}>Архив</button>
                  <button type="button" onClick={() => onDeleteSession(session.session_id)}>Удалить</button>
                </span>
              </div>
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
    </>
  );
}

function SettingsSidebar({
  activeTab,
  onChange,
  onOpenChat,
}: {
  activeTab: SettingsTab;
  onChange: (tab: SettingsTab) => void;
  onOpenChat: () => void;
}) {
  return (
    <>
      <div className="settings-sidebar-heading">
        <span>Настройки</span>
      </div>
      <SettingsTabs activeTab={activeTab} onChange={onChange} />
      <div className="runtime-sidebar-bottom">
        <button type="button" className="runtime-sidebar-action" onClick={onOpenChat}>
          <IconMessages size={17} />
          <span>Чаты</span>
        </button>
      </div>
    </>
  );
}

function sessionMatchesQuery(session: SessionListItemDTO, query: string): boolean {
  return [session.title, session.model, session.provider].some((value) => (value || "").toLowerCase().includes(query));
}

function sessionTitle(session: SessionListItemDTO): string {
  return session.title || "Новый чат";
}
