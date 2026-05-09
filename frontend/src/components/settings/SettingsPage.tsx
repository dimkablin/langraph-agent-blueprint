import { useState } from "react";

import type { RegistryMap } from "../../api/schemas.ts";
import type { RuntimeStatus } from "../../api/status.ts";
import type { ModelIntelligenceLevel } from "../../runtime/modelIntelligence.ts";
import type { RuntimeContextState } from "../../runtime/reducer.ts";
import { DEFAULT_SETTINGS_TAB, settingsTabLabel, type SettingsTab } from "../../runtime/settingsPage.ts";
import type { UIPreferences } from "../../runtime/uiPreferences.ts";
import { AppearanceSettingsTab } from "./AppearanceSettingsTab.tsx";
import { ConfigurationSettingsTab } from "./ConfigurationSettingsTab.tsx";
import { GeneralSettingsTab } from "./GeneralSettingsTab.tsx";
import { MCPServersSettingsTab } from "./MCPServersSettingsTab.tsx";
import { PluginsSettingsTab } from "./PluginsSettingsTab.tsx";
import { SettingsTabs } from "./SettingsTabs.tsx";
import { SkillsSettingsTab } from "./SkillsSettingsTab.tsx";
import "./settings.css";

export function SettingsPage({
  status,
  skills,
  context,
  contextMaxTokens,
  modelIntelligenceLevel,
  preferences,
  sessionId,
  threadId,
  onPreferencesChange,
  onBack,
}: {
  status: RuntimeStatus | null;
  skills: RegistryMap;
  context: RuntimeContextState;
  contextMaxTokens: number | null;
  modelIntelligenceLevel: ModelIntelligenceLevel;
  preferences: UIPreferences;
  sessionId: string | null;
  threadId: string | null;
  onPreferencesChange: (patch: Partial<UIPreferences>) => void;
  onBack: () => void;
}) {
  const [activeTab, setActiveTab] = useState<SettingsTab>(DEFAULT_SETTINGS_TAB);

  return (
    <section className="settings-page" aria-label="Настройки">
      <div className="settings-page-shell">
        <aside className="settings-page-sidebar">
          <button type="button" className="settings-back-button" onClick={onBack}>
            Back to chat
          </button>
          <div className="settings-page-title">
            <span>Runtime settings</span>
            <h1>Настройки</h1>
            <p>Backend/runtime settings are read-only. Config file only changes stay locked; interface preferences stay local to this browser.</p>
          </div>
          <SettingsTabs activeTab={activeTab} onChange={setActiveTab} />
        </aside>
        <div className="settings-page-content">
          <header className="settings-page-content-header">
            <div>
              <span>Settings</span>
              <h2>{settingsTabLabel(activeTab)}</h2>
            </div>
          </header>
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
  switch (activeTab) {
    case "general":
      return <GeneralSettingsTab status={status} sessionId={sessionId} threadId={threadId} modelIntelligenceLevel={modelIntelligenceLevel} />;
    case "appearance":
      return <AppearanceSettingsTab preferences={preferences} onPreferencesChange={onPreferencesChange} />;
    case "configuration":
      return <ConfigurationSettingsTab config={status?.config ?? null} explain={status?.configExplain ?? null} validation={status?.configValidation ?? null} />;
    case "mcp":
      return <MCPServersSettingsTab status={status?.mcp ?? null} />;
    case "plugins":
      return <PluginsSettingsTab status={status?.plugins ?? null} />;
    case "skills":
      return <SkillsSettingsTab skills={skills} />;
    default:
      return <GeneralSettingsTab status={status} sessionId={sessionId} threadId={threadId} modelIntelligenceLevel={modelIntelligenceLevel} />;
  }
}
