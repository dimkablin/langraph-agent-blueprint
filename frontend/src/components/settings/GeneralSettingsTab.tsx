import type { ConfigShowDTO } from "../../api/schemas.ts";
import type { RuntimeStatus } from "../../api/status.ts";
import type { ModelIntelligenceLevel } from "../../runtime/modelIntelligence.ts";
import { MODEL_INTELLIGENCE_OPTIONS } from "../../runtime/modelIntelligence.ts";
import { SettingsRows, SettingsSection, StatusBadge } from "./SettingsSection.tsx";

export function GeneralSettingsTab({
  status,
  sessionId,
  threadId,
  modelIntelligenceLevel,
}: {
  status: RuntimeStatus | null;
  sessionId: string | null;
  threadId: string | null;
  modelIntelligenceLevel: ModelIntelligenceLevel;
}) {
  const config = status?.config ?? null;
  const values = config?.values ?? {};
  const selectedIntelligence = MODEL_INTELLIGENCE_OPTIONS.find((option) => option.id === modelIntelligenceLevel);

  return (
    <div className="settings-tab-panel" aria-label="Общее">
      <div className="settings-dashboard-grid">
        <SettingsSection title="Model" eyebrow="read-only">
          <SettingsRows
            rows={[
              { label: "Provider", value: stringValue(values.llm_provider, "unknown"), locked: true, note: "config file only" },
              { label: "Model", value: effectiveModel(config), locked: true, note: "config file only" },
              { label: "Run intelligence", value: selectedIntelligence?.label ?? modelIntelligenceLevel, note: "set from chat composer" },
            ]}
          />
        </SettingsSection>
        <SettingsSection title="Runtime" eyebrow="status">
          <SettingsRows
            rows={[
              { label: "API", value: <StatusBadge tone={status ? "ok" : "warning"}>{status ? "ready" : "unavailable"}</StatusBadge> },
              { label: "Streaming", value: <StatusBadge tone="ok">SSE available</StatusBadge> },
              { label: "Config health", value: <StatusBadge tone={status?.configValidation?.ok === false ? "warning" : "ok"}>{status?.configValidation?.ok === false ? "warnings" : "ok"}</StatusBadge> },
            ]}
          />
        </SettingsSection>
        <SettingsSection title="Session" eyebrow="current">
          <SettingsRows
            rows={[
              { label: "Session id", value: sessionId || "new session" },
              { label: "Thread id", value: threadId || "new thread" },
              { label: "Storage", value: stringValue(values.storage_dir, "unknown"), locked: true },
            ]}
          />
        </SettingsSection>
        <SettingsSection title="Safety" eyebrow="read-only">
          <SettingsRows
            rows={[
              { label: "Permission mode", value: stringValue(values.permission_mode, "unknown"), locked: true },
              { label: "Network", value: <StatusBadge tone={values.network_enabled ? "warning" : "neutral"}>{values.network_enabled ? "enabled" : "disabled"}</StatusBadge>, locked: true },
              { label: "Private web hosts", value: <StatusBadge tone={values.web_fetch_allow_private_hosts ? "danger" : "neutral"}>{values.web_fetch_allow_private_hosts ? "allowed" : "blocked"}</StatusBadge>, locked: true },
            ]}
          />
        </SettingsSection>
      </div>
    </div>
  );
}

function effectiveModel(config: ConfigShowDTO | null): string {
  const values = config?.values ?? {};
  const provider = stringValue(values.llm_provider);
  if (provider === "openai") return stringValue(values.openai_model, stringValue(values.model_name, "unknown"));
  if (provider === "anthropic") return stringValue(values.anthropic_model, stringValue(values.model_name, "unknown"));
  if (provider === "ollama") return stringValue(values.ollama_model, stringValue(values.model_name, "unknown"));
  if (provider === "openai_compatible") return stringValue(values.openai_compatible_model, stringValue(values.model_name, "unknown"));
  return stringValue(values.model_name, "unknown");
}

function stringValue(value: unknown, fallback = ""): string {
  return typeof value === "string" && value ? value : fallback;
}
