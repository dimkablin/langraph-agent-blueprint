import type { MCPStatusDTO } from "../../api/schemas.ts";
import { EmptySettings, SettingsSection, StatusBadge } from "./SettingsSection.tsx";

export function MCPSettingsSection({ status }: { status: MCPStatusDTO | null }) {
  const servers = status?.servers ?? [];
  const warnings = status?.warnings ?? [];
  const invalid = status?.invalid_servers ?? [];
  const toolCount = status ? Object.keys(status.tools || {}).length : 0;
  const resourceCount = status ? Object.values(status.resources || {}).reduce((total, items) => total + items.length, 0) : 0;
  const promptCount = status ? Object.values(status.prompts || {}).reduce((total, items) => total + items.length, 0) : 0;

  return (
    <SettingsSection title="MCP" eyebrow="passive snapshot">
      <div className="settings-summary-line">
        <StatusBadge>{toolCount} tools</StatusBadge>
        <StatusBadge>{resourceCount} resources</StatusBadge>
        <StatusBadge>{promptCount} prompts</StatusBadge>
      </div>
      {warnings.map((warning, index) => (
        <p className="settings-warning" key={`mcp-warning-${index}`}>
          {stringValue(warning.message, JSON.stringify(warning))}
        </p>
      ))}
      {invalid.map((item, index) => (
        <p className="settings-warning" key={`mcp-invalid-${index}`}>
          Invalid server {stringValue(item.name, "unknown")}: {stringValue(item.error, "unknown error")}
        </p>
      ))}
      {servers.length ? (
        <div className="settings-card-list">
          {servers.map((server) => (
            <article className="settings-card" key={stringValue(server.name, "server")}>
              <div>
                <strong>{stringValue(server.name, "unknown server")}</strong>
                <span>{stringValue(server.transport, "unknown transport")}</span>
              </div>
              <div className="settings-inline-badges">
                <StatusBadge tone={server.enabled === false ? "warning" : "ok"}>{server.enabled === false ? "disabled" : "enabled"}</StatusBadge>
                <StatusBadge tone={server.status === "failed" ? "danger" : "neutral"}>{stringValue(server.status, "unknown")}</StatusBadge>
                <StatusBadge>{stringValue(server.trust_level, "untrusted")}</StatusBadge>
              </div>
            </article>
          ))}
        </div>
      ) : (
        <EmptySettings>No MCP servers configured.</EmptySettings>
      )}
    </SettingsSection>
  );
}

function stringValue(value: unknown, fallback: string): string {
  return typeof value === "string" && value ? value : fallback;
}
