"""Asset probe: can the model author the 3D assets of a video itself, and do they come out well?

One topic in, a contact sheet out (and optionally a silent 10 s clip). No audio, no queue, no database, nothing of the main flow is touched.

    uv run python scripts/asset_probe.py --topic "La olla de presión" --text "La olla de presión cocina más caliente sin usar más fuego. ..."
    uv run python scripts/asset_probe.py --topic "..." --text "..." --video          # also a silent 10 s clip of the camera flying between the shots
    uv run python scripts/asset_probe.py --topic "..." --text "..." --stub reply.json  # no model: {"code": "<designed.tsx source>"}; tests everything else

Flow: design (the model writes motion/probe/designed.tsx using only motion/probe/kit.tsx) -> static checks -> render the shots with automatic framing ->
(--review on by default) the model looks at the sheet and lists defects -> one fix round -> final sheet. At most 4 model calls per run
(design, repair, review, fix). Output: out/asset-probe/<slug>/ (designed.tsx, sheet.png, shot_*.png, report.json, clip.mp4).

SECURITY: the code the model writes runs in the render browser (Remotion). It is checked first: only `react` and `./kit` may be imported and anything that reaches the network,
the page or the machine is refused. Run it only on your own computer, only for this probe.
"""
import argparse
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import time
from pathlib import Path
from typing import Literal

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from pydantic import BaseModel  # noqa: E402

PROBE = ROOT / "motion" / "probe"
REMOTION = ROOT / "motion" / "node_modules" / "@remotion" / "cli" / "remotion-cli.js"
OUT = ROOT / "out" / "asset-probe"

FORBIDDEN = re.compile(r"(\bimport\s*\(|\brequire\s*\(|\bfetch\s*\(|\beval\s*\(|\bnew\s+Function\b|\bFunction\s*\(|\bwindow\b|\bdocument\b|\bglobalThis\b|\bprocess\b|XMLHttpRequest|WebSocket|localStorage|sessionStorage|"
                       r"dangerouslySetInnerHTML|<script|__proto__|\bsetTimeout\b|\bsetInterval\b|\bMath\.random\b|\bDate\b)")
ALLOWED_IMPORTS = {"react", "./kit"}


class Designed(BaseModel):
    code: str
    notes: str


class Patch(BaseModel):
    old: list[str]
    new: list[str]
    notes: str


class Review(BaseModel):
    verdict: Literal["ok", "fix"]
    problems: list[str]


