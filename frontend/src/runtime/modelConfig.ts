import type { ConfigShowDTO } from "../api/schemas.ts";

const PROVIDER_MODEL_KEYS: Record<string, string> = {
  anthropic: "anthropic_model",
  ollama: "ollama_model",
  openai: "openai_model",
  openai_compatible: "openai_compatible_model",
};

export function effectiveModelName(config: ConfigShowDTO | null | undefined): string {
  const values = config?.values ?? {};
  const fallbackModel = stringValue(values.model_name, "unknown");
  const provider = stringValue(values.llm_provider);
  const providerModelKey = provider ? PROVIDER_MODEL_KEYS[provider] : undefined;

  return providerModelKey ? stringValue(values[providerModelKey], fallbackModel) : fallbackModel;
}

function stringValue(value: unknown, fallback = ""): string {
  return typeof value === "string" && value ? value : fallback;
}
