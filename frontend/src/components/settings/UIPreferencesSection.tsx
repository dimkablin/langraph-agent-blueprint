import type { UIPreferences } from "../../runtime/uiPreferences.ts";
import { SettingsSection } from "./SettingsSection.tsx";
import { SettingsSelect, type SettingsSelectOption } from "./SettingsSelect.tsx";

const DENSITY_OPTIONS: readonly SettingsSelectOption<UIPreferences["density"]>[] = [
  { value: "comfortable", label: "Comfortable", description: "Default spacing" },
  { value: "compact", label: "Compact", description: "Tighter chat layout" },
];

const VERBOSITY_OPTIONS: readonly SettingsSelectOption<UIPreferences["eventVerbosity"]>[] = [
  { value: "essential", label: "Essential", description: "Only important runtime events" },
  { value: "normal", label: "Normal", description: "Balanced event timeline" },
  { value: "debug", label: "Debug", description: "Include low-signal events" },
];

export function UIPreferencesSection({
  preferences,
  onChange,
}: {
  preferences: UIPreferences;
  onChange: (patch: Partial<UIPreferences>) => void;
}) {
  return (
    <SettingsSection title="Поведение интерфейса">
      <div className="settings-control-grid">
        <div className="settings-control-row">
          <span>Density</span>
          <SettingsSelect label="Density" value={preferences.density} options={DENSITY_OPTIONS} onChange={(density) => onChange({ density })} />
        </div>
        <div className="settings-control-row">
          <span>Events</span>
          <SettingsSelect label="Events" value={preferences.eventVerbosity} options={VERBOSITY_OPTIONS} onChange={(eventVerbosity) => onChange({ eventVerbosity })} />
        </div>
      </div>
      <label className="settings-checkbox">
        <input type="checkbox" checked={preferences.autoScroll} onChange={(event) => onChange({ autoScroll: event.target.checked })} />
        Auto-scroll chat while streaming
      </label>
      <label className="settings-checkbox">
        <input type="checkbox" checked={preferences.showDebugEvents} onChange={(event) => onChange({ showDebugEvents: event.target.checked })} />
        Show debug/low-signal events
      </label>
    </SettingsSection>
  );
}
