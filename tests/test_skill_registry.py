"""Pytest coverage for skill registry behavior in the Python/LangGraph assistant."""

from langgraph_agent_blueprint.skills.registry import build_builtin_skill_registry


def test_builtin_skills_present():
    registry = build_builtin_skill_registry()

    for name in ["debug", "remember", "simplify", "skillify", "stuck", "update-config", "verify", "batch"]:
        assert registry.get(name).metadata.name == name


def test_dynamic_skill_registration(tmp_path):
    registry = build_builtin_skill_registry()
    skill_dir = tmp_path / "custom"
    skill_dir.mkdir()
    (skill_dir / "SKILL.md").write_text("---\nname: custom\n---\nCustom prompt\n", encoding="utf-8")

    registry.load_from_paths([tmp_path])

    assert registry.get("custom").prompt_template == "Custom prompt\n"

