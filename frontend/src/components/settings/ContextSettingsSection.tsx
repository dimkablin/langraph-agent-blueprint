import type { ConfigShowDTO } from "../../api/schemas.ts";
import type { RuntimeContextState } from "../../runtime/reducer.ts";
import { SettingsRows, SettingsSection, StatusBadge } from "./SettingsSection.tsx";

export function ContextSettingsSection({
  config,
  context,
  configuredMaxTokens,
}: {
  config: ConfigShowDTO | null;
  context: RuntimeContextState;
  configuredMaxTokens: number | null;
}) {
  const values = config?.values ?? {};
  const budget = context.budget ?? {};
  return (
    <SettingsSection title="Context" eyebrow="read-only budget">
      <SettingsRows
        rows={[
          { label: "Max context tokens", value: tokenValue(configuredMaxTokens ?? values.context_max_tokens), locked: true, note: "config file only" },
          { label: "Max file bytes", value: numberValue(values.context_max_file_bytes), locked: true },
          { label: "Max directory files", value: numberValue(values.context_max_directory_files), locked: true },
          { label: "Max glob files", value: numberValue(values.context_max_glob_files), locked: true },
          { label: "Current session budget", value: `${numberValue(budget.used_tokens)} / ${tokenValue(budget.max_tokens)}` },
          { label: "Fragments", value: String(context.fragments.length) },
        ]}
      />
      <p className="settings-help">
        Context is rendered as data, not instruction. External, MCP, and plugin context should be treated as untrusted prompt content.
      </p>
      <div className="settings-inline-badges">
        <StatusBadge>trusted_local</StatusBadge>
        <StatusBadge>mcp_external</StatusBadge>
        <StatusBadge>plugin_provided</StatusBadge>
        <StatusBadge>untrusted_external</StatusBadge>
      </div>
    </SettingsSection>
  );
}

function numberValue(value: unknown): string {
  return typeof value === "number" ? String(value) : "unknown";
}

function tokenValue(value: unknown): string {
  return typeof value === "number" ? `${formatCompact(value)} tokens` : "unknown";
}

function formatCompact(value: number): string {
  return value >= 1000 ? `${Math.round(value / 1000)}k` : String(value);
}
