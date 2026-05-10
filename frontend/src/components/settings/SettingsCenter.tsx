import type { RegistryMap } from "../../api/schemas.ts";
import type { RuntimeStatus } from "../../api/status.ts";
import type { ModelIntelligenceLevel } from "../../runtime/modelIntelligence.ts";
import type { RuntimeContextState } from "../../runtime/reducer.ts";
import { DEFAULT_SETTINGS_TAB, type SettingsTab } from "../../runtime/settingsPage.ts";
import type { UIPreferences } from "../../runtime/uiPreferences.ts";
import { SettingsPage } from "./SettingsPage.tsx";

export function SettingsCenter({
  status,
  skills,
  context,
  contextMaxTokens,
  modelIntelligenceLevel,
  preferences,
  onPreferencesChange,
  activeTab = DEFAULT_SETTINGS_TAB,
  sessionId = null,
  threadId = null,
}: {
  status: RuntimeStatus | null;
  skills: RegistryMap;
  context: RuntimeContextState;
  contextMaxTokens: number | null;
  modelIntelligenceLevel: ModelIntelligenceLevel;
  preferences: UIPreferences;
  onPreferencesChange: (patch: Partial<UIPreferences>) => void;
  activeTab?: SettingsTab;
  sessionId?: string | null;
  threadId?: string | null;
}) {
  return (
    <SettingsPage
      activeTab={activeTab}
      status={status}
      skills={skills}
      context={context}
      contextMaxTokens={contextMaxTokens}
      modelIntelligenceLevel={modelIntelligenceLevel}
      preferences={preferences}
      sessionId={sessionId}
      threadId={threadId}
      onPreferencesChange={onPreferencesChange}
    />
  );
}
