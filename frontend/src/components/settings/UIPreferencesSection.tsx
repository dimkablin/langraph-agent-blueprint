import type { UIPreferences } from "../../runtime/uiPreferences.ts";
import { SettingsSection, StatusBadge } from "./SettingsSection.tsx";

export function UIPreferencesSection({
  preferences,
  onChange,
}: {
  preferences: UIPreferences;
  onChange: (patch: Partial<UIPreferences>) => void;
}) {
  return (
    <SettingsSection title="UI Preferences" eyebrow="local only">
      <div className="settings-control-grid">
        <label>
          Theme
          <select value={preferences.theme} onChange={(event) => onChange({ theme: event.target.value as UIPreferences["theme"] })}>
            <option value="system">System</option>
            <option value="dark">Dark</option>
            <option value="light">Light</option>
          </select>
        </label>
        <label>
          Density
          <select value={preferences.density} onChange={(event) => onChange({ density: event.target.value as UIPreferences["density"] })}>
            <option value="comfortable">Comfortable</option>
            <option value="compact">Compact</option>
          </select>
        </label>
        <label>
          Events
          <select value={preferences.eventVerbosity} onChange={(event) => onChange({ eventVerbosity: event.target.value as UIPreferences["eventVerbosity"] })}>
            <option value="essential">Essential</option>
            <option value="normal">Normal</option>
            <option value="debug">Debug</option>
          </select>
        </label>
      </div>
      <label className="settings-checkbox">
        <input type="checkbox" checked={preferences.autoScroll} onChange={(event) => onChange({ autoScroll: event.target.checked })} />
        Auto-scroll chat while streaming
      </label>
      <label className="settings-checkbox">
        <input type="checkbox" checked={preferences.showDebugEvents} onChange={(event) => onChange({ showDebugEvents: event.target.checked })} />
        Show debug/low-signal events
      </label>
      <p className="settings-help">
        These preferences are stored in localStorage and never write backend config.
      </p>
      <StatusBadge>frontend only</StatusBadge>
    </SettingsSection>
  );
}
