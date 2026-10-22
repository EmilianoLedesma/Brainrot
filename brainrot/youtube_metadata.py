"""Repo-owned Shorts guidance, source-aware generation, and reusable drafts."""
import hashlib
import json
import os
from pathlib import Path

from pydantic import BaseModel, Field, model_validator

from . import db, llm

SKILL = Path(__file__).parent / "skills" / "youtube-shorts-publishing" / "SKILL.md"


class Metadata(BaseModel):
    title: str = Field(min_length=1, max_length=100)
    description: str = Field(min_length=1, max_length=4500)
    tags: list[str] = Field(min_length=3, max_length=8)

    @model_validator(mode="after")
    def valid_text(self):
        self.title = self.title.strip()
        self.description = self.description.strip()
        self.tags = list(dict.fromkeys(tag.strip().lstrip("#") for tag in self.tags))
        if not self.title or not self.description or any(not tag or len(tag) > 60 for tag in self.tags) or len(self.tags) < 3:
            raise ValueError("Metadata needs a title, description, and three to eight short tags")
        return self


def _row(table, identifier):
    rows = db.client().table(table).select("*").eq("id", identifier).execute().data
    if not rows:
        raise ValueError("This video is no longer available.")
    return rows[0]


def source_material(source, identifier):
    if source not in {"chapter", "clip"}:
        raise ValueError("Choose a finished video.")
    row = _row("story_chapters" if source == "chapter" else "clips", identifier)
    if row["status"] != "ready":
        raise ValueError("Choose a finished video.")
    if source == "chapter":
        parent = _row("stories", row["story_id"])
        material = {"title": parent.get("title"), "narration": row["text"], "chapter": row["chapter_index"]}
        credit = parent.get("permalink")
        job_id = parent["job_id"]
    else:
        parent = _row("source_videos", row["source_video_id"])
        transcript = parent.get("transcript") or []
        if isinstance(transcript, dict):
            transcript = transcript.get("segments", [])
        text = " ".join(segment.get("text", "") for segment in transcript
                        if float(segment.get("end", 0)) > float(row["start_seconds"])
                        and float(segment.get("start", 0)) < float(row["end_seconds"]))
        material = {"title": row.get("title"), "narration": text}
        credit = parent.get("youtube_url")
        job_id = row["job_id"]
    if not material["narration"].strip():
        raise ValueError("This video has no saved narration to generate upload details from.")
    job = _row("jobs", job_id)
    provider = (job.get("params") or {}).get("llm_provider") or os.getenv("BRAINROT_LLM_PROVIDER", "claude-code")
    return material, credit, provider


def draft(source, identifier, *, regenerate=False):
    material, credit, provider = source_material(source, identifier)
    guidance = SKILL.read_text(encoding="utf-8").split("---", 2)[-1].strip()
    fingerprint = hashlib.sha256(json.dumps([material, credit, provider, guidance], sort_keys=True).encode()).hexdigest()
    field = "chapter_id" if source == "chapter" else "clip_id"
    existing = db.client().table("youtube_metadata_drafts").select("*").eq(field, identifier).execute().data
    if not regenerate and existing and existing[0]["fingerprint"] == fingerprint:
        return existing[0]["metadata"]
    result = llm.generate(guidance, json.dumps(material, ensure_ascii=False), Metadata, max_tokens=1500, provider=provider).model_dump()
    if credit and credit.startswith("https://"):
        result["description"] += "\n\nSource: " + credit
    db.client().table("youtube_metadata_drafts").upsert({field: identifier, "fingerprint": fingerprint, "metadata": result}, on_conflict=field).execute()
    return result
