Ниже — **priority tree для аналога Claude Code на LangGraph**. Я ориентировался на публичные docs Claude Code, поэтому это не “внутренняя спецификация Anthropic”, а **максимально подробный parity-checklist по наблюдаемому/документированному функционалу**. Claude Code сейчас описывается как agentic coding tool, доступный не только в терминале, но и в IDE, desktop, browser/web, Slack/CI и других поверхностях. ([Claude][1])

## Легенда приоритетов

**P0 — MVP / ядро**: без этого продукт не ощущается как Claude Code-like coding agent.
**P1 — daily-driver parity**: то, что делает инструмент реально удобным каждый день.
**P2 — power-user / platform**: расширяемость, команды, субагенты, MCP, hooks, плагины.
**P3 — enterprise / cloud / experimental**: команды агентов, scheduled tasks, policy, security, cloud/web/Slack.

## Актуальный статус готовности

Обновлено: **2026-05-22**.

Этот файл теперь используется в двух режимах:

1. Верхний блок ниже — **текущий readiness-чеклист MVP/v0.1**.
2. Подробный parity-tree ниже по документу — **backlog полной Claude Code-like parity**, а не обязательный блокер для первого MVP.

Статусы:

* `[x]` — готово и подтверждено тестами/смоуком.
* `[~]` — работает для MVP, но есть явно описанное ограничение.
* `[ ]` — не готово или не проверено.
* `[defer]` — осознанно вынесено за рамки MVP.

### MVP readiness summary

| Область | Статус | Доказательство | Что осталось |
| --- | --- | --- | --- |
| LangGraph runtime / agent loop | [x] ready | `python -m pytest -q` проходит на текущей ветке: 54 backend tests; runtime, tools, permissions, sessions, context, eval, plugins, MCP, workspace and cancellation contracts покрыты тестами. | Поддерживать event contracts при новых фичах. |
| CLI/headless | [~] ready with caveat | `query`, `chat`, `serve`, `sessions`, `skills`, `tools`, `plugins`, `eval`, `config` существуют. | Windows CP1251 Unicode output для `lg-agent query` нужно починить или явно задокументировать перед public tag. |
| API contract | [x] ready | FastAPI routes покрывают chat, SSE stream, approval, sessions, context, child runs, export, registries, config, hooks, plugins, MCP, observability, workspaces. | Прямые command/context/todo/memory endpoints можно добавить позже; MVP работает через chat/session routes. |
| React frontend MVP | [x] ready | TypeScript React/Vite frontend реализован: chat, safe GFM markdown renderer, SSE timeline, permissions, sessions, context meter/window, settings center, runtime sidebar, workspace controls. `npm.cmd run build`, `npm.cmd test` (79 tests), `npm.cmd run test:static` проходят. | Playwright/browser smoke с fake provider; upload/download UX; richer subagent transcript UI. |
| Permission UX | [x] ready | Frontend хранит `session_id`, `thread_id`, `tool_call_id`; backend approval/rejection resume работает через `/approval`. | Nested subagent approval остаётся ограничением runtime, не frontend blocker. |
| Sessions/context/workspaces | [x] ready | Session list/detail/messages/events/context/child-runs/export endpoints есть; frontend tests покрывают active session, sidebar, context window, workspace API/control/folder picker/branch checkout. | Export download/read endpoint и file upload endpoint — post-MVP polish. |
| Run cancellation / stale workspace resilience | [x] ready | `/chat/cancel` сериализует typed cancellation result; frontend stop/new-chat sends cancellation before abort and swallows cancel-call failure; workspace service/API ignore stale registered workspaces and `/chat` returns 400 for deleted workspace roots. | Add visible UX copy for stale/deleted workspace recovery and browser smoke around stop/new-chat cancellation. |
| Settings/extension panels | [x] ready | Read-only Settings page показывает config, runtime, model, MCP, plugins, hooks, observability, skills; UI preferences хранятся локально. | Config editing, plugin management UI, MCP resource browser/editor — post-MVP. |
| Eval/replay | [x] ready for engineering | CLI eval/replay harness существует и покрыт тестами. | Eval dashboard/API — post-MVP. |
| Security/safety baseline | [x] ready | Permission gate, protected config redaction, no direct frontend tool execution, MCP snapshot separation, path/session id hardening covered by tests/docs. | Продолжать threat review для plugin install UI, upload/download и executable plugin adapters. |
| Release readiness | [~] candidate | Backend/frontend/build checks green на 2026-05-22; текущая ветка содержит проверенный WIP по cancellation/workspace handling. | Закрыть CLI Unicode caveat, добавить browser smoke, обновить stale historical audit labels, разделить WIP на аккуратные коммиты. |

### MVP release criteria

* [x] Backend tests pass.
* [x] Frontend static tests pass.
* [x] Frontend unit tests pass outside Windows sandbox.
* [x] Frontend production build passes outside Windows sandbox.
* [x] Runtime API and frontend do not bypass the graph/tool/permission flow.
* [x] Frontend is implemented as the actual usable first screen, not a placeholder shell.
* [x] Stream/run cancellation path is contract-tested across frontend and API.
* [x] Stale/deleted workspace registry entries no longer break workspace list/active chat paths.
* [~] CLI quickstart is usable, with a known Windows legacy-console Unicode caveat.
* [~] Browser-level E2E smoke is still manual/not automated.
* [defer] Full Claude Code parity, enterprise/cloud, IDE/LSP, agent teams, marketplace, background tasks, and remote surfaces.

### Next change plan

1. Split the current dirty worktree into focused commits: cancellation serialization/frontend cancel tolerance, stale workspace handling, and docs/checklist.
2. Add a browser-level smoke for stop/new-chat cancellation and permission rejection recovery so the React behavior is covered beyond static source checks.
3. Add user-facing stale workspace recovery copy/actions in the workspace control when a previously active folder disappears.
4. Close the Windows CP1251 CLI Unicode caveat for `lg-agent query`.
5. Add export download/read and file upload endpoints as post-MVP polish.
6. Continue stale audit cleanup: historical docs still describe several parity items as open even when the current runtime has tests for them.

---

# P0. Базовое ядро agentic coding assistant

## 0.1. Главная модель поведения агента

Claude Code работает не как обычный чат, а как **агентный цикл**: собирает контекст, выполняет действие, проверяет результат, при необходимости повторяет итерацию. Пользователь может прерывать и направлять его в процессе. ([Claude][2])

* [ ] Агент принимает задачу естественным языком: “почини баг”, “добавь кнопку”, “объясни архитектуру”.
* [ ] Агент сам решает, какие файлы читать.
* [ ] Агент сам строит план действий.
* [ ] Агент сам редактирует файлы.
* [ ] Агент сам запускает тесты, линтеры, typecheck, build.
* [ ] Агент сам анализирует ошибки команд.
* [ ] Агент повторяет цикл исправления, пока задача не завершена или не упёрся в блокер.
* [ ] Агент может задавать уточняющий вопрос, когда без него высок риск сломать проект.
* [ ] Агент может быть прерван пользователем.
* [ ] После прерывания пользователь может уточнить направление, и агент продолжит с новым контекстом.
* [ ] Агент различает:

  * [ ] exploration;
  * [ ] planning;
  * [ ] implementation;
  * [ ] verification;
  * [ ] final summary.
* [ ] Агент ведёт внутренний список TODO.
* [ ] Агент не раскрывает hidden reasoning, но показывает безопасные публичные progress updates.
* [ ] Агент умеет объяснять, что сделал, какие файлы изменил и чем проверил.

**LangGraph mapping:**

* `UserInputNode`
* `ContextGatheringNode`
* `PlannerNode`
* `PermissionGateNode`
* `ToolExecutionNode`
* `PatchApplicationNode`
* `VerifierNode`
* `FinalizerNode`
* `InterruptRouter`
* `ErrorRecoveryRouter`

---

## 0.2. Terminal-first interactive session

Claude Code начинается как CLI/TUI-инструмент: можно открыть интерактивную сессию, дать one-shot query, передать input через pipe, продолжить прошлую сессию или возобновить конкретную. ([Claude][3])

* [ ] Команда запуска без аргументов: интерактивный режим.
* [ ] Команда запуска с prompt: `agent "fix this bug"`.
* [ ] Non-interactive print mode: `agent -p "..."`.
* [ ] Pipe input:

  * [ ] `cat logs.txt | agent -p "analyze errors"`;
  * [ ] `git diff | agent -p "review this diff"`.
