import { IconMonitor, IconMoon, IconSun } from "../../icons.ts";
import {
  UI_BLOCK_RADIUS_MAX,
  UI_BLOCK_RADIUS_MIN,
  activeThemeVariant,
  applyThemePreset,
  type ThemeConfig,
  type ThemeVariant,
  type UIPreferences,
  themePresetOptionsForVariant,
  updateThemeConfig,
} from "../../runtime/uiPreferences.ts";
import { SettingsSection } from "./SettingsSection.tsx";
import { SettingsSelect } from "./SettingsSelect.tsx";

const THEME_MODE_OPTIONS: {
  value: UIPreferences["theme"];
  label: string;
  icon: typeof IconSun;
}[] = [
  { value: "light", label: "Светлый", icon: IconSun },
  { value: "dark", label: "Темный", icon: IconMoon },
  { value: "system", label: "Системный", icon: IconMonitor },
];

export function ThemeAppearanceSection({
  preferences,
  onChange,
}: {
  preferences: UIPreferences;
  onChange: (patch: Partial<UIPreferences>) => void;
}) {
  const activeVariant = activeThemeVariant(preferences.theme);
  const activeTheme = preferences.themes[activeVariant];
  const presetOptions = themePresetOptionsForVariant(activeVariant);

  function updateActiveTheme(patch: Partial<ThemeConfig>) {
    const next = updateThemeConfig(preferences, activeVariant, patch);
    onChange({ themes: next.themes });
  }

  function applyPreset(preset: ThemeConfig["preset"]) {
    const next = applyThemePreset(preferences, activeVariant, preset);
    onChange({ themes: next.themes });
  }

  function copyTheme() {
    const payload = `codex-theme-v1:${JSON.stringify(toThemeExport(activeTheme, activeVariant))}`;
    void navigator.clipboard?.writeText(payload);
  }

  return (
    <SettingsSection title="Тема">
      <div className="theme-settings-header">
        <div>
          <strong>Внешний вид интерфейса</strong>
          <p>Используйте светлую, темную или системную тему. Параметры сохраняются только в браузере.</p>
        </div>
        <div className="theme-mode-toggle" aria-label="Theme mode">
          {THEME_MODE_OPTIONS.map((option) => {
            const Icon = option.icon;
            const isActive = preferences.theme === option.value;
            return (
              <button
                type="button"
                className={isActive ? "theme-mode-button theme-mode-button-active" : "theme-mode-button"}
                aria-pressed={isActive}
                key={option.value}
                onClick={() => onChange({ theme: option.value })}
              >
                <Icon size={15} />
                <span>{option.label}</span>
              </button>
            );
          })}
        </div>
      </div>

      <ThemePreview theme={activeTheme} variant={activeVariant} />

      <div className="theme-editor-card">
        <div className="theme-editor-toolbar">
          <strong>{activeVariant === "dark" ? "Темная тема" : "Светлая тема"}</strong>
          <div className="theme-editor-actions">
            <button type="button" className="theme-token-button" onClick={copyTheme}>
              Скопировать тему
            </button>
            <SettingsSelect label="Theme preset" value={activeTheme.preset} options={presetOptions} onChange={applyPreset} />
          </div>
        </div>
        <ThemeColorRow label="Акцентный цвет" value={activeTheme.accent} onChange={(accent) => updateActiveTheme({ accent })} />
        <ThemeColorRow label="Фон" value={activeTheme.surface} onChange={(surface) => updateActiveTheme({ surface })} />
        <ThemeColorRow label="Цвет переднего плана" value={activeTheme.ink} onChange={(ink) => updateActiveTheme({ ink })} />
        <ThemeColorRow
          label="Diff added"
          value={activeTheme.semanticColors.diffAdded}
          onChange={(diffAdded) => updateActiveTheme({ semanticColors: { ...activeTheme.semanticColors, diffAdded } })}
        />
        <ThemeColorRow
          label="Diff removed"
          value={activeTheme.semanticColors.diffRemoved}
          onChange={(diffRemoved) => updateActiveTheme({ semanticColors: { ...activeTheme.semanticColors, diffRemoved } })}
        />
        <ThemeColorRow
          label="Skill color"
          value={activeTheme.semanticColors.skill}
          onChange={(skill) => updateActiveTheme({ semanticColors: { ...activeTheme.semanticColors, skill } })}
        />
        <ThemeTextRow label="Шрифт интерфейса" value={activeTheme.uiFont} onChange={(uiFont) => updateActiveTheme({ uiFont })} />
        <ThemeTextRow label="Шрифт кода" value={activeTheme.codeFont} onChange={(codeFont) => updateActiveTheme({ codeFont })} />
        <ThemeSwitchRow
          label="Полупрозрачная боковая панель"
          checked={!activeTheme.opaqueWindows}
          onChange={(checked) => updateActiveTheme({ opaqueWindows: !checked })}
        />
        <ThemeRangeRow label="Контраст" value={activeTheme.contrast} min={0} max={100} onChange={(contrast) => updateActiveTheme({ contrast })} />
        <ThemeNumberRow label="Размер шрифта интерфейса" value={activeTheme.uiFontSize} onChange={(uiFontSize) => updateActiveTheme({ uiFontSize })} />
        <ThemeNumberRow label="Размер шрифта кода" value={activeTheme.codeFontSize} onChange={(codeFontSize) => updateActiveTheme({ codeFontSize })} />
        <ThemeRangeRow
          label="Радиус блоков"
          value={preferences.blockRadius}
          min={UI_BLOCK_RADIUS_MIN}
          max={UI_BLOCK_RADIUS_MAX}
          suffix="px"
          onChange={(blockRadius) => onChange({ blockRadius })}
        />
      </div>
    </SettingsSection>
  );
}

