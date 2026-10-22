from types import SimpleNamespace

from brainrot import repurpose


def test_selection_keeps_three_strong_distinct_moments_within_source(monkeypatch):
    spans = [(0, 100, 0.9), (50, 150, 0.8), (100, 210, 0.7), (220, 320, 0.6), (330, 430, 0.5), (500, 650, 1.0)]
    candidates = [repurpose.Moment(start_seconds=start, end_seconds=end, score=score, title=str(start), reason="Complete")
                  for start, end, score in spans]
    monkeypatch.setattr(repurpose.llm, "generate", lambda *args, **kwargs: SimpleNamespace(moments=candidates))
    result = repurpose.select_moments([{"start": 0, "end": 600, "text": "Source"}])
    assert [moment.start_seconds for moment in result] == [0, 100, 220]
