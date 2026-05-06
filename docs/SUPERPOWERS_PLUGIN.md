# Superpowers Plugin

Superpowers is an external agentic skills framework and software development methodology plugin. The upstream package name is `superpowers`; its Codex manifest declares `skills: "./skills/"`, and the Claude manifest is used as metadata fallback.

## Install

```powershell
$env:NETWORK_ENABLED = "true"
lg-agent plugins install superpowers@git+https://github.com/obra/superpowers.git#v5.1.0
lg-agent plugins list
lg-agent skills list
```

For offline development and tests, a local plugin directory can be installed:

```powershell
lg-agent plugins install C:\path\to\superpowers
```

## Discovery

The adapter resolves metadata in this order:

1. `.codex-plugin/plugin.json`, including the `skills` field.
2. Repo `skills/` fallback for known Superpowers layout.
3. `package.json` name/version fallback.
4. `.claude-plugin/plugin.json` metadata fallback.

For Superpowers, `plugin_name` is `superpowers`, `skills_path` is `<repo>/skills`, and `bootstrap_skill` is `using-superpowers`.

## Registered Skills

Superpowers skills are registered with a namespace:

```text
superpowers/using-superpowers
superpowers/brainstorming
superpowers/test-driven-development
superpowers/systematic-debugging
...
```

The unqualified alias, such as `brainstorming`, resolves to `superpowers/brainstorming` only when no local skill with that name exists. Built-ins such as `verify` do not conflict with `superpowers/verification-before-completion`.

Explicit invocation:

```powershell
lg-agent query "/skill superpowers/brainstorming Let's make a react todo list"
```

Model invocation through `SkillTool` uses the same graph route:

```json
{"skill": "superpowers/brainstorming", "args": "Let's make a react todo list"}
```

## Bootstrap Context

When the plugin is enabled, `context_builder` injects a compact bootstrap fragment before the first model response. It tells the model:

- Superpowers is enabled.
- `superpowers/using-superpowers` is the bootstrap rule.
- development tasks should check relevant Superpowers skills before answering or acting.
- new feature/build/component prompts should activate `superpowers/brainstorming` before code.
- user explicit instructions have priority.
- upstream tool names map to runtime tools: Skill -> `skill`, TodoWrite -> `todo_write`, Task -> `agent`, Read -> `read_file`, Bash -> `bash`, Grep -> `grep`, Glob -> `glob`.

The upstream `SKILL.md` files are not rewritten.

## Acceptance Trigger

The runtime does not rely only on model obedience. A `plugin_policy` LangGraph node runs after slash-command routing and before `context_builder`. For an enabled Superpowers plugin, obvious development prompts activate `superpowers/brainstorming` through `skill_graph`.

Acceptance scenario:

```text
clean session
user: Let's make a react todo list
```

Expected graph behavior:

- `superpowers_skill_policy_applied`
- `skill_started` for `superpowers/brainstorming`
- `skill_finished` for `superpowers/brainstorming`
- model response happens after the skill prompt is inserted

Session metadata stores `skill_invocations`, so the same session does not repeatedly activate brainstorming on every later turn.

## Security And Trust

Superpowers skill files are untrusted behavior-shaping prompt content. They cannot bypass tool permissions. File writes, shell, network, MCP, and future plugin tools still go through `PermissionService` and normal approval flow.

Install/update never executes package scripts. Git access requires `NETWORK_ENABLED=true`. License text is preserved in plugin `lock.json` when a license file is present.

## Limitations

The first policy pass implements deterministic activation for new development work and debugging prompts. Completion claims such as "I think this is done" do not yet auto-trigger `superpowers/verification-before-completion`; that remains a future policy mapping.

CI and local acceptance use a fixture plugin layout, so they do not require live GitHub access. Live GitHub install is an optional smoke that requires git plus `NETWORK_ENABLED=true`.

Upstream Superpowers content may evolve. The runtime treats external plugin content as untrusted prompt content and keeps permissions, tool scope, and user-instruction priority enforced by the host runtime.
