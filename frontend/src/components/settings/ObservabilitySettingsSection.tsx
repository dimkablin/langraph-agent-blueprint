import type { ObservabilityStatusDTO } from "../../api/schemas.ts";
import { SettingsRows, SettingsSection, StatusBadge } from "./SettingsSection.tsx";

export function ObservabilitySettingsSection({ status }: { status: ObservabilityStatusDTO | null }) {
  return (
    <SettingsSection title="Observability" eyebrow="read-only privacy">
      <SettingsRows
        rows={[
          { label: "Langfuse", value: <StatusBadge tone={status?.enabled ? "ok" : "neutral"}>{status?.enabled ? "enabled" : "disabled"}</StatusBadge>, locked: true },
          { label: "SDK", value: <StatusBadge tone={status?.sdk_installed ? "ok" : "warning"}>{status?.sdk_installed ? "installed" : "missing"}</StatusBadge> },
          { label: "Base URL", value: status?.base_url_configured ? "configured" : "not configured", locked: true },
          { label: "Public key", value: status?.public_key_present ? "present" : "missing", locked: true, note: "value hidden" },
          { label: "Secret key", value: status?.secret_key_present ? "present" : "missing", locked: true, note: "value hidden" },
          { label: "Environment", value: status?.environment || "unknown" },
          { label: "Release", value: status?.release || "unknown" },
          { label: "Capture inputs", value: status?.capture_inputs ? "enabled" : "disabled", locked: true },
          { label: "Capture outputs", value: status?.capture_outputs ? "enabled" : "disabled", locked: true },
          { label: "Runtime events", value: status?.runtime_events_mode || status?.mode || "unknown", locked: true },
        ]}
      />
      {status?.last_error ? <p className="settings-warning">{status.last_error}</p> : null}
    </SettingsSection>
  );
}