* [ ] Continue last session.
* [ ] Resume session by id/name.
* [ ] Session list.
* [ ] Session rename.
* [ ] Session delete.
* [ ] Clear current conversation context.
* [ ] Export transcript.
* [ ] Copy last response.
* [ ] Status command.
* [ ] Doctor command for diagnostics.
* [ ] Login/logout/status if есть auth.
* [ ] Update/install commands if это CLI package.
* [ ] Help command.
* [ ] Version command.
* [ ] Verbose/debug mode.
* [ ] Working directory awareness.
* [ ] `--add-dir` для дополнительных директорий.
* [ ] `--model` selection.
* [ ] `--permission-mode`.
* [ ] `--allowedTools`.
* [ ] `--disallowedTools`.
* [ ] `--append-system-prompt`.
* [ ] `--agent` / `--agents` для выбора subagent/team mode.
* [ ] `--dangerously-skip-permissions` только как отдельный явно опасный режим.

---

## 0.3. Project awareness

Claude Code имеет доступ к project files, terminal, git state, `CLAUDE.md`, memory, extensions; он может читать, искать, редактировать, запускать тесты и делать commit. ([Claude][2])

* [ ] Определение project root.
* [ ] Поддержка mono-repo.
* [ ] Поддержка nested packages.
* [ ] Чтение структуры директорий.
* [ ] Поиск файлов по glob.
* [ ] Поиск текста по grep/ripgrep.
* [ ] Чтение файлов с line numbers.
* [ ] Ограничение больших файлов.
* [ ] Поддержка binary-file detection.
* [ ] Поддержка `.gitignore`.
* [ ] Поддержка дополнительных ignore-файлов агента.
* [ ] Выделение generated/vendor/build/cache директорий.
* [ ] Git status awareness.
* [ ] Git branch awareness.
* [ ] Git diff awareness.
* [ ] Recent commits awareness.
* [ ] Наличие uncommitted changes.
* [ ] Отличать изменения пользователя от изменений агента.
* [ ] Не перетирать чужие изменения.
* [ ] Возможность попросить пользователя подтвердить конфликт.
* [ ] Project instructions discovery:

  * [ ] `CLAUDE.md`-like файл;
  * [ ] `.agent/AGENTS.md`;
  * [ ] `.cursor/rules`;
  * [ ] `.github/copilot-instructions.md`;
  * [ ] локальные настройки.
* [ ] Явное отображение, какие instructions загружены.

---

## 0.4. Context management

Claude Code держит в context window conversation, file contents, tool outputs, `CLAUDE.md`, memory, skills; при переполнении выполняет auto-compaction, есть `/context` и `/compact`. ([Claude][2])

* [ ] Context budget accounting.
* [ ] Видимый пользователю context usage.
* [ ] Context inspector:

  * [ ] какие файлы загружены;
  * [ ] какие instructions активны;
  * [ ] какие tool outputs в контексте;
  * [ ] сколько осталось токенов.
* [ ] Автоматическое сжатие истории.
* [ ] Ручное сжатие `/compact`.
* [ ] Сжатие без потери:

  * [ ] текущей задачи;
  * [ ] принятых решений;
  * [ ] изменённых файлов;
  * [ ] TODO;
  * [ ] ошибок тестов;
  * [ ] пользовательских ограничений.
* [ ] Отдельное хранение:

  * [ ] raw transcript;
  * [ ] compacted summary;
  * [ ] tool events;
  * [ ] artifacts;
  * [ ] patch history.
* [ ] Возможность очистить conversation context без удаления файлов.
* [ ] Возможность продолжить после compaction.
* [ ] Защита от “forgot what I was doing”.
* [ ] Context fork для subagents/skills.
* [ ] Lazy-loading для больших инструкций/skills.

**LangGraph mapping:**

* `ContextState`
* `ContextBudgetManager`
* `CompactionNode`
* `ContextInspectorTool`
* `MemoryInjectionNode`
* `SkillContextLoader`

---

# P0.5. Базовые built-in tools

Официальная tools reference перечисляет core tools вроде `Read`, `Write`, `Edit`, `Bash`, `Glob`, `Grep`, `WebFetch`, `WebSearch`, `TodoWrite`, `TaskCreate`, `TaskList`, `LSP`, `NotebookEdit`, `Monitor`, `Skill`, `Agent`, `AskUserQuestion` и другие. ([Claude][4])

## 0.5.1. File tools

* [ ] `Read`

  * [ ] читать файл целиком;
  * [ ] читать диапазон строк;
  * [ ] показывать line numbers;
  * [ ] ограничивать huge files;
  * [ ] binary detection;
  * [ ] image/PDF если нужно — отдельные handlers.
* [ ] `Write`

  * [ ] создать новый файл;
  * [ ] перезаписать файл;
  * [ ] требовать permission для overwrite;
  * [ ] сохранять snapshot до записи.
* [ ] `Edit`

  * [ ] точечная замена;
  * [ ] multi-edit;
  * [ ] проверка, что old text найден ровно один раз;
  * [ ] graceful failure, если match неоднозначный;
  * [ ] сохранение форматирования;
  * [ ] diff before apply;
  * [ ] undo support.
* [ ] `Glob`

  * [ ] искать файлы по паттерну;
  * [ ] ограничивать директории;
  * [ ] уважать ignore.
* [ ] `Grep`

  * [ ] искать текст;
  * [ ] regex;
  * [ ] case sensitivity;
  * [ ] include/exclude globs;
  * [ ] context lines.
* [ ] Directory listing.
* [ ] File metadata:

  * [ ] size;
  * [ ] modified time;
  * [ ] language;
  * [ ] encoding.
* [ ] File snapshot history.
* [ ] Patch application.
* [ ] Patch rollback.

---

## 0.5.2. Shell tools

Claude Code has `Bash` and `PowerShell`; Bash has session-like cwd persistence inside allowed dirs, while environment variables do not persist unless special env/session mechanisms are used. ([Claude][4])

* [ ] Bash execution.
* [ ] PowerShell execution for Windows.
* [ ] Command timeout.
* [ ] Streaming stdout/stderr.
* [ ] Truncation of huge output.
* [ ] Full output saved outside context.
* [ ] Exit code handling.
* [ ] Working directory persistence.
* [ ] Environment handling.
* [ ] Command classification:

  * [ ] read-only;
  * [ ] modifies local files;
  * [ ] destructive local;
  * [ ] network;
  * [ ] secrets;
  * [ ] production;
  * [ ] git remote;
  * [ ] package install;
  * [ ] migration/deploy.
* [ ] Permission request before dangerous commands.
* [ ] Denylist for dangerous commands.
* [ ] Allowlist for safe commands.
* [ ] Shell command explanation before execution.
* [ ] Command retry with correction.
* [ ] Background command support.
* [ ] Kill running command.
* [ ] Attach to running command output.
* [ ] Command history.
* [ ] Command provenance: which agent node requested it.
* [ ] Support for package managers:

  * [ ] npm;
  * [ ] pnpm;
  * [ ] yarn;
  * [ ] pip;
  * [ ] uv;
  * [ ] poetry;
  * [ ] cargo;
  * [ ] go;
  * [ ] maven/gradle;
  * [ ] docker compose.
* [ ] Detect “server already running”.
* [ ] Detect “port already in use”.
* [ ] Suggest not killing user processes without approval.

---

## 0.5.3. Web tools

* [ ] Web search.
* [ ] Web fetch.
* [ ] Domain restrictions.
* [ ] Citation/source tracking.
* [ ] Timeout.
* [ ] Robots/compliance depending on product requirements.
* [ ] Cache fetched docs.
* [ ] Detect stale docs.
* [ ] Prefer official docs for code/API/library questions.
* [ ] Summarize fetched pages.
* [ ] Use web only when needed, not for every task.

---

## 0.5.4. Todo/task tools

* [ ] Agent-maintained TODO list.
* [ ] User-visible task status.
* [ ] `pending / in_progress / completed / blocked`.
* [ ] Exactly one active implementation task at a time.
* [ ] Use TODO list for multi-step tasks.
* [ ] Update TODO after tool calls.
* [ ] Persist TODO across compaction.
* [ ] Persist TODO across session resume.
* [ ] Mark verification tasks separately from implementation tasks.

