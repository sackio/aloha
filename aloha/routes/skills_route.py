"""
aloha/routes/skills_route.py

Serve + manage the HA skill library from the box's own web app. Built-in skills
ship with Aloha; user skills live in ``{data_dir}/skills/`` and are picked up by
the agent automatically (the loader reads both). This lets the box UI browse
skills, read them, and add/remove your own.

  GET    /api/skills           — list all skills (name, category, description, editable)
  GET    /api/skills/{name}    — one skill's full markdown playbook (raw text)
  POST   /api/skills           — add/replace a user skill {name, content}
  DELETE /api/skills/{name}    — remove a user skill (built-ins are protected)
"""

from __future__ import annotations

import re
from pathlib import Path

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import JSONResponse, PlainTextResponse
from pydantic import BaseModel

from aloha.config import AlohaConfig
from aloha.skills import load_skills

router = APIRouter()

_SLUG = re.compile(r"[^a-z0-9-]+")


def _user_skills_dir(cfg: AlohaConfig) -> Path:
    return Path(cfg.data_dir) / "skills"


def _is_user_skill(source: str, cfg: AlohaConfig) -> bool:
    try:
        return _user_skills_dir(cfg).resolve() in Path(source).resolve().parents
    except Exception:
        return False


@router.get("/api/skills")
async def list_skills(request: Request) -> JSONResponse:
    cfg = AlohaConfig.load()
    skills = load_skills(cfg.data_dir)
    return JSONResponse(
        [
            {
                "name": s.name,
                "category": s.category,
                "description": s.description,
                "editable": _is_user_skill(s.source, cfg),
                "url": f"/api/skills/{s.name}",
            }
            for s in skills.values()
        ]
    )


@router.get("/api/skills/{name}")
async def get_skill(name: str) -> PlainTextResponse:
    cfg = AlohaConfig.load()
    skills = load_skills(cfg.data_dir)
    skill = skills.get(name)
    if skill is None:
        raise HTTPException(status_code=404, detail=f"skill '{name}' not found")
    # Return the full skill as markdown (frontmatter + body) so it's drop-in.
    text = (
        f"---\nname: {skill.name}\ndescription: {skill.description}\n"
        f"category: {skill.category}\n---\n{skill.body}\n"
    )
    return PlainTextResponse(text, media_type="text/markdown; charset=utf-8")


class SkillUpload(BaseModel):
    name: str
    content: str


@router.post("/api/skills")
async def add_skill(skill: SkillUpload) -> JSONResponse:
    """Save a user skill to {data_dir}/skills/ — immediately available to the agent."""
    cfg = AlohaConfig.load()
    slug = _SLUG.sub("-", skill.name.strip().lower()).strip("-")[:60]
    if not slug:
        raise HTTPException(status_code=400, detail="invalid skill name")
    if len(skill.content) > 60_000:
        raise HTTPException(status_code=400, detail="skill too large (60 KB max)")

    # Protect built-ins: don't let an upload shadow a built-in of the same name.
    existing = load_skills(cfg.data_dir).get(slug)
    if existing is not None and not _is_user_skill(existing.source, cfg):
        raise HTTPException(status_code=409,
                            detail=f"'{slug}' is a built-in skill — pick a different name")

    content = skill.content
    # If the upload has no frontmatter, add a minimal one so it loads cleanly.
    if not content.lstrip().startswith("---"):
        first = next((ln.strip() for ln in content.splitlines() if ln.strip()), slug)
        content = f"---\nname: {slug}\ndescription: {first[:120]}\ncategory: general\n---\n\n{content}"

    d = _user_skills_dir(cfg)
    d.mkdir(parents=True, exist_ok=True)
    (d / f"{slug}.md").write_text(content, encoding="utf-8")
    return JSONResponse({"ok": True, "name": slug})


@router.delete("/api/skills/{name}")
async def delete_skill(name: str) -> JSONResponse:
    cfg = AlohaConfig.load()
    slug = _SLUG.sub("-", name.strip().lower()).strip("-")
    skill = load_skills(cfg.data_dir).get(slug)
    if skill is None:
        raise HTTPException(status_code=404, detail=f"skill '{slug}' not found")
    if not _is_user_skill(skill.source, cfg):
        raise HTTPException(status_code=403, detail="built-in skills can't be deleted")
    try:
        Path(skill.source).unlink()
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=500, detail=f"could not delete: {exc}")
    return JSONResponse({"ok": True})
