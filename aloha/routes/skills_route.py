"""
aloha/routes/skills_route.py

Serve the HA skill library over HTTP so people can browse the skills and grab
the files to add to their own chatbot.

  GET /api/skills             — list all skills (name, category, description)
  GET /api/skills/{name}      — one skill's full markdown playbook (raw text)
"""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import JSONResponse, PlainTextResponse

from aloha.config import AlohaConfig
from aloha.skills import load_skills

router = APIRouter()


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