---

# P0.6. Editing and patch workflow

## 0.6.1. Safe editing

* [ ] Before modifying file, read it.
* [ ] Before modifying file, check if it changed since read.
* [ ] Use minimal diffs.
* [ ] Preserve user formatting where possible.
* [ ] Avoid unrelated refactors.
* [ ] Avoid hardcoded hacks.
* [ ] Avoid broad rewrites unless requested.
* [ ] Avoid deleting user changes.
* [ ] Keep changes scoped to task.
* [ ] Explain risky edits.
* [ ] Snapshot before write/edit.
* [ ] Support rollback.
* [ ] Support `/rewind`-like restore.
* [ ] Support “show diff”.
* [ ] Support “accept/reject edit” if UI supports it.

Claude Code docs mention snapshots before code changes and checkpoint/rewind-like behavior for recovering from edits. ([Claude][2])

---

## 0.6.2. Diff UX

* [ ] Show changed files.
* [ ] Show hunks.
* [ ] Highlight additions/deletions.
* [ ] Summarize semantic changes.
* [ ] Show generated files separately.
* [ ] Show tests/build commands run after diff.
* [ ] Show unverified changes.
* [ ] Let user ask “why did you change this?”
* [ ] Let user revert one file.
* [ ] Let user revert whole turn.
* [ ] Let user continue from before edit.

---

## 0.6.3. Git workflow

* [ ] Read git status.
* [ ] Read git diff.
* [ ] Detect staged vs unstaged.
* [ ] Detect untracked files.
* [ ] Detect merge conflicts.
* [ ] Detect current branch.
* [ ] Detect upstream.
* [ ] Commit message generation.
* [ ] Create commit only if user asks.
* [ ] Never push without explicit approval.
* [ ] Block force push unless explicit.
* [ ] Support branch creation.
* [ ] Support worktree creation.
* [ ] Support PR review.
* [ ] Support PR comments if integrated.
* [ ] Detect CI failure logs.
* [ ] Autofix PR comments as P1/P2.

---

# P0.7. Verification loop

* [ ] Infer test command from project.
* [ ] Infer build command.
* [ ] Infer lint command.
* [ ] Infer typecheck command.
* [ ] Ask user if ambiguous.
* [ ] Prefer targeted tests first.
* [ ] Then run broader tests.
* [ ] Parse test failures.
* [ ] Parse TypeScript/Python/Rust/Go errors.
* [ ] Map error to file/line.
* [ ] Fix and rerun.
* [ ] Stop after bounded retries.
* [ ] Report:

  * [ ] commands run;
  * [ ] passing/failing;
  * [ ] known remaining issues;
  * [ ] things not verified.
* [ ] If unable to run tests, explain why.
* [ ] Never claim verified if not verified.

---

# P0.8. Permission and safety system

Claude Code has several permission modes: default, accept edits, plan, auto, don’t ask, bypass permissions. It also supports allow/ask/deny rules and protected paths. ([Claude][5])

## 0.8.1. Permission modes

* [ ] `default`

  * ask before file edits;
  * ask before risky shell commands.
* [ ] `acceptEdits`

  * automatically accept file edits;
  * still ask for risky shell commands.
* [ ] `plan`

  * no edits;
  * no side effects;
  * only exploration/planning.
* [ ] `dontAsk`

  * more autonomous local actions;
  * still block protected/dangerous operations.
* [ ] `auto`

  * background classifier/autonomy mode;
  * block sensitive actions.
* [ ] `bypassPermissions`

  * explicit dangerous mode;
  * only for trusted local/sandbox;
  * never default.

## 0.8.2. Fine-grained permission rules

Claude Code rules can target a whole tool or a tool with specifier, like `Bash(npm run build)`, `Read(./.env)`, `WebFetch(domain:example.com)`, and deny rules take precedence over ask/allow. ([Claude][6])

* [ ] Rule scopes:

  * [ ] user;
  * [ ] project;
  * [ ] local project;
  * [ ] enterprise/managed.
* [ ] Rule actions:

  * [ ] allow;
  * [ ] ask;
  * [ ] deny.
* [ ] Rule matching:

  * [ ] by tool name;
  * [ ] by command prefix;
  * [ ] by file path;
  * [ ] by domain;
  * [ ] by MCP server/tool;
  * [ ] by subagent.
* [ ] Precedence:

  * [ ] deny;
  * [ ] ask;
  * [ ] allow.
* [ ] Display reason for permission request.
* [ ] Let user approve once.
* [ ] Let user approve for session.
* [ ] Let user approve for project.
* [ ] Let user deny once.
* [ ] Let user add deny rule.
* [ ] Store permission decision.
* [ ] Audit permission decisions.

## 0.8.3. Protected paths

* [ ] Block edits to:

  * [ ] `.env`;
  * [ ] secrets;
  * [ ] SSH keys;
  * [ ] cloud credentials;
  * [ ] production config;
  * [ ] lockfiles if not expected;
  * [ ] `.git`;
  * [ ] system directories.
* [ ] Ask before reading secrets.
* [ ] Never paste secrets into model context unless explicitly allowed.
* [ ] Redact secrets in logs.
* [ ] Redact secrets in final answer.
* [ ] Detect accidental secret exposure.
* [ ] Warn if user asks to commit secrets.

---

# P0.9. Session persistence

Claude Code stores sessions locally as JSONL under project-specific directories, supports resume/continue/fork, and keeps file snapshots. ([Claude][2])

* [ ] Unique session id.
* [ ] Session name/title.
* [ ] Project path binding.
* [ ] Transcript storage.
* [ ] Tool event storage.
* [ ] File snapshot storage.
* [ ] Patch history.
* [ ] Permission decisions.
* [ ] Context summaries.
* [ ] Active TODO list.
* [ ] Active goal/loop if any.
* [ ] Resume last session.
* [ ] Resume by id.
* [ ] Fork session.
* [ ] Branch session from checkpoint.
* [ ] Delete session.
* [ ] Purge project data.
* [ ] Export transcript.
* [ ] Search history across sessions.
* [ ] Continue after crash.
* [ ] Continue after compaction.
* [ ] Record model used.
* [ ] Record token/cost usage.
* [ ] Record tool timings.
* [ ] Record errors.

---

# P1. Daily-driver parity

# P1.1. Slash command system

Claude Code exposes many slash commands for session control, memory, model, permissions, context, review, remote control, plugins, hooks, scheduling, themes, statusline, etc. ([Claude][7])

## Core session commands

* [ ] `/help`
* [ ] `/exit`
* [ ] `/clear`
* [ ] `/compact`
* [ ] `/context`
* [ ] `/status`
* [ ] `/stats`
* [ ] `/usage`
* [ ] `/extra-usage`
* [ ] `/copy`
* [ ] `/export`
* [ ] `/rename`
* [ ] `/resume`
* [ ] `/branch`
* [ ] `/rewind`
* [ ] `/doctor`
* [ ] `/debug`
* [ ] `/feedback`

## Model and reasoning commands

* [ ] `/model`
* [ ] `/effort`
* [ ] `/fast`
* [ ] `/ultraplan`
* [ ] `/ultrareview`

## Planning and workflow commands

* [ ] `/plan`
* [ ] `/goal`
* [ ] `/loop`
* [ ] `/batch`
* [ ] `/simplify`
* [ ] `/review`
* [ ] `/security-review`
* [ ] `/autofix-pr`
* [ ] `/pr-comments` if PR integration exists.
* [ ] `/btw` for side-notes/additional instructions.

## Project/config commands

* [ ] `/init`
* [ ] `/config`
* [ ] `/permissions`
* [ ] `/memory`
* [ ] `/add-dir`
* [ ] `/terminal-setup`
* [ ] `/keybindings`
* [ ] `/theme`
* [ ] `/color`
* [ ] `/statusline`
* [ ] `/output-style` equivalent.

## Extensions/integrations commands

* [ ] `/mcp`
* [ ] `/plugin`
* [ ] `/reload-plugins`
* [ ] `/skills`
* [ ] `/agents`
* [ ] `/hooks`
* [ ] `/ide`
* [ ] `/desktop`
* [ ] `/remote-control`
* [ ] `/remote-env`
* [ ] `/teleport`
* [ ] `/mobile`
* [ ] `/chrome`
* [ ] `/install-github-app`
* [ ] `/install-slack-app`

