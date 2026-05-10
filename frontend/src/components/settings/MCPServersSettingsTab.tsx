import { useMemo, useState, type ReactNode } from "react";

import type { MCPStatusDTO } from "../../api/schemas.ts";
import { IconArrowLeft, IconPlus, IconSettings, IconTrash } from "../../icons.ts";
import {
  emptyMCPServerDraft,
  mcpServerEditorTitle,
  normalizeMCPSettingsSnapshot,
  type MCPKeyValue,
  type MCPSettingsServer,
  type MCPSettingsTransport,
} from "../../runtime/mcpSettings.ts";
import { EmptySettings, StatusBadge } from "./SettingsSection.tsx";

type MCPSettingsView =
  | { mode: "list" }
  | { mode: "create"; transport: MCPSettingsTransport }
  | { mode: "edit"; serverName: string };

export function MCPServersSettingsTab({ status, mcpConfig }: { status: MCPStatusDTO | null; mcpConfig?: unknown }) {
  const snapshot = useMemo(() => normalizeMCPSettingsSnapshot(status, mcpConfig), [status, mcpConfig]);
  const [view, setView] = useState<MCPSettingsView>({ mode: "list" });
  const selectedServer = view.mode === "edit" ? snapshot.servers.find((server) => server.name === view.serverName) : null;

  if (view.mode === "create") {
    return (
      <MCPServerEditor
        mode="create"
        server={emptyMCPServerDraft(view.transport)}
        onBack={() => setView({ mode: "list" })}
        onTransportChange={(transport) => setView({ mode: "create", transport })}
      />
    );
  }

  if (view.mode === "edit" && selectedServer) {
    return <MCPServerEditor mode="edit" server={selectedServer} onBack={() => setView({ mode: "list" })} />;
  }

  return (
    <div className="settings-tab-panel mcp-settings-list" aria-label="Серверы MCP">
      <header className="mcp-settings-hero">
        <h2>Серверы MCP</h2>
        <p>Подключайте внешние инструменты и источники данных.</p>
      </header>

      <section className="mcp-server-list-section" aria-label="Настроенные MCP серверы">
        <div className="mcp-server-list-header">
          <strong>Серверы</strong>
          <button type="button" className="mcp-add-button" onClick={() => setView({ mode: "create", transport: "stdio" })}>
            <IconPlus size={16} />
            <span>Добавить сервер</span>
          </button>
        </div>

        {snapshot.warnings.map((warning, index) => (
          <p className="settings-warning" key={`mcp-warning-${index}`}>
            {warning}
          </p>
        ))}
        {snapshot.invalidServers.map((warning, index) => (
          <p className="settings-warning" key={`mcp-invalid-${index}`}>
            {warning}
          </p>
        ))}

        {snapshot.servers.length ? (
          <div className="mcp-server-list">
            {snapshot.servers.map((server) => (
              <article className="mcp-server-row" key={server.name}>
                <button type="button" className="mcp-server-main" onClick={() => setView({ mode: "edit", serverName: server.name })}>
                  <strong>{server.name}</strong>
                  <span>{server.counts.tools} tools</span>
                </button>
                <span className="mcp-server-meta">
                  <StatusBadge tone={server.status === "failed" ? "danger" : server.enabled ? "ok" : "warning"}>{server.status}</StatusBadge>
                </span>
                <button type="button" className="mcp-icon-action" aria-label={`Настроить ${server.name}`} onClick={() => setView({ mode: "edit", serverName: server.name })}>
                  <IconSettings size={16} />
                </button>
                <span className={server.enabled ? "mcp-server-toggle mcp-server-toggle-on" : "mcp-server-toggle"} aria-label={server.enabled ? "enabled" : "disabled"} />
              </article>
            ))}
          </div>
        ) : (
          <EmptySettings>No MCP servers configured.</EmptySettings>
        )}
      </section>
    </div>
  );
}

