"""Generate the zebra script with the real Brainrot storytelling call, grounded on the researched, sourced facts in reference.json.

Run from the repository root:
    $env:PYTHONPATH="."; uv run --locked python experiments/zebra-lowpoly/write_story.py
Writes story.json beside this file (title, script, generator, words, sources). Provider claude-code, default CLI model, level 30, factual.
"""

import json
from pathlib import Path

from brainrot import script

HERE = Path(__file__).resolve().parent
ref = json.loads((HERE / "reference.json").read_text(encoding="utf-8"))
names = {s["id"]: s["title"] for s in ref["sources"]}
context = ("Facts researched from the sources below. Use only these as specifics; do not add numbers, studies or anecdotes beyond them. "
           "A fact marked single rests on one industry source: say it plainly, without overclaiming.\n"
           + "\n".join(f"- {f['text']} [{', '.join(f['sources'])}]" + (f" ({f['note']})" if f.get("note") else "") for f in ref["facts"])
           + "\nSources: " + "; ".join(f"[{k}] {v}" for k, v in names.items()))

story = script.write_story(ref["topic"], provider="claude-code", brainrot_level=30, reference_context=context)
out = HERE / "story.json"
out.write_text(json.dumps({
    "title": story.title,
    "script": story.script,
    "generator": "brainrot.script.write_story(provider=claude-code, BRAINROT_CLAUDE_MODEL unset = CLI default model, brainrot_level=30, factual, reference_context from reference.json)",
    "words": len(story.script.split()),
    "sources": [s["url"] for s in ref["sources"]],
}, ensure_ascii=False, indent=1), encoding="utf-8")
print(out, len(story.script.split()), "words")
