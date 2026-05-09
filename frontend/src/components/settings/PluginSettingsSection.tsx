import type { PluginStatusDTO } from "../../api/schemas.ts";
import { EmptySettings, SettingsSection, StatusBadge } from "./SettingsSection.tsx";

export function PluginSettingsSection({ status }: { status: PluginStatusDTO | null }) {
  const plugins = status?.plugins ?? [];
  const warnings = status?.warnings?.length ?? 0;
  const errors = status?.errors?.length ?? 0;

  return (
    <SettingsSection title="Plugins" eyebrow="read-only">
      <div className="settings-summary-line">
        <StatusBadge tone={errors ? "danger" : warnings ? "warning" : "neutral"}>
          {plugins.length} plugins, {warnings} warnings, {errors} errors
        </StatusBadge>
      </div>
      {plugins.length ? (
        <div className="settings-card-list">
          {plugins.slice(0, 10).map((plugin) => (
            <article className="settings-card" key={stringValue(plugin.name, "plugin")}>
              <div>
                <strong>{stringValue(plugin.name, "unknown plugin")}</strong>
                <span>{stringValue(plugin.version, "version unknown")}</span>
              </div>
              <p>{stringValue(plugin.description, "No description.")}</p>
              <div className="settings-inline-badges">
                <StatusBadge tone={plugin.enabled === false ? "warning" : "ok"}>{plugin.enabled === false ? "disabled" : "enabled"}</StatusBadge>
                <StatusBadge>{trustLevel(plugin.trust)}</StatusBadge>
                <StatusBadge>{contributionSummary(plugin)}</StatusBadge>
              </div>
            </article>
          ))}
        </div>
      ) : (
        <EmptySettings>No plugins discovered.</EmptySettings>
      )}
    </SettingsSection>
  );
}

function contributionSummary(plugin: Record<string, unknown>): string {
  const parts = [
    count(plugin.skills_count, "skills"),
    count(plugin.hooks_count, "hooks"),
    count(plugin.tools_count, "tools"),
    count(plugin.mcp_servers_count, "mcp"),
  ].filter(Boolean);
  return parts.join(" / ") || "no contributions";
}

function count(value: unknown, label: string): string | null {
  return typeof value === "number" && value > 0 ? `${value} ${label}` : null;
}

function trustLevel(value: unknown): string {
  if (value && typeof value === "object" && "level" in value) {
    return `trust: ${String(value.level)}`;
  }
  return "trust: untrusted";
}

function stringValue(value: unknown, fallback: string): string {
  return typeof value === "string" && value ? value : fallback;
}