## Background/scheduling commands

* [ ] `/background`
* [ ] `/tasks`
* [ ] `/schedule`
* [ ] `/stop`

## Account/privacy commands

* [ ] `/login`
* [ ] `/logout`
* [ ] `/privacy-settings`
* [ ] `/setup-bedrock`
* [ ] `/setup-vertex`
* [ ] `/upgrade`

---

# P1.2. Memory system

Claude Code uses `CLAUDE.md` and auto memory. `CLAUDE.md` is for project/user/org instructions like coding standards and workflows; auto memory can learn project notes and is stored per working tree. ([Claude API Docs][8])

## 1.2.1. Manual memory / instruction files

* [ ] Project memory file:

  * [ ] `CLAUDE.md`;
  * [ ] `.claude/CLAUDE.md`;
  * [ ] custom configured path.
* [ ] User memory:

  * [ ] `~/.claude/CLAUDE.md` equivalent.
* [ ] Enterprise/managed memory.
* [ ] Local uncommitted memory.
* [ ] Path-specific rules.
* [ ] Import/include syntax.
* [ ] Memory editing command.
* [ ] Memory reload command.
* [ ] Show loaded memory.
* [ ] Explain memory precedence.
* [ ] Warn if memory file is too large.
* [ ] Separate:

  * [ ] project architecture;
  * [ ] coding style;
  * [ ] test commands;
  * [ ] deployment rules;
  * [ ] “do not touch” files;
  * [ ] domain glossary.

## 1.2.2. Auto memory

* [ ] Agent can save discovered facts:

  * [ ] build command;
  * [ ] test command;
  * [ ] project architecture;
  * [ ] common failure/fix;
  * [ ] user preferences.
* [ ] Auto memory is per project/worktree.
* [ ] Auto memory has size limit.
* [ ] Auto memory is visible/editable.
* [ ] Auto memory can be disabled.
* [ ] Auto memory can be cleared.
* [ ] Auto memory is loaded at session start.
* [ ] Auto memory is not treated as hard policy, only context.
* [ ] Sensitive facts are not saved automatically.
* [ ] User can explicitly save note.
* [ ] User can explicitly forget note.

---

# P1.3. Settings/config architecture

Claude Code settings have scopes like managed policy, user, project, local project, and precedence rules; `.claude` can hold settings, agents, skills, hooks, MCP config, commands, themes and app data. ([Claude][9])

* [ ] Settings scopes:

  * [ ] managed/enterprise;
  * [ ] CLI args;
  * [ ] local project;
  * [ ] project;
  * [ ] user.
* [ ] Deterministic precedence.
* [ ] JSON schema for settings.
* [ ] Settings validation.
* [ ] Settings migration.
* [ ] Settings diagnostics.
* [ ] Per-project local settings ignored by git.
* [ ] Shared project settings committed to repo.
* [ ] User global settings.
* [ ] Managed policy cannot be overridden.
* [ ] Store:

  * [ ] permissions;
  * [ ] model;
  * [ ] effort;
  * [ ] hooks;
  * [ ] MCP;
  * [ ] skills;
  * [ ] agents;
  * [ ] theme;
  * [ ] statusline;
  * [ ] keybindings;
  * [ ] env;
  * [ ] output style;
  * [ ] plugin dirs;
  * [ ] telemetry preferences.
* [ ] App data storage:

  * [ ] transcripts;
  * [ ] tool results;
  * [ ] file history;
  * [ ] plans;
  * [ ] debug logs;
  * [ ] paste cache;
  * [ ] image cache;
  * [ ] shell snapshots;
  * [ ] tasks.

---

# P1.4. Plan mode

Claude Code has plan mode: it explores and proposes a plan before making changes. ([Claude][2])

* [ ] User can enter plan mode.
* [ ] Agent cannot edit files in plan mode.
* [ ] Agent cannot run side-effect commands in plan mode.
* [ ] Agent can read files.
* [ ] Agent can inspect git status.
* [ ] Agent can ask clarifying questions.
* [ ] Agent produces:

  * [ ] summary of understanding;
  * [ ] affected files;
  * [ ] proposed changes;
  * [ ] risks;
  * [ ] test plan;
  * [ ] rollback plan.
* [ ] User can approve plan.
* [ ] User can modify plan.
* [ ] User can reject plan.
* [ ] Agent exits plan mode only after approval.
* [ ] Plan persists across context compaction.
* [ ] Plan can be reopened.
* [ ] Plan can be exported.

---

# P1.5. Skills

Claude Code skills are markdown-based capabilities with `SKILL.md`, can be manually invoked or auto-invoked, lazy-load content, include supporting files, define allowed tools, model/effort/context behavior, shell context injection and forked context. ([Claude][10])

## 1.5.1. Skill discovery

* [ ] Discover personal skills.
* [ ] Discover project skills.
* [ ] Discover enterprise skills.
* [ ] Discover plugin skills.
* [ ] Support nested skills in monorepo.
* [ ] Support skills from additional directories.
* [ ] Live reload changed skills.
* [ ] Precedence by scope.
* [ ] Namespaced skills.
* [ ] Disable specific skill.
* [ ] Deny skill via permission rule.
* [ ] List skills.
* [ ] Search skills.
* [ ] Show active skill.

## 1.5.2. `SKILL.md` schema

* [ ] `name`
* [ ] `description`
* [ ] `when_to_use`
* [ ] `argument-hint`
* [ ] `arguments`
* [ ] `allowed-tools`
* [ ] `model`
* [ ] `effort`
* [ ] `context`
* [ ] `agent`
* [ ] `hooks`
* [ ] `paths`
* [ ] `shell`
* [ ] `user-invocable`
* [ ] `disable-model-invocation`
* [ ] Validation errors.
* [ ] Frontmatter parser.
* [ ] Human-readable diagnostics.

## 1.5.3. Skill invocation

* [ ] Manual invocation: `/skill-name`.
* [ ] Auto invocation based on description/when_to_use.
* [ ] User-only skills.
* [ ] Model-only skills.
* [ ] Both manual and auto skills.
* [ ] Argument substitution:

  * [ ] `$ARGUMENTS`;
  * [ ] `$1`, `$2`;
  * [ ] named arguments;
  * [ ] session id;
  * [ ] effort;
  * [ ] skill directory.
* [ ] Skill can include:

  * [ ] reference docs;
  * [ ] examples;
  * [ ] scripts;
  * [ ] templates;
  * [ ] images/assets.
* [ ] Lazy load supporting files only when needed.
* [ ] Keep minimal skill summary in main context.
* [ ] Skill-specific allowed tools.
* [ ] Skill-specific model.
* [ ] Skill-specific effort.
* [ ] Skill-specific shell commands.
* [ ] Skill dynamic context injection via shell command.
* [ ] Skill forked context.
* [ ] Skill can run in subagent.
* [ ] Skill returns compact result to main agent.

## 1.5.4. Bundled skills parity

* [ ] `/simplify`
* [ ] `/batch`
* [ ] `/debug`
* [ ] `/loop`
* [ ] `/claude-api`
* [ ] `/review`
* [ ] `/security-review`
* [ ] Project-specific custom commands migrated to skills.

---

# P1.6. Subagents

Claude Code subagents are specialized assistants with their own context window, system prompt, tools, permissions and model. Built-ins include Explore, Plan and general-purpose. ([Claude][11])

## 1.6.1. Built-in subagents

* [ ] `Explore`

  * [ ] read-only;
  * [ ] fast/cheap model option;
  * [ ] gathers context;
  * [ ] returns concise summary.
* [ ] `Plan`

  * [ ] read-only;
  * [ ] produces implementation plan;
  * [ ] no side effects.
* [ ] `general-purpose`

  * [ ] broad tools;
  * [ ] delegated implementation/research.
* [ ] Helper agents for:

  * [ ] code search;
  * [ ] test failure analysis;
  * [ ] dependency investigation;
  * [ ] docs research;
  * [ ] PR review;
  * [ ] security review.

## 1.6.2. Custom subagents

Claude Code subagent configs can include description, prompt, tools/disallowed tools, model, effort, permission mode, skills, MCP servers, memory, background mode, worktree isolation, hooks and color. ([Claude][11])

