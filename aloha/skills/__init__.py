"""
aloha/skills/

Skill system for the Aloha agent.

A *skill* is a curated, reusable Home Assistant playbook — a markdown file with
YAML frontmatter that teaches the agent how to accomplish a specific class of
task (configure / debug / operate) using the regular HA tools.

This mirrors the Claude Code skill model: the agent is shown a lightweight index
of available skills (name + description) in its system prompt, and pulls the full
playbook on demand by calling the ``use_skill`` tool. Skills keep the HA
*expertise* — the how-to knowledge — out of the model's weights and in editable,
shippable files.

Discovery order (later overrides earlier on name collision):
  1. Built-in library: ``aloha/skills/library/*.md``
  2. User skills:      ``{data_dir}/skills/*.md``   (optional)

Frontmatter schema:
  ---
  name: debug-automation            # kebab-case, unique
  description: One-line "when to use this" summary (shown in the index)
  category: configure | debug | operate
  ---
  <markdown playbook body>
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

import yaml

log = logging.getLogger(__name__)

_LIBRARY_DIR = Path(__file__).parent / "library"


@dataclass(frozen=True)
class Skill:
    """A single loaded skill."""

    name: str
    description: str
    category: str
    body: str
    source: str  # absolute path the skill was loaded from


def _parse_skill(path: Path) -> Optional[Skill]:
    """Parse one markdown-with-frontmatter file into a Skill, or None on error."""
    try:
        text = path.read_text(encoding="utf-8")
    except Exception:
        log.warning("Could not read skill file %s", path, exc_info=True)
        return None

    name = path.stem
    description = ""
    category = "general"
    body = text

    # Split frontmatter if present: leading '---\n ... \n---\n'
    if text.startswith("---"):
        parts = text.split("---", 2)
        if len(parts) == 3:
            try:
                meta = yaml.safe_load(parts[1]) or {}
                name = str(meta.get("name", name))
                description = str(meta.get("description", "")).strip()
                category = str(meta.get("category", category)).strip() or "general"
                body = parts[2].strip()
            except Exception:
                log.warning("Bad frontmatter in skill %s; using raw body", path, exc_info=True)

    if not description:
        # Fall back to first non-empty body line as the description.
        for line in body.splitlines():
            line = line.strip().lstrip("#").strip()
            if line:
                description = line
                break

    return Skill(name=name, description=description, category=category, body=body, source=str(path))


def load_skills(data_dir: Optional[Path] = None) -> dict[str, Skill]:
    """
    Load all skills, built-in first then user skills (user overrides built-in).

    Parameters
    ----------
    data_dir : Path | None
        If given, ``{data_dir}/skills/*.md`` are loaded as user skills.

    Returns
    -------
    dict[str, Skill]   keyed by skill name, in stable (sorted) order.
    """
    skills: dict[str, Skill] = {}

    search_dirs: list[Path] = [_LIBRARY_DIR]
    if data_dir is not None:
        search_dirs.append(Path(data_dir) / "skills")

    for d in search_dirs:
        if not d.is_dir():
            continue
        for path in sorted(d.glob("*.md")):
            skill = _parse_skill(path)
            if skill:
                skills[skill.name] = skill

    return dict(sorted(skills.items()))


def render_skill_index(skills: dict[str, Skill]) -> str:
    """Render a compact index of skills for injection into the system prompt."""
    if not skills:
        return ""
    by_cat: dict[str, list[Skill]] = {}
    for s in skills.values():
        by_cat.setdefault(s.category, []).append(s)

    lines = [
        "You have HA-specific SKILLS — curated playbooks for common tasks.",
        "When a request matches one, call the `use_skill` tool with its name to load "
        "the full step-by-step playbook, then follow it. Available skills:",
    ]
    for cat in sorted(by_cat):
        lines.append(f"\n[{cat}]")
        for s in by_cat[cat]:
            lines.append(f"  - {s.name}: {s.description}")
    return "\n".join(lines)
