import pytest

from claude_code_langgraph.skills.loader import SkillLoader


def test_loads_skill_name_skill_md_and_metadata(tmp_path):
    skill_dir = tmp_path / "example-skill"
    skill_dir.mkdir()
    (skill_dir / "SKILL.md").write_text(
        "---\nname: example\nallowed_tools:\n  - read_file\nmodel: fake\n---\nUse {{args}} carefully.\n",
        encoding="utf-8",
    )

    skill = SkillLoader().load_skill_dir(skill_dir)

    assert skill.metadata.name == "example"
    assert skill.metadata.allowed_tools == ["read_file"]
    assert "Use {{args}}" in skill.prompt_template


def test_invalid_skill_metadata_is_rejected(tmp_path):
    skill_dir = tmp_path / "bad"
    skill_dir.mkdir()
    (skill_dir / "SKILL.md").write_text("---\nname: 123\n---\nBody\n", encoding="utf-8")

    with pytest.raises(ValueError):
        SkillLoader().load_skill_dir(skill_dir)

