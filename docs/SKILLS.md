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

Optional audited skills are documented but disabled initially: `loop`, `schedule`, `keybindings-help`, `lorem-ipsum`, `claude-api`, `claude-api-content`, `claude-in-chrome`.

Skills do not own workflow routing. LangGraph invokes skills through `skill_graph` and `SkillTool`.

