import type { ConfigExplainDTO, ConfigShowDTO, ConfigValidateDTO } from "../../api/schemas.ts";
import { EmptySettings, SettingsRows, SettingsSection, StatusBadge } from "./SettingsSection.tsx";

const PRIMARY_CONFIG_KEYS = [
  "llm_provider",
  "model_name",
  "permission_mode",
  "network_enabled",
  "context_max_tokens",
  "storage_dir",
  "shell_timeout_seconds",
  "tool_output_limit",
  "auto_compact_threshold",
] as const;

export function ConfigurationSettingsTab({
  config,
  explain,
  validation,
}: {
  config: ConfigShowDTO | null;
  explain: ConfigExplainDTO | null;
  validation: ConfigValidateDTO | null;
}) {
  const values = config?.values ?? {};
  const sources = explain?.sources ?? [];
  const diagnostics = validation?.diagnostics ?? explain?.diagnostics ?? [];
  const valueOrigins = explain?.values ?? [];

  return (
    <div className="settings-tab-panel" aria-label="Конфигурация">
      <SettingsSection title="Effective configuration" eyebrow="redacted read-only">
        <SettingsRows
          rows={PRIMARY_CONFIG_KEYS.map((key) => ({
            label: configLabel(key),
            value: displayValue(key, values[key]),
            locked: true,
            note: sourceForKey(valueOrigins, key),
          }))}
        />
      </SettingsSection>

      <SettingsSection title="Sources" eyebrow={`${sources.length} layers`}>
        {sources.length ? (
          <div className="settings-card-list">
            {sources.map((source, index) => (
              <article className="settings-card" key={`${stringValue(source.name, "source")}-${index}`}>
                <div>
                  <strong>{stringValue(source.name, "unknown source")}</strong>
                  <span>{stringValue(source.kind, "unknown")}</span>
                </div>
                <div className="settings-inline-badges">
                  <StatusBadge tone={source.loaded === false ? "neutral" : "ok"}>{source.loaded === false ? "not loaded" : "loaded"}</StatusBadge>
                  {source.path ? <StatusBadge>{String(source.path)}</StatusBadge> : null}
                </div>
                {source.error ? <p className="settings-warning">{String(source.error)}</p> : null}
              </article>
            ))}
          </div>
        ) : (
          <EmptySettings>Config source report is unavailable.</EmptySettings>
        )}
      </SettingsSection>

      <SettingsSection title="Validation" eyebrow={validation?.ok === false ? "warnings" : "ok"}>
        {diagnostics.length ? (
          <div className="settings-card-list">
            {diagnostics.map((diagnostic, index) => (
              <article className="settings-card" key={`${stringValue(diagnostic.key, "diagnostic")}-${index}`}>
                <div>
                  <strong>{stringValue(diagnostic.key, "config")}</strong>
                  <span>{stringValue(diagnostic.status, "info")}</span>
                </div>
                <p>{stringValue(diagnostic.message, "No diagnostic message.")}</p>
              </article>
            ))}
          </div>
        ) : (
          <EmptySettings>No config diagnostics.</EmptySettings>
        )}
      </SettingsSection>
    </div>
  );
}

function configLabel(key: string): string {
  return key.replaceAll("_", " ");
}

function displayValue(key: string, value: unknown): string {
  if (isSensitiveKey(key)) return present(value) ? "***" : "not configured";
  if (typeof value === "boolean") return value ? "enabled" : "disabled";
  if (typeof value === "number") return String(value);
  if (typeof value === "string") return value || "not configured";
  if (value == null) return "not configured";
  return JSON.stringify(value);
}

function isSensitiveKey(key: string): boolean {
  return /api[_-]?key|secret|token|password|authorization/i.test(key);
}

function present(value: unknown): boolean {
  return value != null && value !== "";
}

function sourceForKey(values: Record<string, unknown>[], key: string): string | undefined {
  const origin = values.find((item) => item.key === key);
  return typeof origin?.source === "string" ? origin.source : undefined;
}

function stringValue(value: unknown, fallback: string): string {
  return typeof value === "string" && value ? value : fallback;
}
