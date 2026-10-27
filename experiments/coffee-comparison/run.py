"""Local, unpublished A/B film: Brainrot Remotion versus Lemo-Opuscar.

Run from the checkout: .venv/Scripts/python experiments/coffee-comparison/run.py prepare
Stages cache their outputs; no database, worker or publication is involved.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
from pathlib import Path
import shutil
import subprocess
import sys
import time
from typing import Literal
from pydantic import BaseModel

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from brainrot import llm, motion, render, script, tts

HERE = Path(__file__).resolve().parent
OUT = ROOT / "out" / "coffee-comparison"
SHARED = OUT / "shared"
LEMO = HERE / "vendor" / "lemo-opuscar"


class Shot(BaseModel):
    cue: str
    kind: Literal["cups", "roast", "particle", "grind", "controls", "flow", "uneven", "strength", "dilution", "payoff"]
    heading: str
    labels: list[str]
    camera: Literal["push", "pull", "track", "hold"]
    reason: str


class ShotPlan(BaseModel):
    shots: list[Shot]

REFERENCES = """Verified research notes; write original wording, not a source summary.
Scope: the science of brewing coffee, with a clear mechanism and practical payoff.
Roasting changes the seed chemically and develops aroma compounds, including
Maillard chemistry involving sugars and amino compounds. Brewing extracts soluble
material into water; it does not dissolve the entire ground bean. Grinding exposes
surface area. Temperature, contact time, grind and coffee/water ratio affect the cup.
Source: https://axial.acs.org/agriculture-and-food-chemistry/chemistry-tea-coffee
Extraction kinetics differ by compound; do not claim that every acid comes first
or all bitterness comes last. Water moves dissolved material out of porous grounds.
Source: https://pubs.acs.org/doi/abs/10.1021/acs.iecr.0c01153
Finer is not always better in percolation: very fine beds can produce uneven flow
and extraction. Lee, Smith and Arshad modelled two flow pathways; this is a possible
mechanism, not a universal experimental guarantee or a measured statistic.
Source: https://arxiv.org/abs/2206.12373
Concentration (dissolved material per water) and extraction (material removed from
the grounds) are distinct. Adding water dilutes a cup; it cannot undo how it brewed.
Source: https://arxiv.org/abs/2501.14950
Avoid health claims, caffeine neuroscience, invented percentages and perfect recipes.
Use no study names/numbers unless necessary. Explain the mechanism in everyday words.
"""


def save(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, ensure_ascii=False), encoding="utf-8")


def run(command, *, cwd=ROOT, timeout=3600, log=None):
    print("Running", Path(str(command[0])).name, flush=True)
    if log:
        log.parent.mkdir(parents=True, exist_ok=True)
        with log.open("w", encoding="utf-8") as handle:
            result = subprocess.run([str(x) for x in command], cwd=cwd, stdout=handle,
                                    stderr=subprocess.STDOUT, timeout=timeout)
    else:
        result = subprocess.run([str(x) for x in command], cwd=cwd, timeout=timeout)
    if result.returncode:
        raise RuntimeError(f"Command failed ({result.returncode}); see {log}")


def prepare():
    SHARED.mkdir(parents=True, exist_ok=True)
    os.environ["BRAINROT_LLM_PROVIDER"] = "codex"
    os.environ["BRAINROT_LLM_TIMEOUT_SECONDS"] = "900"
    story_path = SHARED / "story.json"
    if not story_path.exists():
        print("Generating original Grounded script with Brainrot storytelling guidance", flush=True)
        story = script.write_story(
            "The science of coffee: how the same beans can taste different, from roasting "
            "to extraction and uneven flow. Write in English. Grounded factual explainer, "
            "not a shopping guide. Aim for 300-340 words including the spoken title.",
            provider="codex", brainrot_level=0, reference_context=REFERENCES)
        save(story_path, story.model_dump())
    story = script.Story.model_validate_json(story_path.read_text(encoding="utf-8"))
    count = len((story.title + " " + story.script).split())
    if not 280 <= count <= 380:
        raise ValueError(f"Script has {count} words; review it before speech")
    print(f"Script ready: {count} words", flush=True)
    if not (SHARED / "narration.mp3").exists():
        print("Generating shared English narration with Brainrot TTS", flush=True)
        audio, words = tts.narrate(story.script, voice="en-US-GuyNeural", title=story.title)
        save(SHARED / "words.json", words)
        (SHARED / "narration.mp3").write_bytes(audio)
        (SHARED / "captions.srt").write_text(render.build_srt(words), encoding="utf-8")
    seconds = render.check_media(str(SHARED / "narration.mp3"))
    words = json.loads((SHARED / "words.json").read_text(encoding="utf-8"))
    render.check_captions(words, seconds)
    save(SHARED / "manifest.json", {
        "provider": "codex", "brainrot_level": 0, "language": "en", "voice": "en-US-GuyNeural",
        "duration": seconds, "word_count": count,
        "audio_sha256": hashlib.sha256((SHARED / "narration.mp3").read_bytes()).hexdigest(),
        "storytelling_skill_sha256": hashlib.sha256(script.STORYTELLING_SKILL.read_bytes()).hexdigest(),
        "references": REFERENCES, "publication": "off", "database_job": False})
    print(f"Shared narration ready: {seconds:.2f} seconds", flush=True)


def baseline():
    """Use the unmodified production planning, design and render entry point."""
    os.environ["BRAINROT_LLM_PROVIDER"] = "codex"
    os.environ["BRAINROT_LLM_TIMEOUT_SECONDS"] = "900"
    folder = OUT / "baseline"
    folder.mkdir(parents=True, exist_ok=True)
    final = folder / "final.mp4"
    if final.exists():
        render.check_video(str(final))
        return
    words = json.loads((SHARED / "words.json").read_text(encoding="utf-8"))
    print("Rendering current production Remotion edit", flush=True)
    started = time.monotonic()
    # Capture the exact props the production renderer prepares without replacing
    # planning or design logic; retained as evidence, not a separate generation.
    original_plan = motion.plan
    def record_plan(*args, **kwargs):
        props = original_plan(*args, **kwargs)
        recorded.append(props)
        return props
    recorded = []
    motion.plan = record_plan
    try:
        video = motion.render_video((SHARED / "narration.mp3").read_bytes(), words)
    finally:
        motion.plan = original_plan
    final.write_bytes(video)
    if recorded:
        save(folder / "props.json", recorded[0])
    save(folder / "render.json", {"seconds": time.monotonic() - started,
         "entry_point": "brainrot.motion.render_video", "devices": sum("device" in s for s in recorded[0]["scenes"])})
    print("Baseline ready", flush=True)


def design():
    os.environ["BRAINROT_LLM_TIMEOUT_SECONDS"] = "900"
    destination = OUT / "lemo" / "shot-plan.json"
    if destination.exists():
        return
    story = json.loads((SHARED / "story.json").read_text(encoding="utf-8"))
    guide = (LEMO / "DIRECTOR.md").read_text(encoding="utf-8")
    style = (LEMO / "styles/iso-infographic/STYLE.md").read_text(encoding="utf-8")
    system = (
        "You are planning a grounded original coffee science film. Adapt the supplied "
        "Lemo directing and isometric style guidance to an EXISTING Brainrot narration. "
        "Return the requested JSON shot plan, not code. Never change the spoken script. "
        "No new facts, statistics, measured quantities or sources. Use 11-14 chronological "
        "shots covering the whole script, including title. Each cue must be an exact, "
        "unique contiguous phrase of 4-8 words in the title or narration. First shot cue "
        "must be the full title. Subsequent cue phrases must occur in narration order. "
        "Use distinct semantic cut points, avoid shots shorter than a spoken sentence. "
        "Kinds select original coffee-specific geometry, not generic title cards. "
        "Use cups for the opening; roast for Maillard; particle for porous-grain "
        "dissolution; grind for surface area; controls for temperature/time/ratio; "
        "flow for permeability; uneven for unequal flow; strength for concentration "
        "versus extraction; dilution for added water; payoff for return to cups. "
        "Every heading <=28 characters, labels <=20 characters, 0-2 labels per shot. "
        "Labels must explain the narrated mechanism, not supply new data. Vary camera "
        "scale and movement while keeping projection. Actual timing comes from TTS; "
        "do not invent seconds. No mandatory numeric music grid: speech is master.\n\n"
        + guide + "\n\n" + style)
    result = llm.generate(system, story["title"] + "\n\n" + story["script"],
                          ShotPlan, max_tokens=5000, provider="codex")
    save(destination, result.model_dump())
    print(f"Lemo-directed plan ready: {len(result.shots)} shots", flush=True)


def browser_environment():
    """Use a local browser if available; no saved machine paths in film sources."""
    if os.environ.get("PLAYWRIGHT_CHROME"):
        return
    if os.name == "nt":
        for variable in ("PROGRAMFILES(X86)", "PROGRAMFILES", "LOCALAPPDATA"):
            root = os.environ.get(variable)
            if not root:
                continue
            for relative in ("Microsoft/Edge/Application/msedge.exe", "Google/Chrome/Application/chrome.exe"):
                path = Path(root) / relative
                if path.is_file():
                    os.environ["PLAYWRIGHT_CHROME"] = str(path)
                    return


def build_lemo():
    folder = OUT / "lemo"
    folder.mkdir(parents=True, exist_ok=True)
    story = json.loads((SHARED / "story.json").read_text(encoding="utf-8"))
    manifest = json.loads((SHARED / "manifest.json").read_text(encoding="utf-8"))
    words = json.loads((SHARED / "words.json").read_text(encoding="utf-8"))
    plan = ShotPlan.model_validate_json((folder / "shot-plan.json").read_text(encoding="utf-8"))
    norm = lambda value: re.sub(r"[^a-z0-9]", "", value.lower())
    spoken = [norm(w["text"]) for w in words]
    shots = []
    for shot in plan.shots:
        target = [norm(w) for w in shot.cue.split()]
        found = [i for i in range(len(spoken)-len(target)+1) if spoken[i:i+len(target)] == target]
        if len(found) != 1:
            raise ValueError(f"Cue must match exactly once: {shot.cue}")
        start = 0.0 if not shots else words[found[0]]["start"]
        if shots and start <= shots[-1]["start"]:
            raise ValueError("Nonchronological shot plan")
        shots.append({**shot.model_dump(), "start": start})
    # Merge adjacent same-kind shots and very short title/ending beats. This
    # preserves the spoken content and gives each heading enough reading time.
    merged = []
    for i, shot in enumerate(shots):
        end = shots[i+1]["start"] if i+1<len(shots) else manifest["duration"]
        if merged and (shot["kind"] == merged[-1]["kind"] or end-shot["start"] < 4.5):
            merged[-1]["end"] = end
            merged[-1]["reason"] += " " + shot["reason"]
        else:
            merged.append({**shot,"end":end})
    captions = []
    group = []
    for i, word in enumerate(words):
        if group and (len(group)>=8 or word["start"]-group[0]["start"]>3.4
                      or word["start"]-group[-1]["end"]>.65):
            captions.append({"start":group[0]["start"], "end":min(word["start"],group[-1]["end"]+.6), "words":group})
            group=[]
        group.append(word)
    if group:
        captions.append({"start":group[0]["start"], "end":manifest["duration"], "words":group})
    save(folder / "data.json", {"duration":manifest["duration"],"title":story["title"],
         "shots":merged,"captions":captions,"words":words})
    for name in ("index.html","film.js"):
        shutil.copyfile(HERE / "film" / name, folder / name)
    shutil.copyfile(ROOT / "motion/DMSans.ttf", folder / "DMSans.ttf")
    shutil.copyfile(ROOT / "motion/OFL-DMSans.txt", folder / "OFL-DMSans.txt")
    for name in ("CREDITS", "FACTS.md", "TREATMENT.md"):
        shutil.copyfile(HERE / name, folder / name)
    shutil.copyfile(SHARED / "captions.srt", folder / "captions.srt")
    browser_environment()
    run(["node",LEMO / "core/render/still.mjs",folder,"2","22","43","65","88","111","125",
         "--size","1080x1920","--out",folder/"stills"],cwd=LEMO,log=folder/"stills.log")
    run(["node",LEMO / "core/render/readcheck.mjs",folder,"--size","1080x1920"],cwd=LEMO,log=folder/"readcheck.log")
    run(["node",LEMO / "core/render/events.mjs",folder,"--size","1080x1920"],cwd=LEMO,log=folder/"events.log")
    print(f"Lemo film built: {len(merged)} timed shots",flush=True)


def render_lemo():
    folder = OUT / "lemo"
    browser_environment()
    if not (folder / "raw.mp4").exists():
        run(["node",LEMO/"core/render/video.mjs",folder,"--size","1080x1920",
             "--fps","30","--workers","2","--out",folder/"raw.mp4"],cwd=LEMO,log=folder/"render.log")
    # Voice-only control: the same waveform and mastering as the production edit.
    run(["ffmpeg","-y","-hide_banner","-loglevel","error","-i",folder/"raw.mp4",
         "-i",SHARED/"narration.mp3","-map","0:v","-map","1:a","-c:v","libx264",
         "-preset","veryfast","-crf","23",*render.VIDEO_RATE_OPTIONS,
         "-af",render.VOICE_FILTER,"-c:a","aac","-b:a","128k","-movflags","+faststart",
         "-shortest",folder/"voice-only.mp4"],log=folder/"voice-only.log")
    python = HERE / ".venv" / ("Scripts/python.exe" if os.name=="nt" else "bin/python")
    run([python,HERE/"mix.py",OUT],log=folder/"mix.log")
    run(["ffmpeg","-y","-hide_banner","-loglevel","error","-i",folder/"voice-only.mp4",
         "-i",folder/"mix.wav","-map","0:v","-map","1:a","-c:v","copy",
         "-af",render.VOICE_FILTER,"-c:a","aac","-b:a","128k","-movflags","+faststart",
         "-shortest",folder/"final.mp4"],log=folder/"master.log")
    render.check_video(str(folder/"final.mp4"))
    render.check_video(str(folder/"voice-only.mp4"))
    print("Lemo film ready (sound design and voice-only control)",flush=True)


def playback():
    browser_environment()
    run(["node",HERE/"playback.mjs",OUT],log=OUT/"playback.log",timeout=240)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("stage", choices=["prepare", "baseline", "design", "build-lemo", "render-lemo", "playback"])
    args = parser.parse_args()
    {"prepare": prepare, "baseline": baseline, "design": design,
     "build-lemo": build_lemo,"render-lemo":render_lemo,"playback":playback}[args.stage]()
