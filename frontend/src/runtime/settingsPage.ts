export const SETTINGS_TABS = [
  {
    id: "general",
    label: "Общее",
    description: "Runtime, model, session, and safety status.",
  },
  {
    id: "appearance",
    label: "Внешний вид",
    description: "Local interface preferences stored in this browser.",
  },
  {
    id: "configuration",
    label: "Конфигурация",
    description: "Read-only effective config, sources, and diagnostics.",
  },
  {
    id: "mcp",
    label: "Серверы MCP",
    description: "Passive MCP snapshot without starting servers.",
  },
  {
    id: "plugins",
    label: "Плагины",
    description: "Installed plugin manifests and contribution counts.",
  },
  {
    id: "skills",
    label: "Скилы",
    description: "Registered built-in and plugin skills.",
  },
] as const;

export type SettingsTab = (typeof SETTINGS_TABS)[number]["id"];

export const DEFAULT_SETTINGS_TAB: SettingsTab = "general";

const SETTINGS_TAB_IDS = new Set<string>(SETTINGS_TABS.map((tab) => tab.id));

export function isSettingsTab(value: string): value is SettingsTab {
  return SETTINGS_TAB_IDS.has(value);
}

export function settingsTabLabel(tabId: SettingsTab): string {
  return SETTINGS_TABS.find((tab) => tab.id === tabId)?.label ?? tabId;
}
