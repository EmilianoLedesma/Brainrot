"""The H2 / H2b production pipeline.

A topic or a Reddit post becomes a script, the script becomes narration, and the
narration becomes one or more rendered chapters sitting in Supabase Storage.
"""

import logging
import math
import re
from typing import Callable

from . import db, investigate, motion, render, scheduler, script, tts, media
from .world import design as world_design, director as world_director, render as world_render
from .application.stages import stage
from .domain.jobs import PermanentError

log = logging.getLogger(__name__)

# Normal generated scripts stay whole. Balance unusually long saved stories so
# a final short fragment does not become a separate video. TTS checks real time.
WORDS_PER_CHAPTER = 450


def split_chapters(text: str) -> list[str]:
    """Split on sentence boundaries, packing sentences up to the word budget.

    Splitting mid-sentence would cut a chapter off mid-thought, so a sentence
    longer than the budget is left whole rather than broken.
    """
    sentences = [s.strip() for s in re.split(r"(?<=[.!?])\s+", text.strip()) if s.strip()]
    count = max(1, math.ceil(len(text.split()) / WORDS_PER_CHAPTER))
    target = len(text.split()) / count
    chapters: list[list[str]] = []
    budget = 0
    for sentence in sentences:
        length = len(sentence.split())
        if not chapters or (
            len(chapters) < count and budget > 0
            and abs(budget - target) <= abs(budget + length - target)
        ):
            chapters.append([sentence])
            budget = length
        else:
            chapters[-1].append(sentence)
            budget += length
    return [" ".join(c) for c in chapters] or [text]


def pick_background(story_id: str) -> bytes:
    path = db.assign_story_background(story_id)
    if path is None:
        raise PermanentError(
            "no active background_clips - add one with: python -m brainrot.cli add-background <file>"
        )
    return db.download(path)


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


def produce(job_id: str, write: Callable[[], script.Story], motion_graphics: bool = False, world: bool = False, **story_fields) -> str:
    """Render every chapter of the job's story and record it. Returns the story id.

    motion_graphics swaps the looping background for the Remotion motion edit; world swaps it for one directed, continuous 3D scene (docs/world-mode.md).

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
        # Preserve existing chapter boundaries across a deployment and retry.
        # Never reuse a ready video for a newly assigned piece of the script.
        texts = split_chapters(story["script"])
        if done:
            saved = [done[i]["text"] for i in sorted(done)]
            remaining = story["script"].split()
            for text in saved:
                tokens = text.split()
                if remaining[:len(tokens)] != tokens:
                    raise PermanentError("Saved chapters do not match the story. Create a new job.")
                remaining = remaining[len(tokens):]
            texts = saved + (split_chapters(" ".join(remaining)) if remaining else [])
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

        if background is None and not (motion_graphics or world):
            with stage("background"):
                background = pick_background(story_id)
        scope = f"chapter:{index}"
        spec = None
        if world:  # the world is designed from the script before narration: a topic it cannot represent fails here, not after TTS
            with stage("design", scope):
                spec = world_design.cached(story.get("topic") or story.get("title") or "The story", text)
        with stage("tts", scope):
            audio, words = tts.narrate(text, title=story.get("title") or story.get("topic") or "The story")
        title = story.get("title") or story.get("topic") or "The story"
        if world:
            with stage("direct", scope):
                plan = world_director.direct(story.get("topic") or title, text, words, world_render.seconds(audio), world=spec)
        with stage("render", scope):
            if world:
                video = world_render.render_video(audio, words, title, text, plan)
            else:
                video = motion.render_video(audio, words) if motion_graphics else render.render(background, audio, words)
        with stage("upload", scope):
            if media.local():
                db.upload_job_media(job_id, "story_chapters", chapter_id, f"stories/{story_id}/{index:02d}.srt",
                                    render.build_srt(words).encode("utf-8"), "application/x-subrip")
            audio_path = db.upload_job_media(job_id, "story_chapters", chapter_id,
                                             f"stories/{story_id}/{index:02d}.mp3", audio, "audio/mpeg")
            video_path = db.upload_job_media(job_id, "story_chapters", chapter_id,
                                             f"stories/{story_id}/{index:02d}.mp4", video, "video/mp4")
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
    level = job["params"].get("brainrot_level")
    options = {"brainrot_level": level} if level is not None else {}
    if job["params"].get("reference_context"):
        options["reference_context"] = job["params"]["reference_context"]
    web = bool(job["params"].get("web_research"))

    def write() -> script.Story:
        if web:  # inside the script stage: a retry reuses the saved story, so a job never researches twice
            found = investigate.run(topic)
            log.info("research: %s", investigate.summary(found))
            options["reference_context"] = "\n\n".join(filter(None, [options.get("reference_context"), investigate.context(found)]))
        return script.write_story(topic, **options)

    return produce(job["id"], write, motion_graphics=bool(job["params"].get("motion_graphics")), world=bool(job["params"].get("world")), topic=topic)