* [ ] Create subagent via command.
* [ ] Store personal subagent.
* [ ] Store project subagent.
* [ ] Store local subagent.
* [ ] Subagent frontmatter:

  * [ ] `name`;
  * [ ] `description`;
  * [ ] `tools`;
  * [ ] `disallowedTools`;
  * [ ] `model`;
  * [ ] `effort`;
  * [ ] `permissionMode`;
  * [ ] `skills`;
  * [ ] `mcpServers`;
  * [ ] `memory`;
  * [ ] `background`;
  * [ ] `isolation`;
  * [ ] `color`;
  * [ ] `initialPrompt`;
  * [ ] `hooks`.
* [ ] Subagent has own system prompt.
* [ ] Subagent has own context.
* [ ] Subagent can be invoked explicitly.
* [ ] Main agent can delegate automatically.
* [ ] Main agent receives summary, not full raw context.
* [ ] Subagent can be denied by permission rule.
* [ ] Subagent can have scoped MCP tools.
* [ ] Subagent can preload skills.
* [ ] Subagent can have memory.
* [ ] Subagent can run in isolated worktree.
* [ ] Subagent can run in background.
* [ ] Parent permission mode can constrain subagent.
* [ ] Prevent recursive uncontrolled agent spawning.
* [ ] Track subagent cost/tokens separately.
* [ ] Show subagent activity in UI.

**LangGraph mapping:**

* Main graph delegates to `SubagentGraph`.
* Each subagent has:

  * isolated `AgentState`;
  * inherited but filtered context;
  * own tool registry;
  * own permission policy;
  * summarizer node on completion.

---

# P1.7. Hooks

Claude Code hooks run deterministic commands/prompts/agents/http/MCP tools at lifecycle events. They can format files, block protected edits, inject context, audit configs, reload env, approve/deny permissions, etc. ([Claude][12])

## 1.7.1. Hook configuration

* [ ] Hooks in user settings.
* [ ] Hooks in project settings.
* [ ] Hooks in local settings.
* [ ] Hooks in plugin.
* [ ] Hook matcher.
* [ ] Hook timeout.
* [ ] Hook stdout/stderr capture.
* [ ] Hook exit-code interpretation.
* [ ] JSON stdin.
* [ ] JSON stdout.
* [ ] Parallel hook execution.
* [ ] Most restrictive decision wins.
* [ ] Hook diagnostics.
* [ ] Hook enable/disable.
* [ ] Hook dry run.

## 1.7.2. Hook types

Claude Code hook types include command, prompt, agent, HTTP and MCP tool. ([Claude][12])

* [ ] Shell command hook.
* [ ] Prompt hook.
* [ ] Agent hook.
* [ ] HTTP hook.
* [ ] MCP tool hook.

## 1.7.3. Hook events

Claude Code documents many lifecycle events, including session start/end, setup, user prompt, tool pre/post, permission request/denied, subagent start/stop, task created/completed, compact, config change, cwd change, file change, worktree create/remove and more. ([Claude][12])

* [ ] `SessionStart`
* [ ] `Setup`
* [ ] `UserPromptSubmit`
* [ ] `UserPromptExpansion`
* [ ] `PreToolUse`
* [ ] `PermissionRequest`
* [ ] `PermissionDenied`
* [ ] `PostToolUse`
* [ ] `PostToolUseFailure`
* [ ] `PostToolBatch`
* [ ] `Notification`
* [ ] `SubagentStart`
* [ ] `SubagentStop`
* [ ] `TaskCreated`
* [ ] `TaskCompleted`
* [ ] `Stop`
* [ ] `StopFailure`
* [ ] `TeammateIdle`
* [ ] `InstructionsLoaded`
* [ ] `ConfigChange`
* [ ] `CwdChanged`
* [ ] `FileChanged`
* [ ] `WorktreeCreate`
* [ ] `WorktreeRemove`
* [ ] `PreCompact`
* [ ] `PostCompact`
* [ ] `Elicitation`
* [ ] `ElicitationResult`
* [ ] `SessionEnd`

## 1.7.4. Hook use cases

* [ ] Auto-format after edit.
* [ ] Run prettier/ruff/black.
* [ ] Block edits to protected files.
* [ ] Block unsafe bash commands.
* [ ] Inject branch-specific context.
* [ ] Inject current ticket context.
* [ ] Reload env.
* [ ] Notify user when permission needed.
* [ ] Notify user when long task finishes.
* [ ] Auto-approve safe tools.
* [ ] Audit config changes.
* [ ] Validate generated code.
* [ ] Enforce project rules.
* [ ] Enforce “no hardcode” rule.
* [ ] Enforce “no production deploy” rule.
* [ ] Enforce “no force push” rule.

---

# P1.8. MCP integration

Claude Code uses MCP to connect to external tools/data/APIs such as issue trackers, monitoring, databases, Figma/Slack, Gmail drafts and event channels. It supports remote HTTP, local stdio, OAuth, scopes, dynamic tool updates and plugin-bundled MCP servers. ([Claude][13])

## 1.8.1. MCP server management

* [ ] Add MCP server.
* [ ] Remove MCP server.
* [ ] List MCP servers.
* [ ] Get MCP server details.
* [ ] Enable/disable MCP server.
* [ ] Project-scoped MCP.
* [ ] User-scoped MCP.
* [ ] Local/private MCP.
* [ ] Enterprise-managed MCP.
* [ ] Remote HTTP transport.
* [ ] Local stdio transport.
* [ ] SSE compatibility if needed.
* [ ] OAuth login flow.
* [ ] Env vars for local servers.
* [ ] Timeout config.
* [ ] Output token limit.
* [ ] Tool list refresh.
* [ ] Automatic reconnection.
* [ ] Server approval prompt for shared project configs.

## 1.8.2. MCP capabilities

* [ ] MCP tools as callable tools.
* [ ] MCP resources.
* [ ] MCP prompts as slash commands.
* [ ] MCP event channels.
* [ ] Tool search / deferred loading.
* [ ] Namespaced tool names.
* [ ] Permission rules for MCP tools.
* [ ] Scoped MCP access for subagents.
* [ ] MCP output truncation.
* [ ] MCP error handling.
* [ ] MCP audit log.
* [ ] MCP health check.

## 1.8.3. Useful MCP categories

* [ ] GitHub.
* [ ] GitLab.
* [ ] Jira/Linear.
* [ ] Sentry.
* [ ] Datadog.
* [ ] Postgres.
* [ ] Snowflake.
* [ ] BigQuery.
* [ ] Figma.
* [ ] Slack.
* [ ] Gmail.
* [ ] Google Calendar.
* [ ] Browser automation.
* [ ] Docs/wiki.
* [ ] Feature flag systems.
* [ ] CI/CD systems.

---

# P1.9. LSP/code intelligence

Claude Code has an LSP tool for definitions, references, type info, symbols, implementations, call hierarchy and automatic type-error reporting after edits. ([Claude][4])

* [ ] Detect language servers.
* [ ] Configure language servers.
* [ ] Start/stop LSP server.
* [ ] Go to definition.
* [ ] Find references.
* [ ] Hover/type info.
* [ ] Document symbols.
* [ ] Workspace symbols.
* [ ] Find implementations.
* [ ] Call hierarchy.
* [ ] Diagnostics after edit.
* [ ] Type errors after edit.
* [ ] LSP output included in context.
* [ ] LSP tool permissions.
* [ ] Per-language support:

  * [ ] TypeScript;
  * [ ] Python;
  * [ ] Rust;
  * [ ] Go;
  * [ ] Java;
  * [ ] C/C++;
  * [ ] C#;
  * [ ] Kotlin;
  * [ ] Swift.
* [ ] Plugin-provided LSP config.

---

# P1.10. IDE integration

Claude Code supports IDE usage such as VS Code and JetBrains, while docs also describe broader surfaces like terminal, desktop, web and CI/CD. ([Claude][14])

* [ ] VS Code extension.
* [ ] JetBrains plugin.
* [ ] Current file awareness.
* [ ] Current selection awareness.
* [ ] Open tabs awareness.
* [ ] Diagnostics awareness.
* [ ] Inline diff preview.
* [ ] Accept/reject changes.
* [ ] Jump to changed file.
* [ ] Chat panel.
* [ ] Terminal integration.
* [ ] Mode selector.
* [ ] Model selector.
* [ ] Permission prompt UI.
* [ ] Status indicator.
* [ ] Mention files with `@file`.
* [ ] Mention folders.
* [ ] Mention symbols.
* [ ] Mention diagnostics.
* [ ] Mention terminal output.
* [ ] Start agent from selected code.
* [ ] Apply patch from agent.
* [ ] Undo patch.
* [ ] Show plan before edit.

