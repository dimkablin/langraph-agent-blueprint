import type { RegistryMap } from "../../api/schemas.ts";
import type { RuntimeStatus } from "../../api/status.ts";
import type { ModelIntelligenceLevel } from "../../runtime/modelIntelligence.ts";
import type { RuntimeContextState } from "../../runtime/reducer.ts";
import type { UIPreferences } from "../../runtime/uiPreferences.ts";
import { ContextSettingsSection } from "./ContextSettingsSection.tsx";
import { HookSettingsSection } from "./HookSettingsSection.tsx";
import { MCPSettingsSection } from "./MCPSettingsSection.tsx";
import { ModelSettingsSection } from "./ModelSettingsSection.tsx";
import { ObservabilitySettingsSection } from "./ObservabilitySettingsSection.tsx";
import { PluginSettingsSection } from "./PluginSettingsSection.tsx";
import { RuntimeSettingsSection } from "./RuntimeSettingsSection.tsx";
import { SkillSettingsSection } from "./SkillSettingsSection.tsx";
import { SettingsRows, SettingsSection, StatusBadge } from "./SettingsSection.tsx";
import { UIPreferencesSection } from "./UIPreferencesSection.tsx";
import "./settings.css";

export function SettingsCenter({
  status,
  skills,
  context,
  contextMaxTokens,
  modelIntelligenceLevel,
  preferences,
  onPreferencesChange,
}: {
  status: RuntimeStatus | null;
  skills: RegistryMap;
  context: RuntimeContextState;
  contextMaxTokens: number | null;
  modelIntelligenceLevel: ModelIntelligenceLevel;
  preferences: UIPreferences;
  onPreferencesChange: (patch: Partial<UIPreferences>) => void;
}) {
  return (
    <div className="settings-center" aria-label="Settings Center">
      <SettingsSection title="Overview" eyebrow="read-only">
        <SettingsRows
          rows={[
            { label: "Backend settings", value: <StatusBadge>read-only</StatusBadge>, note: "no browser-side config writes" },
            { label: "Config health", value: status?.configValidation?.ok === false ? <StatusBadge tone="warning">warnings</StatusBadge> : <StatusBadge tone="ok">ok</StatusBadge> },
            { label: "Config sources", value: String(status?.configExplain?.sources.length ?? 0) },
            { label: "Dangerous settings", value: <StatusBadge tone="warning">config file only</StatusBadge>, note: "keys, MCP commands, plugin installs, and network trust are locked" },
          ]}
        />
      </SettingsSection>
      <ModelSettingsSection config={status?.config ?? null} intelligenceLevel={modelIntelligenceLevel} />
      <RuntimeSettingsSection config={status?.config ?? null} />
      <UIPreferencesSection preferences={preferences} onChange={onPreferencesChange} />
      <PluginSettingsSection status={status?.plugins ?? null} />
      <SkillSettingsSection skills={skills} />
      <HookSettingsSection status={status?.hooks ?? null} />
      <MCPSettingsSection status={status?.mcp ?? null} />
      <ContextSettingsSection config={status?.config ?? null} context={context} configuredMaxTokens={contextMaxTokens} />
      <ObservabilitySettingsSection status={status?.observability ?? null} />
    </div>
  );
}
