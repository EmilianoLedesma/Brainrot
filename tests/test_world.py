import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent))  # the shared world fixture lives beside the tests

from brainrot import pipeline, render, script as story_script, tts
from brainrot.domain.jobs import PermanentError
from brainrot.world import beats, catalog, director, script
from brainrot.world import render as world_render


def spoken(n=150):
    """n words, 0.4 s each, a sentence pause every 10 words."""
    out, t = [], 0.0
    for i in range(n):
        out.append({"text": f"word{i}" + ("." if i % 10 == 9 else ""), "start": round(t, 2), "end": round(t + 0.35, 2)})
        t += 0.4 + (0.5 if i % 10 == 9 else 0)
    return out


@pytest.fixture
def narration(monkeypatch):
    monkeypatch.setattr(tts, "narrate", lambda text, *, title: (b"mp3", [{"text": "w", "start": 0, "end": 1}]))


@pytest.mark.parametrize("pack_id", ["zebra", "birds"])
def test_packs_are_valid_and_expose_typed_answers(pack_id):
    pack = catalog.get(pack_id)
    assert catalog.check(pack) == []
    beat, first, nxt = director.models(pack)
    assert "events" in beat.model_fields and (("subject" in first.model_fields) == bool(pack.get("subject")))
    assert pack["hero"] in director.guidance(pack, "bird" if pack.get("subject") else None)


@pytest.mark.parametrize("pack_id", ["zebra", "birds"])
def test_director_defaults_obey_the_hard_rules_even_when_the_model_returns_nothing(pack_id):
    words = spoken()
    seconds = words[-1]["end"] + 0.4
    pack = catalog.get(pack_id)
    subject = {"id": pack["subject"]["candidates"][0], "why": "x"} if pack.get("subject") else None
    plan = director.plan(words, seconds, pack_id, asked=(subject, {}))
    scenes = plan["scenes"]
    assert scenes[0]["focus"] == scenes[-1]["focus"] == pack["hero"]
    assert scenes[0]["nature"] == "context" and scenes[0]["dist"] == "wide"
    assert all(len(s["notes"]) for s in scenes[:1])
    # stations never overlap actions: each next action starts after the previous one on the same station ended
    last = {}
    for s in scenes:
        for e in s["events"]:
            if e["kind"] == "action":
                dur = pack["actions"][e["target"]][e["action"]][0] / 30
                assert e["at"] >= last.get(e["target"], -1)
                last[e["target"]] = e["at"] + dur
    built = script.build(plan, "Title here", " ".join(w["text"] for w in words), words)
    assert script.problems(built) == []
    assert built["waypoints"][0]["at"] == 0 and len(built["captions"]) > 5


def test_unknown_pack_and_cue_misses_are_noted_not_fatal():
    with pytest.raises(PermanentError):
        catalog.get("nope")
    words = spoken()
    beat, first, nxt = director.models(catalog.get("zebra"))
    scenes = beats.split_long(beats.group(words, words[-1]["end"] + .4), words, 6.5)
    chosen = {1: beat(scene=1, focus="coat", nature="exhibit", shot={"dist": "wide", "angle": "front", "height": "mid", "move": "hold"}, show="s",
                      events=[{"kind": "action", "cue": "not in the beat", "term": "", "target": "", "action": "nothing"}], why="w")}
    plan = director.plan(words, words[-1]["end"] + .4, "zebra", asked=(None, chosen))
    notes = " ".join(n for s in plan["scenes"] for n in s["notes"])
    assert "not found in beat" in notes and "needs dist medium" in notes and len(scenes) == len(plan["scenes"])


def test_world_job_designs_before_narration_then_directs_and_renders(fake_db, monkeypatch):
    from world_fixture import world as fixture_world
    order = []
    monkeypatch.setattr(story_script, "write_story", lambda topic: story_script.Story(title="T", script="Short. Story."))
    monkeypatch.setattr(pipeline, "pick_background", lambda story_id: pytest.fail("no background for the world edit"))
    monkeypatch.setattr(render, "render", lambda *a: pytest.fail("main render must not run"))
    monkeypatch.setattr(tts, "narrate", lambda text, *, title: order.append("tts") or (b"mp3", [{"text": "w", "start": 0, "end": 1}]))
    monkeypatch.setattr(pipeline.world_design, "cached", lambda topic, text, *a: order.append("design") or fixture_world())
    monkeypatch.setattr(world_render, "seconds", lambda audio: 12.0)
    monkeypatch.setattr(pipeline.world_director, "direct", lambda topic, text, words, seconds, provider=None, world=None: order.append("direct") or {"pack": "generic", "world": world.model_dump()})
    monkeypatch.setattr(world_render, "render_video", lambda audio, words, title, text, plan: order.append("render") or b"world-" + plan["pack"].encode())
    pipeline.run_brainrot({"id": "job-world", "kind": "brainrot", "params": {"topic": "t", "world": True}})
    assert order == ["design", "tts", "direct", "render"]
    assert fake_db.rows("story_chapters")[0]["status"] == "ready"