---

# P1.11. Background agents / Agent view

Claude Code Agent view lets you manage multiple background sessions, peek/reply/attach/detach, dispatch tasks, isolate edits in worktrees and supervise running agents. ([Claude][15])

* [ ] Run session in background.
* [ ] Detach from session.
* [ ] Attach to session.
* [ ] Peek at session output.
* [ ] Reply to background session.
* [ ] Kill background session.
* [ ] List background sessions.
* [ ] Group by state:

  * [ ] input needed;
  * [ ] running;
  * [ ] completed;
  * [ ] errored.
* [ ] Display:

  * [ ] repo;
  * [ ] branch/worktree;
  * [ ] task;
  * [ ] last update;
  * [ ] status;
  * [ ] model;
  * [ ] cost/tokens.
* [ ] Dispatch new task.
* [ ] Dispatch to repo.
* [ ] Dispatch to agent.
* [ ] Dispatch to skill.
* [ ] Dispatch from PR URL.
* [ ] Worktree isolation for background task.
* [ ] Cleanup worktree on completion.
* [ ] Detect local machine sleep/session loss.
* [ ] Notify when done.
* [ ] Notify when input needed.
* [ ] Supervisor view.
* [ ] Filters/search.
* [ ] Keyboard shortcuts.

---

# P1.12. Worktrees and isolation

* [ ] Create git worktree for risky task.
* [ ] Enter worktree.
* [ ] Exit worktree.
* [ ] Include/exclude files in worktree.
* [ ] Configure base ref.
* [ ] Detect dirty worktree.
* [ ] Cleanup worktree.
* [ ] Preserve worktree if task failed.
* [ ] Show worktree path.
* [ ] Merge/copy changes back.
* [ ] Avoid conflicting edits between agents.
* [ ] Use worktree for background agents.
* [ ] Use worktree for subagents if requested.

---

# P1.13. Scheduling, loops and goals

Claude Code supports `/loop` and cron-style tools for recurring work inside a session, plus `/goal` for continuing until a completion condition is met. Docs also distinguish cloud/desktop scheduled tasks and loop behavior. ([Claude][16])

## 1.13.1. Loop

* [ ] `/loop every 5 minutes`.
* [ ] `/loop` with prompt.
* [ ] `/loop` with dynamic interval.
* [ ] Default maintenance prompt.
* [ ] Loop can check unfinished work.
* [ ] Loop can tend PR.
* [ ] Loop can run cleanup.
* [ ] Loop can monitor logs.
* [ ] Loop can stop itself.
* [ ] Loop state persists in session.
* [ ] Loop restored on resume if unexpired.
* [ ] Loop cannot perform irreversible action unless authorized.
* [ ] Show active loop.
* [ ] Stop loop.

## 1.13.2. Goal

* [ ] Set completion condition.
* [ ] Evaluator checks after each turn.
* [ ] Continue until goal met.
* [ ] Show active goal.
* [ ] Show evaluator reason.
* [ ] One active goal per session.
* [ ] Stop if model confirms completion.
* [ ] Stop if max turns/time reached.
* [ ] Resume active goal.
* [ ] Non-interactive goal usage.

## 1.13.3. Cron/task tools

* [ ] Create scheduled task.
* [ ] List scheduled tasks.
* [ ] Update scheduled task.
* [ ] Delete scheduled task.
* [ ] Get task.
* [ ] Stop task.
* [ ] Task status.
* [ ] Task persistence.
* [ ] Task permission rules.
* [ ] Task notifications.

---

# P1.14. Review/security review

* [ ] Review diff.
* [ ] Review branch.
* [ ] Review PR.
* [ ] Security review.
* [ ] Find vulnerabilities.
* [ ] Find secrets.
* [ ] Find auth/permission bugs.
* [ ] Find SQL injection.
* [ ] Find XSS.
* [ ] Find unsafe deserialization.
* [ ] Find path traversal.
* [ ] Find SSRF.
* [ ] Find command injection.
* [ ] Find dependency risks.
* [ ] Find hardcoded credentials.
* [ ] Find missing tests.
* [ ] Find broken edge cases.
* [ ] Generate review comments.
* [ ] Prioritize findings.
* [ ] Avoid false-positive spam.
* [ ] Support “fix these review comments”.
* [ ] Support “autofix PR”.
* [ ] Mention what was inspected and not inspected.

---

# P1.15. Monitoring

Claude Code has a `Monitor` tool that can watch logs, PRs, CI, directories, scripts and send output lines to Claude; plugin monitors are also documented. ([Claude][4])

* [ ] Watch command output.
* [ ] Watch log file.
* [ ] Watch directory.
* [ ] Watch CI status.
* [ ] Watch PR status.
* [ ] Watch script output.
* [ ] Send new lines to agent.
* [ ] Trigger agent turn on event.
* [ ] Stop monitor.
* [ ] List monitors.
* [ ] Monitor timeout.
* [ ] Monitor filters.
* [ ] Plugin-provided monitors.
* [ ] Avoid infinite loops.
* [ ] Permission rules for monitors.

---

# P2. Power-user/platform features

# P2.1. Plugin system

Claude Code plugins can share skills, agents, hooks, MCP servers, LSP config, monitors, commands, binaries and settings. They can be local, private, marketplace-style, URL/zip-based, and namespaced. ([Claude][17])

## 2.1.1. Plugin manifest

* [ ] `.agent-plugin/plugin.json` equivalent.
* [ ] Name.
* [ ] Version.
* [ ] Description.
* [ ] Author.
* [ ] Skills list.
* [ ] Agents list.
* [ ] Hooks list.
* [ ] MCP servers.
* [ ] LSP servers.
* [ ] Monitors.
* [ ] Commands.
* [ ] Bin directory.
* [ ] Settings.
* [ ] Compatibility constraints.
* [ ] Required permissions.
* [ ] Signature/checksum if enterprise.

## 2.1.2. Plugin lifecycle

* [ ] Install plugin from local dir.
* [ ] Install plugin from URL.
* [ ] Install plugin from zip/archive.
* [ ] List plugins.
* [ ] Enable plugin.
* [ ] Disable plugin.
* [ ] Remove plugin.
* [ ] Reload plugins.
* [ ] Update plugin.
* [ ] Pin plugin version.
* [ ] Plugin namespaces.
* [ ] Plugin conflict detection.
* [ ] Plugin diagnostics.
* [ ] Plugin security review.
* [ ] Plugin marketplace/private registry.
* [ ] Team-shared plugin config.
* [ ] Plugin migration from `.claude`/local config.

## 2.1.3. Plugin contents

* [ ] Skills.
* [ ] Slash commands.
* [ ] Subagents.
* [ ] Hooks.
* [ ] MCP servers.
* [ ] LSP config.
* [ ] Monitors.
* [ ] Binaries/scripts.
* [ ] Templates.
* [ ] Prompt fragments.
* [ ] Settings defaults.
* [ ] Docs.

---

# P2.2. Agent teams

Claude Code docs describe experimental agent teams: multiple sessions coordinated by a lead agent with shared tasks and inter-agent messaging; this differs from subagents. ([Claude][18])

* [ ] Create agent team.
* [ ] Delete agent team.
* [ ] Lead agent.
* [ ] Teammate agents.
* [ ] Shared task board.
* [ ] Inter-agent messages.
* [ ] Agent roles.
* [ ] Agent idle detection.
* [ ] Team-level status.
* [ ] Team-level cost tracking.
* [ ] Assign task to agent.
* [ ] Reassign task.
* [ ] Merge agent results.
* [ ] Detect conflicting file edits.
* [ ] Worktree per teammate.
* [ ] Shared context summary.
* [ ] Private agent context.
* [ ] Human can message lead.
* [ ] Human can message teammate.
* [ ] Team can research alternatives in parallel.
* [ ] Team can debug competing hypotheses.
* [ ] Team can implement cross-layer features.
* [ ] Team can review each other’s changes.
* [ ] Stop whole team.
* [ ] Stop individual teammate.