DESIGN_RULES = """You are a 3D art director who also writes the code. You design the assets of ONE short vertical explainer video and write them as a single React Three Fiber file, `designed.tsx`, \
using ONLY the components of the kit below. The video is 9:16, low-poly and soft: rounded shapes, 2 or 3 tones per object, small recognisable details that belong to THIS topic.

Return the whole file in `code` and one sentence per decision in `notes`.

## The file
- Imports: only `react` and `./kit` (exactly `import React from 'react';` and `import {...} from './kit';`). Nothing else. No randomness, no clocks, no hooks except `useTime` from the kit: the scene is deterministic.
- Imports from `./kit` may also include `Move`, `Act`, `useTime`, `ramp`, `mix` (motion, see below).
- Export `GROUND` (a hex colour for an endless floor, or `null` when the scene is a diorama on a `Slab`; prefer `null` + Slab), `SKY` (two hex colours, top and bottom of the sky gradient), `SHOTS` and `Scene`:
  `export const SHOTS=[{focus:'all',az:.4,el:.32},{focus:'pot',az:0,el:.16},...]` - 4 to 6 shots; the first has focus 'all' (the whole scene); the others each name a group of Scene. Vary the scale of consecutive shots (wide, medium, extreme close-up) and the angle (az and el must change between shots, even on the same group). The camera already pushes in and drifts slowly during each shot. `az` and `el` are the camera
  angle in radians (az -0.7..0.7, el 0.08..0.55); optional `zoom` (below 1 = closer, above 1 = farther) and `dy` (look higher or lower, in world units) tune the framing. The camera distance is computed from the bounding box of the group, so a group always fills the frame: put each thing the story needs to show in its own named group.
  A group that is a small detail (a valve, goggles) gets a close shot by itself; do not make the details tiny parts of a huge group.
- `export function Scene(){return <>...</>;}` - every main object is `<group name="lowercase_id" position={[x,y,z]} rotation={[0,ry,0]}>...</group>`; ids are used by SHOTS and must match exactly.
- World units: a person is about 3.4 tall, a house about 6, the whole scene fits in about 25 x 25. The top of the ground is y = 0 and everything stands ON it (feet, wheels and bases touch it; nothing floats, nothing sinks). Keep the scene composed around the origin, the hero near the centre.
- Colour: pastel but saturated mid-tones, one dominant hue family per video, a clean floor colour, no pure black or pure white large areas. No text.
- PROPORTIONS are real: size every object against the person (3.4 tall). A house is 6-8, an igloo 8 wide, a boat 12, a tree 6-10. Never shrink an object so that a shot "fits": the camera frames every group by itself, so you only change SHOTS (focus, angle) to fix framing, never the size or position of things.
- SPACING: spread the world out. The scene is about 25 x 25: keep clear space (at least one body width, usually 3-5 units) between the hero, the props and the background objects, and put background objects behind the hero, not around its feet. The wide first shot must read as a PLACE (horizon, background shapes, ground features), not as a pile of props.
- NO ARROWS. Show forces, light, heat and flow with the things themselves: emissive glows, soft translucent cones of light, steam, particles, colour change, a shadow. At most ONE small arrow in the whole video, only if nothing else can say it, and never in the wide shot.
- MOTION: nothing in a video stands still. Wrap at least 6 elements in `<Move>`; every shot must have something moving in it. `<Move from={[x,y,z]} to={[x,y,z]} t0={0.2} t1={0.6}>` travels once (t0, t1 are 0..1 over the whole clip); `loop={3}` repeats the from->to path 3 times (rising bubbles, steam, falling snow, drifting sparks); `spin={0.8}` rotates (rad/s); `bob={0.1}` bobs up and down; `sway={0.15}` tilts side to side; `pop={0.3}` makes it appear at that time. Ideas: the hero breathes (bob), a tool swings (sway), particles loop, a part slides into place, something appears when the narration reaches it.
- ACCURACY: in `notes`, first list the 3 features a viewer needs to recognise the main object as THAT object (not a generic shape) and say which part of the model carries each. A real object has its real proportions and construction (a flat bone strip with thin slits is not a box; a face is not a ball with a band stuck on).
- The frame is narrow and tall: make the hero tall or compact, not long and thin. Everything that matters must be visible from the front shots.

## The world is a DIORAMA with structure (this is what the reference videos all do; an empty plane is a failure)
- Ground: use `Slab` (a block whose top is y=0 and whose cut sides show 2-3 layers: grass/snow/sand over soil over rock, or a table over a floor). Never a flat plane, never a floating object in white. `GROUND=null`.
- Surface texture comes from geometry: `Planks`, `Tiles`, strips, dots, grains, cracks, stones, footprints, tracks. A big flat colour is not an environment.
- Sky: `SKY` gradient with value contrast against the ground (a pale ground under a pale sky disappears), plus `Cloud`s that drift (`Move loop`) or far scenery. No backdrop walls, domes or curtains.
- Fill the world with at least 20 environment elements at different distances and sizes (`Scatter` + `Pine`, `Tree`, `Rock`, `Mound`, or your own: reeds, fences, buildings, lamp posts, signs without text), kept clear of the hero and the camera lines, in groups of their own (`nature`). The set must say WHERE this happens (arctic coast, kitchen counter, river valley, workshop) at a glance.
- Frame the world with the group that holds the ground (`focus:'banks'`, `'island'`...) for the wide shot; `focus:'all'` also counts the sky decorations and shrinks it. Put the camera where nothing stands in front of the subject (trees, walls): keep the sightlines of each shot free of scenery.
- Hero characters and objects are BIG and detailed (the example heroes are 20+ parts); the scene is macro: one subject per shot, filling the frame.

## The scene must PROVE the narration
- In `notes`, first write the claim of the narration in one sentence and the visual proof: what the viewer sees change, and where. The proof must be logically coherent: if the narration says something blends into its surroundings, it must END UP in front of or on the thing it matches, with the same colours and texture (a grey octopus on pale sand does not prove camouflage: move it onto the rock, then change it); if something is hot, cold, heavy or fast, show it with the objects themselves.
- Show before and after OVER TIME (the same object, early in the clip and later), never by leaving one part unchanged: the whole subject changes, every limb and detail included. A single arm or patch left in the old state reads as a mistake.
- Wide first shot: the hero is at least a third of the frame width and the ground fills the lower half (el 0.3-0.5); make the Slab at least 40 x 40 so no edge or empty sky shows below it; scale the world to the hero, not the reverse.
- Close-ups keep context: at least a third of the frame shows the parent object around the detail. For something microscopic or hidden (cells, atoms, wires, a mechanism), build an ENLARGED model of it on a plate, lens or pedestal beside the hero, 4-6x bigger, and shoot that; never dive into the surface of the hero until the detail is a blur.

## Motion is the explanation, not decoration
- Anything that changes colour or state changes GRADUALLY and ALL together: `const k=ramp(useTime(),0.4,0.5)` and `c={mix('#E8704F','#8C8C7A',k)}` on every part that belongs to it (no second copy of the body, no shells that pop in over the first one). New texture (bumps, spikes, spots) grows in with `Act` scale from 0 to 1 as the colour changes.
- The narration is cut into 4-6 parts, one per shot. In `notes`, write the plan first: `part → shot → what happens (the action)`. Each action is a verb the viewer can see: a car crosses, water rises, a flame lights, a tool carves, snow falls, a part slides in, something lights up, a cutaway opens.
- Make actions with `<Act keys={[{t:0.1,p:[..]},{t:0.4,p:[..],rot:[..]}]}>`: t is 0..1 over the clip and must match when that part of the narration is spoken (shot k starts at about (k-1)/shots). Use `Move loop` only for ambient things (water, clouds, steam, snow). Do not make characters or heroes bob or sway on their own: idle wobble looks wrong. Move a limb, a tool, a part, a vehicle, a light, a liquid.

## How to make things look made, not placed
- Build from a silhouette that reads at thumbnail size, then add the 3-5 details that say what it is (rims, handles, valves, straps, rivets, a face, bubbles, flames). Use `Lathe` for anything round (bodies, pots, lids, bottles, lamps), `RBox` for anything boxy.
- To show how something works, CUT it open: `Lathe` with `phi0={Math.PI/2} phi={Math.PI}` is the back half of a round body (the cut faces +z, the camera); `HalfCyl` is a solid half cylinder for what is inside (water, fuel, filling).
  Put the parts the story is about inside the cut and make them big (arrows, bubbles, particles, small characters for scale).
- Cast shadows are free; contact matters: things sit on or touch the floor and each other.
- Do not make 40 identical blocks when 8 will do; do not leave a hero as a single primitive; the hero needs at least 15 parts.

## Look at the two examples and match their level of structure and detail, not their subject
"""

