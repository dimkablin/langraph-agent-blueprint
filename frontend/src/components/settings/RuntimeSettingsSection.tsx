import type { ConfigShowDTO } from "../../api/schemas.ts";
import { SettingsRows, SettingsSection, StatusBadge } from "./SettingsSection.tsx";

export function RuntimeSettingsSection({ config }: { config: ConfigShowDTO | null }) {
  const values = config?.values ?? {};
  return (
    <SettingsSection title="Runtime" eyebrow="read-only safety posture">
      <SettingsRows
        rows={[
          { label: "Permission mode", value: stringValue(values.permission_mode, "unknown"), locked: true, note: "config file only" },
          { label: "Network", value: <StatusBadge tone={values.network_enabled ? "warning" : "neutral"}>{values.network_enabled ? "enabled" : "disabled"}</StatusBadge>, locked: true },
          { label: "Streaming", value: <StatusBadge tone="ok">SSE enabled</StatusBadge> },
          { label: "Shell timeout", value: seconds(values.shell_timeout_seconds), locked: true },
          { label: "Tool output limit", value: numberValue(values.tool_output_limit), locked: true },
          { label: "Auto compact threshold", value: numberValue(values.auto_compact_threshold), locked: true },
          { label: "Recent messages after compact", value: numberValue(values.max_recent_messages_after_compact), locked: true },
        ]}
      />
    </SettingsSection>
  );
}

function seconds(value: unknown): string {
  return typeof value === "number" ? `${value}s` : "unknown";
}

function numberValue(value: unknown): string {
  return typeof value === "number" ? String(value) : "unknown";
}

function stringValue(value: unknown, fallback: string): string {
  return typeof value === "string" && value ? value : fallback;
}
