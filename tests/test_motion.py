from brainrot import motion


def _words(text, step=0.5):
    return [{"text": w, "start": i * step, "end": i * step + 0.4} for i, w in enumerate(text.split())]


def test_plan_covers_the_narration_and_picks_spaced_keywords():
    words = _words("In 2019 scientists studied horses. " * 12 + "Biologists measured twenty one subspecies carefully.")
    seconds = words[-1]["end"]
    result = motion.plan(words, seconds)
    scenes = result["scenes"]
    assert scenes[0]["start"] == 0 and scenes[-1]["end"] == seconds
    assert all(a["end"] == b["start"] for a, b in zip(scenes, scenes[1:]))
    for scene in scenes:
        keywords = scene["keywords"]
        assert len(keywords) <= motion.MAX_KEYWORDS
        assert all(b["at"] - a["at"] >= motion.KEYWORD_GAP for a, b in zip(keywords, keywords[1:]))
        assert all(scene["start"] <= k["at"] < scene["end"] for k in keywords)


def _beat(scene, device, cue="", title="T", big="", items=(), values=(), highlight=-1):
    return motion.Beat(scene=scene, device=device, cue=cue, title=title, big=big, items=list(items), values=list(values), highlight=highlight)


def test_design_validates_and_attaches_devices(monkeypatch):
    words = _words("Scene zero words here. " * 3 + "Twenty one subspecies were compared closely. " * 3, step=2.0)
    scenes = [{"start": 0.0, "end": 20.0, "text": ""}, {"start": 20.0, "end": 40.0, "text": ""}, {"start": 40.0, "end": 60.0, "text": ""}]
    beats = [
        _beat(0, "stat", cue="zero words", big="21", title="subspecies"),
        _beat(1, "stat", big="9", title="repeat"),          # same device back to back: dropped
        _beat(2, "checklist", items=["a", "b"]),              # too few rows: dropped
        _beat(7, "stamp", title="Nope"),                      # unknown scene: dropped
    ]
    monkeypatch.setattr(motion.llm, "generate", lambda *a, **k: motion.Design(beats=beats))
    motion.design(scenes, words)
    assert scenes[0]["device"]["kind"] == "stat" and scenes[0]["device"]["at"] >= 0
    assert "device" not in scenes[1] and "device" not in scenes[2]
