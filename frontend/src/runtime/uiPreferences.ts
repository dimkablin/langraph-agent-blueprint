import type { RuntimeEvent } from "../api/schemas.ts";

export type UITheme = "system" | "light" | "dark";
export type ThemeVariant = "light" | "dark";
export type ThemePresetId = "codex" | "matrix" | "temple" | "everforest" | "notion" | "github";
export type UIDensity = "comfortable" | "compact";
export type EventVerbosity = "essential" | "normal" | "debug";

export type ThemeSemanticColors = {
  diffAdded: string;
  diffRemoved: string;
  skill: string;
};

export type ThemeConfig = {
  preset: ThemePresetId;
  codeThemeId: string;
  accent: string;
  surface: string;
  ink: string;
  uiFont: string;
  codeFont: string;
  opaqueWindows: boolean;
  semanticColors: ThemeSemanticColors;
  contrast: number;
  uiFontSize: number;
  codeFontSize: number;
  usePointerCursor: boolean;
};

export type ThemePreferences = Record<ThemeVariant, ThemeConfig>;

export type ThemePresetOption = {
  value: ThemePresetId;
  label: string;
  description: string;
};

export type UIPreferences = {
  theme: UITheme;
  themes: ThemePreferences;
  density: UIDensity;
  eventVerbosity: EventVerbosity;
  blockRadius: number;
  autoScroll: boolean;
  showDebugEvents: boolean;
};

export type UIPreferencesStorage = {
  getItem(key: string): string | null;
  setItem(key: string, value: string): void;
  removeItem?(key: string): void;
};

export const UI_PREFERENCES_STORAGE_KEY = "lg-agent-ui-preferences";

export const THEME_VARIANTS: ThemeVariant[] = ["light", "dark"];

const DEFAULT_UI_FONT = "Inter";
const DEFAULT_CODE_FONT = "\"Jetbrains Mono\"";
const DEFAULT_DARK_CODE_FONT = "\"Geist Mono\", ui-monospace, \"SFMono-Regular\"";
const DARK_SIDEBAR_SURFACE_MIX = 72;
const DARK_SIDEBAR_SHADOW_SURFACE = "#000000";
export const UI_BLOCK_RADIUS_MIN = 0;
export const UI_BLOCK_RADIUS_MAX = 32;
export const DEFAULT_UI_BLOCK_RADIUS = 18;

const THEME_PRESETS: Record<ThemeVariant, ThemePresetOption[]> = {
  light: [
    { value: "codex", label: "Codex", description: "Clean light developer surface" },
    { value: "everforest", label: "Everforest", description: "Warm low-contrast light surface" },
    { value: "notion", label: "Notion", description: "Paper-like neutral surface" },
    { value: "github", label: "GitHub", description: "GitHub light developer surface" },
  ],
  dark: [
    { value: "codex", label: "Codex", description: "Clean dark developer surface" },
    { value: "matrix", label: "Matrix", description: "Monospace terminal surface" },
    { value: "temple", label: "Temple", description: "High-contrast dark temple surface" },
    { value: "github", label: "GitHub", description: "GitHub dark developer surface" },
  ],
};

export const THEME_PRESET_OPTIONS: readonly ThemePresetOption[] = [
  ...THEME_PRESETS.light,
  ...THEME_PRESETS.dark.filter((darkPreset) => !THEME_PRESETS.light.some((lightPreset) => lightPreset.value === darkPreset.value)),
];

export const DEFAULT_THEME_PREFERENCES: ThemePreferences = {
  light: {
    preset: "codex",
    codeThemeId: "codex",
    accent: "#0169cc",
    surface: "#ffffff",
    ink: "#0d0d0d",
    uiFont: DEFAULT_UI_FONT,
    codeFont: DEFAULT_CODE_FONT,
    opaqueWindows: false,
    semanticColors: {
      diffAdded: "#00a240",
      diffRemoved: "#e02e2a",
      skill: "#751ed9",
    },
    contrast: 45,
    uiFontSize: 13,
    codeFontSize: 12,
    usePointerCursor: true,
  },
  dark: {
    preset: "codex",
    codeThemeId: "codex",
    accent: "#0169cc",
    surface: "#111111",
    ink: "#fcfcfc",
    uiFont: DEFAULT_UI_FONT,
    codeFont: DEFAULT_DARK_CODE_FONT,
    opaqueWindows: true,
    semanticColors: {
      diffAdded: "#00a240",
      diffRemoved: "#e02e2a",
      skill: "#b06dff",
    },
    contrast: 49,
    uiFontSize: 13,
    codeFontSize: 12,
    usePointerCursor: true,
  },
};

