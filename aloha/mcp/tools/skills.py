"""
aloha/mcp/tools/skills.py

Meta-tools that expose the Aloha skill library to the agent.

  list_skills()           — list available skills (name, category, description)
  use_skill(skill_name)   — return a skill's full step-by-step playbook

The agent is shown a compact skill index in its system prompt; when a request
matches a skill it calls ``use_skill`` to pull the playbook, then executes it
using the regular HA tools. Keeping the playbook out of the system prompt keeps
the prompt small and lets the model load only what it needs.
"""

from __future__ import annotations

import json
from typing import Any

from aloha.agent.types import SafetyLevel, ToolDef
from aloha.skills import load_skills

# ---------------------------------------------------------------------------
# Tool definitions
# ---------------------------------------------------------------------------

TOOLS: list[ToolDef] = [
    ToolDef(
        name="list_skills",
        description=(
            "List Aloha's built-in Home Assistant skills (curated playbooks for "
            "configure/debug/operate tasks). Returns each skill's name, category, "
            "and a one-line description of when to use it."
        ),
        parameters={
            "type": "object",
            "properties": {
                "category": {
                    "type": "string",
                    "description": "Optional filter: 'configure', 'debug', or 'operate'.",
                },
            },
        },
        safety=SafetyLevel.READ,
        returns="JSON list of {name, category, description}",
    ),
    ToolDef(
        name="use_skill",
        description=(
            "Load the full step-by-step playbook for a named skill and follow it. "
            "Call this when the user's request matches a skill from the skill index "
            "or list_skills(). Returns the skill's markdown instructions."
        ),
        parameters={
            "type": "object",
            "properties": {
                "skill_name": {
                    "type": "string",
                    "description": "The skill name, e.g. 'debug-automation'.",
                },
            },
            "required": ["skill_name"],
        },
        safety=SafetyLevel.READ,
        returns="The skill's full markdown playbook.",
    ),
]

TOOL_NAMES: set[str] = {t.name for t in TOOLS}


# ---------------------------------------------------------------------------
# Dispatcher
# ---------------------------------------------------------------------------


async def execute_skills_tool(name: str, args: dict[str, Any]) -> str:
    """Execute a skills meta-tool."""
    skills = load_skills()

    if name == "list_skills":
        category = (args.get("category") or "").strip().lower()
        items = [
            {"name": s.name, "category": s.category, "description": s.description}
            for s in skills.values()
            if not category or s.category.lower() == category
        ]
        if not items:
            return "No skills available."
        return json.dumps(items, indent=2)

    if name == "use_skill":
        skill_name = (args.get("skill_name") or "").strip()
        skill = skills.get(skill_name)
        if skill is None:
            available = ", ".join(sorted(skills)) or "(none)"
            return f"Skill '{skill_name}' not found. Available skills: {available}"
        return (
            f"# Skill: {skill.name} ({skill.category})\n"
            f"{skill.description}\n\n"
            f"Follow these steps:\n\n{skill.body}"
        )

    raise ValueError(f"Unknown skills tool: {name!r}")