REVIEW_RULES = """You review a contact sheet of renders of one 3D scene for a short vertical video (the shots from left to right, the same scene). Read BOTH image files with the Read tool: `sheet.png` (one still per shot, left to right) and `time.png` (8 frames across the 10 second clip, left to right, to judge the story and the motion). Then judge them as an art director. Topic: {topic}. Narration: {text}

Say `ok` ONLY if every shot reads clearly without explanation: the subject is recognisable as the real object, fills the frame, nothing is cut off by the frame or hidden, the details that explain the topic are visible, the colours are consistent, sizes are believable against each other (an igloo must be bigger than the person), objects are spread out and not piled up, and there is at most one arrow in the whole scene. Also judge the world: it must have a structured ground (a block with visible layers, a textured surface), a sky with depth, many scenery elements that say where this is, characters and objects standing ON the ground (not floating, not sunk), and no empty flat expanses. If any of that is missing, say `fix`. From time.png judge the STORY: the change the narration describes must be visible, gradual (not a pop or swap), logical (the subject is where the effect makes sense, e.g. camouflaged against what it matches), and the frames must not be nearly identical to each other. Name the time frame number (1-8) in those problems.
Otherwise say `fix` and list at most 5 concrete problems, each naming the shot number (1 = leftmost) and the object, and what to change (bigger, move, recolour, add a part, remove a part). No praise, no generalities."""


def say(msg: str) -> None:
    print(f"[asset-probe] {msg}", flush=True)


