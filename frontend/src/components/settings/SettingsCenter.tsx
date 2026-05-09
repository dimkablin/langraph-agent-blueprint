import type { RegistryMap } from "../../api/schemas.ts";
import type { RuntimeStatus } from "../../api/status.ts";
import type { ModelIntelligenceLevel } from "../../runtime/modelIntelligence.ts";
import type { RuntimeContextState } from "../../runtime/reducer.ts";
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
  sessionId = null,
  threadId = null,
  onBack = () => undefined,
}: {
  status: RuntimeStatus | null;
  skills: RegistryMap;
  context: RuntimeContextState;
  contextMaxTokens: number | null;
  modelIntelligenceLevel: ModelIntelligenceLevel;
  preferences: UIPreferences;
  onPreferencesChange: (patch: Partial<UIPreferences>) => void;
  sessionId?: string | null;
  threadId?: string | null;
  onBack?: () => void;
}) {
  return (
    <SettingsPage
      status={status}
      skills={skills}
      context={context}
      contextMaxTokens={contextMaxTokens}
      modelIntelligenceLevel={modelIntelligenceLevel}
      preferences={preferences}
      sessionId={sessionId}
      threadId={threadId}
      onPreferencesChange={onPreferencesChange}
      onBack={onBack}
    />
  );
}
