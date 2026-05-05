from claude_code_langgraph.commands.registry import build_builtin_command_registry


def test_builtin_commands_are_registered():
    registry = build_builtin_command_registry()

    for name in ["help", "clear", "compact", "resume", "export", "skills", "status", "cost", "config", "doctor", "memory", "todo"]:
        assert registry.get(name).name == name

