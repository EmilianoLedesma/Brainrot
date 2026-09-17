"""The H2 / H2b production pipeline.

A topic or a Reddit post becomes a script, the script becomes narration, and the
narration becomes one or more rendered chapters sitting in Supabase Storage.
"""

import random
import re

from . import db, render, scheduler, script, tts

# Roughly one minute of narration. Anything longer gets split so each chapter
# stands alone in a feed.
WORDS_PER_CHAPTER = 160


def split_chapters(text: str) -> list[str]:
    """Split on sentence boundaries, packing sentences up to the word budget.

    Splitting mid-sentence would cut a chapter off mid-thought, so a sentence
    longer than the budget is left whole rather than broken.
    """
    sentences = [s.strip() for s in re.split(r"(?<=[.!?])\s+", text.strip()) if s.strip()]
    chapters: list[list[str]] = []
    budget = 0
    for sentence in sentences:
        length = len(sentence.split())
        if not chapters or budget + length > WORDS_PER_CHAPTER:
            chapters.append([sentence])
            budget = length
        else:
            chapters[-1].append(sentence)
            budget += length
    return [" ".join(c) for c in chapters] or [text]


def pick_background() -> bytes:
    rows = db.client().table("background_clips").select("storage_path").eq("active", True).execute().data
    if not rows:
        raise RuntimeError(
            "no active background_clips - add one with: python -m brainrot.cli add-background <file>"
        )
    return db.download(random.choice(rows)["storage_path"])


def produce(job_id: str, story: script.Story, **story_fields) -> str:
    """Render every chapter of a story and record it. Returns the story id."""
    row = {"job_id": job_id, "title": story.title, "script": story.script, **story_fields}
    story_id = db.client().table("stories").insert(row).execute().data[0]["id"]

    background = pick_background()
    chapters = split_chapters(story.script)
    for index, text in enumerate(chapters, start=1):
        chapter_id = (
            db.client()
            .table("story_chapters")
            .insert({"story_id": story_id, "chapter_index": index, "text": text, "status": "rendering"})
            .execute()
            .data[0]["id"]
        )
        audio, words = tts.narrate(text)
        video = render.render(background, audio, words)
        audio_path = db.upload(f"stories/{story_id}/{index:02d}.mp3", audio, "audio/mpeg")
        video_path = db.upload(f"stories/{story_id}/{index:02d}.mp4", video, "video/mp4")
        db.client().table("story_chapters").update(
            {"audio_path": audio_path, "video_path": video_path, "status": "ready"}
        ).eq("id", chapter_id).execute()

    db.client().table("stories").update({"status": "ready"}).eq("id", story_id).execute()
    scheduler.plan_story(story_id)
    return story_id


def run_brainrot(job: dict) -> str:
    """H2: a topic becomes a story."""
    return produce(job["id"], script.write_story(job["params"]["topic"]), topic=job["params"]["topic"])