function MCPServerEditor({
  mode,
  server,
  onBack,
  onTransportChange,
}: {
  mode: "create" | "edit";
  server: MCPSettingsServer;
  onBack: () => void;
  onTransportChange?: (transport: MCPSettingsTransport) => void;
}) {
  const isCreate = mode === "create";
  return (
    <div className="settings-tab-panel mcp-settings-editor" aria-label={isCreate ? "Подключиться к пользовательскому MCP" : mcpServerEditorTitle(server)}>
      <button type="button" className="mcp-back-button" onClick={onBack}>
        <IconArrowLeft size={15} />
        <span>Назад</span>
      </button>

      <header className="mcp-editor-header">
        <div>
          <h2>{isCreate ? "Подключиться к пользовательскому MCP" : mcpServerEditorTitle(server)}</h2>
          <a href="https://modelcontextprotocol.io/" target="_blank" rel="noreferrer">
            Документы
          </a>
        </div>
        {!isCreate ? (
          <button type="button" className="mcp-delete-button" disabled>
            <IconTrash size={15} />
            <span>Удалить</span>
          </button>
        ) : null}
      </header>

      {!isCreate ? <p className="mcp-editor-note">Если вы хотите сменить тип сервера MCP, сначала удалите текущую версию.</p> : null}

      <div className="mcp-editor-card">
        <MCPInputGroup label="Имя">
          <input className="mcp-input" defaultValue={server.name} placeholder="MCP server name" readOnly={!isCreate} />
        </MCPInputGroup>

        <div className="mcp-transport-tabs" role="tablist" aria-label="MCP transport">
          <button
            type="button"
            className={server.transport === "stdio" ? "mcp-transport-tab mcp-transport-tab-active" : "mcp-transport-tab"}
            disabled={!isCreate}
            onClick={() => onTransportChange?.("stdio")}
          >
            STDIO
          </button>
          <button
            type="button"
            className={server.transport === "streamable_http" ? "mcp-transport-tab mcp-transport-tab-active" : "mcp-transport-tab"}
            disabled={!isCreate}
            onClick={() => onTransportChange?.("streamable_http")}
          >
            Потоковая передача HTTP
          </button>
        </div>

        {server.transport === "streamable_http" ? <MCPHttpFields server={server} /> : <MCPStdioFields server={server} />}
      </div>

      <div className="mcp-editor-actions">
        <button type="button" className="mcp-save-button" disabled>
          Сохранить
        </button>
      </div>
    </div>
  );
}

function MCPStdioFields({ server }: { server: MCPSettingsServer }) {
  return (
    <>
      <MCPInputGroup label="Команда на запуск">
        <input className="mcp-input" defaultValue={server.stdio.command} placeholder="openai-dev-mcp serve-sqlite" readOnly />
      </MCPInputGroup>
      <MCPListGroup label="Аргументы" addLabel="Добавить аргумент" rows={server.stdio.args.length ? server.stdio.args : [""]} />
      <MCPKeyValueGroup label="Переменные окружения" addLabel="Добавить переменную окружения" rows={server.stdio.env} />
      <MCPListGroup label="Передача переменных окружения" addLabel="Добавить переменную" rows={server.stdio.envPassthrough.length ? server.stdio.envPassthrough : [""]} />
      <MCPInputGroup label="Рабочая директория">
        <input className="mcp-input" defaultValue={server.stdio.cwd} placeholder="~/code" readOnly />
      </MCPInputGroup>
    </>
  );
}

function MCPHttpFields({ server }: { server: MCPSettingsServer }) {
  return (
    <>
      <MCPInputGroup label="URL">
        <input className="mcp-input" defaultValue={server.http.url} placeholder="https://mcp.example.com/mcp" readOnly />
      </MCPInputGroup>
      <MCPInputGroup label="Переменная окружения токена Bearer">
        <input className="mcp-input" defaultValue={server.http.bearerTokenEnv} placeholder="MCP_BEARER_TOKEN" readOnly />
      </MCPInputGroup>
      <MCPKeyValueGroup label="Заголовки" addLabel="Добавить заголовок" rows={server.http.headers} />
      <MCPKeyValueGroup label="Заголовки из переменных окружения" addLabel="Добавить переменную" rows={server.http.headerEnv} />
    </>
  );
}

function MCPInputGroup({ label, children }: { label: string; children: ReactNode }) {
  return (
    <label className="mcp-field-group">
      <span>{label}</span>
      {children}
    </label>
  );
}

function MCPListGroup({ label, addLabel, rows }: { label: string; addLabel: string; rows: string[] }) {
  return (
    <div className="mcp-field-group">
      <span>{label}</span>
      <div className="mcp-list-fields">
        {rows.map((value, index) => (
          <div className="mcp-inline-field" key={`${label}-${index}`}>
            <input className="mcp-input" defaultValue={value} readOnly />
            <button type="button" aria-label="Удалить" disabled>
              <IconTrash size={14} />
            </button>
          </div>
        ))}
      </div>
      <button type="button" className="mcp-add-field-button" disabled>
        <IconPlus size={14} />
        <span>{addLabel}</span>
      </button>
    </div>
  );
}

function MCPKeyValueGroup({ label, addLabel, rows }: { label: string; addLabel: string; rows: MCPKeyValue[] }) {
  const visibleRows = rows.length ? rows : [{ key: "", value: "" }];
  return (
    <div className="mcp-field-group">
      <span>{label}</span>
      <div className="mcp-list-fields">
        {visibleRows.map((row, index) => (
          <div className="mcp-inline-field mcp-inline-field-pair" key={`${label}-${index}`}>
            <input className="mcp-input" defaultValue={row.key} placeholder="Ключ" readOnly />
            <input className="mcp-input" defaultValue={row.value} placeholder="Значение" readOnly />
            <button type="button" aria-label="Удалить" disabled>
              <IconTrash size={14} />
            </button>
          </div>
        ))}
      </div>
      <button type="button" className="mcp-add-field-button" disabled>
        <IconPlus size={14} />
        <span>{addLabel}</span>
      </button>
    </div>
  );
}