function ThemePreview({ theme, variant }: { theme: ThemeConfig; variant: ThemeVariant }) {
  const lines = [
    "const themePreview = {",
    `  codeThemeId: "${theme.codeThemeId}",`,
    `  surface: "${theme.surface}",`,
    `  accent: "${theme.accent}",`,
    `  contrast: ${theme.contrast},`,
    "};",
  ];
  return (
    <div className="theme-preview" aria-label="Theme preview">
      <PreviewPane lines={lines} tone="removed" />
      <PreviewPane lines={lines.map((line) => line.replace("themePreview", `${variant}Theme`))} tone="added" />
    </div>
  );
}

function PreviewPane({ lines, tone }: { lines: string[]; tone: "added" | "removed" }) {
  return (
    <div className={`theme-preview-pane theme-preview-pane-${tone}`}>
      {lines.map((line, index) => (
        <div className="theme-preview-line" key={`${tone}-${line}-${index}`}>
          <span>{index + 1}</span>
          <code>{line}</code>
        </div>
      ))}
    </div>
  );
}

function toThemeExport(theme: ThemeConfig, variant: ThemeVariant) {
  return {
    codeThemeId: theme.codeThemeId,
    theme: {
      accent: theme.accent,
      contrast: theme.contrast,
      fonts: {
        code: theme.codeFont,
        ui: theme.uiFont,
      },
      ink: theme.ink,
      opaqueWindows: theme.opaqueWindows,
      semanticColors: theme.semanticColors,
      surface: theme.surface,
    },
    variant,
  };
}

function ThemeColorRow({ label, value, onChange }: { label: string; value: string; onChange: (value: string) => void }) {
  return (
    <label className="theme-control-row">
      <span>{label}</span>
      <span className="theme-color-field">
        <span className="theme-color-picker">
          <span className="theme-color-swatch" style={{ backgroundColor: value }} aria-hidden="true" />
          <input type="color" value={value} onChange={(event) => onChange(event.target.value)} aria-label={label} />
        </span>
        <input type="text" value={value} onChange={(event) => onChange(event.target.value)} aria-label={`${label} value`} />
      </span>
    </label>
  );
}

function ThemeTextRow({ label, value, onChange }: { label: string; value: string; onChange: (value: string) => void }) {
  return (
    <label className="theme-control-row">
      <span>{label}</span>
      <input className="theme-text-field" type="text" value={value} onChange={(event) => onChange(event.target.value)} aria-label={label} />
    </label>
  );
}

function ThemeSwitchRow({
  label,
  note,
  checked,
  onChange,
}: {
  label: string;
  note?: string;
  checked: boolean;
  onChange: (checked: boolean) => void;
}) {
  return (
    <label className="theme-control-row">
      <span>
        {label}
        {note ? <small>{note}</small> : null}
      </span>
      <span className={checked ? "settings-switch settings-switch-on" : "settings-switch"}>
        <input type="checkbox" checked={checked} onChange={(event) => onChange(event.target.checked)} aria-label={label} />
        <span aria-hidden="true" />
      </span>
    </label>
  );
}

function ThemeRangeRow({
  label,
  value,
  min,
  max,
  suffix,
  onChange,
}: {
  label: string;
  value: number;
  min: number;
  max: number;
  suffix?: string;
  onChange: (value: number) => void;
}) {
  return (
    <label className="theme-control-row">
      <span>{label}</span>
      <span className="theme-range-field">
        <input type="range" min={min} max={max} value={value} onChange={(event) => onChange(Number(event.target.value))} aria-label={label} />
        <strong>{suffix ? `${value}${suffix}` : value}</strong>
      </span>
    </label>
  );
}

function ThemeNumberRow({ label, value, onChange }: { label: string; value: number; onChange: (value: number) => void }) {
  return (
    <label className="theme-control-row">
      <span>{label}</span>
      <span className="theme-number-field">
        <input type="number" min={10} max={18} value={value} onChange={(event) => onChange(Number(event.target.value))} aria-label={label} />
        <small>px</small>
      </span>
    </label>
  );
}
