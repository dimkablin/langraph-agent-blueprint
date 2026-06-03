import type { RuntimeContextState } from "./reducer.ts";

export type ContextWindowSectionKind = "fragments" | "references" | "attachments" | "errors";

export type ContextBudgetView = {
  usedTokens: number | null;
  maxTokens: number | null;
  remainingTokens: number | null;
  percent: number | null;
};

export type ContextWindowRecordView = {
  key: string;
  title: string;
  preview: string | null;
  tokens: number | null;
  chips: string[];
  source: Record<string, unknown>;
};

export type ContextWindowSectionView = {
  kind: ContextWindowSectionKind;
  items: ContextWindowRecordView[];
};

export type ContextWindowView = {
  budget: ContextBudgetView;
  sections: ContextWindowSectionView[];
  hasContext: boolean;
};

const COLLAPSED_RECORD_PREVIEW_CHARS = 360;
const TEXT_KEYS = ["content", "preview", "text", "snippet", "body", "summary", "value"];
const TITLE_KEYS = ["title", "name", "path", "uri", "reference", "id"];
const TYPE_KEYS = ["kind", "type", "source", "provider", "trust", "trust_level"];

export function buildContextWindowView(
  context: RuntimeContextState,
  configuredMaxTokens?: number | null,
  usage?: Record<string, unknown> | null,
): ContextWindowView {
  const sections: ContextWindowSectionView[] = [
    { kind: "fragments", items: records(context.fragments, "Фрагмент") },
    { kind: "references", items: records(context.references, "Ссылка") },
    { kind: "attachments", items: records(context.attachments, "Вложение") },
    { kind: "errors", items: records(context.errors, "Ошибка") },
  ];
  return {
    budget: budgetView(context.budget, configuredMaxTokens, usage),
    sections,
    hasContext: sections.some((section) => section.items.length > 0) || Boolean(context.budget) || hasUsageBudget(usage),
  };
}

export function formatContextTokenCount(value: number | null): string {
  if (value == null) return "unknown";
  if (Math.abs(value) >= 1000) {
    return `${new Intl.NumberFormat(undefined, { maximumFractionDigits: 1 }).format(value / 1000)}к`;
  }
  return new Intl.NumberFormat(undefined, { maximumFractionDigits: 0 }).format(value);
}

export function formatContextBudgetLine(budget: ContextBudgetView, modelName = "unknown"): string {
  return `Контекст ${modelName}: ${formatContextTokenCount(budget.usedTokens)} / ${formatContextTokenCount(budget.maxTokens)} токенов`;
}

export function isExpandableContextRecord(item: ContextWindowRecordView): boolean {
  return Boolean(item.preview && item.preview.length > COLLAPSED_RECORD_PREVIEW_CHARS);
}

export function contextRecordPreview(item: ContextWindowRecordView, expanded: boolean): string {
  if (!item.preview) return "Нет текстового превью.";
  if (expanded || !isExpandableContextRecord(item)) return item.preview;
  return `${item.preview.slice(0, COLLAPSED_RECORD_PREVIEW_CHARS).trimEnd()}...`;
}

function budgetView(
  budget: Record<string, unknown> | null,
  configuredMaxTokens?: number | null,
  usage?: Record<string, unknown> | null,
): ContextBudgetView {
  const usageBudget = usageBudgetView(usage, configuredMaxTokens ?? numberValue(budget?.max_tokens));
  if (usageBudget) return usageBudget;

  const maxTokens = numberValue(budget?.max_tokens) ?? configuredMaxTokens ?? null;
  const usedTokens = numberValue(budget?.used_tokens) ?? numberValue(budget?.total_tokens) ?? numberValue(budget?.tokens) ?? (maxTokens != null ? 0 : null);
  const remainingTokens = numberValue(budget?.remaining_tokens) ?? (usedTokens != null && maxTokens != null ? Math.max(maxTokens - usedTokens, 0) : null);
  const percent =
    usedTokens != null && maxTokens != null && maxTokens > 0 ? Math.min(100, Math.max(0, Math.round((usedTokens / maxTokens) * 100))) : null;

  return { usedTokens, maxTokens, remainingTokens, percent };
}

function usageBudgetView(usage?: Record<string, unknown> | null, fallbackMaxTokens?: number | null): ContextBudgetView | null {
  if (!usage || !hasUsageBudget(usage)) return null;
  const usedTokens =
    numberValue(usage.context_used) ??
    sumNumbers(numberValue(usage.input_tokens), numberValue(usage.output_tokens)) ??
    numberValue(usage.total_tokens) ??
    numberValue(usage.total);
  const maxTokens = numberValue(usage.context_max) ?? fallbackMaxTokens ?? null;
  const rawPercent = numberValue(usage.context_percent);
  const percent =
    rawPercent != null
      ? normalizePercent(rawPercent)
      : usedTokens != null && maxTokens != null && maxTokens > 0
        ? normalizePercent((usedTokens / maxTokens) * 100)
        : null;
  const remainingTokens = usedTokens != null && maxTokens != null ? Math.max(maxTokens - usedTokens, 0) : null;
  return { usedTokens, maxTokens, remainingTokens, percent };
}

function hasUsageBudget(usage?: Record<string, unknown> | null): boolean {
  return Boolean(
    usage &&
      (numberValue(usage.context_used) != null ||
        numberValue(usage.input_tokens) != null ||
        numberValue(usage.output_tokens) != null ||
        numberValue(usage.total_tokens) != null ||
        numberValue(usage.total) != null ||
        numberValue(usage.context_percent) != null),
  );
}

function sumNumbers(...values: Array<number | null>): number | null {
  const present = values.filter((value): value is number => value != null);
  return present.length > 0 ? present.reduce((total, value) => total + value, 0) : null;
}

function normalizePercent(value: number): number {
  return Math.min(100, Math.max(0, Math.round(value <= 1 ? value * 100 : value)));
}

function records(items: Record<string, unknown>[], fallbackTitle: string): ContextWindowRecordView[] {
  return items.map((item, index) => ({
    key: recordKey(item, index),
    title: firstString(item, TITLE_KEYS) || `${fallbackTitle} ${index + 1}`,
    preview: firstString(item, TEXT_KEYS),
    tokens: numberValue(item.token_estimate) ?? numberValue(item.tokens) ?? numberValue(item.estimated_tokens),
    chips: TYPE_KEYS.map((key) => firstString(item, [key]))
      .filter((value): value is string => Boolean(value))
      .slice(0, 4),
    source: item,
  }));
}

function recordKey(item: Record<string, unknown>, index: number): string {
  return firstString(item, ["id", "fragment_id", "attachment_id", "path", "uri"]) || `context-record-${index}`;
}

function firstString(item: Record<string, unknown>, keys: string[]): string | null {
  for (const key of keys) {
    const value = item[key];
    if (typeof value === "string" && value.trim()) return value;
    if (typeof value === "number" && Number.isFinite(value)) return String(value);
    if (Array.isArray(value)) {
      const text = value.filter((entry): entry is string => typeof entry === "string" && Boolean(entry.trim())).join(", ");
      if (text) return text;
    }
  }
  return null;
}

function numberValue(value: unknown): number | null {
  return typeof value === "number" && Number.isFinite(value) ? value : null;
}
