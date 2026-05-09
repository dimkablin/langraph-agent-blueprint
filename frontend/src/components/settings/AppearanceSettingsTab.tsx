import type { UIPreferences } from "../../runtime/uiPreferences.ts";
import { UIPreferencesSection } from "./UIPreferencesSection.tsx";

export function AppearanceSettingsTab({
  preferences,
  onPreferencesChange,
}: {
  preferences: UIPreferences;
  onPreferencesChange: (patch: Partial<UIPreferences>) => void;
}) {
  return (
    <div className="settings-tab-panel" aria-label="Внешний вид">
      <UIPreferencesSection preferences={preferences} onChange={onPreferencesChange} />
    </div>
  );
}
