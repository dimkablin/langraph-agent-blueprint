import type { UIPreferences } from "../../runtime/uiPreferences.ts";
import { ThemeAppearanceSection } from "./ThemeAppearanceSection.tsx";
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
      <ThemeAppearanceSection preferences={preferences} onChange={onPreferencesChange} />
      <UIPreferencesSection preferences={preferences} onChange={onPreferencesChange} />
    </div>
  );
}