const THEME_PRESET_CONFIGS: Record<ThemeVariant, Partial<Record<ThemePresetId, ThemeConfig>>> = {
  light: {
    codex: DEFAULT_THEME_PREFERENCES.light,
    everforest: {
      ...DEFAULT_THEME_PREFERENCES.light,
      preset: "everforest",
      codeThemeId: "everforest",
      accent: "#93b259",
      surface: "#fdf6e3",
      ink: "#5c6a72",
      uiFont: DEFAULT_UI_FONT,
      codeFont: DEFAULT_CODE_FONT,
      opaqueWindows: true,
      semanticColors: {
        diffAdded: "#8da101",
        diffRemoved: "#f85552",
        skill: "#df69ba",
      },
      contrast: 40,
    },
    notion: {
      ...DEFAULT_THEME_PREFERENCES.light,
      preset: "notion",
      codeThemeId: "notion",
      accent: "#3183d8",
      surface: "#ffffff",
      ink: "#37352f",
      uiFont: DEFAULT_UI_FONT,
      codeFont: DEFAULT_CODE_FONT,
      opaqueWindows: true,
      semanticColors: {
        diffAdded: "#008000",
        diffRemoved: "#a31515",
        skill: "#0000ff",
      },
      contrast: 40,
    },
    github: {
      ...DEFAULT_THEME_PREFERENCES.light,
      preset: "github",
      codeThemeId: "github",
      accent: "#0969da",
      surface: "#ffffff",
      ink: "#1f2328",
      uiFont: DEFAULT_UI_FONT,
      codeFont: DEFAULT_CODE_FONT,
      opaqueWindows: true,
      semanticColors: {
        diffAdded: "#1a7f37",
        diffRemoved: "#cf222e",
        skill: "#8250df",
      },
      contrast: 40,
    },
  },
  dark: {
    codex: DEFAULT_THEME_PREFERENCES.dark,
    matrix: {
      ...DEFAULT_THEME_PREFERENCES.dark,
      preset: "matrix",
      codeThemeId: "matrix",
      accent: "#1eff5a",
      surface: "#040805",
      ink: "#b8ffca",
      uiFont: "ui-monospace, \"SFMono-Regular\", \"SF Mono\", Menlo, Consolas, \"Liberation Mono\", monospace",
      codeFont: DEFAULT_DARK_CODE_FONT,
      opaqueWindows: true,
      semanticColors: {
        diffAdded: "#1eff5a",
        diffRemoved: "#fa423e",
        skill: "#1eff5a",
      },
      contrast: 49,
    },
    temple: {
      ...DEFAULT_THEME_PREFERENCES.dark,
      preset: "temple",
      codeThemeId: "temple",
      accent: "#e4f222",
      surface: "#02120c",
      ink: "#c7e6da",
      uiFont: "Geist, Inter",
      codeFont: DEFAULT_DARK_CODE_FONT,
      opaqueWindows: true,
      semanticColors: {
        diffAdded: "#40c977",
        diffRemoved: "#fa423e",
        skill: "#e4f222",
      },
      contrast: 100,
    },
    github: {
      ...DEFAULT_THEME_PREFERENCES.dark,
      preset: "github",
      codeThemeId: "github",
      accent: "#1f6feb",
      surface: "#0d1117",
      ink: "#e6edf3",
      uiFont: DEFAULT_UI_FONT,
      codeFont: DEFAULT_DARK_CODE_FONT,
      opaqueWindows: true,
      semanticColors: {
        diffAdded: "#3fb950",
        diffRemoved: "#f85149",
        skill: "#bc8cff",
      },
      contrast: 49,
    },
  },
};

export const DEFAULT_UI_PREFERENCES: UIPreferences = {
  theme: "system",
  themes: DEFAULT_THEME_PREFERENCES,
  density: "comfortable",
  eventVerbosity: "normal",
  blockRadius: DEFAULT_UI_BLOCK_RADIUS,
  autoScroll: true,
  showDebugEvents: false,
};

const THEME_VALUES: UITheme[] = ["system", "light", "dark"];
const THEME_PRESET_VALUES: ThemePresetId[] = ["codex", "matrix", "temple", "everforest", "notion", "github"];
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

