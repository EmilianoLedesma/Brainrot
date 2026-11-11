import pytest

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


def test_world_job_skips_background_directs_and_renders_the_world(fake_db, narration, monkeypatch):
    monkeypatch.setattr(story_script, "write_story", lambda topic: story_script.Story(title="T", script="Short. Story."))
    monkeypatch.setattr(pipeline, "pick_background", lambda story_id: pytest.fail("no background for the world edit"))
    monkeypatch.setattr(render, "render", lambda *a: pytest.fail("main render must not run"))
    monkeypatch.setattr(world_render, "seconds", lambda audio: 12.0)
    monkeypatch.setattr(pipeline.world_director, "direct", lambda topic, text, words, seconds: {"pack": "zebra"})
    monkeypatch.setattr(world_render, "render_video", lambda audio, words, title, text, plan: b"world-" + plan["pack"].encode())
    pipeline.run_brainrot({"id": "job-world", "kind": "brainrot", "params": {"topic": "t", "world": True}})
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

