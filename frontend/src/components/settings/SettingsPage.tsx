import type { RegistryMap } from "../../api/schemas.ts";
import type { RuntimeStatus } from "../../api/status.ts";
import type { ModelIntelligenceLevel } from "../../runtime/modelIntelligence.ts";
import type { RuntimeContextState } from "../../runtime/reducer.ts";
import { settingsTabDescription, settingsTabLabel, type SettingsTab } from "../../runtime/settingsPage.ts";
import type { UIPreferences } from "../../runtime/uiPreferences.ts";
import { AppearanceSettingsTab } from "./AppearanceSettingsTab.tsx";
import { ConfigurationSettingsTab } from "./ConfigurationSettingsTab.tsx";
import { GeneralSettingsTab } from "./GeneralSettingsTab.tsx";
import { MCPServersSettingsTab } from "./MCPServersSettingsTab.tsx";
import { PluginsSettingsTab } from "./PluginsSettingsTab.tsx";
import { SkillsSettingsTab } from "./SkillsSettingsTab.tsx";
import "./settings.css";

export function SettingsPage({
  activeTab,
  status,
  skills,
  context,
  contextMaxTokens,
  modelIntelligenceLevel,
  preferences,
  sessionId,
  threadId,
  onPreferencesChange,
}: {
  activeTab: SettingsTab;
  status: RuntimeStatus | null;
  skills: RegistryMap;
  context: RuntimeContextState;
  contextMaxTokens: number | null;
  modelIntelligenceLevel: ModelIntelligenceLevel;
  preferences: UIPreferences;
  sessionId: string | null;
  threadId: string | null;
  onPreferencesChange: (patch: Partial<UIPreferences>) => void;
}) {
  const activeTabDescription = settingsTabDescription(activeTab);
  const showPageHeader = activeTab !== "mcp";
  return (
    <section className="settings-page" aria-label="Настройки">
      <div className="settings-page-shell">
        <div className="settings-page-content">
          {showPageHeader ? (
            <header className="settings-page-content-header">
              <h2>{settingsTabLabel(activeTab)}</h2>
              {activeTabDescription ? <p>{activeTabDescription}</p> : null}
            </header>
          ) : null}
          {renderTab({
            activeTab,
            status,
            skills,
            context,
            contextMaxTokens,
            modelIntelligenceLevel,
            preferences,
            sessionId,
            threadId,
            onPreferencesChange,
          })}
        </div>
      </div>
    </section>
  );
}

function renderTab({
  activeTab,
  status,
  skills,
  modelIntelligenceLevel,
  preferences,
  sessionId,
  threadId,
  onPreferencesChange,
}: {
  activeTab: SettingsTab;
  status: RuntimeStatus | null;
  skills: RegistryMap;
  context: RuntimeContextState;
  contextMaxTokens: number | null;
  modelIntelligenceLevel: ModelIntelligenceLevel;
  preferences: UIPreferences;
  sessionId: string | null;
  threadId: string | null;
  onPreferencesChange: (patch: Partial<UIPreferences>) => void;
}) {
  switch (activeTab) {
    case "general":
      return <GeneralSettingsTab status={status} sessionId={sessionId} threadId={threadId} modelIntelligenceLevel={modelIntelligenceLevel} />;
    case "appearance":
      return <AppearanceSettingsTab preferences={preferences} onPreferencesChange={onPreferencesChange} />;
    case "configuration":
      return <ConfigurationSettingsTab config={status?.config ?? null} explain={status?.configExplain ?? null} validation={status?.configValidation ?? null} />;
    case "mcp":
      return <MCPServersSettingsTab status={status?.mcp ?? null} mcpConfig={status?.config?.values?.mcp_config ?? null} />;
    case "plugins":
      return <PluginsSettingsTab status={status?.plugins ?? null} />;
    case "skills":
      return <SkillsSettingsTab skills={skills} />;
    default:
      return <GeneralSettingsTab status={status} sessionId={sessionId} threadId={threadId} modelIntelligenceLevel={modelIntelligenceLevel} />;
  }
}