def test_web_research_feeds_the_writer_once(fake_db, narration, monkeypatch):
    from brainrot import investigate
    seen = {}
    pack = investigate.ResearchPack(sources=[investigate.Source(id="s1", title="T", url="https://e.org/a", read="full")], facts=[investigate.Fact(text="f", sources=["s1"], note="")])
    monkeypatch.setattr(investigate, "run", lambda topic: pack)

    def write(topic, **options):
        seen.update(options)
        return story_script.Story(title="T", script="Short. Story.")

    monkeypatch.setattr(story_script, "write_story", write)
    monkeypatch.setattr(pipeline, "pick_background", lambda story_id: b"bg")
    monkeypatch.setattr(render, "render", lambda *a: b"video")
    pipeline.run_brainrot({"id": "job-research", "kind": "brainrot", "params": {"topic": "t", "web_research": True}})
    assert "Facts researched on the web" in seen["reference_context"]



# ---- the designed world (spec, design stage, director on a spec) ----------------------------------------------------------------------------------------

def fixture():
    from world_fixture import world
    return world()


def test_the_fixture_world_is_valid_and_maps_to_a_director_manifest():
    from brainrot.world import spec
    w = fixture()
    assert spec.check(w) == []
    pack = spec.to_pack(w)
    assert pack["hero"] == "boardwalk" and pack["stations"][0] == "boardwalk" and pack["opening"] == {"station_action": "sun_glare"}
    assert pack["nouns"]["inuit"] == "snow" and set(pack["cutaway_stations"]) == {"snow", "quartz", "uv"} and pack["subject"] is None


def test_spec_rejects_what_the_renderer_or_the_recipe_cannot_use():
    from brainrot.world import spec
    w = fixture()
    w.stations[3].actions[0].effects[0].color = "#E5333B"                 # a red ray: red is reserved for arrows
    w.stations[1].actions[0].effects.append(spec.Effect(type="move", piece="ghost", vec=[1, 0, 0]))
    w.stations[3].pieces[1].hidden, w.stations[3].actions[1].effects = True, [spec.Effect(type="glow", piece="lens")]  # hidden but never appears
    w.stations[2].ground, w.stations[4].ground = "grass", "water"        # four grounds
    w.stations[0].pieces = [p for p in w.stations[0].pieces if p.id == "walker"]; w.stations[0].pieces[0].scale = 1   # a hero made of one tiny person
    problems = " | ".join(spec.check(w))
    for expected in ("reserved", "unknown piece", "no action makes it appear", "at most three different grounds", "nothing readable"):
        assert expected in problems, expected


def test_director_directs_a_designed_world_and_the_script_carries_it():
    from brainrot.world import spec
    w = fixture()
    words = spoken()
    plan = director.plan(words, words[-1]["end"] + .4, spec.to_pack(w), asked=(None, {}), world=w.model_dump())
    built = script.build(plan, "Titulo", " ".join(x["text"] for x in words), words)
    assert plan["pack"] == "generic" and built["world"]["hero"] == "boardwalk" and script.problems(built) == []
    assert {a["target"] for a in built["actions"]} <= {s.id for s in w.stations}


def test_design_repairs_once_and_then_gives_up_with_a_friendly_error(monkeypatch, tmp_path):
    from brainrot import llm
    from brainrot.world import design, spec
    good, bad = fixture(), fixture()
    bad.hero = "nowhere"
    answers, prompts = [bad, good], []
    monkeypatch.setattr(llm, "generate", lambda system, user, output, **kw: prompts.append((user, kw)) or answers.pop(0))
    assert design.design("t", "text").hero == "boardwalk"
    assert len(prompts) == 2 and "hero 'nowhere'" in prompts[1][0] and all(kw["tier"] == "strong" for _, kw in prompts)
    answers[:] = [bad, bad]
    with pytest.raises(PermanentError, match="could not be designed"):
        design.design("t", "text")
    monkeypatch.setattr(design, "CACHE", tmp_path)
    answers[:] = [good]
    assert design.cached("t", "text").hero == "boardwalk" and design.cached("t", "text").hero == "boardwalk" and not answers  # the second call reads the cache
