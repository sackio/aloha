"""Skill loader: built-ins, user skills, frontmatter, override."""

from aloha.skills import load_skills, render_skill_index


def test_builtin_library_loads():
    skills = load_skills()
    assert len(skills) >= 20  # the shipped library
    # frontmatter parsed
    s = next(iter(skills.values()))
    assert s.name and s.description and s.category


def test_user_skill_picked_up(data_dir):
    (data_dir / "skills").mkdir()
    (data_dir / "skills" / "my-skill.md").write_text(
        "---\nname: my-skill\ndescription: does a thing\ncategory: operate\n---\n\n1. step\n"
    )
    skills = load_skills(data_dir)
    assert "my-skill" in skills
    assert skills["my-skill"].description == "does a thing"
    assert skills["my-skill"].category == "operate"


def test_user_overrides_builtin(data_dir):
    builtin = next(iter(load_skills().keys()))
    (data_dir / "skills").mkdir()
    (data_dir / "skills" / f"{builtin}.md").write_text(
        f"---\nname: {builtin}\ndescription: OVERRIDDEN\ncategory: operate\n---\n\nbody\n"
    )
    skills = load_skills(data_dir)
    assert skills[builtin].description == "OVERRIDDEN"


def test_render_index_groups_by_category():
    idx = render_skill_index(load_skills())
    assert "SKILLS" in idx
    assert "use_skill" in idx
