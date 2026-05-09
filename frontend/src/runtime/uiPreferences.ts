import type { RuntimeEvent } from "../api/schemas.ts";

export type UITheme = "system" | "light" | "dark";
export type UIDensity = "comfortable" | "compact";
export type EventVerbosity = "essential" | "normal" | "debug";

export type UIPreferences = {
  theme: UITheme;
  density: UIDensity;
  eventVerbosity: EventVerbosity;
  autoScroll: boolean;
  showDebugEvents: boolean;
};

export type UIPreferencesStorage = {
  getItem(key: string): string | null;
  setItem(key: string, value: string): void;
  removeItem?(key: string): void;
};

export const UI_PREFERENCES_STORAGE_KEY = "lg-agent-ui-preferences";

export const DEFAULT_UI_PREFERENCES: UIPreferences = {
  theme: "system",
  density: "comfortable",
  eventVerbosity: "normal",
  autoScroll: true,
  showDebugEvents: false,
};

const THEME_VALUES: UITheme[] = ["system", "light", "dark"];
const DENSITY_VALUES: UIDensity[] = ["comfortable", "compact"];
const VERBOSITY_VALUES: EventVerbosity[] = ["essential", "normal", "debug"];

const DEBUG_EVENT_TYPES = new Set([
  "hook_event",
  "mcp_tools_discovered",
  "mcp_resources_discovered",
  "mcp_prompts_discovered",
  "session_persisted",
]);

const ESSENTIAL_EVENT_TYPES = new Set([
  "final_response",
  "error",
  "permission_required",
  "permission_resolved",
  "tool_call_error",
  "subagent_error",
  "subagent_timeout",
  "context_resolution_error",
]);

export function loadUIPreferences(storage: UIPreferencesStorage | null = browserStorage()): UIPreferences {
  if (!storage) return DEFAULT_UI_PREFERENCES;
  const raw = storage.getItem(UI_PREFERENCES_STORAGE_KEY);
  if (!raw) return DEFAULT_UI_PREFERENCES;
  try {
    return normalizeUIPreferences(JSON.parse(raw));
  } catch {
    return DEFAULT_UI_PREFERENCES;
  }
}

export function saveUIPreferences(
  preferences: UIPreferences,
  storage: UIPreferencesStorage | null = browserStorage(),
): UIPreferences {
  const normalized = normalizeUIPreferences(preferences);
  storage?.setItem(UI_PREFERENCES_STORAGE_KEY, JSON.stringify(normalized));
  return normalized;
}

export function updateUIPreferences(current: UIPreferences, patch: Partial<UIPreferences>): UIPreferences {
  return normalizeUIPreferences({ ...current, ...patch });
}

export function filterEventsByPreferences(events: RuntimeEvent[], preferences: UIPreferences): RuntimeEvent[] {
  if (preferences.eventVerbosity === "debug" && preferences.showDebugEvents) return events;
  return events.filter((event) => {
    if (event.severity === "error") return true;
    if (preferences.eventVerbosity === "essential") {
      return ESSENTIAL_EVENT_TYPES.has(event.type);
    }
    if (!preferences.showDebugEvents && DEBUG_EVENT_TYPES.has(event.type)) {
      return false;
    }
    return true;
  });
}

function normalizeUIPreferences(value: unknown): UIPreferences {
  if (!isRecord(value)) return DEFAULT_UI_PREFERENCES;
  return {
    theme: pickValue(value.theme, THEME_VALUES, DEFAULT_UI_PREFERENCES.theme),
    density: pickValue(value.density, DENSITY_VALUES, DEFAULT_UI_PREFERENCES.density),
    eventVerbosity: pickValue(value.eventVerbosity, VERBOSITY_VALUES, DEFAULT_UI_PREFERENCES.eventVerbosity),
    autoScroll: typeof value.autoScroll === "boolean" ? value.autoScroll : DEFAULT_UI_PREFERENCES.autoScroll,
    showDebugEvents: typeof value.showDebugEvents === "boolean" ? value.showDebugEvents : DEFAULT_UI_PREFERENCES.showDebugEvents,
  };
}

function pickValue<T extends string>(value: unknown, choices: T[], fallback: T): T {
  return typeof value === "string" && choices.includes(value as T) ? (value as T) : fallback;
}

function browserStorage(): UIPreferencesStorage | null {
  return typeof localStorage === "undefined" ? null : localStorage;
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return Boolean(value) && typeof value === "object" && !Array.isArray(value);
}
