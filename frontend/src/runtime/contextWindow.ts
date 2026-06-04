import type { RuntimeContextState } from "./reducer.ts";

export type ContextWindowSectionKind = "state";

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

export function buildContextWindowView(
  context: RuntimeContextState,
  configuredMaxTokens?: number | null,
  usage?: Record<string, unknown> | null,
): ContextWindowView {
  const sections: ContextWindowSectionView[] = [{ kind: "state", items: contextManagerStateRecords(context, configuredMaxTokens, usage) }];
  return {
    budget: budgetView(context.budget, configuredMaxTokens, usage, context.modelContext),
    sections,
    hasContext: sections.some((section) => section.items.length > 0) || hasUsageBudget(usage),
  };
}

export function formatContextTokenCount(value: number | null): string {
  if (value == null) return "unknown";
  if (Math.abs(value) >= 1000) {
    return `${new Intl.NumberFormat(undefined, { maximumFractionDigits: 1 }).format(value / 1000)}k`;
  }
  return new Intl.NumberFormat(undefined, { maximumFractionDigits: 0 }).format(value);
}

export function formatContextBudgetLine(budget: ContextBudgetView, modelName = "unknown"): string {
  return `Контекст ${modelName}: ${formatContextTokenCount(budget.usedTokens)} / ${formatContextTokenCount(budget.maxTokens)} tokens`;
}

export function isExpandableContextRecord(item: ContextWindowRecordView): boolean {
  return Boolean(item.preview && item.preview.length > COLLAPSED_RECORD_PREVIEW_CHARS);
}

export function contextRecordPreview(item: ContextWindowRecordView, expanded: boolean): string {
  if (!item.preview) return "No state payload.";
  if (expanded || !isExpandableContextRecord(item)) return item.preview;
  return `${item.preview.slice(0, COLLAPSED_RECORD_PREVIEW_CHARS).trimEnd()}...`;
}

function contextManagerStateRecords(
  context: RuntimeContextState,
  configuredMaxTokens?: number | null,
  usage?: Record<string, unknown> | null,
): ContextWindowRecordView[] {
  const budget = budgetView(context.budget, configuredMaxTokens, usage, context.modelContext);
  return [
    stateRecord("budget", "Budget report", budgetSource(context.budget, budget), ["budget"], tokenValue(budget.usedTokens)),
    stateRecord("references", "References", context.references, ["references", String(context.references.length)]),
    stateRecord("fragments", "Resolved fragments", context.fragments, ["fragments", String(context.fragments.length)], sumTokenEstimates(context.fragments)),
    stateRecord("attachments", "Attachments", context.attachments, ["attachments", String(context.attachments.length)]),
    stateRecord("model-context", "Model request report", context.modelContext, modelContextChips(context.modelContext), numberValue(context.modelContext?.used_tokens)),
    stateRecord("errors", "Resolution errors", context.errors, ["errors", String(context.errors.length)]),
  ].filter((item): item is ContextWindowRecordView => item !== null);
}

function stateRecord(
  key: string,
  title: string,
  payload: unknown,
  chips: string[],
  tokens: number | null = null,
): ContextWindowRecordView | null {
  if (isEmptyPayload(payload)) return null;
  return {
    key: `context-manager-${key}`,
    title,
    preview: statePreview(payload),
    tokens,
    chips,
    source: isRecord(payload) ? payload : { value: payload },
  };
}

function budgetSource(rawBudget: Record<string, unknown> | null, budget: ContextBudgetView): Record<string, unknown> {
  return {
    ...(rawBudget || {}),
    used_tokens: budget.usedTokens,
    max_tokens: budget.maxTokens,
    remaining_tokens: budget.remainingTokens,
    percent: budget.percent,
  };
}

function modelContextChips(modelContext?: Record<string, unknown> | null): string[] {
  const chips = ["model_context"];
  if (modelContext?.truncated === true) chips.push("truncated");
  return chips;
}

function statePreview(payload: unknown): string {
  if (typeof payload === "string") return payload;
  try {
    return JSON.stringify(payload, null, 2);
  } catch {
    return String(payload);
  }
}

function budgetView(
  budget: Record<string, unknown> | null,
  configuredMaxTokens?: number | null,
  usage?: Record<string, unknown> | null,
  modelContext?: Record<string, unknown> | null,
): ContextBudgetView {
  const modelContextBudget = modelContextBudgetView(modelContext);
  if (modelContextBudget) return modelContextBudget;

  const usageBudget = usageBudgetView(usage, configuredMaxTokens ?? numberValue(budget?.max_tokens));
  if (usageBudget) return usageBudget;

  const maxTokens = numberValue(budget?.max_tokens) ?? configuredMaxTokens ?? null;
  const usedTokens = numberValue(budget?.used_tokens) ?? numberValue(budget?.total_tokens) ?? numberValue(budget?.tokens) ?? (maxTokens != null ? 0 : null);
  const remainingTokens = numberValue(budget?.remaining_tokens) ?? (usedTokens != null && maxTokens != null ? Math.max(maxTokens - usedTokens, 0) : null);
  const percent =
    usedTokens != null && maxTokens != null && maxTokens > 0 ? Math.min(100, Math.max(0, Math.round((usedTokens / maxTokens) * 100))) : null;

  return { usedTokens, maxTokens, remainingTokens, percent };
}

function modelContextBudgetView(modelContext?: Record<string, unknown> | null): ContextBudgetView | null {
  if (!modelContext) return null;
  const usedTokens = numberValue(modelContext.used_tokens);
  const maxTokens = numberValue(modelContext.max_tokens);
  if (usedTokens == null && maxTokens == null) return null;
  const remainingTokens =
    numberValue(modelContext.remaining_tokens) ?? (usedTokens != null && maxTokens != null ? Math.max(maxTokens - usedTokens, 0) : null);
  const rawPercent = numberValue(modelContext.percent);
  const percent =
    rawPercent != null
      ? normalizePercent(rawPercent)
      : usedTokens != null && maxTokens != null && maxTokens > 0
        ? normalizePercent((usedTokens / maxTokens) * 100)
        : null;
  return { usedTokens, maxTokens, remainingTokens, percent };
}

function usageBudgetView(usage?: Record<string, unknown> | null, fallbackMaxTokens?: number | null): ContextBudgetView | null {
  if (!usage || !hasUsageBudget(usage)) return null;
  const usedTokens = numberValue(usage.context_used);
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
        numberValue(usage.context_max) != null ||
        numberValue(usage.context_percent) != null),
  );
}

function normalizePercent(value: number): number {
  return Math.min(100, Math.max(0, Math.round(value <= 1 ? value * 100 : value)));
}

function sumTokenEstimates(items: Record<string, unknown>[]): number | null {
  const total = items.reduce((sum, item) => sum + (numberValue(item.token_estimate) ?? numberValue(item.tokens) ?? numberValue(item.estimated_tokens) ?? 0), 0);
  return total > 0 ? total : null;
}

function tokenValue(value: number | null): number | null {
  return value != null && value > 0 ? value : null;
}

function numberValue(value: unknown): number | null {
  return typeof value === "number" && Number.isFinite(value) ? value : null;
}

function isEmptyPayload(value: unknown): boolean {
  if (value == null) return true;
  if (Array.isArray(value)) return value.length === 0;
  if (isRecord(value)) return Object.keys(value).length === 0;
  return false;
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return Boolean(value) && typeof value === "object" && !Array.isArray(value);
}