def slugify(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")[:40] or "topic"


def check_code(code: str) -> list[str]:
    problems = []
    for line in code.splitlines():
        m = re.match(r"\s*import\s+(?:.+?\s+from\s+)?['\"]([^'\"]+)['\"]", line)
        if line.strip().startswith("import") and not m:
            problems.append(f"unparseable import: {line.strip()[:80]}")
        elif m and m.group(1) not in ALLOWED_IMPORTS:
            problems.append(f"import of '{m.group(1)}' is not allowed (only react and ./kit)")
    found = sorted({m.group(0) for m in FORBIDDEN.finditer(code)})
    if found:
        problems.append("forbidden: " + ", ".join(found))
    for name, pattern in (("GROUND", r"export\s+const\s+GROUND\b"), ("SHOTS", r"export\s+const\s+SHOTS\b"), ("Scene", r"export\s+(?:function|const)\s+Scene\b")):
        if not re.search(pattern, code):
            problems.append(f"missing export {name}")
    ids = set(re.findall(r"name=[\"']([a-z0-9_]+)[\"']", code))
    focus = set(re.findall(r"focus\s*:\s*[\"']([a-z0-9_]+)[\"']", code)) - {"all"}
    if focus - ids:
        problems.append("SHOTS focus without a matching <group name>: " + ", ".join(sorted(focus - ids)))
    return problems


def _system_prompt() -> str:
    kit = (PROBE / "kit.tsx").read_text(encoding="utf-8")
    examples = [(PROBE / "examples" / name).read_text(encoding="utf-8").replace("from '../kit'", "from './kit'") for name in ("puente.tsx", "olla.tsx")]
    return (DESIGN_RULES + f"\n### kit.tsx (the only components you may use)\n```tsx\n{kit}\n```\n\n### Example 1 designed.tsx (a bridge over a river: world, layout, action)\n```tsx\n{examples[0]}\n```\n\n"
            f"### Example 2 designed.tsx (a pressure cooker: how to cut an object open to explain it)\n```tsx\n{examples[1]}\n```\n")


def design(topic: str, text: str, previous: str | None = None, feedback: list[str] | None = None, provider: str | None = None) -> Designed:
    from brainrot import llm
    system = _system_prompt()
    user = f"Topic: {topic}\n\nNarration (about 10 seconds):\n{text}\n"
    if previous and feedback:
        user += "\nYour previous file:\n```tsx\n" + previous + "\n```\n\nFix exactly this, keep everything else, and return the whole file again. Do NOT shrink objects or pull them closer together to fix framing (framing is automatic): change the SHOTS or the part itself:\n" + "\n".join(f"- {p}" for p in feedback)
    return llm.generate(system, user, Designed, max_tokens=16000, provider=provider, timeout=1500, tier="strong")


PATCH_RULES = """You fix an existing designed.tsx. Do NOT rewrite the file: return a patch as two parallel lists, `old` and `new` (same length). `old[i]` is an exact, unique snippet copied from the current file (a few whole lines, enough to be unique);
`new[i]` replaces it. To ADD code, copy one existing line as `old[i]` and return that same line plus the new code in `new[i]`. To delete, return an empty `new[i]`. Keep every edit small and local. Put in `notes` one sentence per fix.
Remember the framing is automatic (never shrink or move things to fix framing: change SHOTS: focus, az, el, zoom below 1 = closer, dy)."""


def fix(topic: str, text: str, code: str, problems: list[str], provider: str | None = None) -> Patch:
    from brainrot import llm
    system = _system_prompt() + "\n\n## THIS TASK\n" + PATCH_RULES
    user = f"Topic: {topic}\n\nNarration:\n{text}\n\nCurrent designed.tsx:\n```tsx\n{code}\n```\n\nProblems found by the art review, fix all of them:\n" + "\n".join(f"- {p}" for p in problems)
    return llm.generate(system, user, Patch, max_tokens=8000, provider=provider, timeout=900, tier="strong")


def apply_patch(code: str, patch: Patch) -> tuple[str, list[str]]:
    failed = []
    for i, (old, new) in enumerate(zip(patch.old, patch.new)):
        if old and code.count(old) == 1:
            code = code.replace(old, new)
        else:
            failed.append(f"edit {i + 1}: " + ("snippet not found" if code.count(old) == 0 else "snippet not unique"))
    return code, failed


def render(out: Path, seconds: float | None, scale: float) -> tuple[bool, str]:
    node = shutil.which("node")
    if not node or not REMOTION.is_file():
        return False, "node or motion/node_modules missing: run `npm ci --prefix motion`"
    props = out / "props.json"
    props.write_text(json.dumps({"mode": "video" if seconds else "stills", "seconds": seconds or 10}), encoding="utf-8")
    target = out / "clip-silent.mp4" if seconds else out / "frames"
    if not seconds and target.exists():
        shutil.rmtree(target)
    command = [node, str(REMOTION), "render", "probe/index.tsx", "Probe", str(target), f"--props={props}", "--gl=angle", f"--scale={scale}", "--log=error", "--concurrency=2"]
    if os.environ.get("BRAINROT_BROWSER"):
        command.append(f"--browser-executable={os.environ['BRAINROT_BROWSER']}")
    command += ["--codec=h264", "--crf=22", "--x264-preset=veryfast"] if seconds else ["--sequence", "--image-format=png"]
    result = subprocess.run(command, cwd=ROOT / "motion", capture_output=True, text=True, timeout=1800)
    if result.returncode != 0:
        return False, (result.stderr or result.stdout).strip()[-1500:]
    return True, ""


def make_sheet(out: Path) -> Path:
    frames = sorted((out / "frames").glob("element-*.png"), key=lambda p: int(re.findall(r"\d+", p.stem)[0]))
    for i, f in enumerate(frames):
        shutil.copy(f, out / f"shot_{i + 1}.png")
    sheet = out / "sheet.png"
    try:
        from PIL import Image
        images = [Image.open(f) for f in frames]
        w, h = images[0].size
        canvas = Image.new("RGB", (w * len(images), h), "white")
        for i, im in enumerate(images):
            canvas.paste(im, (i * w, 0))
        canvas.save(sheet)
    except ImportError:
        inputs = [arg for f in frames for arg in ("-i", str(f))]
        subprocess.run(["ffmpeg", "-y", "-hide_banner", "-loglevel", "error", *inputs, "-filter_complex", f"hstack=inputs={len(frames)}", str(sheet)], check=True)
    return sheet


def make_time(out: Path) -> Path | None:
    clip = out / "clip-silent.mp4"
    if not clip.is_file() or not shutil.which("ffmpeg"):
        return None
    frames = "+".join(f"eq(n,{round(u * 300)})" for u in (.03, .15, .27, .4, .52, .65, .78, .93))
    target = out / "time.png"
    result = subprocess.run(["ffmpeg", "-y", "-hide_banner", "-loglevel", "error", "-i", str(clip), "-vf", f"select='{frames}',scale=270:-1,tile=8x1", "-frames:v", "1", str(target)], capture_output=True)
    return target if result.returncode == 0 and target.is_file() else None


def review(sheet: Path, topic: str, text: str, provider: str | None) -> Review | None:
    """The model looks at the sheet through the CLI's Read tool, confined to a temp folder that holds only the image. Failure is not fatal: the probe goes on without a review."""
    from brainrot import llm
    selected = provider or llm._job_provider.get() or "claude-code"
    if selected != "claude-code":
        say("review needs the Claude CLI (the image is read with its Read tool); skipped")
        return None
    try:
        command, env = llm._command("claude-code"), llm._environment()
        with tempfile.TemporaryDirectory(prefix="brainrot-review-") as directory:
            shutil.copy(sheet, Path(directory) / "sheet.png")
            timeline = sheet.parent / "time.png"
            if timeline.is_file():
                shutil.copy(timeline, Path(directory) / "time.png")
            llm._require_subscription("claude-code", command, directory, env)
            arguments = ["--safe-mode", "--print", "--output-format", "json", "--json-schema", json.dumps(llm._schema(Review)), "--system-prompt", REVIEW_RULES.format(topic=topic, text=text),
                         "--tools", "Read", "--allowedTools", "Read", "--strict-mcp-config", "--disable-slash-commands", "--no-session-persistence", "--max-turns", "6"]
            model = llm._model("claude-code", "strong")
            if model:
                arguments += ["--model", model]
            raw = llm._run([*command, *arguments], cwd=directory, env=env, timeout=600, prompt="Review sheet.png and time.png now." if timeline.is_file() else "Review sheet.png now.")
        envelope = json.loads(raw)
        data = envelope.get("structured_output") or json.loads(envelope["result"])
        return Review.model_validate(data, strict=True)
    except Exception as error:  # noqa: BLE001 - a review that cannot run must never lose the render
        say(f"review failed ({type(error).__name__}); continuing without it")
        return None


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--topic", required=True)
    ap.add_argument("--text", required=True, help="about 25 words of narration (10 s); only used as context")
    ap.add_argument("--stub", help="JSON file {\"code\": \"...\"} instead of calling the model (tests the rest)")
    ap.add_argument("--resume", action="store_true", help="skip the design call: take out/asset-probe/<topic>/designed.tsx as the first version and go straight to render, review and fix")
    ap.add_argument("--no-review", action="store_true")
    ap.add_argument("--video", action="store_true", help="also render a silent 10 s clip")
    ap.add_argument("--provider", choices=["claude-code", "codex", "anthropic"], default="claude-code")
    ap.add_argument("--scale", type=float, default=0.5, help="render scale (0.5 = 540x960)")
    args = ap.parse_args()

    out = OUT / slugify(args.topic)
    out.mkdir(parents=True, exist_ok=True)
    report = {"topic": args.topic, "calls": [], "rounds": []}
    started = time.time()
    designed_path = PROBE / "designed.tsx"
    code, feedback, calls = None, None, 0

    def write(code_: str) -> None:
        designed_path.write_text(code_, encoding="utf-8")
        (out / "designed.tsx").write_text(code_, encoding="utf-8")

    for attempt in range(3):
        if args.stub:
            code = json.loads(Path(args.stub).read_text(encoding="utf-8"))["code"]
            report["calls"].append("stub")
        elif args.resume and attempt == 0:
            code = (out / "designed.tsx").read_text(encoding="utf-8")
            report["calls"].append("resumed from designed.tsx")
            say("resuming from the existing designed.tsx (no design call)")
        else:
            if calls >= 4:
                break
            say("asking the model to design the assets..." if attempt == 0 else "asking the model to repair the file...")
            t = time.time()
            reply = design(args.topic, args.text, code, feedback, args.provider)
            calls += 1
            code = reply.code
            report["calls"].append({"kind": "design" if attempt == 0 else "repair", "seconds": round(time.time() - t), "notes": reply.notes})
        problems = check_code(code)
        if problems:
            say("static check failed: " + "; ".join(problems))
            report["rounds"].append({"static": problems})
            feedback = problems
            if args.stub:
                return 2
            continue
        write(code)
        say("rendering the shots...")
        ok, error = render(out, None, args.scale)
        if ok:
            break
        say("render failed: " + (error.splitlines()[-1][:200] if error else ""))
        report["rounds"].append({"render": error})
        feedback = ["the render failed with this error, fix the file: " + error[-900:]]
        if args.stub:
            return 3
    else:
        (out / "report.json").write_text(json.dumps(report, indent=1, ensure_ascii=False), encoding="utf-8")
        say("no renderable file after the repair rounds; see report.json")
        return 4

    sheet = make_sheet(out)
    say(f"sheet: {sheet}")
    clip_done = False
    if not args.stub and not args.no_review and calls < 4:
        say("rendering the clip so the review can judge the story and the motion...")
        clip_done = render(out, 10.0, args.scale)[0]
        if clip_done:
            make_time(out)
        verdict = review(sheet, args.topic, args.text, args.provider)
        report["review"] = verdict.model_dump() if verdict else None
        if verdict and verdict.verdict == "fix" and calls < 4:
            say("review found problems: " + " | ".join(verdict.problems))
            shutil.copy(sheet, out / "sheet-v1.png")
            report["first_version_code_kept"] = True
            try:
                patch = fix(args.topic, args.text, code, verdict.problems, args.provider)
                calls += 1
            except Exception as error:  # noqa: BLE001 - a fix round that fails must keep the first version and the report
                patch = None
                say(f"fix round failed ({type(error).__name__}); keeping the first version")
            if patch is not None:
                fixed, failed = apply_patch(code, patch)
                if failed:
                    say("some edits could not be applied: " + "; ".join(failed))
                problems = check_code(fixed) if fixed != code else ["no edit applied"]
                if problems:
                    say("fix round discarded; keeping the first version: " + "; ".join(problems))
                else:
                    write(fixed)
                    ok, error = render(out, None, args.scale)
                    if ok:
                        sheet = make_sheet(out)
                        report["calls"].append({"kind": "fix", "notes": patch.notes, "failed_edits": failed})
                        say(f"sheet after the fix round: {sheet}")
                        clip_done = render(out, 10.0, args.scale)[0]
                        if clip_done:
                            make_time(out)
                    else:
                        write(code)  # keep the first, good file for the clip
                        render(out, None, args.scale)
                        sheet = make_sheet(out)
                        say("the fixed file did not render; kept the first version")
    if args.video and not clip_done:
        say("rendering a silent 10 s clip...")
        ok, error = render(out, 10.0, args.scale)
        say("clip: " + str(out / "clip-silent.mp4") if ok else "clip failed: " + error[-300:])
    report["seconds"] = round(time.time() - started)
    report["model_calls"] = calls
    (out / "report.json").write_text(json.dumps(report, indent=1, ensure_ascii=False), encoding="utf-8")
    say(f"done in {report['seconds']} s, {calls} model calls. Open {sheet}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