export function updateThemeConfig(
  current: UIPreferences,
  variant: ThemeVariant,
  patch: Partial<ThemeConfig>,
): UIPreferences {
  return normalizeUIPreferences({
    ...current,
    themes: {
      ...current.themes,
      [variant]: {
        ...current.themes[variant],
        ...patch,
      },
    },
  });
}

export function applyThemePreset(current: UIPreferences, variant: ThemeVariant, preset: ThemePresetId): UIPreferences {
  const config = THEME_PRESET_CONFIGS[variant][preset];
  if (!config) return current;
  return updateThemeConfig(current, variant, config);
}

export function themePresetOptionsForVariant(variant: ThemeVariant): readonly ThemePresetOption[] {
  return THEME_PRESETS[variant];
}

export function activeThemeVariant(theme: UITheme): ThemeVariant {
  return theme === "dark" ? "dark" : "light";
}

export function themeConfigForPreferences(preferences: UIPreferences): ThemeConfig {
  return preferences.themes[activeThemeVariant(preferences.theme)];
}

export function themeCSSVariables(preferences: UIPreferences): Record<`--${string}`, string> {
  const variant = activeThemeVariant(preferences.theme);
  const theme = themeConfigForPreferences(preferences);
  const contrast = theme.contrast;
  const sidebarMix = clampPercentage(99 - contrast * 0.07);
  const defaultSidebarSurface = `color-mix(in oklab, ${theme.surface} ${sidebarMix}%, ${theme.ink})`;
  const sidebarSurface =
    variant === "dark"
      ? `color-mix(in oklab, ${theme.surface} ${DARK_SIDEBAR_SURFACE_MIX}%, ${DARK_SIDEBAR_SHADOW_SURFACE})`
      : defaultSidebarSurface;
  const swapPageAndSidebar = variant === "dark" && (theme.preset === "codex" || theme.preset === "github");
  const fontScale = fontSizeScale(theme.uiFontSize, theme.codeFontSize);
  return {
    "--codex-theme-id": theme.codeThemeId,
    "--codex-theme-variant": variant,
    "--codex-accent": theme.accent,
    "--codex-surface": theme.surface,
    "--codex-background-surface": swapPageAndSidebar ? defaultSidebarSurface : theme.surface,
    "--codex-sidebar-surface": sidebarSurface,
    "--codex-ink": theme.ink,
    "--codex-contrast": String(theme.contrast),
    "--codex-opaque-windows": theme.opaqueWindows ? "1" : "0",
    "--codex-diff-added": theme.semanticColors.diffAdded,
    "--codex-diff-removed": theme.semanticColors.diffRemoved,
    "--codex-skill": theme.semanticColors.skill,
    "--theme-surface-1-mix": `${clampPercentage(99 - contrast * 0.05)}%`,
    "--theme-surface-2-mix": `${clampPercentage(98 - contrast * 0.08)}%`,
    "--theme-surface-3-mix": `${clampPercentage(97 - contrast * 0.14)}%`,
    "--theme-sidebar-mix": `${sidebarMix}%`,
    "--theme-terminal-mix": `${clampPercentage(98 - contrast * 0.12)}%`,
    "--theme-muted-mix": `${clampPercentage(46 + contrast * 0.32)}%`,
    "--theme-muted-weak-mix": `${clampPercentage(28 + contrast * 0.28)}%`,
    "--theme-border-mix": `${clampPercentage(8 + contrast * 0.08)}%`,
    "--theme-border-strong-mix": `${clampPercentage(12 + contrast * 0.12)}%`,
    "--theme-hover-mix": `${clampPercentage(3 + contrast * 0.05)}%`,
    "--theme-active-mix": `${clampPercentage(8 + contrast * 0.12)}%`,
    "--theme-primary-soft-mix": `${clampPercentage(6 + contrast * 0.08)}%`,
    "--font-sans": `${theme.uiFont}, ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif`,
    "--font-mono": `${theme.codeFont}, "Cascadia Code", ui-monospace, SFMono-Regular, Consolas, monospace`,
    "--app-ui-font-size": `${theme.uiFontSize}px`,
    "--app-code-font-size": `${theme.codeFontSize}px`,
    "--ui-element-radius": `${preferences.blockRadius}px`,
    ...fontScale,
    "--app-interactive-cursor": theme.usePointerCursor ? "pointer" : "default",
  };
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
    themes: normalizeThemePreferences(value.themes),
    density: pickValue(value.density, DENSITY_VALUES, DEFAULT_UI_PREFERENCES.density),
    eventVerbosity: pickValue(value.eventVerbosity, VERBOSITY_VALUES, DEFAULT_UI_PREFERENCES.eventVerbosity),
    blockRadius: normalizeNumber(value.blockRadius, UI_BLOCK_RADIUS_MIN, UI_BLOCK_RADIUS_MAX, DEFAULT_UI_PREFERENCES.blockRadius),
    autoScroll: typeof value.autoScroll === "boolean" ? value.autoScroll : DEFAULT_UI_PREFERENCES.autoScroll,
    showDebugEvents: typeof value.showDebugEvents === "boolean" ? value.showDebugEvents : DEFAULT_UI_PREFERENCES.showDebugEvents,
  };
}