---

# P2.3. Remote control / dispatch / teleport

Claude Code docs mention working from terminal, desktop, web/iOS, Slack, remote control, dispatch and teleporting work between surfaces. ([Claude][14])

* [ ] Remote-control session.
* [ ] Start local session from remote UI.
* [ ] Send prompt to running local session.
* [ ] Mobile notification.
* [ ] Dispatch task to repo.
* [ ] Dispatch task to running agent.
* [ ] Teleport session to another surface.
* [ ] Desktop integration.
* [ ] Web integration.
* [ ] Slack integration.
* [ ] Preserve session identity across surfaces.
* [ ] Preserve permissions across surfaces.
* [ ] Show which surface controls session.
* [ ] Prevent two UIs from conflicting.
* [ ] Attach/detach semantics.
* [ ] Remote env inspection.

---

# P2.4. Desktop/web/cloud surfaces

* [ ] Terminal TUI.
* [ ] Browser UI.
* [ ] Desktop app.
* [ ] IDE panel.
* [ ] Slack bot.
* [ ] CI/CD mode.
* [ ] Mobile/web dispatch.
* [ ] Shared session links.
* [ ] Cloud execution environment.
* [ ] Local execution environment.
* [ ] Remote execution environment.
* [ ] Environment selection.
* [ ] File sync.
* [ ] Repo checkout.
* [ ] Branch/worktree sync.
* [ ] Secrets management.
* [ ] Artifact download.
* [ ] Diff review UI.
* [ ] Terminal output panel.
* [ ] Permissions UI.
* [ ] Agent status dashboard.

---

# P2.5. GitHub/CI/CD integration

Claude Code docs show CLI use in CI-like flows and list GitHub/Slack install commands; web/CI/CD surfaces are also documented. ([Claude][14])

* [ ] GitHub app install.
* [ ] Slack app install.
* [ ] PR URL parsing.
* [ ] Resume by PR URL.
* [ ] Read PR diff.
* [ ] Read PR comments.
* [ ] Generate PR review.
* [ ] Post PR comments.
* [ ] Autofix PR comments.
* [ ] Read CI status.
* [ ] Read CI logs.
* [ ] Fix CI failures.
* [ ] Open pull request.
* [ ] Update pull request.
* [ ] Create branch.
* [ ] Commit changes.
* [ ] Push with explicit approval.
* [ ] Never force push unless explicit.
* [ ] GitLab equivalent.
* [ ] Bitbucket equivalent.
* [ ] GitHub Actions integration.
* [ ] CI non-interactive mode.
* [ ] Exit codes for automation.
* [ ] JSON output mode.

---

# P2.6. Notebook support

The tools reference includes `NotebookEdit`. ([Claude][4])

* [ ] Read notebook cells.
* [ ] Edit code cell.
* [ ] Edit markdown cell.
* [ ] Add cell.
* [ ] Delete cell.
* [ ] Preserve outputs optionally.
* [ ] Clear outputs.
* [ ] Run notebook command.
* [ ] Understand cell execution order.
* [ ] Convert notebook context safely.
* [ ] Avoid corrupting `.ipynb`.
* [ ] Show notebook diff in readable way.

---

# P2.7. Output styles, themes, keybindings, statusline

Claude Code docs list commands for themes, keybindings, statusline, color and output/status customization. ([Claude][7])

* [ ] Theme selection.
* [ ] Custom themes.
* [ ] Light/dark.
* [ ] Color accents.
* [ ] Statusline config.
* [ ] Show model.
* [ ] Show mode.
* [ ] Show cwd.
* [ ] Show git branch.
* [ ] Show cost/tokens.
* [ ] Show context usage.
* [ ] Keybindings config.
* [ ] Vim mode.
* [ ] Multiline input.
* [ ] Paste handling.
* [ ] Image paste.
* [ ] Alternate screen toggle.
* [ ] TUI layout.
* [ ] Transcript viewer.
* [ ] Diff viewer.
* [ ] Notification style.

---

# P2.8. Cost, usage and telemetry

* [ ] Token counting.
* [ ] Cost estimate.
* [ ] Per-session usage.
* [ ] Per-project usage.
* [ ] Per-model usage.
* [ ] Tool-call counts.
* [ ] Subagent usage.
* [ ] MCP usage.
* [ ] Background agent usage.
* [ ] Usage command.
* [ ] Extra usage command.
* [ ] Export usage.
* [ ] Rate limit display.
* [ ] Retry after rate limit.
* [ ] Privacy settings.
* [ ] Telemetry opt-out.
* [ ] Debug logs.
* [ ] Error reporting.

---

# P2.9. Browser/computer-use style capabilities

* [ ] Chrome integration.
* [ ] Browser page awareness.
* [ ] Screenshot capture.
* [ ] DOM inspection.
* [ ] Click/type automation if supported.
* [ ] Use only with explicit permission.
* [ ] Avoid credential entry unless user controls it.
* [ ] Web app debugging.
* [ ] Visual QA.
* [ ] Compare screenshot to design.
* [ ] Figma-to-code workflow via MCP/plugin.
* [ ] Browser console logs.
* [ ] Network logs.
* [ ] Localhost app inspection.

---

# P3. Enterprise, policy, security, cloud

# P3.1. Enterprise managed settings

Claude Code docs describe managed/user/project/local settings and precedence, with managed policy taking highest precedence. ([Claude][9])

* [ ] Managed config.
* [ ] Organization policy.
* [ ] Disallow bypass permissions.
* [ ] Force specific model/provider.
* [ ] Disable web search.
* [ ] Disable MCP.
* [ ] Allow only approved MCP servers.
* [ ] Allow only approved plugins.
* [ ] Disable auto memory.
* [ ] Disable shell.
* [ ] Disable risky commands.
* [ ] Force audit logging.
* [ ] Force telemetry settings.
* [ ] Force protected paths.
* [ ] Force permission mode.
* [ ] MDM/plist/registry/file-based policy.
* [ ] Policy diagnostics.
* [ ] Policy conflict explanations.

---

# P3.2. Security model

* [ ] Local sandbox.
* [ ] Container sandbox.
* [ ] Network sandbox.
* [ ] Filesystem sandbox.
* [ ] Command sandbox.
* [ ] Protected paths.
* [ ] Secret redaction.
* [ ] Prompt injection detection for tool outputs.
* [ ] Treat external content as untrusted.
* [ ] Prevent docs/web content from overriding system policy.
* [ ] Prevent malicious repo instructions.
* [ ] Confirmation for destructive commands.
* [ ] Confirmation for remote side effects.
* [ ] Confirmation for package install.
* [ ] Confirmation for DB migrations.
* [ ] Confirmation for deploy.
* [ ] Confirmation for IAM/security changes.
* [ ] Confirmation for force push.
* [ ] Audit log.
* [ ] Replay session.
* [ ] Compliance export.
* [ ] Zero data retention option if applicable.
* [ ] Provider routing policy.
* [ ] SSO/SAML if enterprise.
* [ ] Role-based access.

---

# P3.3. Auto mode

Claude Code auto mode is documented as a mode with background classifier and hard deny behavior for sensitive operations such as downloads/execution, sensitive data, production deploy/migrations, IAM and force push. ([Claude][5])

* [ ] Auto-approve safe actions.
* [ ] Background risk classifier.
* [ ] Hard-deny dangerous actions.
* [ ] Ask user when uncertain.
* [ ] Block:

  * [ ] arbitrary download+execute;
  * [ ] sensitive data access;
  * [ ] production deployment;
  * [ ] database migration;
  * [ ] IAM/security policy changes;
  * [ ] force push;
  * [ ] destructive filesystem actions.
* [ ] Explain auto-mode decision.
* [ ] Log classifier decision.
* [ ] Enterprise can disable auto mode.
* [ ] Protected paths still respected.
* [ ] Auto mode fallback to default when classifier unavailable.

---

# P3.4. Providers/models

Claude Code docs mention model switching through `/model` or CLI flags, and setup commands for Bedrock/Vertex. ([Claude][2])

* [ ] Model selector.
* [ ] Effort selector.
* [ ] Fast mode.
* [ ] High-reasoning mode.
* [ ] Provider selector:

  * [ ] Anthropic API;
  * [ ] Bedrock;
  * [ ] Vertex;
  * [ ] OpenAI-compatible;
  * [ ] local model if your product supports it.
