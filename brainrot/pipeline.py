"""The H2 / H2b production pipeline.

A topic or a Reddit post becomes a script, the script becomes narration, and the
narration becomes one or more rendered chapters sitting in Supabase Storage.
"""

import random
import re
from typing import Callable

from . import db, render, scheduler, script, tts
from .application.stages import stage
from .domain.jobs import PermanentError

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
        raise PermanentError(
            "no active background_clips - add one with: python -m brainrot.cli add-background <file>"
        )
    return db.download(random.choice(rows)["storage_path"])


def _story_for(job_id: str, write: Callable[[], script.Story], fields: dict) -> dict:
    """The job's story row: the one an earlier attempt saved, or a fresh one.

    Reusing it means a retry never pays for a second Claude call and never trips
    the unique reddit_post_id.
    """
    existing = db.client().table("stories").select("*").eq("job_id", job_id).execute().data
    if existing:
        return existing[0]
    with stage("script"):
        story = write()
        row = {"job_id": job_id, "title": story.title, "script": story.script, **fields}
        return db.client().table("stories").insert(row).execute().data[0]


def produce(job_id: str, write: Callable[[], script.Story], **story_fields) -> str:
    """Render every chapter of the job's story and record it. Returns the story id.

    Safe to re-run: chapters an earlier attempt finished are left alone, and only
    the missing or unfinished ones are rendered.
    """
    story = _story_for(job_id, write, story_fields)
    story_id = story["id"]
    done = {
        c["chapter_index"]: c
        for c in db.client().table("story_chapters").select("*").eq("story_id", story_id).execute().data
    }

    background = None
    # split_chapters is deterministic, so the same script yields the same chapters.
    with stage("chaptering"):
        texts = split_chapters(story["script"])
    for index, text in enumerate(texts, start=1):
        chapter = done.get(index)
        if chapter and chapter["status"] == "ready":
            continue
        if chapter is None:
            chapter_id = (
                db.client()
                .table("story_chapters")
                .insert({"story_id": story_id, "chapter_index": index, "text": text, "status": "rendering"})
                .execute()
                .data[0]["id"]
            )
        else:
            chapter_id = chapter["id"]
            db.client().table("story_chapters").update({"status": "rendering"}).eq("id", chapter_id).execute()

        if background is None:
            with stage("background"):
                background = pick_background()
        scope = f"chapter:{index}"
        with stage("tts", scope):
            audio, words = tts.narrate(text)
        with stage("render", scope):
            video = render.render(background, audio, words)
        with stage("upload", scope):
            audio_path = db.upload(f"stories/{story_id}/{index:02d}.mp3", audio, "audio/mpeg")
            video_path = db.upload(f"stories/{story_id}/{index:02d}.mp4", video, "video/mp4")
            db.client().table("story_chapters").update(
                {"audio_path": audio_path, "video_path": video_path, "status": "ready"}
            ).eq("id", chapter_id).execute()

    db.client().table("stories").update({"status": "ready"}).eq("id", story_id).execute()
    with stage("schedule"):
        scheduler.plan_story(story_id)
    return story_id


def run_brainrot(job: dict) -> str:
    """H2: a topic becomes a story."""
    topic = job["params"]["topic"]
    return produce(job["id"], lambda: script.write_story(topic), topic=topic)