function normalizeThemePreferences(value: unknown): ThemePreferences {
  const source = isRecord(value) ? value : {};
  return {
    light: normalizeThemeConfig(source.light, DEFAULT_THEME_PREFERENCES.light),
    dark: normalizeThemeConfig(source.dark, DEFAULT_THEME_PREFERENCES.dark),
  };
}

function normalizeThemeConfig(value: unknown, fallback: ThemeConfig): ThemeConfig {
  if (!isRecord(value)) return fallback;
  return {
    preset: pickValue(value.preset, THEME_PRESET_VALUES, fallback.preset),
    codeThemeId: normalizeThemeString(value.codeThemeId, fallback.codeThemeId),
    accent: normalizeHexColor(value.accent, fallback.accent),
    surface: normalizeHexColor(value.surface, fallback.surface),
    ink: normalizeHexColor(value.ink, fallback.ink),
    uiFont: normalizeThemeString(value.uiFont, fallback.uiFont),
    codeFont: normalizeThemeString(value.codeFont, fallback.codeFont),
    opaqueWindows: typeof value.opaqueWindows === "boolean" ? value.opaqueWindows : fallback.opaqueWindows,
    semanticColors: normalizeThemeSemanticColors(value.semanticColors, fallback.semanticColors),
    contrast: normalizeNumber(value.contrast, 0, 100, fallback.contrast),
    uiFontSize: normalizeNumber(value.uiFontSize, 11, 18, fallback.uiFontSize),
    codeFontSize: normalizeNumber(value.codeFontSize, 10, 18, fallback.codeFontSize),
    usePointerCursor: typeof value.usePointerCursor === "boolean" ? value.usePointerCursor : fallback.usePointerCursor,
  };
}

function normalizeThemeSemanticColors(value: unknown, fallback: ThemeSemanticColors): ThemeSemanticColors {
  const source = isRecord(value) ? value : {};
  return {
    diffAdded: normalizeHexColor(source.diffAdded, fallback.diffAdded),
    diffRemoved: normalizeHexColor(source.diffRemoved, fallback.diffRemoved),
    skill: normalizeHexColor(source.skill, fallback.skill),
  };
}

function normalizeHexColor(value: unknown, fallback: string): string {
  return typeof value === "string" && /^#[0-9a-fA-F]{6}$/.test(value) ? value.toLowerCase() : fallback;
}

function normalizeThemeString(value: unknown, fallback: string): string {
  if (typeof value !== "string") return fallback;
  const trimmed = value.trim();
  return trimmed.length > 0 && trimmed.length <= 120 ? trimmed : fallback;
}

function normalizeNumber(value: unknown, min: number, max: number, fallback: number): number {
  if (typeof value !== "number" || !Number.isFinite(value)) return fallback;
  return Math.min(max, Math.max(min, Math.round(value)));
}

function clampPercentage(value: number): number {
  return Math.min(99, Math.max(1, Number(value.toFixed(2))));
}

function fontSizeScale(uiFontSize: number, codeFontSize: number): Record<`--font-size-${string}`, string> {
  return {
    "--font-size-caption": `${Math.max(10, uiFontSize - 2)}px`,
    "--font-size-small": `${Math.max(11, uiFontSize - 1)}px`,
    "--font-size-body": `${uiFontSize}px`,
    "--font-size-body-lg": `${uiFontSize + 1}px`,
    "--font-size-title": `${uiFontSize + 7}px`,
    "--font-size-heading": `${uiFontSize + 9}px`,
    "--font-size-code": `${codeFontSize}px`,
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