* [ ] Per-agent model.
* [ ] Per-skill model.
* [ ] Per-task model.
* [ ] Fallback model.
* [ ] Rate-limit-aware routing.
* [ ] Cost-aware routing.
* [ ] Tool-capability-aware routing.
* [ ] Context-size-aware routing.
* [ ] Disable unsupported features per model.
* [ ] Show model in UI.
* [ ] Store model used in transcript.

---

# P3.5. Routines / scheduled cloud tasks

Claude Code docs distinguish `/loop`, desktop scheduled tasks and cloud scheduled tasks/routines. ([Claude][16])

* [ ] Cloud routine.
* [ ] Desktop scheduled task.
* [ ] Local loop.
* [ ] Recurring schedule.
* [ ] Minimum interval enforcement.
* [ ] Timezone handling.
* [ ] Calendar-like schedule.
* [ ] Run without open terminal.
* [ ] Notify on completion.
* [ ] Notify on failure.
* [ ] Connect to repo.
* [ ] Connect to issue/PR.
* [ ] Safe permission handling.
* [ ] Stop routine.
* [ ] Edit routine.
* [ ] Audit routine actions.

---

# Отдельный parity-checklist по built-in tools

Из official tools reference стоит сделать у себя хотя бы такие tool families: `Agent`, `AskUserQuestion`, shell tools, cron/task tools, file tools, worktree tools, search tools, LSP, monitor, notebook, MCP resources/tools, skills, web, todo. ([Claude][4])

## Must-have tools

* [ ] `Read`
* [ ] `Write`
* [ ] `Edit`
* [ ] `Glob`
* [ ] `Grep`
* [ ] `Bash`
* [ ] `PowerShell`
* [ ] `TodoWrite`
* [ ] `AskUserQuestion`
* [ ] `WebSearch`
* [ ] `WebFetch`
* [ ] `EnterPlanMode`
* [ ] `ExitPlanMode`

## Should-have tools

* [ ] `Agent`
* [ ] `Skill`
* [ ] `TaskCreate`
* [ ] `TaskList`
* [ ] `TaskGet`
* [ ] `TaskUpdate`
* [ ] `TaskStop`
* [ ] `CronCreate`
* [ ] `CronList`
* [ ] `CronDelete`
* [ ] `EnterWorktree`
* [ ] `ExitWorktree`
* [ ] `LSP`
* [ ] `Monitor`
* [ ] `NotebookEdit`
* [ ] `ToolSearch`
* [ ] MCP resource read.
* [ ] MCP tool call.
* [ ] MCP prompt call.

## Nice-to-have tools

* [ ] `TeamCreate`
* [ ] `TeamDelete`
* [ ] `SendMessage`
* [ ] `ShareOnboardingGuide`
* [ ] PR review tool.
* [ ] CI log tool.
* [ ] Browser tool.
* [ ] Figma/design tool.
* [ ] GitHub/GitLab tool.
* [ ] Slack tool.
* [ ] Desktop/mobile notification tool.

---

# Suggested implementation order for your LangGraph analogue

## Phase 1 — “usable coding agent”

* [x] Interactive CLI.
* [x] Session state.
* [x] Read/Edit/Write/Glob/Grep/Bash.
* [x] Permission gate.
* [x] Plan mode.
* [x] TODO state.
* [x] Git diff/status awareness.
* [x] Test/build verification loop.
* [x] Context compaction.
* [x] File snapshots.
* [x] Resume session.
* [x] Final summary with changed files and verification.

## Phase 2 — “daily driver”

* [x] Slash commands.
* [x] Project/user memory.
* [x] Settings scopes.
* [x] Better permission rules.
* [x] Hooks.
* [x] Skills.
* [~] Subagents: local child graph baseline works; nested approval resume and background lifecycle remain.
* [defer] LSP.
* [defer] IDE integration.
* [~] Worktree/workspace controls: frontend workspace/project/branch controls exist; full isolated worktree workflow remains post-MVP.
* [defer] Background session support.

## Phase 3 — “Claude Code-like platform”

* [~] MCP: stdio/config/tools/resources/prompts baseline works; HTTP/OAuth/server mode deferred.
* [~] Plugin system: local/git plugin baseline, skills/hooks/policies/context/MCP contributions work; marketplace and executable adapters deferred.
* [~] Agent view: basic child-run/session surfaces exist; richer transcript/team view deferred.
* [defer] Remote control.
* [defer] GitHub/CI integration.
* [defer] PR review/autofix.
* [~] Loop/goal/tasks: eval/replay and local agent task baseline exist; scheduled/background task lifecycle deferred.
* [defer] Monitor.
* [x] Desktop/web UI: React browser frontend MVP is implemented.
* [~] Usage/cost dashboard: `/cost` and config/status surfaces exist; provider-specific cost accounting/dashboard deferred.

## Phase 4 — “enterprise / advanced”

* [defer] Managed policy.
* [defer] Enterprise permissions.
* [~] Sandboxing: local permission/safety baseline exists; enterprise/container sandboxing deferred.
* [defer] Auto mode classifier.
* [defer] Agent teams.
* [defer] Cloud scheduled tasks.
* [defer] Plugin marketplace.
* [~] Audit/compliance: logs/evals/observability baseline exists; compliance export deferred.
* [~] Multi-provider model routing: provider abstraction exists; advanced routing/fallback/cost-aware policy deferred.

---

# Самый важный “definition of done”

Твой аналог будет ощущаться как Claude Code-like не тогда, когда у него будет 100 slash-команд, а когда он стабильно делает это:

1. **Понимает проект**: сам находит релевантные файлы, инструкции, git-состояние.
2. **Планирует перед риском**: умеет plan mode и не ломится редактировать вслепую.
3. **Редактирует безопасно**: минимальные diff, snapshots, rollback, не трогает чужие изменения.
4. **Проверяет себя**: запускает тесты/build/lint и честно сообщает результат.
5. **Работает итеративно**: ошибка → анализ → исправление → повторная проверка.
6. **Управляется пользователем**: interrupt, permissions, slash commands, resume.
7. **Расширяется**: skills, hooks, MCP, subagents.
8. **Не теряет состояние**: session persistence, memory, compaction, TODO.
9. **Не делает опасного молча**: protected paths, command policy, permission modes.
10. **Даёт прозрачный итог**: что изменено, почему, чем проверено, что осталось.

[1]: https://code.claude.com/docs/llms.txt "code.claude.com"
[2]: https://code.claude.com/docs/en/how-claude-code-works "How Claude Code works - Claude Code Docs"
[3]: https://code.claude.com/docs/en/cli-reference "CLI reference - Claude Code Docs"
[4]: https://code.claude.com/docs/en/tools-reference "Tools reference - Claude Code Docs"
[5]: https://code.claude.com/docs/en/permission-modes "Choose a permission mode - Claude Code Docs"
[6]: https://code.claude.com/docs/en/permissions "Configure permissions - Claude Code Docs"
[7]: https://code.claude.com/docs/en/commands "Commands - Claude Code Docs"
[8]: https://docs.anthropic.com/en/docs/claude-code/memory "How Claude remembers your project - Claude Code Docs"
[9]: https://code.claude.com/docs/en/settings "Claude Code settings - Claude Code Docs"
[10]: https://code.claude.com/docs/en/skills "Extend Claude with skills - Claude Code Docs"
[11]: https://code.claude.com/docs/en/sub-agents "Create custom subagents - Claude Code Docs"
[12]: https://code.claude.com/docs/en/hooks-guide "Automate workflows with hooks - Claude Code Docs"
[13]: https://code.claude.com/docs/en/mcp "Connect Claude Code to tools via MCP - Claude Code Docs"
[14]: https://code.claude.com/docs/en/overview "Claude Code overview - Claude Code Docs"
[15]: https://code.claude.com/docs/en/agent-view "Manage multiple agents with agent view - Claude Code Docs"
[16]: https://code.claude.com/docs/en/scheduled-tasks "Run prompts on a schedule - Claude Code Docs"
[17]: https://code.claude.com/docs/en/plugins "Create plugins - Claude Code Docs"
[18]: https://code.claude.com/docs/en/agent-teams "Orchestrate teams of Claude Code sessions - Claude Code Docs"
