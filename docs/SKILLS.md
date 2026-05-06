# Skills

Skills are first-class prompt-driven capabilities. File-based skills use:

```text
skill-name/
  SKILL.md
```

`SKILL.md` supports YAML frontmatter:

- `name`
- `description`
- `allowed_tools`
- `model`
- `effort`
- `hooks`
- `context`
- `agent`
- `paths`
- `shell`
- `enabled`
- `feature_gate`

Built-in skills:

- `batch`
- `debug`
- `remember`
- `simplify`
- `skillify`
- `stuck`
- `update-config`
- `verify`

Plugin skills are loaded by `PluginService` as external contributions and registered with a namespace:

```text
<plugin-name>/<skill-name>
```

For example, the Superpowers plugin registers:

- `superpowers/using-superpowers`
- `superpowers/brainstorming`
- `superpowers/test-driven-development`
- `superpowers/systematic-debugging`

Unqualified aliases such as `brainstorming` may resolve to a plugin skill only when no local or built-in skill with that name exists.

Optional audited skills are documented but disabled initially: `loop`, `schedule`, `keybindings-help`, `lorem-ipsum`, `claude-api`, `claude-api-content`, `claude-in-chrome`.

Skills do not own workflow routing. LangGraph invokes skills through `skill_graph` and `SkillTool`.

When Langfuse observability is enabled, skill lifecycle events are exported through `ObservabilityService` as redacted RuntimeEvent-derived events. Observability does not change skill lookup, allowed-tool scoping, plugin bootstrap, or permission behavior.

MCP prompts are discovered through `MCPService.prompts/list` and can be retrieved as untrusted prompt content with `prompts/get`. Automatic MCP prompt-to-skill registration is not enabled in Phase 2; the planned namespace is `mcp/<server>/prompt/<prompt>`.

Skill arguments are typed with Pydantic schemas. Built-in skills use dedicated schemas such as
`RememberSkillArgs`, `VerifySkillArgs`, `SimplifySkillArgs`, and `SkillifySkillArgs`; file-based
skills without a specific schema use `GenericSkillArgs`. The runtime validates raw args before
skill execution and returns a structured ToolMessage validation error if args are invalid.
Prompt interpolation is handled separately by `format_skill_args_for_prompt`.

Runtime status after fixes:

- `/skill <name>` enters the graph skill route.
- Model-invoked `skill` tool calls also enter the skill route.
- Skill lifecycle events are visible.
- `allowed_tools` narrows provider-bound tools and is enforced by `tool_router`.
- Plugin bootstrap context can make plugin skills discoverable before the first model response.
- `remember` writes durable memory; `/memory` reads it.
- Other bundled skills remain prompt-driven capabilities that use the shared model/tool loop and normal permission rules for side effects.
- Skill events, including plugin skills such as `superpowers/brainstorming`, are observable when Langfuse is enabled.
