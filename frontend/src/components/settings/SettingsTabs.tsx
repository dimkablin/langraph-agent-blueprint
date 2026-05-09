import { SETTINGS_TABS, type SettingsTab } from "../../runtime/settingsPage.ts";

export function SettingsTabs({
  activeTab,
  onChange,
}: {
  activeTab: SettingsTab;
  onChange: (tab: SettingsTab) => void;
}) {
  return (
    <nav className="settings-tabs" aria-label="Settings sections">
      {SETTINGS_TABS.map((tab) => (
        <button
          type="button"
          className={tab.id === activeTab ? "settings-tab settings-tab-active" : "settings-tab"}
          key={tab.id}
          aria-selected={tab.id === activeTab}
          onClick={() => onChange(tab.id)}
        >
          <strong>{tab.label}</strong>
          <span>{tab.description}</span>
        </button>
      ))}
    </nav>
  );
}
