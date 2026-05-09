import type { RegistryMap } from "../api/schemas.ts";
import { registryItems } from "./viewModels.ts";

export type ComposerSuggestionKind = "context" | "command";

export type ComposerSuggestion = {
  kind: ComposerSuggestionKind;
  value: string;
  title: string;
  description: string;
  group: string;
};

export type ComposerSuggestionTrigger = {
  kind: ComposerSuggestionKind;
  query: string;
  tokenStart: number;
  tokenEnd: number;
};

export const CONTEXT_SUGGESTIONS: ComposerSuggestion[] = [
  {
    kind: "context",
    value: "@README.md",
    title: "Файл",
    description: "Подключить файл из проекта",
    group: "Контекст",
  },
  {
    kind: "context",
    value: "@src/",
    title: "Папка",
    description: "Добавить краткое дерево директории",
    group: "Контекст",
  },
  {
    kind: "context",
    value: "@glob:src/**/*.py",
    title: "Glob",
    description: "Подключить список файлов по шаблону",
    group: "Контекст",
  },
  {
    kind: "context",
    value: "@notebook:notebook.ipynb",
    title: "Notebook",
    description: "Добавить summary ноутбука без исполнения",
    group: "Контекст",
  },
  {
    kind: "context",
    value: "@mcp:<server>:<uri>",
    title: "MCP resource",
    description: "Добавить внешний MCP resource как untrusted context",
    group: "Контекст",
  },
  {
    kind: "context",
    value: "@plugin:<plugin>:<provider>",
    title: "Plugin context",
    description: "Добавить plugin-provided context",
    group: "Контекст",
  },
  {
    kind: "context",
    value: "@url:https://example.com",
    title: "URL",
    description: "Добавить web context через backend guardrails",
    group: "Контекст",
  },
];

export function detectComposerSuggestionTrigger(input: string): ComposerSuggestionTrigger | null {
  const tokenStart = Math.max(input.lastIndexOf(" "), input.lastIndexOf("\n"), input.lastIndexOf("\t")) + 1;
  const token = input.slice(tokenStart);
  if (token.startsWith("@")) {
    return { kind: "context", query: token.slice(1), tokenStart, tokenEnd: input.length };
  }
  if (token.startsWith("/")) {
    return { kind: "command", query: token.slice(1), tokenStart, tokenEnd: input.length };
  }
  return null;
}

export function buildCommandSuggestions(commands: RegistryMap): ComposerSuggestion[] {
  return registryItems(commands).map((item) => {
    const name = item.name.startsWith("/") ? item.name.slice(1) : item.name;
    return {
      kind: "command",
      value: `/${name}`,
      title: `/${name}`,
      description: item.description || "Runtime slash command",
      group: "Команды",
    };
  });
}

export function filterComposerSuggestions(suggestions: ComposerSuggestion[], trigger: ComposerSuggestionTrigger): ComposerSuggestion[] {
  const query = trigger.query.trim().toLowerCase();
  const filtered = query
    ? suggestions.filter((item) => `${item.value} ${item.title} ${item.description}`.toLowerCase().includes(query))
    : suggestions;
  return filtered.slice(0, 8);
}

export function applyComposerSuggestion(input: string, trigger: ComposerSuggestionTrigger, suggestion: ComposerSuggestion): string {
  return `${input.slice(0, trigger.tokenStart)}${suggestion.value} ${input.slice(trigger.tokenEnd).trimStart()}`;
}
