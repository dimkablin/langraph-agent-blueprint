import type { ConfigShowDTO, ModelIntelligenceLevel } from "../../api/schemas.ts";
import { effectiveModelName } from "../../runtime/modelConfig.ts";
import { MODEL_INTELLIGENCE_OPTIONS } from "../../runtime/modelIntelligence.ts";
import { SettingsRows, SettingsSection, StatusBadge } from "./SettingsSection.tsx";

export function ModelSettingsSection({
  config,
  intelligenceLevel,
}: {
  config: ConfigShowDTO | null;
  intelligenceLevel: ModelIntelligenceLevel;
}) {
  const values = config?.values ?? {};
  const provider = stringValue(values.llm_provider, "unknown");
  const model = stringValue(values.model_name, "unknown");
  const effectiveModel = effectiveModelName(config);
  const selected = MODEL_INTELLIGENCE_OPTIONS.find((option) => option.id === intelligenceLevel);

  return (
    <SettingsSection title="Model" eyebrow="read-only backend">
      <SettingsRows
        rows={[
          { label: "Provider", value: provider, locked: true, note: "config file only" },
          { label: "Effective model", value: effectiveModel, locked: true, note: "config file only" },
          { label: "Default model", value: model, locked: true },
          {
            label: "API keys",
            value: (
              <span className="settings-inline-badges">
                <StatusBadge tone={present(values.openai_api_key) ? "ok" : "neutral"}>OpenAI {present(values.openai_api_key) ? "present" : "missing"}</StatusBadge>
                <StatusBadge tone={present(values.anthropic_api_key) ? "ok" : "neutral"}>Anthropic {present(values.anthropic_api_key) ? "present" : "missing"}</StatusBadge>
              </span>
            ),
            locked: true,
            note: "values are never shown",
          },
          { label: "Run intelligence", value: selected?.label ?? intelligenceLevel, note: "editable from the chat composer" },
        ]}
      />
    </SettingsSection>
  );
}

function present(value: unknown): boolean {
  return typeof value === "string" && value.length > 0;
}

function stringValue(value: unknown, fallback = ""): string {
  return typeof value === "string" && value ? value : fallback;
}
