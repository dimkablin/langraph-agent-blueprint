export const slashCommands = [
  { name: "/help", detail: "show available commands" },
  { name: "/clear", detail: "clear conversation state" },
  { name: "/compact", detail: "compact long context" },
  { name: "/resume", detail: "resume a saved session" },
  { name: "/export", detail: "export transcript" },
  { name: "/skills", detail: "list loaded skills" },
  { name: "/status", detail: "show runtime status" },
  { name: "/cost", detail: "show usage and cost telemetry" },
  { name: "/config", detail: "show redacted config" },
  { name: "/doctor", detail: "run diagnostics" },
  { name: "/memory", detail: "show memory scopes" },
  { name: "/todo", detail: "show current todos" },
  { name: "/prompt", detail: "turn args into a model prompt" },
  { name: "/skill", detail: "invoke a named skill" },
];

export const toolHints = [
  { name: "read_file", detail: "read files under project root" },
  { name: "write_file", detail: "write files after permission" },
  { name: "edit_file", detail: "edit prior-read files after permission" },
  { name: "notebook_read", detail: "read ipynb cells" },
  { name: "notebook_edit", detail: "edit ipynb cells after permission" },
  { name: "glob", detail: "find files by pattern" },
  { name: "grep", detail: "search file contents" },
  { name: "bash", detail: "run shell command with approval" },
  { name: "powershell", detail: "run PowerShell with approval" },
  { name: "web_fetch", detail: "fetch URL when network is enabled" },
  { name: "web_search", detail: "search web when configured" },
  { name: "todo_write", detail: "update visible todos" },
  { name: "agent", detail: "run a child graph/subagent" },
  { name: "skill", detail: "invoke SkillTool" },
  { name: "diagnostics", detail: "run environment checks" },
];

export const skillHints = [
  { name: "debug", detail: "systematically diagnose failures" },
  { name: "remember", detail: "write durable memory" },
  { name: "simplify", detail: "simplify code or prose" },
  { name: "skillify", detail: "create a reusable SKILL.md" },
  { name: "stuck", detail: "recover when blocked" },
  { name: "update-config", detail: "change config safely" },
  { name: "verify", detail: "run checks and report evidence" },
  { name: "batch", detail: "coordinate independent work batches" },
];

export const keyboardHints = [
  "Enter sends the command",
  "Shift+Enter inserts a newline",
  "Type / to filter slash commands",
  "Use tool:bash echo hi to exercise permission flow with fake provider",
  "Frontend never executes tools directly; it calls /chat and /approval",
];

export function filterHints(input, hints) {
  const text = input.trim().toLowerCase();
  if (!text || text === "/") return hints;
  return hints.filter((hint) => hint.name.toLowerCase().startsWith(text));
}

