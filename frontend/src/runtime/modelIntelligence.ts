import type { ModelIntelligenceLevel } from "../api/schemas.ts";

export type { ModelIntelligenceLevel };

export type ModelIntelligenceOption = {
  id: ModelIntelligenceLevel;
  label: string;
};

export const MODEL_INTELLIGENCE_OPTIONS: ModelIntelligenceOption[] = [
  { id: "low", label: "Низкий" },
  { id: "medium", label: "Средний" },
  { id: "high", label: "Высокий" },
  { id: "very_high", label: "Очень высокий" },
];

export const DEFAULT_MODEL_INTELLIGENCE_LEVEL: ModelIntelligenceLevel = "medium";

export function modelIntelligenceOptionById(level: ModelIntelligenceLevel): ModelIntelligenceOption {
  return MODEL_INTELLIGENCE_OPTIONS.find((option) => option.id === level) ?? MODEL_INTELLIGENCE_OPTIONS[0];
}
