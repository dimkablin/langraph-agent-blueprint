import type { ReactElement } from "react";

import { SETTINGS_TABS, type SettingsTab } from "../../runtime/settingsPage.ts";
import {
  IconBlocks,
  IconCommand,
  IconFileText,
  IconSettings,
  IconShieldExclamation,
  IconSparkles,
  type AppIconProps,
} from "../../icons.ts";

type SettingsTabIcon = (props: AppIconProps) => ReactElement;

const SETTINGS_TAB_ICONS: Record<SettingsTab, SettingsTabIcon> = {
  general: IconSettings,
  appearance: IconSparkles,
  configuration: IconShieldExclamation,
  mcp: IconBlocks,
  plugins: IconCommand,
  skills: IconFileText,
};

export function SettingsTabs({
  activeTab,
  onChange,
  showDescriptions = false,
}: {
  activeTab: SettingsTab;
  onChange: (tab: SettingsTab) => void;
  showDescriptions?: boolean;
}) {
  return (
    <nav className="settings-tabs" aria-label="Settings sections">
      {SETTINGS_TABS.map((tab) => {
        const Icon = SETTINGS_TAB_ICONS[tab.id];

        return (
          <button
            type="button"
            className={tab.id === activeTab ? "settings-tab settings-tab-active" : "settings-tab"}
            key={tab.id}
            aria-selected={tab.id === activeTab}
            onClick={() => onChange(tab.id)}
          >
            <Icon size={16} />
            <strong>{tab.label}</strong>
            {showDescriptions ? <span>{tab.description}</span> : null}
          </button>
        );
      })}
    </nav>
  );
}
